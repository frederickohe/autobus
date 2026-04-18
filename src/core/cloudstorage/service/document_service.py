import os
import logging
import pickle
import threading
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import UploadFile
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.cloudstorage.model.aitrainingfilemodel import AITrainingFileModel
from core.cloudstorage.service.storageservice import StorageService
from core.agent.tools.rag.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for managing AI training documents and their processing.
    
    Handles:
    - Document uploads to cloud storage
    - Document metadata storage in database
    - Document processing and chunking
    - Retriever pickle file management
    """
    
    def __init__(self, db_session: Session):
        """Initialize document service.
        
        Args:
            db_session: SQLAlchemy database session for document operations
        """
        self.db_session = db_session
        self.storage_service = StorageService()
        self.docs_dir = "agent_outputs/docs_processed"
        os.makedirs(self.docs_dir, exist_ok=True)
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            add_start_index=True,
            strip_whitespace=True,
            separators=["\n\n", "\n", ".", " ", ""],
        )
    
    def upload_document(self, user_id: str, file: UploadFile) -> dict:
        """Upload a document for a user and process it.
        
        Args:
            user_id: ID of the user uploading the document
            file: UploadFile object from FastAPI
            
        Returns:
            dict: Document metadata including file_url, file_name, etc.
            
        Raises:
            Exception: If upload or processing fails
        """
        try:
            # Generate unique filename with user_id prefix
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_name = f"{user_id}_{timestamp}_{file.filename}"
            
            # Read file content
            file_content = file.file.read()
            file.file.seek(0)
            file_size = len(file_content)
            file_type = file.content_type or "application/octet-stream"
            
            # Upload to cloud storage
            file_url = self.storage_service.upload_file(
                file.file,
                file_name,
                content_type=file_type,
                subfolder="ai-training-files/"
            )
            
            # Create document record in database
            doc_record = AITrainingFileModel(
                user_id=user_id,
                file_name=file_name,
                file_url=file_url,
                subfolder="ai-training-files/",
                file_size=file_size,
                file_type=file_type
            )
            
            self.db_session.add(doc_record)
            self.db_session.commit()
            
            logger.info(f"Successfully uploaded document {file_name} for user {user_id}")
            
            # Extract content asynchronously to avoid blocking
            extract_thread = threading.Thread(
                target=self._extract_document_content,
                args=(doc_record.id, file_url, file_type)
            )
            extract_thread.daemon = True
            extract_thread.start()
            
            # Re-process user's documents for retriever
            self._reprocess_user_documents(user_id)
            
            return {
                "file_name": file_name,
                "file_url": file_url,
                "file_size": file_size,
                "file_type": file_type,
                "uploaded_at": doc_record.upload_timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error uploading document for user {user_id}: {str(e)}", exc_info=True)
            self.db_session.rollback()
            raise
    
    def get_user_documents(self, user_id: str) -> List[dict]:
        """Get all documents for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of document metadata dictionaries
        """
        try:
            documents = self.db_session.query(AITrainingFileModel).filter(
                AITrainingFileModel.user_id == user_id
            ).order_by(AITrainingFileModel.upload_timestamp.desc()).all()
            
            return [
                {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "file_url": doc.file_url,
                    "file_size": doc.file_size,
                    "file_type": doc.file_type,
                    "uploaded_at": doc.upload_timestamp.isoformat()
                }
                for doc in documents
            ]
        except Exception as e:
            logger.error(f"Error retrieving documents for user {user_id}: {str(e)}")
            return []
    
    def delete_document(self, user_id: str, doc_id: int) -> bool:
        """Delete a document for a user.
        
        Args:
            user_id: ID of the user
            doc_id: ID of the document to delete
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            doc = self.db_session.query(AITrainingFileModel).filter(
                AITrainingFileModel.id == doc_id,
                AITrainingFileModel.user_id == user_id
            ).first()
            
            if not doc:
                logger.warning(f"Document {doc_id} not found for user {user_id}")
                return False
            
            self.db_session.delete(doc)
            self.db_session.commit()
            
            # Re-process user's documents
            self._reprocess_user_documents(user_id)
            
            logger.info(f"Deleted document {doc_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting document {doc_id} for user {user_id}: {str(e)}")
            self.db_session.rollback()
            return False
    
    def _extract_document_content(self, doc_id: int, file_url: str, file_type: str) -> None:
        """Extract text content from a document and store in database.
        
        Runs in background thread to avoid blocking uploads.
        
        Args:
            doc_id: ID of the document record
            file_url: URL to download the document from
            file_type: MIME type of the document
        """
        try:
            logger.info(f"Extracting content from document {doc_id} at {file_url}")
            
            # Extract text content from the file
            content = DocumentProcessor.extract_text_from_url(file_url, file_type)
            
            if content:
                # Update the document record with extracted content
                from utilities.dbconfig import SessionLocal
                db_session = SessionLocal()
                try:
                    doc = db_session.query(AITrainingFileModel).filter(
                        AITrainingFileModel.id == doc_id
                    ).first()
                    if doc:
                        doc.content = content
                        doc.content_extracted = "success"
                        db_session.commit()
                        logger.info(f"Successfully extracted content for document {doc_id}: {len(content)} chars")
                    else:
                        logger.warning(f"Document {doc_id} not found in database")
                finally:
                    db_session.close()
            else:
                # Mark as failed if no content extracted
                from utilities.dbconfig import SessionLocal
                db_session = SessionLocal()
                try:
                    doc = db_session.query(AITrainingFileModel).filter(
                        AITrainingFileModel.id == doc_id
                    ).first()
                    if doc:
                        doc.content_extracted = "failed"
                        db_session.commit()
                        logger.warning(f"Failed to extract content for document {doc_id}")
                finally:
                    db_session.close()
        except Exception as e:
            logger.error(f"Error extracting content for document {doc_id}: {str(e)}", exc_info=True)
    
    def _reprocess_user_documents(self, user_id: str) -> None:
        """Reprocess all documents for a user and create retriever pickle.
        
        This should be called after uploading or deleting documents.
        
        Args:
            user_id: ID of the user
        """
        try:
            documents = self.db_session.query(AITrainingFileModel).filter(
                AITrainingFileModel.user_id == user_id
            ).all()
            
            if not documents:
                logger.info(f"No documents for user {user_id}, skipping processing")
                return
            
            # Create langchain Documents from database records with extracted content
            source_docs = []
            for doc in documents:
                # Use extracted content if available, otherwise use metadata
                if doc.content and doc.content.strip():
                    page_content = doc.content
                else:
                    # Fallback to metadata-only if content extraction hasn't completed yet
                    page_content = f"Document: {doc.file_name}\nFile Type: {doc.file_type}\nURL: {doc.file_url}"
                
                source_doc = Document(
                    page_content=page_content,
                    metadata={
                        "source": doc.file_name,
                        "file_url": doc.file_url,
                        "uploaded_at": doc.upload_timestamp.isoformat(),
                        "content_extracted": doc.content_extracted
                    }
                )
                source_docs.append(source_doc)
            
            # Split documents into chunks
            docs_processed = self.text_splitter.split_documents(source_docs)
            
            # Save processed documents for this user
            user_docs_path = os.path.join(self.docs_dir, f"{user_id}_docs_processed.pkl")
            with open(user_docs_path, "wb") as f:
                pickle.dump(docs_processed, f)
            
            logger.info(f"Processed {len(docs_processed)} chunks for user {user_id}, saved to {user_docs_path}")
            
        except Exception as e:
            logger.error(f"Error reprocessing documents for user {user_id}: {str(e)}", exc_info=True)
    
    def get_user_docs_path(self, user_id: str) -> str:
        """Get the path to the pickled documents for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            str: Path to the user's docs_processed.pkl file
        """
        return os.path.join(self.docs_dir, f"{user_id}_docs_processed.pkl")

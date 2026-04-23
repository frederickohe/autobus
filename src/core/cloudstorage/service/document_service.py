import os
import logging
import pickle
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import UploadFile
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.cloudstorage.model.aitrainingfilemodel import AITrainingFileModel
from core.cloudstorage.service.storageservice import StorageService
from core.cloudstorage.service.file_content_extractor import FileContentExtractor
from core.rag.embedding_service import EmbeddingService

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
            
            logger.info(
                f"[DOC UPLOAD] Starting upload - user_id={user_id}, "
                f"file_name={file_name}, size={file_size}, type={file_type}"
            )
            
            # Extract text content from the file
            extracted_content = FileContentExtractor.extract_content(file, file_content)
            
            logger.debug(
                f"[DOC UPLOAD] Content extraction - "
                f"success={extracted_content is not None}, "
                f"content_length={len(extracted_content) if extracted_content else 0}"
            )
            
            # Upload to cloud storage
            file_url = self.storage_service.upload_file(
                file.file,
                file_name,
                content_type=file_type,
                subfolder="ai-training-files/"
            )
            
            logger.info(f"[DOC UPLOAD] File uploaded to S3 - url={file_url}")
            
            # Create document record in database with extracted content
            doc_record = AITrainingFileModel(
                user_id=user_id,
                file_name=file_name,
                file_url=file_url,
                content=extracted_content,
                subfolder="ai-training-files/",
                file_size=file_size,
                file_type=file_type
            )
            
            self.db_session.add(doc_record)
            self.db_session.commit()
            
            doc_id = doc_record.id
            logger.info(
                f"[DOC UPLOAD] Document record created - id={doc_id}, user_id={user_id}"
            )
            
            if extracted_content:
                logger.info(
                    f"[DOC UPLOAD] Extracted {len(extracted_content)} characters from {file_name}"
                )
            else:
                logger.warning(f"[DOC UPLOAD] Could not extract content from {file_name}")
            
            # Generate embedding for RAG
            try:
                logger.info(f"[DOC UPLOAD] Generating embedding for doc_id={doc_id}")
                
                embedding_service = EmbeddingService()
                
                # Generate embedding from extracted content (or file_name if no content)
                content_to_embed = extracted_content if extracted_content else file_name
                embedding = embedding_service.generate_embedding(content_to_embed)
                
                # Store embedding in database
                doc_record.embedding = embedding
                self.db_session.commit()
                
                logger.info(
                    f"[DOC UPLOAD] Embedding generated and stored successfully - "
                    f"doc_id={doc_id}, dimensions={len(embedding)}"
                )
                
            except Exception as e:
                logger.error(
                    f"[DOC UPLOAD] Failed to generate embedding for doc_id={doc_id}: {str(e)}", 
                    exc_info=True
                )
                logger.info(
                    f"[DOC UPLOAD] Document stored without embedding. "
                    f"It will not be searchable via RAG until embedding is generated."
                )
            
            # Re-process user's documents for retriever
            self._reprocess_user_documents(user_id)
            
            logger.info(f"[DOC UPLOAD] Upload complete - doc_id={doc_id}, user_id={user_id}")
            
            return {
                "file_name": file_name,
                "file_url": file_url,
                "file_size": file_size,
                "file_type": file_type,
                "uploaded_at": doc_record.upload_timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(
                f"[DOC UPLOAD] Error uploading document for user {user_id}: {str(e)}", 
                exc_info=True
            )
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
            
            logger.info(
                f"[DOC UPLOAD] Retrieved {len(documents)} documents for user {user_id}"
            )
            
            result = []
            for doc in documents:
                has_embedding = doc.embedding is not None
                doc_info = {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "file_url": doc.file_url,
                    "file_size": doc.file_size,
                    "file_type": doc.file_type,
                    "uploaded_at": doc.upload_timestamp.isoformat(),
                    "has_embedding": has_embedding
                }
                result.append(doc_info)
                
                logger.debug(
                    f"[DOC UPLOAD] Document - id={doc.id}, name={doc.file_name}, "
                    f"has_embedding={has_embedding}"
                )
            
            return result
        except Exception as e:
            logger.error(
                f"[DOC UPLOAD] Error retrieving documents for user {user_id}: {str(e)}", 
                exc_info=True
            )
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
                logger.warning(
                    f"[DOC UPLOAD] Document not found - id={doc_id}, user_id={user_id}"
                )
                return False
            
            logger.info(
                f"[DOC UPLOAD] Deleting document - id={doc_id}, user_id={user_id}, "
                f"file_name={doc.file_name}"
            )
            
            self.db_session.delete(doc)
            self.db_session.commit()
            
            # Re-process user's documents
            self._reprocess_user_documents(user_id)
            
            logger.info(
                f"[DOC UPLOAD] Document deleted successfully - id={doc_id}, user_id={user_id}"
            )
            return True
            
        except Exception as e:
            logger.error(
                f"[DOC UPLOAD] Error deleting document - id={doc_id}, user_id={user_id}: {str(e)}", 
                exc_info=True
            )
            self.db_session.rollback()
            return False
    
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
            
            # Create langchain Documents with actual extracted content
            source_docs = []
            for doc in documents:
                # Use extracted content if available, otherwise use metadata
                page_content = doc.content if doc.content else f"Document: {doc.file_name}"
                
                source_doc = Document(
                    page_content=page_content,
                    metadata={
                        "source": doc.file_name,
                        "file_url": doc.file_url,
                        "file_type": doc.file_type,
                        "uploaded_at": doc.upload_timestamp.isoformat(),
                        "doc_id": doc.id
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

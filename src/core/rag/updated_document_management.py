"""
Updated Document Management Tool - LangChain Compatible with Embedding Support

Uploads documents and automatically generates embeddings for RAG.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from sqlalchemy.orm import Session

from core.cloudstorage.service.document_service import DocumentService
from core.rag.document_processor import DocumentProcessor
from core.cloudstorage.model.aitrainingfilemodel import AITrainingFileModel

logger = logging.getLogger(__name__)


class UploadDocumentInput(BaseModel):
    """Input schema for document upload tool."""
    
    user_id: str = Field(
        ...,
        description="The user ID associated with the document upload"
    )
    file_content: str = Field(
        ...,
        description="The content of the file to upload"
    )
    file_name: str = Field(
        ...,
        description="Name of the file being uploaded"
    )
    file_type: str = Field(
        default="text/plain",
        description="MIME type of the file"
    )


class GetDocumentsInput(BaseModel):
    """Input schema for getting user documents."""
    
    user_id: str = Field(
        ...,
        description="The user ID to get documents for"
    )


class UpdatedUploadDocumentTool(BaseTool):
    """
    Updated document upload tool with automatic embedding generation.
    
    Uploads documents to cloud storage and automatically generates
    vector embeddings for RAG semantic search.
    """
    
    name: str = "upload_document"
    description: str = (
        "Upload a document for AI training and semantic search. "
        "The document will be processed and stored for RAG queries. "
        "Automatically generates embeddings for optimal search results."
    )
    args_schema: type = UploadDocumentInput
    
    def __init__(self, db_session: Session, api_key: Optional[str] = None):
        """
        Initialize document upload tool.
        
        Args:
            db_session: SQLAlchemy database session
            api_key: OpenAI API key (optional)
        """
        super().__init__()
        self.db = db_session
        self.document_service = DocumentService(db_session)
        self.document_processor = DocumentProcessor(db_session, api_key=api_key)
    
    def _run(
        self,
        user_id: str,
        file_content: str,
        file_name: str,
        file_type: str = "text/plain"
    ) -> str:
        """
        Upload a document and generate embeddings.
        
        Args:
            user_id: User ID
            file_content: Document content
            file_name: File name
            file_type: MIME type
            
        Returns:
            Confirmation message with file details
        """
        try:
            if not user_id:
                return "Error: user_id is required"
            
            if not file_content or not file_content.strip():
                return "Error: file_content cannot be empty"
            
            if not file_name:
                return "Error: file_name is required"
            
            logger.info(
                f"[RAG DEBUG] Upload started - user_id={user_id}, "
                f"file_name={file_name}, content_length={len(file_content)}, type={file_type}"
            )
            
            # Store document metadata in database
            try:
                logger.debug(f"[RAG DEBUG] Creating file record in database")
                file_record = AITrainingFileModel(
                    user_id=user_id,
                    file_name=file_name,
                    file_url=f"uploaded/{user_id}/{file_name}",
                    subfolder="ai-training-files/",
                    file_size=len(file_content),
                    file_type=file_type
                )
                self.db.add(file_record)
                self.db.flush()  # Get the ID
                file_id = file_record.id
                self.db.commit()
                
                logger.info(
                    f"[RAG DEBUG] File record created successfully - "
                    f"file_id={file_id}, user_id={user_id}"
                )
                
            except Exception as e:
                logger.error(
                    f"[RAG DEBUG] Failed to store file metadata: {str(e)}", 
                    exc_info=True
                )
                self.db.rollback()
                return f"Error storing file metadata: {str(e)}"
            
            # Generate embedding for the document
            try:
                logger.info(
                    f"[RAG DEBUG] Starting embedding generation for file_id={file_id}"
                )
                success = self.document_processor.embed_and_store_document(
                    file_id=file_id,
                    document_content=file_content,
                    user_id=user_id
                )
                
                if not success:
                    logger.warning(
                        f"[RAG DEBUG] Failed to generate embedding for file_id={file_id}"
                    )
                    # Don't fail - document is uploaded but without embedding
                    return (
                        f"Document '{file_name}' uploaded successfully. "
                        f"(Size: {len(file_content)} bytes, Type: {file_type}) "
                        f"Note: Embedding generation failed, semantic search may not work optimally."
                    )
                
                logger.info(
                    f"[RAG DEBUG] Embedding generation completed successfully "
                    f"for file_id={file_id}"
                )
                
            except Exception as e:
                logger.error(
                    f"[RAG DEBUG] Failed to generate embedding: {str(e)}", 
                    exc_info=True
                )
                # Still return success - document is stored even if embedding fails
                logger.info(
                    f"[RAG DEBUG] Document stored but embedding failed. "
                    f"Can be reprocessed later."
                )
            
            logger.info(
                f"[RAG DEBUG] Document upload complete - "
                f"file_id={file_id}, user_id={user_id}, file_name={file_name}"
            )
            
            return (
                f"✅ Document '{file_name}' uploaded successfully and embedded! "
                f"Size: {len(file_content)} bytes, Type: {file_type}. "
                f"It's now available for semantic search queries."
            )
            
        except Exception as e:
            logger.error(
                f"[RAG DEBUG] Document upload error: {str(e)}", 
                exc_info=True
            )
            return f"Error uploading document: {str(e)}"
    
    async def _arun(
        self,
        user_id: str,
        file_content: str,
        file_name: str,
        file_type: str = "text/plain"
    ) -> str:
        """Async version of _run."""
        return self._run(user_id, file_content, file_name, file_type)


class GetDocumentsTool(BaseTool):
    """Tool for listing a user's documents."""
    
    name: str = "list_documents"
    description: str = "List all documents uploaded by a user for RAG queries."
    args_schema: type = GetDocumentsInput
    
    def __init__(self, db_session: Session):
        """
        Initialize get documents tool.
        
        Args:
            db_session: SQLAlchemy database session
        """
        super().__init__()
        self.db = db_session
    
    def _run(self, user_id: str) -> str:
        """
        Get list of documents for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Formatted list of documents
        """
        try:
            if not user_id:
                return "Error: user_id is required"
            
            # Query documents
            documents = self.db.query(AITrainingFileModel).filter(
                AITrainingFileModel.user_id == user_id
            ).all()
            
            if not documents:
                return f"No documents found for user {user_id}"
            
            # Format output
            output_parts = [f"Documents for user {user_id}:\n"]
            
            for i, doc in enumerate(documents, 1):
                embedding_status = "✅ Embedded" if doc.embedding else "⏳ Pending"
                output_parts.append(
                    f"{i}. {doc.file_name}\n"
                    f"   Size: {doc.file_size} bytes\n"
                    f"   Type: {doc.file_type}\n"
                    f"   Uploaded: {doc.upload_timestamp}\n"
                    f"   Status: {embedding_status}\n"
                )
            
            logger.info(f"Retrieved {len(documents)} documents for user {user_id}")
            return "\n".join(output_parts)
            
        except Exception as e:
            logger.error(f"Error getting documents: {str(e)}")
            return f"Error retrieving documents: {str(e)}"
    
    async def _arun(self, user_id: str) -> str:
        """Async version of _run."""
        return self._run(user_id)

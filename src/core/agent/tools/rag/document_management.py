from smolagents import Tool
import logging
from sqlalchemy.orm import Session
from typing import Optional

from core.cloudstorage.service.document_service import DocumentService

logger = logging.getLogger(__name__)


class UploadDocumentTool(Tool):
    """Tool for uploading training documents to the system.
    
    Allows users to upload documents that will be used by the retriever
    for RAG (Retrieval Augmented Generation) operations.
    """
    
    name = "upload_document"
    description = "Upload a document for AI training and retrieval. The document will be stored and processed for use in semantic search queries."
    inputs = {
        "user_id": {
            "type": "string",
            "description": "The user ID associated with the document upload",
        },
        "file_path": {
            "type": "string",
            "description": "Path to the document file to upload",
        }
    }
    output_type = "string"
    
    def __init__(self, db_session: Optional[Session] = None, **kwargs):
        super().__init__(**kwargs)
        self.db_session = db_session
        self.document_service = DocumentService(db_session) if db_session else None
    
    def forward(self, user_id: str, file_path: str) -> str:
        """Upload a document for a user.
        
        Args:
            user_id: The user ID
            file_path: Path to the file to upload
            
        Returns:
            str: Confirmation message with file details
        """
        if not self.document_service:
            return "Error: Document service not initialized"
        
        try:
            # Open file and upload
            with open(file_path, 'rb') as f:
                # We need to create a file-like object that mimics FastAPI's UploadFile
                class SimpleUploadFile:
                    def __init__(self, file_obj, filename):
                        self.file = file_obj
                        self.filename = filename
                        self.content_type = "application/octet-stream"
                
                upload_file = SimpleUploadFile(f, file_path.split('/')[-1])
                result = self.document_service.upload_document(user_id, upload_file)
            
            logger.info(f"Document uploaded successfully for user {user_id}")
            return f"Document '{result['file_name']}' uploaded successfully. Size: {result['file_size']} bytes, Type: {result['file_type']}"
            
        except FileNotFoundError:
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error uploading document: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg


class GetDocumentsTool(Tool):
    """Tool for retrieving list of uploaded documents for a user."""
    
    name = "get_documents"
    description = "Retrieve list of all documents uploaded by a user for training and retrieval."
    inputs = {
        "user_id": {
            "type": "string",
            "description": "The user ID to get documents for",
        }
    }
    output_type = "string"
    
    def __init__(self, db_session: Optional[Session] = None, **kwargs):
        super().__init__(**kwargs)
        self.db_session = db_session
        self.document_service = DocumentService(db_session) if db_session else None
    
    def forward(self, user_id: str) -> str:
        """Get all documents for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            str: Formatted list of documents
        """
        if not self.document_service:
            return "Error: Document service not initialized"
        
        try:
            documents = self.document_service.get_user_documents(user_id)
            
            if not documents:
                return f"No documents found for user {user_id}"
            
            doc_list = "Documents for user " + user_id + ":\n"
            for doc in documents:
                doc_list += f"\n- {doc['file_name']} ({doc['file_size']} bytes, {doc['file_type']})"
                doc_list += f"\n  Uploaded: {doc['uploaded_at']}"
            
            return doc_list
            
        except Exception as e:
            error_msg = f"Error retrieving documents: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg


class DeleteDocumentTool(Tool):
    """Tool for deleting uploaded documents."""
    
    name = "delete_document"
    description = "Delete an uploaded document by its ID."
    inputs = {
        "user_id": {
            "type": "string",
            "description": "The user ID",
        },
        "doc_id": {
            "type": "integer",
            "description": "The document ID to delete",
        }
    }
    output_type = "string"
    
    def __init__(self, db_session: Optional[Session] = None, **kwargs):
        super().__init__(**kwargs)
        self.db_session = db_session
        self.document_service = DocumentService(db_session) if db_session else None
    
    def forward(self, user_id: str, doc_id: int) -> str:
        """Delete a document for a user.
        
        Args:
            user_id: The user ID
            doc_id: The document ID to delete
            
        Returns:
            str: Confirmation message
        """
        if not self.document_service:
            return "Error: Document service not initialized"
        
        try:
            success = self.document_service.delete_document(user_id, doc_id)
            
            if success:
                return f"Document {doc_id} deleted successfully"
            else:
                return f"Document {doc_id} not found for user {user_id}"
                
        except Exception as e:
            error_msg = f"Error deleting document: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg

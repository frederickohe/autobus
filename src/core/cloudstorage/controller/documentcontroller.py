from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import logging

from utilities.dbconfig import get_db
from core.cloudstorage.service.document_service import DocumentService
from core.cloudstorage.dto.document_dto import (
    DocumentUploadResponseDTO,
    DocumentListResponseDTO,
    DocumentDeleteRequestDTO,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload/{user_id}", response_model=DocumentUploadResponseDTO)
async def upload_document(
    user_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a document for AI training and retrieval.
    
    Args:
        user_id: The user ID uploading the document
        file: The document file to upload
        db: Database session
        
    Returns:
        DocumentUploadResponseDTO with file details
    """
    try:
        doc_service = DocumentService(db)
        result = doc_service.upload_document(user_id, file)
        
        return DocumentUploadResponseDTO(
            success=True,
            message=f"Document '{result['file_name']}' uploaded successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error uploading document for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")


@router.get("/user/{user_id}", response_model=DocumentListResponseDTO)
async def get_user_documents(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get all documents uploaded by a user.
    
    Args:
        user_id: The user ID
        db: Database session
        
    Returns:
        DocumentListResponseDTO with list of documents
    """
    try:
        doc_service = DocumentService(db)
        documents = doc_service.get_user_documents(user_id)
        
        return DocumentListResponseDTO(
            success=True,
            message=f"Retrieved {len(documents)} documents for user {user_id}",
            data=documents
        )
    except Exception as e:
        logger.error(f"Error retrieving documents for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")


@router.delete("/user/{user_id}/document/{doc_id}")
async def delete_document(
    user_id: str,
    doc_id: int,
    db: Session = Depends(get_db)
):
    """Delete a document uploaded by a user.
    
    Args:
        user_id: The user ID
        doc_id: The document ID to delete
        db: Database session
        
    Returns:
        Success/failure message
    """
    try:
        doc_service = DocumentService(db)
        success = doc_service.delete_document(user_id, doc_id)
        
        if success:
            return {
                "success": True,
                "message": f"Document {doc_id} deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {doc_id} for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

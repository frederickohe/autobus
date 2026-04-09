from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class DocumentMetadataDTO(BaseModel):
    """DTO for document metadata."""
    id: int
    file_name: str
    file_url: str
    file_size: int
    file_type: str
    uploaded_at: str


class DocumentUploadResponseDTO(BaseModel):
    """DTO for document upload response."""
    success: bool
    message: str
    data: Dict[str, Any]


class DocumentListResponseDTO(BaseModel):
    """DTO for document list response."""
    success: bool
    message: str
    data: List[DocumentMetadataDTO]


class DocumentDeleteRequestDTO(BaseModel):
    """DTO for document deletion request."""
    doc_id: int

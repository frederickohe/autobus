from pydantic import BaseModel
from typing import Optional


class FileDTO(BaseModel):
    file_name: str
    file_url: str
    folder: Optional[str] = None
    object_key: Optional[str] = None


class FileUploadRagResponse(FileDTO):
    """Response for authenticated upload + optional Qdrant indexing."""

    rag_indexed_chunks: int = 0
    rag_detail: Optional[str] = None

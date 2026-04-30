from pydantic import BaseModel
from typing import Optional

class FileDTO(BaseModel):
    file_name: str
    file_url: str
    folder: Optional[str] = None
    object_key: Optional[str] = None

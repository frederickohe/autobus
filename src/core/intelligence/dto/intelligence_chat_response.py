from typing import List, Optional

from pydantic import BaseModel, Field


class IntelligenceChatResponse(BaseModel):
    message: str
    success: bool = True
    used_llm: bool = False
    sources: List[str] = Field(default_factory=list)
    snapshot: Optional[dict] = None

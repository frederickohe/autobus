from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class OnboardingQuestion(BaseModel):
    id: str
    prompt: str
    hint: str = ""
    placeholder: str = ""
    multiline: bool = True
    required: bool = True


class OnboardingProfileResponse(BaseModel):
    completed: bool
    profile: Dict[str, Any]
    questions: List[OnboardingQuestion]
    indexed_chunks: Optional[int] = None
    rag_detail: Optional[str] = None

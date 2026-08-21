from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class NLURequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=15, description="User's phone number")
    message: str = Field(..., min_length=1, max_length=1000, description="User message to process")
    
    class Config:
        json_schema_extra = {
            "example": {
                "phone": "0234567890",
                "message": "I want to send 50 cedis to 0234567890"
            }
        }


class NLUDetectRequest(BaseModel):
    """Classify a message with the intent engine without running NLU handlers."""

    message: str = Field(..., min_length=1, max_length=8000)
    current_intent: Optional[str] = None
    conversation: Optional[List[Dict[str, str]]] = None
from pydantic import BaseModel
from typing import Optional, Dict, Any

class PaystackInitializeResponse(BaseModel):
    status: bool
    message: str
    authorization_url: Optional[str] = None
    access_code: Optional[str] = None
    reference: Optional[str] = None
    
class PaystackVerifyResponse(BaseModel):
    status: bool
    message: str
    data: Optional[Dict[str, Any]] = None
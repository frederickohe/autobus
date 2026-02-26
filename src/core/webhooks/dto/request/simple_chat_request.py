from pydantic import BaseModel


class SimpleChatRequest(BaseModel):
    """DTO for simple direct chat requests from Flutter app"""
    userid: str
    message: str

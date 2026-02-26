from pydantic import BaseModel


class SimpleChatResponse(BaseModel):
    """DTO for simple direct chat response to Flutter app"""
    message: str

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class ConversationSummaryDTO(BaseModel):
    id: int
    conversation_id: Optional[str] = None
    user_id: str
    user_fullname: Optional[str] = None
    conversation_date: date
    conversation_lifecycle: str
    intervention_active: bool = False
    intervention_id: Optional[int] = None
    intervention_reason: Optional[str] = None
    current_intent: Optional[str] = None
    last_message: Optional[str] = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationListResponseDTO(BaseModel):
    completed: List[ConversationSummaryDTO]
    intervention_active: List[ConversationSummaryDTO]


class ConversationDetailDTO(BaseModel):
    """Full conversation session including message history."""

    id: int
    conversation_id: Optional[str] = None
    user_id: str
    user_fullname: Optional[str] = None
    conversation_date: date
    conversation_lifecycle: str
    intervention_active: bool = False
    intervention_id: Optional[int] = None
    intervention_reason: Optional[str] = None
    current_intent: Optional[str] = None
    conversation_history: List[dict] = []
    collected_slots: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

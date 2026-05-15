from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from core.conversationmanager.dto.conversation_response_dto import ConversationSummaryDTO
from core.nlu.model.Conversation import DailyConversation
from core.user.model.User import User


class ConversationListService:
    def __init__(self, db: Session):
        self.db = db

    def list_grouped_conversations(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ConversationSummaryDTO], List[ConversationSummaryDTO]]:
        completed_rows = self._query_completed(skip=skip, limit=limit).all()
        intervention_rows = self._query_intervention_active(skip=skip, limit=limit).all()

        user_names = self._load_user_fullnames(
            {row.user_id for row in completed_rows} | {row.user_id for row in intervention_rows}
        )

        completed = [self._to_summary(row, user_names) for row in completed_rows]
        intervention_active = [self._to_summary(row, user_names) for row in intervention_rows]
        return completed, intervention_active

    def _query_completed(self, skip: int, limit: int):
        return (
            self.db.query(DailyConversation)
            .filter(
                DailyConversation.conversation_state["conversation_lifecycle"].astext == "completed"
            )
            .order_by(DailyConversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )

    def _query_intervention_active(self, skip: int, limit: int):
        return (
            self.db.query(DailyConversation)
            .filter(
                DailyConversation.conversation_state["intervention_active"].astext == "true"
            )
            .order_by(DailyConversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )

    def _load_user_fullnames(self, user_ids: set) -> Dict[str, str]:
        if not user_ids:
            return {}
        users = (
            self.db.query(User)
            .filter(User.phone.in_(list(user_ids)))
            .all()
        )
        return {user.phone: user.fullname for user in users if user.phone}

    def _to_summary(
        self, row: DailyConversation, user_names: Dict[str, str]
    ) -> ConversationSummaryDTO:
        state = row.conversation_state or {}
        history = state.get("conversation_history") or []
        last_message = self._last_message(history)

        return ConversationSummaryDTO(
            id=row.id,
            conversation_id=state.get("conversation_id"),
            user_id=row.user_id,
            user_fullname=user_names.get(row.user_id),
            conversation_date=row.conversation_date,
            conversation_lifecycle=state.get("conversation_lifecycle", "active"),
            intervention_active=bool(state.get("intervention_active", False)),
            intervention_id=state.get("intervention_id"),
            intervention_reason=state.get("intervention_reason"),
            current_intent=state.get("current_intent") or None,
            last_message=last_message,
            message_count=len(history),
            created_at=row.created_at or datetime.utcnow(),
            updated_at=row.updated_at or datetime.utcnow(),
        )

    @staticmethod
    def _last_message(history: list) -> Optional[str]:
        if not history:
            return None
        content = history[-1].get("content")
        if content is None:
            return None
        text = str(content)
        return text[:500] if len(text) > 500 else text

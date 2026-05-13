from typing import Optional

from sqlalchemy.orm import Session

from core.chatwoot.model.ChatwootAccount import ChatwootAccount
from utilities.crypto import decrypt_secret


class ChatwootOrgService:
    """User-scoped Chatwoot tenant mapping (mirrors `PostizOrgService`)."""

    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, user_id: str) -> Optional[ChatwootAccount]:
        return (
            self.db.query(ChatwootAccount)
            .filter(ChatwootAccount.user_id == user_id)
            .first()
        )

    def get_user_access_token(self, user_id: str) -> Optional[str]:
        row = self.get_for_user(user_id)
        if not row:
            return None
        return decrypt_secret(row.chatwoot_user_access_token_encrypted)

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from core.socialmedia.model.PostizOrganization import PostizOrganization
from utilities.crypto import decrypt_secret


class PostizOrgService:
    def __init__(self, db: Session):
        self.db = db

    def get_for_user(self, user_id: str) -> Optional[PostizOrganization]:
        return (
            self.db.query(PostizOrganization)
            .filter(PostizOrganization.user_id == user_id)
            .first()
        )

    def get_public_api_key_for_user(self, user_id: str) -> Optional[str]:
        org = self.get_for_user(user_id)
        if not org:
            return None
        return decrypt_secret(org.postiz_public_api_key_encrypted)


import logging
from typing import Optional

from sqlalchemy.orm import Session

from core.nlu.nlu import get_nlu_system

logger = logging.getLogger(__name__)


class AutoBus:
    """Compatibility shim. Chat goes through NLU, not an agent loop."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session

    def process_user_message(
        self,
        userid: str,
        message: str,
        agent_name: str = "",
        db_session: Optional[Session] = None,
    ) -> str:
        try:
            return get_nlu_system().process_message(userid, message)
        except Exception as e:
            logger.error("Error processing message for user %s: %s", userid, e, exc_info=True)
            return "Sorry, I could not process your message. Please try again."

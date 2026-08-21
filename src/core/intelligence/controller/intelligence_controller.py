import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from another_fastapi_jwt_auth import AuthJWT

from core.auth.dependencies import get_current_user, get_db, validate_token
from core.intelligence.dto.intelligence_chat_request import IntelligenceChatRequest
from core.intelligence.dto.intelligence_chat_response import IntelligenceChatResponse
from core.intelligence.service.owner_copilot_service import OwnerCopilotService
from core.user.model.User import User

logger = logging.getLogger(__name__)

intelligence_routes = APIRouter()


@intelligence_routes.post("/chat", response_model=IntelligenceChatResponse)
def owner_intelligence_chat(
    request: IntelligenceChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    """
    Authenticated owner copilot. Answers from this merchant's live profile,
    indexed knowledge, products, orders, and inbox — not the public customer webhook.
    """
    try:
        service = OwnerCopilotService(db)
        result = service.chat(current_user, request.message)

        return IntelligenceChatResponse(
            message=result.message,
            success=True,
            used_llm=result.used_llm,
            sources=result.sources,
            snapshot=result.snapshot or None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[MY_AI] chat failed for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing your business AI message",
        )

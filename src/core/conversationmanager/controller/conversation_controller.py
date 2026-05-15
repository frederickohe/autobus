import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from another_fastapi_jwt_auth import AuthJWT

from core.conversationmanager.dto.conversation_response_dto import ConversationListResponseDTO
from core.conversationmanager.service.conversation_list_service import ConversationListService
from core.user.controller.usercontroller import get_db, validate_token

logger = logging.getLogger(__name__)

conversation_routes = APIRouter()


@conversation_routes.get("", response_model=ConversationListResponseDTO)
def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    """
    List conversations grouped for the admin inbox:
    - completed: sessions with conversation_lifecycle == completed
    - intervention_active: sessions where a human agent handover is active
    """
    _ = authjwt
    try:
        service = ConversationListService(db)
        completed, intervention_active = service.list_grouped_conversations(
            skip=skip, limit=limit
        )
        logger.info(
            "[CONVERSATION_CONTROLLER] Listed conversations completed=%s intervention_active=%s",
            len(completed),
            len(intervention_active),
        )
        return ConversationListResponseDTO(
            completed=completed,
            intervention_active=intervention_active,
        )
    except Exception as e:
        logger.error(
            "[CONVERSATION_CONTROLLER] Error listing conversations: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving conversations: {str(e)}",
        )

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from another_fastapi_jwt_auth import AuthJWT

from core.auth.dependencies import get_current_user, get_db, validate_token
from core.intelligence.dto.agent_turn import AgentTurnRequest, AgentTurnResponse
from core.intelligence.dto.intelligence_chat_request import IntelligenceChatRequest
from core.intelligence.dto.intelligence_chat_response import IntelligenceChatResponse
from core.intelligence.dto.onboarding_request import OnboardingSubmitRequest
from core.intelligence.dto.onboarding_response import OnboardingProfileResponse
from core.intelligence.service.onboarding_index_service import OnboardingIndexService
from core.intelligence.service.owner_agent_service import OwnerAgentService
from core.intelligence.service.owner_copilot_service import OwnerCopilotService
from core.user.model.User import User

logger = logging.getLogger(__name__)

intelligence_routes = APIRouter()


@intelligence_routes.get("/onboarding", response_model=OnboardingProfileResponse)
def get_business_onboarding(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    """Return the signup questionnaire and any saved business-profile answers."""
    return OnboardingIndexService(db).get_profile(current_user)


@intelligence_routes.post("/onboarding", response_model=OnboardingProfileResponse)
def submit_business_onboarding(
    request: OnboardingSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    """
    Save the owner's onboarding Q&A and index it into Qdrant intelligence
    so the public webhook can answer business questions without a website
    or uploaded documents. Does not require an active subscription.
    """
    try:
        return OnboardingIndexService(db).submit(current_user, request.answers)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "[ONBOARDING] submit failed for user %s: %s",
            current_user.id,
            e,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save and index your business profile",
        )


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


@intelligence_routes.post("/agent", response_model=AgentTurnResponse)
def owner_agent_turn(
    request: AgentTurnRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    """Authenticated owner agent: tools, media asks, and confirmation before writes."""
    try:
        return OwnerAgentService(db).turn(current_user, request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[OWNER_AGENT] turn failed for user %s: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error running your business agent",
        )

from fastapi import APIRouter, Depends, HTTPException
from another_fastapi_jwt_auth import AuthJWT
from sqlalchemy.orm import Session
from core.agent.dto.commandreqeust import CommandRequest
from core.auth.dependencies import validate_token, get_current_user, get_db
from core.user.model.User import User
from core.agent.agent import AutoBus
from core.agent.dto.media_generation_request import MediaGenerationRequest
from core.credits.model.credit_types import CreditType
from core.credits.service.credit_service import CreditService
from core.media.controller.media_controller import generate_image, generate_video
from core.media.dto.media_generation_response import ImageGenerationResponse, VideoGenerationResponse
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

_autobus_agent_instance = None


def get_autobus_agent():
    """Lazy initialization of AutoBus agent. Only created on first use."""
    global _autobus_agent_instance
    if _autobus_agent_instance is None:
        logger.info("Lazy initializing AutoBus agent on first use...")
        _autobus_agent_instance = AutoBus()
    return _autobus_agent_instance


agent_routes = APIRouter()


@agent_routes.post("/command")
def agent(
    query: CommandRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    """Authenticated agent command. Caller may only act as themselves."""
    allowed_ids = {x for x in (current_user.id, current_user.phone, current_user.email) if x}
    if query.userid not in allowed_ids:
        raise HTTPException(status_code=403, detail="Cannot invoke agent as another user")

    credit_service = CreditService(db)
    credit_service.require_credits(current_user.id, CreditType.LLM.value, 1.0, "agent_command")

    assistant = get_autobus_agent()
    response_text = assistant.process_user_message(
        userid=query.userid,
        message=query.message,
        agent_name=query.agent_name,
        db_session=db,
    )
    return {"response": response_text}


@agent_routes.post("/generate-image", response_model=ImageGenerationResponse)
async def agent_generate_image(
    req: MediaGenerationRequest,
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    return await generate_image(req, db=db, authjwt=authjwt)


@agent_routes.post("/generate-video", response_model=VideoGenerationResponse)
async def agent_generate_video(
    req: MediaGenerationRequest,
    store: bool = False,
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    return await generate_video(req, store=store, db=db, authjwt=authjwt)

from fastapi import APIRouter, Depends, HTTPException
from another_fastapi_jwt_auth import AuthJWT
from sqlalchemy.orm import Session
from core.agent.dto.commandreqeust import CommandRequest
from core.auth.dependencies import validate_token, get_current_user, get_db
from core.user.model.User import User
from core.agent.dto.media_generation_request import MediaGenerationRequest
from core.credits.model.credit_types import CreditType
from core.credits.service.credit_service import CreditService
from core.media.controller.media_controller import generate_image, generate_video
from core.media.dto.media_generation_response import ImageGenerationResponse, VideoGenerationResponse
from core.nlu.config import SYSTEM_PROMPTS
from core.nlu.nlu import get_nlu_system
from utilities.plain_text import strip_markdown_formatting
import logging

logger = logging.getLogger(__name__)

MARKETING_AGENT_NAMES = frozenset({
    "marketing",
    "digital_marketing",
    "digital-marketing",
    "digital_margeting",
})

agent_routes = APIRouter()


@agent_routes.post("/command")
def agent(
    query: CommandRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    authjwt: AuthJWT = Depends(validate_token),
):
    """Authenticated command. Marketing copy uses a single LLM call; everything else uses NLU."""
    allowed_ids = {x for x in (current_user.id, current_user.phone, current_user.email) if x}
    if query.userid not in allowed_ids:
        raise HTTPException(status_code=403, detail="Cannot invoke agent as another user")

    credit_service = CreditService(db)
    credit_service.require_credits(current_user.id, CreditType.LLM.value, 1.0, "agent_command")

    if _is_marketing_agent(query.agent_name):
        return {"response": _generate_marketing_content(query.message)}

    response_text = get_nlu_system().process_message(query.userid, query.message)
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


def _is_marketing_agent(agent_name: str) -> bool:
    return (agent_name or "").strip().lower() in MARKETING_AGENT_NAMES


def _generate_marketing_content(prompt: str) -> str:
    from core.nlu.service.llmclient import LLMClient

    user_message = (prompt or "").strip()
    if not user_message:
        return "Please provide a short description of what you want to promote."

    response = LLMClient().chat_completion(
        system_prompt=SYSTEM_PROMPTS["marketing"],
        user_message=user_message,
        conversation_history=None,
        temperature=0.8,
        max_tokens=800,
    )
    if not response:
        return "Sorry, I could not generate marketing text right now. Please try again."
    return strip_markdown_formatting(response)

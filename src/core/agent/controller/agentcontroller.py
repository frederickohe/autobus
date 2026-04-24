from fastapi import APIRouter, Depends, HTTPException, Form
from starlette.responses import PlainTextResponse
from another_fastapi_jwt_auth import AuthJWT
from another_fastapi_jwt_auth.exceptions import MissingTokenError
import jwt
from sqlalchemy.orm import Session
from core.agent.dto.commandreqeust import CommandRequest
from core.exceptions import *
from core.auth.dto.request.user_create import UserCreateRequest
from core.auth.service.authservice import AuthService
from utilities.dbconfig import SessionLocal
from core.agent.agent import AutoBus
from core.agent.dto.media_generation_request import MediaGenerationRequest
from core.agent.tools.google_image.google_image_service import GoogleImageService, GoogleImageGenerationError
from core.agent.tools.google_veo.google_veo_service import GoogleVeoService, GoogleVeoGenerationError
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Lazy initialization - only create the agent when first needed
_autobus_agent_instance = None

def get_autobus_agent():
    """Lazy initialization of AutoBus agent. Only created on first use."""
    global _autobus_agent_instance
    if _autobus_agent_instance is None:
        logger.info("Lazy initializing AutoBus agent on first use...")
        _autobus_agent_instance = AutoBus()
    return _autobus_agent_instance

def validate_token(authjwt: AuthJWT = Depends()):
    try:
        authjwt.jwt_required()
        return authjwt
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401, 
            detail="Token expired. Please log in again."
        )
    except MissingTokenError:
        raise HTTPException(
            status_code=401,
            detail="No token found. Please create an account and log in.",
        )
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
agent_routes = APIRouter()

@agent_routes.post("/command")
def agent(query: CommandRequest, db: Session = Depends(get_db)):
    assistant = get_autobus_agent()
    
    return assistant.process_user_message(
        userid=query.userid,
        message=query.message,
        agent_name=query.agent_name
    )


@agent_routes.post("/generate-image", response_class=PlainTextResponse)
async def generate_image(req: MediaGenerationRequest):
    try:
        service = GoogleImageService()
        b64 = await service.generate_image_base64(req.prompt, user_id=req.user_id)
        return PlainTextResponse(content=b64, media_type="text/plain")
    except GoogleImageGenerationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Image generation failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Image generation failed")


@agent_routes.post("/generate-video", response_class=PlainTextResponse)
async def generate_video(req: MediaGenerationRequest):
    try:
        service = GoogleVeoService()
        url = await service.generate_video_and_store(req.prompt, user_id=req.user_id)
        return PlainTextResponse(content=url, media_type="text/plain")
    except GoogleVeoGenerationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Video generation failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Video generation failed")
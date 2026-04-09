from fastapi import APIRouter, Depends, HTTPException, Form
from another_fastapi_jwt_auth import AuthJWT
from another_fastapi_jwt_auth.exceptions import MissingTokenError
import jwt
from sqlalchemy.orm import Session
from core.agent.dto.commandreqeust import CommandRequest
from core.exceptions import *
from core.auth.dto.request.user_create import UserCreateRequest
from core.auth.service.authservice import AuthService
from utilities.dbconfig import SessionLocal
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Lazy load AutoBus to avoid 26s startup delay
_autobus_cache = None

def get_autobus():
    global _autobus_cache
    if _autobus_cache is None:
        logger.info("Initializing AutoBus agent (lazy load)...")
        from core.agent.agent import AutoBus
        _autobus_cache = AutoBus()
    return _autobus_cache

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

    assistant = get_autobus()
    
    return assistant.process_user_message(
        userid=query.userid,
        message=query.message,
        agent_name=query.agent_name
    )
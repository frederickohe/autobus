"""Shared auth / authorization FastAPI dependencies."""

from __future__ import annotations

import logging
from typing import Optional, Set

from another_fastapi_jwt_auth import AuthJWT
from another_fastapi_jwt_auth.exceptions import MissingTokenError
from fastapi import Depends, HTTPException, status
import jwt
from sqlalchemy.orm import Session

from config import settings
from core.user.model.User import User
from utilities.dbconfig import SessionLocal

logger = logging.getLogger(__name__)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_token(authjwt: AuthJWT = Depends()) -> AuthJWT:
    try:
        authjwt.jwt_required()
        return authjwt
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired. Please log in again.",
        )
    except MissingTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No token found. Please create an account and log in.",
        )
    except Exception as e:
        logger.error("Token validation error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def _admin_id_set() -> Set[str]:
    raw = (
        getattr(settings, "ADMIN_USER_IDS", "")
        or getattr(settings, "ADMIN_NOTIFICATION_USER_IDS", "")
        or ""
    )
    return {p.strip() for p in str(raw).split(",") if p.strip()}


def _admin_email_set() -> Set[str]:
    raw = getattr(settings, "ADMIN_EMAILS", "") or ""
    return {p.strip().lower() for p in str(raw).split(",") if p.strip()}


def get_jwt_claims(authjwt: AuthJWT) -> dict:
    try:
        raw = authjwt.get_raw_jwt()
        if isinstance(raw, dict) and raw:
            return raw
    except Exception:
        logger.debug("Could not read raw JWT claims", exc_info=True)
    token = getattr(authjwt, "_token", None)
    if token:
        try:
            return jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[getattr(settings, "ALGORITHM", "HS256")],
            )
        except Exception:
            logger.debug("Could not decode JWT for mgr claim", exc_info=True)
    return {}


def get_manager_id_from_jwt(authjwt: AuthJWT) -> Optional[str]:
    mgr = get_jwt_claims(authjwt).get("mgr")
    if mgr:
        return str(mgr)
    return None


def resolve_session_manager(authjwt: AuthJWT, db: Session, current_user: User) -> User:
    """The login identity that may switch among linked businesses."""
    mgr_id = get_manager_id_from_jwt(authjwt)
    if mgr_id:
        manager = db.query(User).filter(User.id == mgr_id).first()
        if manager and (
            current_user.id == manager.id
            or current_user.managed_by_user_id == manager.id
        ):
            return manager
    if current_user.managed_by_user_id:
        manager = db.query(User).filter(User.id == current_user.managed_by_user_id).first()
        if manager:
            return manager
    return current_user


def resolve_user_from_jwt(authjwt: AuthJWT, db: Session) -> User:
    subject = authjwt.get_jwt_subject()
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    user = db.query(User).filter(User.email == subject).first()
    if not user:
        user = db.query(User).filter(User.id == subject).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def is_platform_admin(user: User) -> bool:
    if user.id in _admin_id_set():
        return True
    if (user.email or "").lower() in _admin_email_set():
        return True
    return False


def get_current_user(
    authjwt: AuthJWT = Depends(validate_token),
    db: Session = Depends(get_db),
) -> User:
    return resolve_user_from_jwt(authjwt, db)


def require_admin(
    authjwt: AuthJWT = Depends(validate_token),
    db: Session = Depends(get_db),
) -> User:
    user = resolve_user_from_jwt(authjwt, db)
    if not is_platform_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


def require_self_or_admin(user_id: str, current: User) -> None:
    if current.id == user_id or is_platform_admin(current):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this resource",
    )

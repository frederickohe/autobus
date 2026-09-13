"""GreenMall connect / authorize / callback for first-party store linking."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from another_fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.chatwoot.controller.chatwoot_controller import resolve_internal_user_id
from core.greenmall.model.GreenMallAccount import GreenMallAccount
from core.greenmall.service.greenmall_oauth_service import (
    RESULT_TTL_SECONDS,
    STATE_TTL_SECONDS,
    GreenMallOAuthService,
    GreenMallOAuthState,
    extract_api_key,
    extract_store_email,
    extract_store_id,
    extract_store_name,
    greenmall_authorize_url,
    greenmall_callback_url,
)
from utilities.dbconfig import get_db

logger = logging.getLogger(__name__)

greenmall_routes = APIRouter()


def validate_token(authjwt: AuthJWT = Depends()) -> str:
    try:
        authjwt.jwt_required()
        return authjwt.get_jwt_subject()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


class GreenMallAccountResponse(BaseModel):
    id: str
    store_id: str
    store_name: Optional[str] = None
    store_email: Optional[str] = None
    is_active: bool
    connected_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GreenMallConnectResponse(BaseModel):
    state: str
    callback_url: str
    authorize_url: str = ""
    expires_in: int = STATE_TTL_SECONDS
    provider: str = "GREENMALL"
    message: str = (
        "Log in with GreenMall in the app. Autobus will receive the store API key "
        "on callback_url."
    )


class GreenMallAuthorizeRequest(BaseModel):
    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    state: str = Field(..., min_length=1)


class GreenMallAuthorizeResponse(BaseModel):
    status: str
    account: Optional[GreenMallAccountResponse] = None
    state: str
    message: str = ""


class GreenMallStatusResponse(BaseModel):
    status: str
    account: Optional[GreenMallAccountResponse] = None
    callback_url: str
    expires_in: int = RESULT_TTL_SECONDS


def _account_response(row: GreenMallAccount) -> GreenMallAccountResponse:
    return GreenMallAccountResponse.model_validate(row)


def _upsert_account(
    db: Session,
    *,
    user_id: str,
    store_id: str,
    store_name: Optional[str],
    store_email: Optional[str],
    api_key: str,
) -> GreenMallAccount:
    svc = GreenMallOAuthService()
    existing = (
        db.query(GreenMallAccount)
        .filter(GreenMallAccount.store_id == store_id)
        .first()
    )
    if existing and existing.user_id != user_id:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This GreenMall store is already linked to another Autobus account.",
            )
        logger.info(
            "[GREENMALL] reclaiming unlinked store_id=%s from user=%s to user=%s",
            store_id,
            existing.user_id,
            user_id,
        )
        existing.user_id = user_id

    token_enc = svc.encrypt_key(api_key)
    now = datetime.now(timezone.utc)
    if existing:
        existing.store_name = store_name or existing.store_name
        existing.store_email = store_email or existing.store_email
        existing.api_key_encrypted = token_enc
        existing.is_active = True
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return existing

    row = GreenMallAccount(
        id=str(uuid.uuid4()),
        user_id=user_id,
        store_id=store_id,
        store_name=store_name,
        store_email=store_email,
        api_key_encrypted=token_enc,
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _complete_link(
    db: Session,
    *,
    user_id: str,
    state: str,
    payload: dict,
    consume_state: bool = True,
) -> GreenMallAccount:
    svc = GreenMallOAuthService()
    api_key = extract_api_key(payload)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GreenMall did not send an API key.",
        )
    store_email = extract_store_email(payload)
    store_id = extract_store_id(payload) or svc.fallback_store_id(
        store_email=store_email,
        api_key=api_key,
    )
    account = _upsert_account(
        db,
        user_id=user_id,
        store_id=store_id,
        store_name=extract_store_name(payload) or None,
        store_email=store_email or None,
        api_key=api_key,
    )
    if consume_state:
        GreenMallOAuthState.consume(state)
    GreenMallOAuthState.store_result(
        state,
        {
            "status": "linked",
            "account_id": account.id,
            "user_id": user_id,
        },
    )
    return account


def _callback_secret_from_headers(
    x_greenmall_secret: Optional[str],
    x_autobus_secret: Optional[str],
    x_api_key: Optional[str],
    authorization: Optional[str],
) -> Optional[str]:
    for value in (x_greenmall_secret, x_autobus_secret, x_api_key):
        if value and value.strip():
            return value.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


@greenmall_routes.get("/connect", response_model=GreenMallConnectResponse)
async def greenmall_connect(
    jwt_subject: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    """Start a GreenMall link session for the signed-in Autobus business."""
    user_id = resolve_internal_user_id(db, jwt_subject)
    state = GreenMallOAuthState.create(user_id)
    return GreenMallConnectResponse(
        state=state,
        callback_url=greenmall_callback_url(),
        authorize_url=greenmall_authorize_url(),
    )


@greenmall_routes.get("/status", response_model=GreenMallStatusResponse)
async def greenmall_status(
    state: str = Query(..., min_length=1),
    jwt_subject: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    """Poll whether GreenMall has posted an API key for this link session."""
    user_id = resolve_internal_user_id(db, jwt_subject)
    result = GreenMallOAuthState.read_result(state)
    if result:
        result_user = str(result.get("user_id") or "")
        if result_user and result_user != user_id:
            raise HTTPException(status_code=403, detail="This link session belongs to another login.")
        account_id = str(result.get("account_id") or "")
        row = (
            db.query(GreenMallAccount)
            .filter(
                GreenMallAccount.id == account_id,
                GreenMallAccount.user_id == user_id,
                GreenMallAccount.is_active.is_(True),
            )
            .first()
        )
        if row:
            return GreenMallStatusResponse(
                status="linked",
                account=_account_response(row),
                callback_url=greenmall_callback_url(),
            )
        return GreenMallStatusResponse(
            status="linked",
            callback_url=greenmall_callback_url(),
        )

    pending = GreenMallOAuthState.peek(state)
    if pending and pending.get("user_id") == user_id:
        return GreenMallStatusResponse(
            status="pending",
            callback_url=greenmall_callback_url(),
            expires_in=STATE_TTL_SECONDS,
        )
    return GreenMallStatusResponse(
        status="expired",
        callback_url=greenmall_callback_url(),
        expires_in=0,
    )


@greenmall_routes.post("/authorize", response_model=GreenMallAuthorizeResponse)
async def greenmall_authorize(
    body: GreenMallAuthorizeRequest,
    jwt_subject: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    """In-app GreenMall login. Autobus forwards credentials and waits for the API key."""
    user_id = resolve_internal_user_id(db, jwt_subject)
    session = GreenMallOAuthState.peek(body.state)
    if not session or session.get("user_id") != user_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired GreenMall link session. Try linking again.",
        )

    svc = GreenMallOAuthService()
    try:
        payload = svc.authorize_on_greenmall(
            email=body.email.strip(),
            password=body.password,
            state=body.state,
            callback_url=greenmall_callback_url(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if extract_api_key(payload):
        try:
            account = _complete_link(
                db,
                user_id=user_id,
                state=body.state,
                payload=payload,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("[GREENMALL] authorize store failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return GreenMallAuthorizeResponse(
            status="linked",
            account=_account_response(account),
            state=body.state,
            message="GreenMall linked.",
        )

    pending = str(payload.get("status") or "").strip().lower() in {
        "pending",
        "accepted",
        "ok",
    } or bool(payload.get("pending"))
    if pending or payload.get("accepted") is True:
        return GreenMallAuthorizeResponse(
            status="pending",
            state=body.state,
            message="GreenMall accepted the login. Waiting for the API key callback.",
        )

    # GreenMall may POST the callback before returning from authorize.
    result = GreenMallOAuthState.read_result(body.state)
    if result and result.get("status") == "linked":
        account_id = str(result.get("account_id") or "")
        row = (
            db.query(GreenMallAccount)
            .filter(
                GreenMallAccount.id == account_id,
                GreenMallAccount.user_id == user_id,
            )
            .first()
        )
        if row:
            return GreenMallAuthorizeResponse(
                status="linked",
                account=_account_response(row),
                state=body.state,
                message="GreenMall linked.",
            )

    return GreenMallAuthorizeResponse(
        status="pending",
        state=body.state,
        message="GreenMall login sent. Waiting for the API key callback.",
    )


@greenmall_routes.post("/callback")
async def greenmall_callback(
    request: Request,
    db: Session = Depends(get_db),
    x_greenmall_secret: Optional[str] = Header(None, alias="X-GreenMall-Secret"),
    x_autobus_secret: Optional[str] = Header(None, alias="X-Autobus-Secret"),
    x_api_key: Optional[str] = Header(None, alias="X-Api-Key"),
    x_greenmall_signature: Optional[str] = Header(None, alias="X-GreenMall-Signature"),
    authorization: Optional[str] = Header(None),
):
    """
    Public callback GreenMall calls after a merchant authorizes Autobus.

    POST JSON: ``{ "state", "api_key", "store_id?", "store_name?", "store_email?" }``
    Authenticate with ``X-GreenMall-Secret`` (or Bearer) matching
    ``GREENMALL_CALLBACK_SECRET`` / ``GREENMALL_SHARED_SECRET``.
    """
    raw = await request.body()
    svc = GreenMallOAuthService()
    try:
        svc.verify_callback_secret(
            _callback_secret_from_headers(
                x_greenmall_secret,
                x_autobus_secret,
                x_api_key,
                authorization,
            )
        )
        svc.verify_callback_signature(raw, x_greenmall_signature)
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected a JSON object.")

    state = str(payload.get("state") or "").strip()
    if not state:
        raise HTTPException(status_code=400, detail="Missing state.")

    session = GreenMallOAuthState.peek(state)
    if not session:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired GreenMall link session.",
        )

    try:
        account = _complete_link(
            db,
            user_id=session["user_id"],
            state=state,
            payload=payload,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[GREENMALL] callback store failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "linked",
        "account_id": account.id,
        "store_id": account.store_id,
        "store_name": account.store_name,
    }


@greenmall_routes.get("/accounts", response_model=List[GreenMallAccountResponse])
async def list_greenmall_accounts(
    jwt_subject: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    user_id = resolve_internal_user_id(db, jwt_subject)
    rows = (
        db.query(GreenMallAccount)
        .filter(GreenMallAccount.user_id == user_id, GreenMallAccount.is_active.is_(True))
        .all()
    )
    return [_account_response(row) for row in rows]


@greenmall_routes.delete("/accounts/{account_id}")
async def disconnect_greenmall_account(
    account_id: str,
    jwt_subject: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    user_id = resolve_internal_user_id(db, jwt_subject)
    row = (
        db.query(GreenMallAccount)
        .filter(GreenMallAccount.id == account_id, GreenMallAccount.user_id == user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="GreenMall account not found")
    db.delete(row)
    db.commit()
    return {"status": "ok", "message": "GreenMall store disconnected"}

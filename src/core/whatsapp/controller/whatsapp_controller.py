"""WhatsApp Cloud API connect routes (Meta Embedded Signup / Business App onboard)."""

from __future__ import annotations

import logging
import os
from typing import List, Optional

from another_fastapi_jwt_auth import AuthJWT
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.chatwoot.controller.chatwoot_controller import resolve_internal_user_id
from core.whatsapp.model.WhatsAppAccount import WhatsAppAccount
from core.whatsapp.service.meta_embedded_signup_service import (
    MetaWhatsAppOAuthState,
    MetaWhatsAppService,
)
from utilities.dbconfig import get_db

logger = logging.getLogger(__name__)

whatsapp_routes = APIRouter()


def validate_token(authjwt: AuthJWT = Depends()) -> str:
    try:
        authjwt.jwt_required()
        return authjwt.get_jwt_subject()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


class WhatsAppAccountResponse(BaseModel):
    id: str
    waba_id: str
    phone_number_id: str
    display_phone_number: Optional[str] = None
    verified_name: Optional[str] = None
    is_active: bool
    webhook_subscribed: bool
    phone_registered: bool

    class Config:
        from_attributes = True


class WhatsAppConnectResponse(BaseModel):
    authorization_url: str
    provider: str = "META_WHATSAPP"
    state: str
    redirect_uri: str
    message: str = "Open authorization_url to link WhatsApp via Meta Embedded Signup."


class WhatsAppCompleteRequest(BaseModel):
    code: str = Field(..., min_length=8)
    waba_id: Optional[str] = None
    phone_number_id: Optional[str] = None
    business_id: Optional[str] = None
    state: Optional[str] = None


def _frontend_base() -> str:
    return (os.getenv("BASE_FRONTEND_URL") or "https://useautobus.com").rstrip("/")


def _upsert_account(
    db: Session,
    *,
    user_id: str,
    waba_id: str,
    phone_number_id: str,
    access_token: str,
    display_phone: Optional[str],
    verified_name: Optional[str],
    business_id: Optional[str],
    webhook_subscribed: bool,
    phone_registered: bool,
) -> WhatsAppAccount:
    svc = MetaWhatsAppService()
    existing = (
        db.query(WhatsAppAccount)
        .filter(WhatsAppAccount.phone_number_id == phone_number_id)
        .first()
    )
    if existing and existing.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This WhatsApp number is already linked to another Autobus account.",
        )

    token_enc = svc.encrypt_token(access_token)
    if existing:
        existing.waba_id = waba_id
        existing.access_token_encrypted = token_enc
        existing.display_phone_number = display_phone or existing.display_phone_number
        existing.verified_name = verified_name or existing.verified_name
        existing.business_id = business_id or existing.business_id
        existing.is_active = True
        existing.webhook_subscribed = webhook_subscribed
        existing.phone_registered = phone_registered
        db.commit()
        db.refresh(existing)
        return existing

    row = WhatsAppAccount(
        id=svc.new_account_id(),
        user_id=user_id,
        waba_id=waba_id,
        phone_number_id=phone_number_id,
        display_phone_number=display_phone,
        verified_name=verified_name,
        business_id=business_id,
        access_token_encrypted=token_enc,
        is_active=True,
        webhook_subscribed=webhook_subscribed,
        phone_registered=phone_registered,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def complete_onboarding(
    db: Session,
    *,
    user_id: str,
    code: str,
    waba_id: Optional[str] = None,
    phone_number_id: Optional[str] = None,
    business_id: Optional[str] = None,
) -> WhatsAppAccount:
    svc = MetaWhatsAppService()
    token_data = svc.exchange_code(code)
    access_token = token_data["access_token"]
    waba_id, phone_number_id, display, name = svc.resolve_waba_and_phone(
        access_token,
        waba_id=waba_id,
        phone_number_id=phone_number_id,
    )
    subscribed = svc.subscribe_webhooks(access_token, waba_id)
    registered = svc.register_phone(access_token, phone_number_id)
    return _upsert_account(
        db,
        user_id=user_id,
        waba_id=waba_id,
        phone_number_id=phone_number_id,
        access_token=access_token,
        display_phone=display,
        verified_name=name,
        business_id=business_id,
        webhook_subscribed=subscribed,
        phone_registered=registered,
    )


def _success_html(account: WhatsAppAccount) -> str:
    phone = account.display_phone_number or account.phone_number_id
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>WhatsApp linked</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
body{{font-family:system-ui,sans-serif;background:#0b0f0c;color:#e8f5e9;display:flex;
align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{max-width:420px;padding:28px;border:1px solid #1f3d2a;border-radius:16px;background:#102016}}
h1{{font-size:1.25rem;margin:0 0 8px}} p{{opacity:.85;line-height:1.45}}
a{{color:#69f0ae}}
</style></head>
<body><div class="card">
<h1>WhatsApp connected</h1>
<p>Number <strong>{phone}</strong> is linked to Autobus.</p>
<p>You can close this window and return to Autobus.</p>
<p><a href="{_frontend_base()}">Back to Autobus</a></p>
</div>
<script>try{{window.opener&&window.opener.postMessage({{type:'AUTOBUS_WHATSAPP_LINKED',phone_number_id:'{account.phone_number_id}'}},'*');}}catch(e){{}}
setTimeout(function(){{window.location.replace('{_frontend_base()}/');}},2500);</script>
</body></html>"""


def _error_html(message: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/><title>WhatsApp link failed</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
body{{font-family:system-ui,sans-serif;background:#140b0b;color:#ffebee;display:flex;
align-items:center;justify-content:center;min-height:100vh;margin:0}}
.card{{max-width:420px;padding:28px;border:1px solid #4a1f1f;border-radius:16px;background:#201010}}
</style></head>
<body><div class="card"><h1>WhatsApp link failed</h1><p>{message}</p>
<p><a style="color:#ff8a80" href="{_frontend_base()}">Back to Autobus</a></p></div></body></html>"""


@whatsapp_routes.get("/connect", response_model=WhatsAppConnectResponse)
async def whatsapp_connect(
    jwt_subject: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    """Return Meta WhatsApp Business App onboard URL for the authenticated user."""
    try:
        user_id = resolve_internal_user_id(db, jwt_subject)
        svc = MetaWhatsAppService()
        svc.require_config()
        state = MetaWhatsAppOAuthState.create(user_id)
        url = svc.build_onboard_url(state)
        return WhatsAppConnectResponse(
            authorization_url=url,
            state=state,
            redirect_uri=svc.redirect_uri,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("[WA] connect failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@whatsapp_routes.get("/accounts", response_model=List[WhatsAppAccountResponse])
async def list_whatsapp_accounts(
    jwt_subject: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    user_id = resolve_internal_user_id(db, jwt_subject)
    rows = (
        db.query(WhatsAppAccount)
        .filter(WhatsAppAccount.user_id == user_id, WhatsAppAccount.is_active.is_(True))
        .all()
    )
    return [WhatsAppAccountResponse.model_validate(r) for r in rows]


@whatsapp_routes.delete("/accounts/{account_id}")
async def disconnect_whatsapp_account(
    account_id: str,
    jwt_subject: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    user_id = resolve_internal_user_id(db, jwt_subject)
    row = (
        db.query(WhatsAppAccount)
        .filter(WhatsAppAccount.id == account_id, WhatsAppAccount.user_id == user_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="WhatsApp account not found")
    row.is_active = False
    db.commit()
    return {"status": "ok", "message": "WhatsApp account disconnected"}


@whatsapp_routes.post("/embedded-signup/complete", response_model=WhatsAppAccountResponse)
async def whatsapp_embedded_signup_complete(
    body: WhatsAppCompleteRequest,
    jwt_subject: str = Depends(validate_token),
    db: Session = Depends(get_db),
):
    """Complete Embedded Signup when the client receives code via FB JS SDK."""
    user_id = resolve_internal_user_id(db, jwt_subject)
    if body.state:
        state_user = MetaWhatsAppOAuthState.validate(body.state)
        if not state_user or state_user != user_id:
            raise HTTPException(status_code=400, detail="Invalid or expired state")
    try:
        account = complete_onboarding(
            db,
            user_id=user_id,
            code=body.code,
            waba_id=body.waba_id,
            phone_number_id=body.phone_number_id,
            business_id=body.business_id,
        )
        return WhatsAppAccountResponse.model_validate(account)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[WA] embedded signup complete failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@whatsapp_routes.get("/callback", response_class=HTMLResponse)
async def whatsapp_meta_callback(
    request: Request,
    db: Session = Depends(get_db),
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    error_message: Optional[str] = Query(None),
    waba_id: Optional[str] = Query(None),
    phone_number_id: Optional[str] = Query(None),
    business_id: Optional[str] = Query(None),
):
    """
    Meta redirect target for WhatsApp Business App onboarding.

    Also mounted at /api/social/callback to match META_WHATSAPP_REDIRECT_URI.
    """
    if error or error_message:
        msg = error_description or error_message or error or "Authorization failed"
        return HTMLResponse(_error_html(msg), status_code=400)

    if not code:
        return HTMLResponse(_error_html("Missing authorization code from Meta."), status_code=400)

    if not state:
        return HTMLResponse(
            _error_html("Missing state. Start linking again from Autobus Manage Channels."),
            status_code=400,
        )

    user_id = MetaWhatsAppOAuthState.validate(state)
    if not user_id:
        return HTMLResponse(
            _error_html("Invalid or expired link session. Please try linking again."),
            status_code=400,
        )

    q = request.query_params
    waba_id = waba_id or q.get("waba_id") or q.get("whatsapp_business_account_id")
    phone_number_id = (
        phone_number_id or q.get("phone_number_id") or q.get("phone_number_ids")
    )
    business_id = business_id or q.get("business_id") or q.get("businessId")

    try:
        account = complete_onboarding(
            db,
            user_id=user_id,
            code=code,
            waba_id=waba_id,
            phone_number_id=phone_number_id,
            business_id=business_id,
        )
        return HTMLResponse(_success_html(account))
    except Exception as exc:
        logger.exception("[WA] meta callback failed")
        return HTMLResponse(_error_html(str(exc)), status_code=400)


# Dedicated mount for Meta's configured redirect_uri:
# https://useautobus.com/api/social/callback
meta_whatsapp_callback_routes = APIRouter()


@meta_whatsapp_callback_routes.get("/social/callback", response_class=HTMLResponse)
async def meta_social_callback(
    request: Request,
    db: Session = Depends(get_db),
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    error_message: Optional[str] = Query(None),
    error_reason: Optional[str] = Query(None),
    waba_id: Optional[str] = Query(None),
    phone_number_id: Optional[str] = Query(None),
    business_id: Optional[str] = Query(None),
):
    """
    Shared Meta redirect URI for WhatsApp Embedded Signup and Instagram Business Login.

    Instagram states are prefixed with ``ig.``; everything else uses the WhatsApp handler.
    """
    from core.instagram.controller.instagram_controller import (
        handle_instagram_oauth_callback,
    )
    from core.instagram.service.instagram_oauth_service import InstagramOAuthState

    if InstagramOAuthState.is_instagram_state(state):
        return await handle_instagram_oauth_callback(
            db=db,
            code=code,
            state=state,
            error=error,
            error_description=error_description,
            error_reason=error_reason or error_message,
        )

    return await whatsapp_meta_callback(
        request=request,
        db=db,
        code=code,
        state=state,
        error=error,
        error_description=error_description,
        error_message=error_message,
        waba_id=waba_id,
        phone_number_id=phone_number_id,
        business_id=business_id,
    )

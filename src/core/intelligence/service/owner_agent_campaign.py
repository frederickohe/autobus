"""Last generated campaign + Instagram helpers for the owner agent."""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.cloudstorage.service.storageservice import StorageFolder, StorageService
from core.instagram.model.InstagramAccount import InstagramAccount
from core.intelligence.service.business_context_assembler import owner_conversation_key
from core.nlu.service.conversation_manager import ConversationManager
from core.user.model.User import User

logger = logging.getLogger(__name__)

CAMPAIGN_KEY = "owner_agent_campaign"


def _await(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def load_campaign(user: User) -> Dict[str, Any]:
    conv_key = owner_conversation_key(user.id)
    state = ConversationManager().get_conversation_state(conv_key)
    pending = state.pending_action if isinstance(state.pending_action, dict) else {}
    campaign = pending.get(CAMPAIGN_KEY)
    return dict(campaign) if isinstance(campaign, dict) else {}


def save_campaign(user: User, **fields: Any) -> Dict[str, Any]:
    conv_key = owner_conversation_key(user.id)
    manager = ConversationManager()
    state = manager.get_conversation_state(conv_key)
    pending = dict(state.pending_action) if isinstance(state.pending_action, dict) else {}
    campaign = dict(pending.get(CAMPAIGN_KEY) or {})
    for key, value in fields.items():
        if value is None:
            continue
        campaign[key] = value
    pending[CAMPAIGN_KEY] = campaign
    state.pending_action = pending
    manager.persist(conv_key)
    return campaign


def fill_publish_args(user: User, args: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(args or {})
    campaign = load_campaign(user)
    urls = _string_list(merged.get("media_urls"))
    if not urls:
        urls = _string_list(campaign.get("media_urls"))
        if not urls:
            url = str(campaign.get("url") or "").strip()
            if url:
                urls = [url]
    if urls:
        merged["media_urls"] = urls
    caption = str(merged.get("caption") or "").strip()
    if not caption:
        caption = str(campaign.get("caption") or campaign.get("copy") or "").strip()
        if caption:
            merged["caption"] = caption
    account_id = str(merged.get("account_id") or "").strip()
    if not account_id:
        account_id = str(campaign.get("account_id") or "").strip()
        if account_id:
            merged["account_id"] = account_id
    return merged


def list_accounts(db: Session, user: User) -> List[Dict[str, Any]]:
    rows = (
        db.query(InstagramAccount)
        .filter(InstagramAccount.user_id == user.id, InstagramAccount.is_active.is_(True))
        .all()
    )
    return [
        {
            "id": row.id,
            "username": row.username,
            "name": row.name,
            "publishing_enabled": bool(row.publishing_enabled),
        }
        for row in rows
    ]


def pick_publish_account(db: Session, user: User, account_id: Optional[str]) -> Optional[InstagramAccount]:
    query = db.query(InstagramAccount).filter(
        InstagramAccount.user_id == user.id,
        InstagramAccount.is_active.is_(True),
    )
    wanted = (account_id or "").strip()
    if wanted:
        return query.filter(InstagramAccount.id == wanted).first()
    rows = query.all()
    for row in rows:
        if row.publishing_enabled:
            return row
    return rows[0] if rows else None


def upload_image_bytes(user_id: str, raw_b64: str, mime: str) -> str:
    blob = raw_b64.strip()
    if "," in blob:
        blob = blob.split(",", 1)[1]
    data = base64.b64decode(blob)
    mime_type = (mime or "image/png").strip() or "image/png"
    ext = "jpg"
    if "png" in mime_type:
        ext = "png"
    elif "webp" in mime_type:
        ext = "webp"
    elif "gif" in mime_type:
        ext = "gif"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{user_id}_{stamp}_{uuid.uuid4().hex[:8]}.{ext}"
    return StorageService().upload_file(
        io.BytesIO(data),
        filename,
        content_type=mime_type,
        folder=StorageFolder.generated_images,
    )


def _string_list(raw: Any) -> List[str]:
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    for item in raw:
        value = str(item or "").strip()
        if value:
            out.append(value)
    return out

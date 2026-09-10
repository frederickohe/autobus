"""TikTok Direct Post helpers: creator_info, publish status, consent copy."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
from sqlalchemy import create_engine, text

from core.socialmedia.service.postiz_api_service import (
    PostizAPIError,
    PostizClient,
    normalize_postiz_integrations_list,
)

logger = logging.getLogger(__name__)

TIKTOK_CREATOR_INFO_URL = (
    "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
)
TIKTOK_PUBLISH_STATUS_URL = (
    "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
)

CANNOT_POST_ERROR_CODES = frozenset(
    {
        "spam_risk_too_many_posts",
        "spam_risk_user_banned_from_posting",
        "reached_active_user_cap",
    }
)

PRIVACY_LABELS = {
    "PUBLIC_TO_EVERYONE": "Everyone",
    "MUTUAL_FOLLOW_FRIENDS": "Friends",
    "FOLLOWER_OF_CREATOR": "Followers",
    "SELF_ONLY": "Only me",
}

MUSIC_USAGE_CONFIRMATION_URL = (
    "https://www.tiktok.com/legal/page/global/music-usage-confirmation/en"
)
BRANDED_CONTENT_POLICY_URL = (
    "https://www.tiktok.com/legal/page/global/bc-policy/en"
)

CONSENT_MUSIC = "By posting, you agree to TikTok's Music Usage Confirmation"
CONSENT_BRANDED = (
    "By posting, you agree to TikTok's Branded Content Policy and Music Usage Confirmation"
)
PROCESSING_NOTICE = (
    "After you finish publishing, it may take a few minutes for the content "
    "to process and be visible on your TikTok profile."
)


def tiktok_consent_text(*, branded_content: bool) -> str:
    return CONSENT_BRANDED if branded_content else CONSENT_MUSIC


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value.strip()))
        except ValueError:
            return None
    return None


def _first_str(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _privacy_options(raw: Any) -> List[str]:
    if not isinstance(raw, list):
        return []
    out: List[str] = []
    seen = set()
    for item in raw:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def cannot_post_reason(error_code: str, error_message: str = "") -> str:
    code = (error_code or "").strip()
    if code == "spam_risk_too_many_posts":
        return "This TikTok account cannot make more posts right now. Try again later."
    if code == "spam_risk_user_banned_from_posting":
        return "This TikTok account is not allowed to post right now."
    if code == "reached_active_user_cap":
        return "TikTok posting is temporarily capped for this app. Try again later."
    if error_message.strip():
        return error_message.strip()
    return "This TikTok account cannot post right now. Try again later."


def normalize_creator_info(
    payload: Any,
    *,
    fallback_name: str = "",
    fallback_username: str = "",
    fallback_avatar: str = "",
) -> Dict[str, Any]:
    """Normalize TikTok / Postiz creator_info payloads into one UI shape."""
    root = _as_dict(payload)
    data = _as_dict(root.get("data")) if "data" in root else root
    if not data and isinstance(root.get("creator_info"), dict):
        data = _as_dict(root.get("creator_info"))

    error = _as_dict(root.get("error"))
    error_code = _first_str(error.get("code"), root.get("error_code"))
    error_message = _first_str(error.get("message"), root.get("message"))
    error_is_ok = error_code.lower() in {"", "ok", "success"}

    can_post_field = data.get("can_post", root.get("can_post"))
    can_post = True if can_post_field is None else _as_bool(can_post_field, True)
    blocked_reason = ""
    if error_code in CANNOT_POST_ERROR_CODES or not error_is_ok:
        can_post = False
        blocked_reason = cannot_post_reason(error_code, error_message)
    elif can_post_field is not None and not can_post:
        blocked_reason = cannot_post_reason(error_code, error_message)

    privacy = _privacy_options(
        data.get("privacy_level_options")
        or data.get("privacyLevelOptions")
        or root.get("privacy_level_options")
        or root.get("privacyLevelOptions")
    )

    max_duration = _as_int(
        data.get("max_video_post_duration_sec")
        or data.get("maxVideoPostDurationSec")
        or data.get("maxDurationSeconds")
        or root.get("max_video_post_duration_sec")
        or root.get("maxDurationSeconds")
    )

    nickname = _first_str(
        data.get("creator_nickname"),
        data.get("nickname"),
        root.get("creator_nickname"),
        root.get("nickname"),
        fallback_name,
    )
    username = _first_str(
        data.get("creator_username"),
        data.get("username"),
        root.get("creator_username"),
        root.get("username"),
        fallback_username,
    )
    avatar = _first_str(
        data.get("creator_avatar_url"),
        data.get("avatar_url"),
        data.get("picture"),
        root.get("creator_avatar_url"),
        fallback_avatar,
    )

    return {
        "creator_nickname": nickname,
        "creator_username": username,
        "creator_avatar_url": avatar,
        "privacy_level_options": privacy,
        "privacy_level_labels": {key: PRIVACY_LABELS.get(key, key) for key in privacy},
        "comment_disabled": _as_bool(
            data.get("comment_disabled", data.get("commentDisabled")), False
        ),
        "duet_disabled": _as_bool(
            data.get("duet_disabled", data.get("duetDisabled")), False
        ),
        "stitch_disabled": _as_bool(
            data.get("stitch_disabled", data.get("stitchDisabled")), False
        ),
        "max_video_post_duration_sec": max_duration,
        "can_post": can_post,
        "cannot_post_reason": blocked_reason,
        "music_usage_confirmation_url": MUSIC_USAGE_CONFIRMATION_URL,
        "branded_content_policy_url": BRANDED_CONTENT_POLICY_URL,
        "consent_music": CONSENT_MUSIC,
        "consent_branded": CONSENT_BRANDED,
        "processing_notice": PROCESSING_NOTICE,
        "error_code": error_code if not error_is_ok else "",
    }


def extract_publish_ids(payload: Any) -> List[str]:
    found: List[str] = []
    seen = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key in (
                "publish_id",
                "publishId",
                "postId",
                "post_id",
                "id",
                "releaseId",
            ):
                value = node.get(key)
                if isinstance(value, str) and value.strip() and value.strip() not in seen:
                    if key in {"publish_id", "publishId"} or str(value).startswith(
                        ("v_pub", "p_pub", "photo_post")
                    ):
                        seen.add(value.strip())
                        found.append(value.strip())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


def extract_post_ids(payload: Any) -> List[str]:
    found: List[str] = []
    seen = set()

    def consider(value: Any) -> None:
        if not isinstance(value, str):
            return
        text = value.strip()
        if not text or text in seen:
            return
        seen.add(text)
        found.append(text)

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key in ("id", "postId", "post_id", "releaseId"):
                consider(node.get(key))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


def normalize_publish_status(payload: Any) -> Dict[str, Any]:
    root = _as_dict(payload)
    data = _as_dict(root.get("data")) if "data" in root else root
    status = _first_str(
        data.get("status"),
        root.get("status"),
        root.get("state"),
        data.get("state"),
    ).upper()
    fail_reason = _first_str(
        data.get("fail_reason"),
        data.get("error"),
        root.get("fail_reason"),
        root.get("error"),
    )
    public_ids = data.get("publicaly_available_post_id") or data.get(
        "publicly_available_post_id"
    )
    if not isinstance(public_ids, list):
        public_ids = []
    complete = status in {"PUBLISH_COMPLETE", "PUBLISHED"}
    failed = status in {"FAILED", "ERROR"}
    processing = status in {
        "PROCESSING_UPLOAD",
        "PROCESSING_DOWNLOAD",
        "SEND_TO_USER_INBOX",
        "QUEUE",
        "PENDING",
    } or (status and not complete and not failed)
    message = PROCESSING_NOTICE
    if complete:
        message = "Your post is on TikTok."
    elif failed:
        message = fail_reason or "TikTok could not publish this post."
    elif status == "SEND_TO_USER_INBOX":
        message = (
            "TikTok sent a draft to the creator inbox. Open TikTok to finish the post."
        )
    return {
        "status": status or "PROCESSING_DOWNLOAD",
        "processing": processing and not complete and not failed,
        "complete": complete,
        "failed": failed,
        "message": message,
        "fail_reason": fail_reason,
        "public_post_ids": [str(x) for x in public_ids if x],
        "processing_notice": PROCESSING_NOTICE,
    }


def token_from_postiz_db(integration_id: str) -> Optional[str]:
    dsn = os.getenv("POSTIZ_DATABASE_URL", "").strip()
    iid = (integration_id or "").strip()
    if not dsn or not iid:
        return None
    queries = (
        """
        SELECT token FROM "Integration"
        WHERE id = :id AND "providerIdentifier" = 'tiktok'
          AND ("deletedAt" IS NULL)
        LIMIT 1
        """,
        """
        SELECT token FROM "Integration"
        WHERE id = :id AND "providerIdentifier" = 'tiktok'
        LIMIT 1
        """,
    )
    try:
        engine = create_engine(dsn, pool_pre_ping=True)
        with engine.connect() as conn:
            for sql in queries:
                try:
                    row = conn.execute(text(sql), {"id": iid}).first()
                except Exception:
                    continue
                if row and row[0]:
                    token = str(row[0]).strip()
                    if token:
                        return token
    except Exception as exc:
        logger.warning("[SOCIAL] Could not read TikTok token from Postiz DB: %s", exc)
    return None


async def query_tiktok_creator_info(access_token: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            TIKTOK_CREATOR_INFO_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={},
        )
    if res.status_code >= 400:
        raise PostizAPIError(
            f"TikTok creator_info failed ({res.status_code}): {res.text}",
            status_code=res.status_code,
            body=res.text or "",
        )
    return res.json() if res.text.strip() else {}


async def query_tiktok_publish_status(
    access_token: str, publish_id: str
) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.post(
            TIKTOK_PUBLISH_STATUS_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
        )
    if res.status_code >= 400:
        raise PostizAPIError(
            f"TikTok publish status failed ({res.status_code}): {res.text}",
            status_code=res.status_code,
            body=res.text or "",
        )
    return res.json() if res.text.strip() else {}


def _integration_row(
    rows: Iterable[Dict[str, Any]], integration_id: str
) -> Optional[Dict[str, Any]]:
    iid = (integration_id or "").strip()
    for row in rows:
        if str(row.get("id") or "").strip() != iid:
            continue
        ident = str(row.get("identifier") or row.get("providerIdentifier") or "").lower()
        if ident and ident != "tiktok":
            return None
        return row
    return None


async def load_tiktok_creator_info(
    *,
    client: PostizClient,
    api_key: str,
    integration_id: str,
    postiz_email: str = "",
    postiz_password: str = "",
) -> Dict[str, Any]:
    iid = (integration_id or "").strip()
    if not iid:
        raise PostizAPIError("integration id is required", status_code=400)

    raw_list = await client.list_integrations(api_key)
    rows = normalize_postiz_integrations_list(raw_list)
    integration = _integration_row(rows, iid)
    if not integration:
        raise PostizAPIError("TikTok channel not found", status_code=404)

    fallback_name = _first_str(integration.get("name"))
    fallback_username = _first_str(integration.get("profile"), integration.get("display"))
    fallback_avatar = _first_str(integration.get("picture"))

    attempts: List[Tuple[str, Any]] = []

    try:
        attempts.append(
            (
                "public",
                await client.get_tiktok_creator_info_public(api_key, iid),
            )
        )
    except PostizAPIError as exc:
        logger.info("[SOCIAL] Postiz public creator-info unavailable: %s", exc)

    session_jwt = ""
    if postiz_email and postiz_password:
        try:
            session_jwt = await client.login_local_session(
                postiz_email, postiz_password
            )
        except PostizAPIError as exc:
            logger.info("[SOCIAL] Postiz session for creator_info failed: %s", exc)

    if session_jwt:
        for method in ("queryCreatorInfo", "getCreatorInfo"):
            try:
                attempts.append(
                    (
                        method,
                        await client.call_integration_function(
                            session_jwt,
                            integration_id=iid,
                            name=method,
                            data={},
                        ),
                    )
                )
            except PostizAPIError as exc:
                logger.info("[SOCIAL] Postiz %s failed: %s", method, exc)

    token = token_from_postiz_db(iid)
    if token:
        try:
            attempts.append(("tiktok", await query_tiktok_creator_info(token)))
        except PostizAPIError as exc:
            logger.info("[SOCIAL] Direct TikTok creator_info failed: %s", exc)

    for _source, payload in attempts:
        info = normalize_creator_info(
            payload,
            fallback_name=fallback_name,
            fallback_username=fallback_username,
            fallback_avatar=fallback_avatar,
        )
        if info["privacy_level_options"] or info["creator_nickname"] or info["error_code"]:
            if not info["creator_nickname"]:
                info["creator_nickname"] = fallback_name
            if not info["creator_username"]:
                info["creator_username"] = fallback_username
            if not info["creator_avatar_url"]:
                info["creator_avatar_url"] = fallback_avatar
            return info

    raise PostizAPIError(
        "Could not load TikTok creator info. Reconnect TikTok and try again.",
        status_code=502,
    )


async def load_tiktok_publish_status(
    *,
    client: PostizClient,
    api_key: str,
    integration_id: str,
    publish_id: str = "",
    postiz_email: str = "",
    postiz_password: str = "",
) -> Dict[str, Any]:
    iid = (integration_id or "").strip()
    pid = (publish_id or "").strip()
    if pid:
        session_jwt = ""
        if postiz_email and postiz_password:
            try:
                session_jwt = await client.login_local_session(
                    postiz_email, postiz_password
                )
            except PostizAPIError:
                session_jwt = ""
        if session_jwt and iid:
            try:
                raw = await client.call_integration_function(
                    session_jwt,
                    integration_id=iid,
                    name="fetchPublishStatus",
                    data={"publish_id": pid},
                )
                return normalize_publish_status(raw)
            except PostizAPIError as exc:
                logger.info("[SOCIAL] Postiz fetchPublishStatus failed: %s", exc)
        token = token_from_postiz_db(iid) if iid else None
        if token:
            try:
                raw = await query_tiktok_publish_status(token, pid)
                return normalize_publish_status(raw)
            except PostizAPIError as exc:
                logger.info("[SOCIAL] Direct TikTok publish status failed: %s", exc)

    start, end = _recent_post_window()
    try:
        posts = await client.list_posts(api_key, start_date=start, end_date=end)
    except PostizAPIError as exc:
        logger.info("[SOCIAL] Postiz list posts failed: %s", exc)
        return normalize_publish_status({"status": "PROCESSING_DOWNLOAD"})

    matched = _posts_for_integration(posts, iid)
    if not matched:
        return normalize_publish_status({"status": "PROCESSING_DOWNLOAD"})
    latest = matched[0]
    return normalize_publish_status(latest)


def _recent_post_window() -> Tuple[str, str]:
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    start = (now - timedelta(hours=6)).isoformat().replace("+00:00", "Z")
    end = (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    return start, end


def _posts_for_integration(payload: Any, integration_id: str) -> List[Dict[str, Any]]:
    iid = (integration_id or "").strip()
    rows: List[Any]
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        inner = (
            payload.get("posts")
            or payload.get("items")
            or payload.get("data")
            or payload.get("value")
            or []
        )
        rows = inner if isinstance(inner, list) else []
    else:
        rows = []

    matched: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        integration = row.get("integration")
        row_iid = ""
        if isinstance(integration, dict):
            row_iid = str(integration.get("id") or "").strip()
            ident = str(integration.get("identifier") or "").lower()
        else:
            row_iid = str(row.get("integrationId") or row.get("integration_id") or "").strip()
            ident = str(row.get("identifier") or "").lower()
        if iid and row_iid and row_iid != iid:
            continue
        if ident and ident != "tiktok" and iid:
            continue
        matched.append(row)
    return matched

"""
Read a linked Facebook Page for the Marketing screen.

business_management: list Meta businesses and the Pages they own or manage.
pages_read_engagement: read posts the Page published, plus reaction and comment counts.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

GRAPH = "https://graph.facebook.com/v25.0"
_TOKEN_IN_TEXT = re.compile(r"access_token=[^&\s\"']+", re.IGNORECASE)


class FacebookPageReviewError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def redact_secrets(value: str) -> str:
    return _TOKEN_IN_TEXT.sub("access_token=redacted", value or "")


def tokens_for_row(token: str, refresh_token: str, in_between: bool) -> Tuple[str, str]:
    """Return (user_token, page_token).

    While Postiz is still waiting for a Page choice, `token` is the user token.
    After the Page is saved, `token` is the Page token and `refreshToken` is
    still the user token from the Facebook login.
    """
    page_or_user = (token or "").strip()
    refresh = (refresh_token or "").strip()
    if in_between:
        return page_or_user, ""
    user_token = refresh if refresh and refresh != page_or_user else ""
    return user_token, page_or_user


def picture_url(node: Any) -> str:
    if not isinstance(node, dict):
        return ""
    picture = node.get("picture")
    if isinstance(picture, str):
        return picture.strip()
    if isinstance(picture, dict):
        data = picture.get("data")
        if isinstance(data, dict) and data.get("url"):
            return str(data["url"]).strip()
        if picture.get("url"):
            return str(picture["url"]).strip()
    return ""


def engagement_count(node: Any, key: str) -> int:
    if not isinstance(node, dict):
        return 0
    block = node.get(key)
    if not isinstance(block, dict):
        return 0
    summary = block.get("summary")
    if isinstance(summary, dict):
        try:
            return int(summary.get("total_count") or 0)
        except (TypeError, ValueError):
            return 0
    return 0


def graph_error_message(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict) and err.get("message"):
            return redact_secrets(str(err["message"]))
    return redact_secrets(fallback)


def parse_business_pages(
    rows: List[Any],
    *,
    relationship: str,
    connected_page_id: str,
) -> List[Dict[str, Any]]:
    pages: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        page_id = str(row["id"])
        if page_id in seen:
            continue
        seen.add(page_id)
        pages.append(
            {
                "id": page_id,
                "name": str(row.get("name") or "Facebook Page"),
                "picture": picture_url(row),
                "relationship": relationship,
                "connected": bool(connected_page_id) and page_id == connected_page_id,
            }
        )
    return pages


def parse_posts(rows: List[Any]) -> List[Dict[str, Any]]:
    posts: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        message = str(row.get("message") or "").strip()
        posts.append(
            {
                "id": str(row["id"]),
                "message": message,
                "created_time": str(row.get("created_time") or ""),
                "permalink_url": str(row.get("permalink_url") or ""),
                "picture": str(row.get("full_picture") or ""),
                "reactions": engagement_count(row, "reactions"),
                "comments": engagement_count(row, "comments"),
            }
        )
    return posts


def _postiz_engine():
    from sqlalchemy import create_engine

    dsn = os.getenv("POSTIZ_DATABASE_URL", "").strip()
    if not dsn:
        raise FacebookPageReviewError("Postiz database is not configured.")
    return create_engine(dsn, pool_pre_ping=True)


def load_facebook_rows(org_id: str, integration_id: str = "") -> List[Dict[str, Any]]:
    from sqlalchemy import text

    org = (org_id or "").strip()
    if not org:
        raise FacebookPageReviewError("No Postiz workspace for this account.")
    sql = """
        SELECT id, "internalId", name, picture, token, "refreshToken", "inBetweenSteps"
        FROM "Integration"
        WHERE "organizationId" = :org
          AND "providerIdentifier" = 'facebook'
          AND "deletedAt" IS NULL
          AND (:integration_id = '' OR id = :integration_id)
        ORDER BY "createdAt" DESC
    """
    engine = _postiz_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(sql),
            {"org": org, "integration_id": (integration_id or "").strip()},
        )
        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in result.fetchall()]


async def _graph_get(
    client: Any,
    path: str,
    token: str,
    params: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    query = dict(params or {})
    query["access_token"] = token
    response = await client.get(f"{GRAPH}/{path.lstrip('/')}", params=query)
    try:
        payload = response.json() if response.text else {}
    except Exception:
        payload = {}
    if response.status_code >= 400 or (isinstance(payload, dict) and payload.get("error")):
        raise FacebookPageReviewError(
            graph_error_message(payload, f"Facebook request failed ({response.status_code})")
        )
    return payload if isinstance(payload, dict) else {}


async def _businesses_for_user(
    client: Any,
    user_token: str,
    connected_page_id: str,
) -> List[Dict[str, Any]]:
    listing = await _graph_get(
        client,
        "me/businesses",
        user_token,
        {"fields": "id,name", "limit": "25"},
    )
    businesses: List[Dict[str, Any]] = []
    for row in listing.get("data") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        business_id = str(row["id"])
        pages: List[Dict[str, Any]] = []
        page_error = ""
        try:
            owned = await _graph_get(
                client,
                f"{business_id}/owned_pages",
                user_token,
                {"fields": "id,name,picture", "limit": "25"},
            )
            pages.extend(
                parse_business_pages(
                    owned.get("data") or [],
                    relationship="Owned by this business",
                    connected_page_id=connected_page_id,
                )
            )
        except FacebookPageReviewError as exc:
            page_error = exc.message
        try:
            clients = await _graph_get(
                client,
                f"{business_id}/client_pages",
                user_token,
                {"fields": "id,name,picture", "limit": "25"},
            )
            existing = {page["id"] for page in pages}
            for page in parse_business_pages(
                clients.get("data") or [],
                relationship="A client Page of this business",
                connected_page_id=connected_page_id,
            ):
                if page["id"] not in existing:
                    pages.append(page)
        except FacebookPageReviewError as exc:
            if not pages:
                page_error = page_error or exc.message
        businesses.append(
            {
                "id": business_id,
                "name": str(row.get("name") or "Meta Business"),
                "pages": pages,
                "pages_error": page_error,
            }
        )
    return businesses


async def _posts_for_page(
    client: Any,
    page_id: str,
    page_token: str,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    profile = await _graph_get(
        client,
        page_id,
        page_token,
        {"fields": "id,name,picture,link,followers_count"},
    )
    feed = await _graph_get(
        client,
        f"{page_id}/published_posts",
        page_token,
        {
            "fields": "id,message,created_time,permalink_url,full_picture,reactions.limit(0).summary(true),comments.limit(0).summary(true)",
            "limit": "8",
        },
    )
    page = {
        "id": str(profile.get("id") or page_id),
        "name": str(profile.get("name") or ""),
        "picture": picture_url(profile),
        "link": str(profile.get("link") or ""),
        "followers_count": int(profile.get("followers_count") or 0),
    }
    return page, parse_posts(feed.get("data") or [])


async def load_facebook_page_activity(org_id: str, integration_id: str = "") -> Dict[str, Any]:
    import httpx

    rows = load_facebook_rows(org_id, integration_id)
    pages: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=25.0) as client:
        for row in rows:
            in_between = bool(row.get("inBetweenSteps"))
            user_token, page_token = tokens_for_row(
                str(row.get("token") or ""),
                str(row.get("refreshToken") or ""),
                in_between,
            )
            connected_page_id = "" if in_between else str(row.get("internalId") or "")
            item: Dict[str, Any] = {
                "integration_id": str(row.get("id") or ""),
                "page": {
                    "id": connected_page_id,
                    "name": str(row.get("name") or "Facebook Page"),
                    "picture": str(row.get("picture") or ""),
                    "link": "",
                "followers_count": 0,
            },
            "owning_business": None,
            "in_between": in_between,
                "needs_reconnect": not user_token,
                "businesses": [],
                "business_error": "",
                "posts": [],
                "posts_error": "",
            }
            if user_token:
                try:
                    item["businesses"] = await _businesses_for_user(
                        client, user_token, connected_page_id
                    )
                except FacebookPageReviewError as exc:
                    item["business_error"] = exc.message
                    item["needs_reconnect"] = True
            else:
                item["business_error"] = (
                    "Reconnect this Facebook Page so Autobus can read the Meta businesses on the login."
                )
            if page_token and connected_page_id:
                try:
                    profile, posts = await _posts_for_page(client, connected_page_id, page_token)
                    if profile.get("name"):
                        item["page"]["name"] = profile["name"]
                    if profile.get("picture"):
                        item["page"]["picture"] = profile["picture"]
                    item["page"]["link"] = profile.get("link") or ""
                    item["page"]["followers_count"] = profile.get("followers_count") or 0
                    item["page"]["id"] = profile.get("id") or connected_page_id
                    item["posts"] = posts
                    try:
                        owned_by = await _graph_get(
                            client,
                            connected_page_id,
                            page_token,
                            {"fields": "business{id,name}"},
                        )
                        business = owned_by.get("business")
                        if isinstance(business, dict) and business.get("id"):
                            item["owning_business"] = {
                                "id": str(business["id"]),
                                "name": str(business.get("name") or "Meta Business"),
                            }
                    except FacebookPageReviewError:
                        item["owning_business"] = None
                except FacebookPageReviewError as exc:
                    item["posts_error"] = exc.message
            elif in_between:
                item["posts_error"] = "Choose a Page to see reactions and comments on its posts."
            pages.append(item)
    return {"pages": pages}

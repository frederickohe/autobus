"""Owner resources: admin catalogue plus the business-owner feed."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import requests
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.admin.dto.admin_dto import (
    OwnerFeedResponse,
    ResourceItemResponse,
    ResourceUpsertRequest,
)
from core.admin.model.owner_resource import OwnerResource
from core.admin.service.owner_resource_logic import (
    SEED_RESOURCES,
    news_rss_url,
    parse_news_rss,
    rank_for_industry,
    thumbnail_for,
    youtube_id_from,
)
from core.intelligence.service.onboarding_index_service import ONBOARDING_INDUSTRY_OPTIONS
from core.user.model.User import User

logger = logging.getLogger(__name__)

_NEWS_CACHE: dict[str, tuple[float, list]] = {}
_NEWS_TTL_SECONDS = 60 * 30
_KINDS = {"video", "news", "guide", "other"}


def industry_of_user(user: User) -> Optional[str]:
    profile = user.onboarding_profile if isinstance(getattr(user, "onboarding_profile", None), dict) else {}
    answers = profile.get("answers") if isinstance(profile.get("answers"), dict) else profile
    raw = ""
    if isinstance(answers, dict):
        raw = str(answers.get("industry") or "").strip()
    if not raw:
        return None
    for option in ONBOARDING_INDUSTRY_OPTIONS:
        if option.casefold() == raw.casefold():
            return option
    return raw


class OwnerResourceService:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> List[ResourceItemResponse]:
        rows = (
            self.db.query(OwnerResource)
            .order_by(OwnerResource.kind.asc(), OwnerResource.sort_order.asc(), OwnerResource.created_at.desc())
            .all()
        )
        return [self._to_dto(row) for row in rows]

    def create(self, payload: ResourceUpsertRequest) -> ResourceItemResponse:
        import uuid

        row = OwnerResource(
            id=f"res_{uuid.uuid4().hex[:12]}",
            published_at=datetime.now(timezone.utc),
        )
        self._apply(row, payload)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._to_dto(row)

    def update(self, resource_id: str, payload: ResourceUpsertRequest) -> ResourceItemResponse:
        row = self._get_or_404(resource_id)
        self._apply(row, payload)
        row.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return self._to_dto(row)

    def toggle(self, resource_id: str) -> ResourceItemResponse:
        row = self._get_or_404(resource_id)
        row.is_active = not bool(row.is_active)
        row.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(row)
        return self._to_dto(row)

    def delete(self, resource_id: str) -> None:
        row = self._get_or_404(resource_id)
        self.db.delete(row)
        self.db.commit()

    def feed_for(self, user: User) -> OwnerFeedResponse:
        industry = industry_of_user(user)
        rows = self.db.query(OwnerResource).filter(OwnerResource.is_active.is_(True)).all()
        videos = rank_for_industry([row for row in rows if row.kind == "video"], industry)[:12]
        guides = rank_for_industry([row for row in rows if row.kind == "guide"], industry)
        others = rank_for_industry([row for row in rows if row.kind == "other"], industry)
        saved_news = rank_for_industry([row for row in rows if row.kind == "news"], industry)
        live = fetch_trending_news(industry)
        seen = {(item.url or "").strip() for item in saved_news if item.url}
        live = [item for item in live if (item.get("url") or "") not in seen]
        news = [_dto_from_mapping(item) for item in live] + [self._to_dto(row) for row in saved_news]
        return OwnerFeedResponse(
            industry=industry,
            videos=[self._to_dto(row) for row in videos],
            news=news[:12],
            guides=[self._to_dto(row) for row in guides],
            others=[self._to_dto(row) for row in others],
        )

    def _apply(self, row: OwnerResource, payload: ResourceUpsertRequest) -> None:
        kind = payload.kind
        if kind not in _KINDS:
            raise HTTPException(status_code=400, detail="Unknown resource type")
        title = payload.title.strip()
        url = (payload.url or "").strip() or None
        body = (payload.body or "").strip() or None
        summary = (payload.summary or "").strip() or None
        industry = _normalize_industry(payload.industry)
        source = (payload.sourceName or "").strip() or None

        if kind == "video":
            if not youtube_id_from(url or ""):
                raise HTTPException(status_code=400, detail="Enter a YouTube link or an 11-character video id")
            source = source or "YouTube"
        elif kind == "news":
            if not url or not url.startswith("http"):
                raise HTTPException(status_code=400, detail="News items need a link")
        elif not body and not url:
            raise HTTPException(status_code=400, detail="Add a write-up or a link")

        row.kind = kind
        row.title = title
        row.summary = summary
        row.url = url
        row.thumbnail_url = thumbnail_for(url, payload.thumbnailUrl)
        row.industry = industry
        row.source_name = source
        row.body = body
        row.is_active = bool(payload.active)
        row.sort_order = int(payload.sortOrder or 0)

    def _get_or_404(self, resource_id: str) -> OwnerResource:
        row = self.db.query(OwnerResource).filter(OwnerResource.id == resource_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Resource not found")
        return row

    def _to_dto(self, row: OwnerResource) -> ResourceItemResponse:
        return ResourceItemResponse(
            id=row.id,
            kind=row.kind if row.kind in _KINDS else "other",
            title=row.title,
            summary=row.summary,
            url=row.url,
            youtubeId=youtube_id_from(row.url or ""),
            thumbnailUrl=thumbnail_for(row.url, row.thumbnail_url),
            industry=row.industry,
            sourceName=row.source_name,
            body=row.body,
            active=bool(row.is_active),
            sortOrder=int(row.sort_order or 0),
            publishedAt=row.published_at.isoformat() if row.published_at else None,
        )


def fetch_trending_news(industry: Optional[str]) -> list:
    key = (industry or "").strip() or "*"
    now = datetime.now(timezone.utc).timestamp()
    cached = _NEWS_CACHE.get(key)
    if cached and now - cached[0] < _NEWS_TTL_SECONDS:
        return cached[1]
    try:
        response = requests.get(
            news_rss_url(industry),
            timeout=4,
            headers={"User-Agent": "AutobusOwnerResources/1.0"},
        )
        response.raise_for_status()
        items = parse_news_rss(response.text, industry=industry or None, limit=6)
    except Exception as exc:
        logger.warning("Trending news fetch failed: %s", exc)
        items = cached[1] if cached else []
    else:
        _NEWS_CACHE[key] = (now, items)
    return items


def seed_owner_resources(db: Session) -> int:
    """Insert catalogue rows that are not already stored. Existing rows are left as the admin edited them."""
    wanted = list(SEED_RESOURCES)
    ids = [item["id"] for item in wanted]
    existing = {
        row_id
        for (row_id,) in db.query(OwnerResource.id).filter(OwnerResource.id.in_(ids)).all()
    }
    added = 0
    now = datetime.now(timezone.utc)
    for index, item in enumerate(wanted):
        if item["id"] in existing:
            continue
        db.add(
            OwnerResource(
                id=item["id"],
                kind=item["kind"],
                title=item["title"],
                summary=item.get("summary"),
                url=item.get("url"),
                thumbnail_url=item.get("thumbnail_url"),
                industry=item.get("industry"),
                source_name=item.get("source_name"),
                body=item.get("body"),
                is_active=True,
                sort_order=int(item.get("sort_order") or 0),
                published_at=now - timedelta(seconds=index),
            )
        )
        added += 1
    if added:
        db.commit()
    return added


def _normalize_industry(raw: Optional[str]) -> Optional[str]:
    value = (raw or "").strip()
    if not value or value.casefold() in {"all", "all niches"}:
        return None
    for option in ONBOARDING_INDUSTRY_OPTIONS:
        if option.casefold() == value.casefold():
            return option
    raise HTTPException(status_code=400, detail="Pick an industry from the list, or leave it open to every business")


def _dto_from_mapping(item: dict) -> ResourceItemResponse:
    published = item.get("published_at")
    return ResourceItemResponse(
        id=item["id"],
        kind="news",
        title=item["title"],
        summary=item.get("summary"),
        url=item.get("url"),
        youtubeId=None,
        thumbnailUrl=item.get("thumbnail_url"),
        industry=item.get("industry"),
        sourceName=item.get("source_name"),
        body=None,
        active=True,
        sortOrder=int(item.get("sort_order") or 0),
        publishedAt=published.isoformat() if isinstance(published, datetime) else None,
    )

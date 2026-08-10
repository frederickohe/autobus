"""Publish media to Instagram via Instagram Graph Content Publishing API."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from core.instagram.model.InstagramAccount import InstagramAccount
from core.instagram.service.instagram_oauth_service import InstagramOAuthService

logger = logging.getLogger(__name__)

GRAPH_VERSION = "v21.0"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _path_ext(url: str) -> str:
    path = urlparse(url).path.lower()
    for ext in VIDEO_EXTENSIONS | IMAGE_EXTENSIONS:
        if path.endswith(ext):
            return ext
    # query-stripped guess from last segment
    name = path.rsplit("/", 1)[-1]
    if "." in name:
        return "." + name.rsplit(".", 1)[-1].lower()
    return ""


def is_video_url(url: str) -> bool:
    return _path_ext(url) in VIDEO_EXTENSIONS


class InstagramPublishService:
    """Create + publish Instagram media containers for a linked Autobus account."""

    def __init__(self) -> None:
        self._oauth = InstagramOAuthService()
        self.graph_base = f"{self._oauth.graph_base}/{GRAPH_VERSION}"

    def _token(self, account: InstagramAccount) -> str:
        return self._oauth.decrypt_token(account.access_token_encrypted)

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        resp = requests.request(
            method,
            url,
            params=params,
            data=data,
            timeout=timeout,
        )
        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:500]}
        if resp.status_code >= 400:
            err = body.get("error") if isinstance(body, dict) else None
            detail = ""
            if isinstance(err, dict):
                detail = err.get("message") or err.get("error_user_msg") or str(err)
            else:
                detail = str(body)[:400]
            logger.error(
                "[IG publish] %s %s failed (%s): %s",
                method,
                url,
                resp.status_code,
                detail,
            )
            raise RuntimeError(detail or f"Instagram API error ({resp.status_code})")
        if not isinstance(body, dict):
            return {"value": body}
        return body

    def _create_image_container(
        self,
        *,
        ig_user_id: str,
        token: str,
        image_url: str,
        caption: Optional[str] = None,
        is_carousel_item: bool = False,
    ) -> str:
        data: Dict[str, Any] = {
            "image_url": image_url,
            "access_token": token,
        }
        if is_carousel_item:
            data["is_carousel_item"] = "true"
        elif caption:
            data["caption"] = caption
        result = self._request(
            "POST",
            f"{self.graph_base}/{ig_user_id}/media",
            data=data,
        )
        creation_id = str(result.get("id") or "").strip()
        if not creation_id:
            raise RuntimeError(f"Instagram did not return a media container id: {result}")
        return creation_id

    def _create_video_container(
        self,
        *,
        ig_user_id: str,
        token: str,
        video_url: str,
        caption: Optional[str] = None,
    ) -> str:
        data: Dict[str, Any] = {
            "media_type": "REELS",
            "video_url": video_url,
            "access_token": token,
            "share_to_feed": "true",
        }
        if caption:
            data["caption"] = caption
        result = self._request(
            "POST",
            f"{self.graph_base}/{ig_user_id}/media",
            data=data,
        )
        creation_id = str(result.get("id") or "").strip()
        if not creation_id:
            raise RuntimeError(f"Instagram did not return a video container id: {result}")
        return creation_id

    def _create_carousel_container(
        self,
        *,
        ig_user_id: str,
        token: str,
        child_ids: List[str],
        caption: Optional[str] = None,
    ) -> str:
        data: Dict[str, Any] = {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "access_token": token,
        }
        if caption:
            data["caption"] = caption
        result = self._request(
            "POST",
            f"{self.graph_base}/{ig_user_id}/media",
            data=data,
        )
        creation_id = str(result.get("id") or "").strip()
        if not creation_id:
            raise RuntimeError(f"Instagram did not return a carousel container id: {result}")
        return creation_id

    def _wait_for_container(self, creation_id: str, token: str, *, max_wait_s: int = 120) -> None:
        """Poll until FINISHED (required for video / carousel children)."""
        deadline = time.time() + max_wait_s
        while time.time() < deadline:
            result = self._request(
                "GET",
                f"{self.graph_base}/{creation_id}",
                params={
                    "fields": "status_code,status",
                    "access_token": token,
                },
            )
            status = str(result.get("status_code") or "").upper()
            if status in ("FINISHED", "PUBLISHED"):
                return
            if status in ("ERROR", "EXPIRED"):
                raise RuntimeError(
                    f"Instagram media container failed ({status}): {result.get('status') or result}"
                )
            time.sleep(3)
        raise RuntimeError("Timed out waiting for Instagram to process media")

    def _publish(self, *, ig_user_id: str, token: str, creation_id: str) -> str:
        result = self._request(
            "POST",
            f"{self.graph_base}/{ig_user_id}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": token,
            },
        )
        post_id = str(result.get("id") or "").strip()
        if not post_id:
            raise RuntimeError(f"Instagram publish returned no post id: {result}")
        return post_id

    def publish(
        self,
        account: InstagramAccount,
        *,
        caption: str,
        media_urls: List[str],
    ) -> Dict[str, Any]:
        if not account.publishing_enabled:
            raise RuntimeError("Publishing is disabled for this Instagram account")

        urls = [u.strip() for u in media_urls if u and str(u).strip()]
        if not urls:
            raise RuntimeError(
                "Instagram requires at least one public image or video URL to publish"
            )

        token = self._token(account)
        ig_user_id = account.ig_user_id
        caption_text = (caption or "").strip()

        videos = [u for u in urls if is_video_url(u)]
        images = [u for u in urls if not is_video_url(u)]

        if videos and images:
            # Prefer a single reel when mixed; Instagram carousel can't mix video+image easily
            # in Instagram Login flow for all account types.
            raise RuntimeError(
                "Instagram publish supports either images or one video per post, not both"
            )

        if videos:
            if len(videos) > 1:
                raise RuntimeError("Instagram supports one video/reel per post")
            creation_id = self._create_video_container(
                ig_user_id=ig_user_id,
                token=token,
                video_url=videos[0],
                caption=caption_text or None,
            )
            self._wait_for_container(creation_id, token)
            post_id = self._publish(
                ig_user_id=ig_user_id, token=token, creation_id=creation_id
            )
            return {
                "post_id": post_id,
                "creation_id": creation_id,
                "media_type": "REELS",
            }

        if len(images) == 1:
            creation_id = self._create_image_container(
                ig_user_id=ig_user_id,
                token=token,
                image_url=images[0],
                caption=caption_text or None,
            )
            post_id = self._publish(
                ig_user_id=ig_user_id, token=token, creation_id=creation_id
            )
            return {
                "post_id": post_id,
                "creation_id": creation_id,
                "media_type": "IMAGE",
            }

        # Carousel (2–10 images)
        if len(images) > 10:
            images = images[:10]
        child_ids: List[str] = []
        for url in images:
            child_id = self._create_image_container(
                ig_user_id=ig_user_id,
                token=token,
                image_url=url,
                is_carousel_item=True,
            )
            child_ids.append(child_id)
        for child_id in child_ids:
            self._wait_for_container(child_id, token, max_wait_s=60)
        creation_id = self._create_carousel_container(
            ig_user_id=ig_user_id,
            token=token,
            child_ids=child_ids,
            caption=caption_text or None,
        )
        self._wait_for_container(creation_id, token, max_wait_s=60)
        post_id = self._publish(
            ig_user_id=ig_user_id, token=token, creation_id=creation_id
        )
        return {
            "post_id": post_id,
            "creation_id": creation_id,
            "media_type": "CAROUSEL",
            "children": child_ids,
        }

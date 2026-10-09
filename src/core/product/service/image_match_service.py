"""Match a customer photo to one merchant's catalogue.

Exact: the photo is a catalogue image, or a copy Autobus posted (short code
AB-XXXX and the hash of that stamped file).
Related: the photo came from somewhere else and looks like one or more products.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from typing import Dict, Iterable, List, Optional, Sequence
from urllib.parse import unquote, urlparse

import requests
from sqlalchemy.orm import Session, joinedload

from core.product.model.product import Product, ProductImage
from core.product.media import media_looks_like_video
from core.product.service.image_fingerprint import (
    EXACT_HAMMING,
    MAX_RELATED,
    RELATED_COSINE,
    best_hash_distance,
    cosine,
    dhash_hex,
    find_match_code,
    new_match_code,
    open_image,
    stamp_jpeg_bytes,
    visual_vector,
)
from core.product.service.image_match import MatchDecision, MatchHit

logger = logging.getLogger(__name__)

_INDEX_BUDGET_SECONDS = 5.0
_DOWNLOAD_TIMEOUT_SECONDS = 4
_MAX_IMAGE_BYTES = 15 * 1024 * 1024
_backfill_lock = threading.Lock()
_backfill_threads: Dict[str, threading.Thread] = {}


def _url_path(url: str) -> str:
    return unquote(urlparse(url or "").path).rstrip("/").lower()


def _same_object(left: str, right: str) -> bool:
    a = _url_path(left)
    b = _url_path(right)
    if not a or not b:
        return False
    return a == b or a.endswith(b) or b.endswith(a)


class ImageMatchService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_match_code(self, image: ProductImage, reserved: Optional[set] = None) -> str:
        existing = (getattr(image, "match_code", None) or "").strip().upper()
        if find_match_code(existing):
            return existing
        taken = reserved if reserved is not None else set()
        for _ in range(8):
            code = new_match_code()
            if code in taken:
                continue
            clash = (
                self.db.query(ProductImage.image_id)
                .filter(ProductImage.match_code == code)
                .first()
            )
            if clash is None:
                image.match_code = code
                taken.add(code)
                return code
        code = new_match_code()
        image.match_code = code
        taken.add(code)
        return code

    def assign_codes(self, images: Iterable[ProductImage]) -> None:
        reserved: set = set()
        for image in images:
            try:
                self.ensure_match_code(image, reserved)
            except Exception as exc:
                logger.warning("[IMAGE_MATCH] Could not assign match code: %s", exc)

    def index_bytes(self, image: ProductImage, data: bytes) -> bool:
        opened = open_image(data)
        if opened is None:
            return False
        self.ensure_match_code(image)
        image.phash = dhash_hex(opened)
        image.visual_vector = json.dumps(list(visual_vector(opened)))
        return True

    def index_url(self, image: ProductImage) -> bool:
        if media_looks_like_video(image.url or ""):
            return False
        data = _download(image.url)
        if not data:
            return False
        return self.index_bytes(image, data)

    def index_product(self, product_id: str, *, budget_seconds: float = _INDEX_BUDGET_SECONDS) -> int:
        try:
            product_uuid = uuid.UUID(str(product_id))
        except ValueError:
            return 0
        rows = (
            self.db.query(ProductImage)
            .filter(ProductImage.product_id == product_uuid)
            .all()
        )
        return self._index_missing(rows, budget_seconds=budget_seconds)

    def match(
        self,
        owner_user_id: str,
        image_bytes: bytes,
        allowed_product_ids: Optional[Iterable[str]] = None,
        ocr_text: str = "",
    ) -> MatchDecision:
        opened = open_image(image_bytes)
        if opened is None or not owner_user_id:
            return MatchDecision()
        if allowed_product_ids is not None and not any(allowed_product_ids):
            return MatchDecision()

        allowed = {str(item) for item in (allowed_product_ids or []) if item}
        rows = self._catalogue_images(owner_user_id, allowed)
        if any(not (row.phash or "").strip() for row in rows):
            self._index_missing(rows, budget_seconds=_INDEX_BUDGET_SECONDS)
            self.db.expire_all()
            rows = self._catalogue_images(owner_user_id, allowed)

        code = find_match_code(ocr_text)
        if code:
            for row in rows:
                if (row.match_code or "").upper() == code and row.product is not None:
                    return MatchDecision(kind="exact", hits=[_hit_from_row(row, 1.0)])

        query_hash = dhash_hex(opened)
        query_vector = visual_vector(opened)
        exact_row = None
        exact_distance = EXACT_HAMMING + 1
        scored: Dict[str, tuple] = {}
        for row in rows:
            if row.product is None:
                continue
            distance = best_hash_distance(
                query_hash, (row.phash or "", row.published_phash or "")
            )
            if distance is not None and distance < exact_distance:
                exact_distance = distance
                exact_row = row
            similarity = cosine(query_vector, _parse_vector(row.visual_vector))
            if similarity is None:
                continue
            product_key = str(row.product_id)
            previous = scored.get(product_key)
            if previous is None or similarity > previous[0]:
                scored[product_key] = (similarity, row)

        if exact_row is not None and exact_distance <= EXACT_HAMMING:
            logger.info(
                "[IMAGE_MATCH] Exact photo match product=%s distance=%s",
                exact_row.product_id,
                exact_distance,
            )
            return MatchDecision(kind="exact", hits=[_hit_from_row(exact_row, 1.0)])

        ranked = sorted(scored.values(), key=lambda item: item[0], reverse=True)
        related = [
            _hit_from_row(row, score)
            for score, row in ranked
            if score >= RELATED_COSINE
        ][:MAX_RELATED]
        if related:
            logger.info(
                "[IMAGE_MATCH] Related products %s",
                [(hit.product_id, round(hit.score, 3)) for hit in related],
            )
            return MatchDecision(kind="related", hits=related)
        return MatchDecision()

    def find_by_code(
        self,
        owner_user_id: str,
        code: str,
        allowed_product_ids: Optional[Iterable[str]] = None,
    ) -> Optional[MatchHit]:
        normalized = find_match_code(code)
        if not normalized or not owner_user_id:
            return None
        if allowed_product_ids is not None and not any(allowed_product_ids):
            return None
        allowed = {str(item) for item in (allowed_product_ids or []) if item}
        for row in self._catalogue_images(owner_user_id, allowed):
            if (row.match_code or "").upper() == normalized and row.product is not None:
                return _hit_from_row(row, 1.0)
        return None

    def stamp_for_source(self, jpeg_bytes: bytes, source_url: str) -> bytes:
        image = self._find_by_source_url(source_url)
        if image is None:
            return jpeg_bytes
        code = self.ensure_match_code(image)
        stamped = stamp_jpeg_bytes(jpeg_bytes, code)
        if not stamped:
            return jpeg_bytes
        opened = open_image(stamped)
        if opened is not None:
            image.published_phash = dhash_hex(opened)
        self.db.commit()
        logger.info("[IMAGE_MATCH] Stamped %s on published image %s", code, image.image_id)
        return stamped

    def _catalogue_images(
        self, owner_user_id: str, allowed: set
    ) -> List[ProductImage]:
        query = (
            self.db.query(ProductImage)
            .join(Product, Product.product_id == ProductImage.product_id)
            .options(joinedload(ProductImage.product))
            .filter(Product.user_id == owner_user_id, Product.is_active.is_(True))
        )
        if allowed:
            uuids = []
            for item in allowed:
                try:
                    uuids.append(uuid.UUID(str(item)))
                except ValueError:
                    continue
            if not uuids:
                return []
            query = query.filter(Product.product_id.in_(uuids))
        rows = query.all()
        return [row for row in rows if not media_looks_like_video(row.url or "")]

    def _index_missing(self, rows: Sequence[ProductImage], *, budget_seconds: float) -> int:
        deadline = time.monotonic() + budget_seconds
        indexed = 0
        changed = False
        for row in rows:
            if time.monotonic() >= deadline:
                break
            if (row.phash or "").strip() and (row.visual_vector or "").strip():
                continue
            if media_looks_like_video(row.url or ""):
                continue
            try:
                if self.index_url(row):
                    indexed += 1
                    changed = True
            except Exception as exc:
                logger.warning("[IMAGE_MATCH] Index failed for %s: %s", row.image_id, exc)
        if changed:
            try:
                self.db.commit()
            except Exception as exc:
                self.db.rollback()
                logger.warning("[IMAGE_MATCH] Could not save fingerprints: %s", exc)
                return 0
        return indexed

    def _find_by_source_url(self, source_url: str) -> Optional[ProductImage]:
        name = _url_path(source_url).rsplit("/", 1)[-1]
        if len(name) < 5 or any(ch in name for ch in "%_\\'\""):
            return None
        rows = (
            self.db.query(ProductImage)
            .filter(ProductImage.url.ilike(f"%{name}%"))
            .limit(20)
            .all()
        )
        for row in rows:
            if _same_object(row.url, source_url):
                return row
        return None


def _hit_from_row(row: ProductImage, score: float) -> MatchHit:
    product = row.product
    price = getattr(product, "price", None)
    return MatchHit(
        product_id=str(row.product_id),
        name=(getattr(product, "name", None) or "").strip(),
        price="" if price is None else str(price),
        image_url=row.url or getattr(product, "photo", None) or "",
        score=score,
    )


def _parse_vector(raw: Optional[str]) -> tuple:
    if not raw:
        return tuple()
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return tuple()
    if not isinstance(data, list) or len(data) != 64:
        return tuple()
    try:
        return tuple(float(item) for item in data)
    except (TypeError, ValueError):
        return tuple()


def _download(url: str) -> Optional[bytes]:
    target = (url or "").strip()
    if not target:
        return None
    try:
        from core.cloudstorage.service.storageservice import refresh_public_object_url

        target = refresh_public_object_url(target) or target
    except Exception as exc:
        logger.debug("[IMAGE_MATCH] URL refresh skipped: %s", exc)
    try:
        response = requests.get(
            target,
            timeout=_DOWNLOAD_TIMEOUT_SECONDS,
            headers={"User-Agent": "AutobusImageMatch/1.0"},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("[IMAGE_MATCH] Could not download catalogue image: %s", exc)
        return None
    data = response.content or b""
    if not data or len(data) > _MAX_IMAGE_BYTES:
        return None
    return data


def schedule_product_image_index(product_id: str, data: Optional[bytes] = None, image_id: Optional[str] = None) -> None:
    """Fingerprint gallery images after a product save, without blocking the request."""
    product_key = str(product_id or "").strip()
    if not product_key and not image_id:
        return
    payload = data

    def _run() -> None:
        from utilities.dbconfig import SessionLocal

        db = SessionLocal()
        try:
            service = ImageMatchService(db)
            if image_id and payload:
                try:
                    image_uuid = uuid.UUID(str(image_id))
                except ValueError:
                    return
                image = db.query(ProductImage).filter(ProductImage.image_id == image_uuid).first()
                if image is None:
                    return
                if service.index_bytes(image, payload):
                    db.commit()
                return
            service.index_product(product_key, budget_seconds=30)
        except Exception as exc:
            logger.warning("[IMAGE_MATCH] Background index failed: %s", exc)
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            db.close()

    thread_key = image_id or product_key
    with _backfill_lock:
        current = _backfill_threads.get(thread_key)
        if current is not None and current.is_alive():
            return
        thread = threading.Thread(target=_run, name=f"image-index-{thread_key}", daemon=True)
        _backfill_threads[thread_key] = thread
        thread.start()


def match_customer_image(
    owner_user_id: str,
    image_bytes: bytes,
    allowed_product_ids: Optional[Iterable[str]] = None,
    ocr_text: str = "",
) -> MatchDecision:
    from utilities.dbconfig import SessionLocal

    db = SessionLocal()
    try:
        return ImageMatchService(db).match(
            owner_user_id,
            image_bytes,
            allowed_product_ids=allowed_product_ids,
            ocr_text=ocr_text,
        )
    except Exception as exc:
        logger.warning("[IMAGE_MATCH] Match failed: %s", exc)
        return MatchDecision()
    finally:
        db.close()


def lookup_match_code(
    owner_user_id: str,
    code: str,
    allowed_product_ids: Optional[Iterable[str]] = None,
) -> Optional[MatchHit]:
    from utilities.dbconfig import SessionLocal

    db = SessionLocal()
    try:
        return ImageMatchService(db).find_by_code(
            owner_user_id, code, allowed_product_ids=allowed_product_ids
        )
    except Exception as exc:
        logger.warning("[IMAGE_MATCH] Code lookup failed: %s", exc)
        return None
    finally:
        db.close()


def stamp_outbound_jpeg(jpeg_bytes: bytes, source_url: str) -> bytes:
    """Stamp the product code onto a file Autobus is about to publish."""
    from utilities.dbconfig import SessionLocal

    db = SessionLocal()
    try:
        return ImageMatchService(db).stamp_for_source(jpeg_bytes, source_url)
    except Exception as exc:
        logger.warning("[IMAGE_MATCH] Could not stamp outbound image: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return jpeg_bytes
    finally:
        db.close()

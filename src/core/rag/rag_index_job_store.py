"""Redis-backed progress store for long-running RAG index jobs."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import redis
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_JOB_TTL_SECONDS = 3600
_KEY_PREFIX = "rag_index_job:"


class RagIndexJobStatus(str, Enum):
    pending = "pending"
    validating = "validating"
    uploading = "uploading"
    scraping = "scraping"
    extracting = "extracting"
    chunking = "chunking"
    indexing = "indexing"
    completed = "completed"
    failed = "failed"


class RagIndexJobRecord(BaseModel):
    job_id: str
    user_subject: str
    status: RagIndexJobStatus = RagIndexJobStatus.pending
    progress: int = Field(default=0, ge=0, le=100)
    message: str = "Queued"
    source_type: str = "file"
    source_label: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RagIndexJobStore:
    def __init__(self) -> None:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD") or None
        self._redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            db=0,
            decode_responses=True,
            socket_connect_timeout=5,
        )

    def create_job(
        self,
        *,
        user_subject: str,
        source_type: str,
        source_label: Optional[str] = None,
    ) -> RagIndexJobRecord:
        job_id = str(uuid.uuid4())
        record = RagIndexJobRecord(
            job_id=job_id,
            user_subject=user_subject,
            source_type=source_type,
            source_label=source_label,
        )
        self._save(record)
        return record

    def get_job(self, job_id: str) -> Optional[RagIndexJobRecord]:
        raw = self._redis.get(f"{_KEY_PREFIX}{job_id}")
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return RagIndexJobRecord.model_validate(data)
        except Exception:
            logger.warning("Invalid RAG job payload for %s", job_id, exc_info=True)
            return None

    def update_job(
        self,
        job_id: str,
        *,
        status: Optional[RagIndexJobStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[RagIndexJobRecord]:
        record = self.get_job(job_id)
        if not record:
            return None
        if status is not None:
            record.status = status
        if progress is not None:
            record.progress = max(0, min(100, progress))
        if message is not None:
            record.message = message
        if result is not None:
            record.result = result
        if error is not None:
            record.error = error
        record.updated_at = datetime.now(timezone.utc)
        self._save(record)
        return record

    def _save(self, record: RagIndexJobRecord) -> None:
        payload = record.model_dump(mode="json")
        self._redis.setex(
            f"{_KEY_PREFIX}{record.job_id}",
            _JOB_TTL_SECONDS,
            json.dumps(payload, default=str),
        )

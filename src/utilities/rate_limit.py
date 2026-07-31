"""Redis-backed fixed-window rate limiting for FastAPI."""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Callable, List, Optional, Pattern, Tuple

import redis
from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# (path_regex, max_requests, window_seconds) — first match wins
RateRule = Tuple[Pattern[str], int, int]

_redis_client: Optional[redis.Redis] = None


def _redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD") or None
        client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=0,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as e:
        logger.warning("Rate limiter Redis unavailable: %s", e)
        return None


def client_ip(request: Request) -> str:
    """Prefer edge-forwarded client IP (Caddy sets X-Real-IP / X-Forwarded-For)."""
    xff = request.headers.get("X-Forwarded-For") or ""
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    real = (request.headers.get("X-Real-IP") or "").strip()
    if real:
        return real
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def hit(bucket: str, *, limit: int, window_seconds: int) -> Tuple[bool, int, int]:
    """
    Increment a fixed window counter.

    Returns (allowed, remaining, retry_after_seconds).
    """
    if limit <= 0:
        return True, limit, 0

    r = _redis()
    if r is None:
        # Fail open so Redis outages do not take down the API; edge still has TLS.
        return True, limit, 0

    key = f"rl:{bucket}"
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = pipe.execute()
        if ttl is None or ttl < 0:
            r.expire(key, window_seconds)
            ttl = window_seconds
        if int(count) > limit:
            return False, 0, max(int(ttl), 1)
        return True, max(limit - int(count), 0), max(int(ttl), 0)
    except Exception as e:
        logger.warning("Rate limit Redis error: %s", e)
        return True, limit, 0


def rate_limit_dependency(*, scope: str, limit: int, window_seconds: int = 60):
    """FastAPI Depends() factory for per-route limits."""

    def _dep(request: Request) -> None:
        enabled = os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if not enabled:
            return
        ip = client_ip(request)
        allowed, remaining, retry_after = hit(
            f"{scope}:{ip}",
            limit=limit,
            window_seconds=window_seconds,
        )
        request.state.rate_limit_remaining = remaining
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

    return _dep


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def default_rules() -> List[RateRule]:
    """Path-prefix rules (most specific first). Limits are per client IP per window."""
    win = _env_int("RATE_LIMIT_WINDOW_SECONDS", 60)
    return [
        (re.compile(r"^/api/v1/otp/send"), _env_int("RATE_LIMIT_OTP_SEND", 5), win),
        (re.compile(r"^/api/v1/otp/verify"), _env_int("RATE_LIMIT_OTP_VERIFY", 15), win),
        (re.compile(r"^/api/v1/otp/test-sms"), _env_int("RATE_LIMIT_OTP_TEST", 3), win),
        (re.compile(r"^/api/v1/auth/signin"), _env_int("RATE_LIMIT_AUTH_SIGNIN", 10), win),
        (re.compile(r"^/api/v1/auth/signup"), _env_int("RATE_LIMIT_AUTH_SIGNUP", 5), win),
        (re.compile(r"^/api/v1/auth/no-auth/reset-password"), _env_int("RATE_LIMIT_AUTH_RESET", 5), win),
        (re.compile(r"^/api/v1/auth/refresh"), _env_int("RATE_LIMIT_AUTH_REFRESH", 30), win),
        (re.compile(r"^/api/v1/auth/verify"), _env_int("RATE_LIMIT_AUTH_VERIFY", 10), win),
        (re.compile(r"^/api/v1/auth/"), _env_int("RATE_LIMIT_AUTH", 40), win),
        (re.compile(r"^/api/v1/webhooks/send-whatsapp"), _env_int("RATE_LIMIT_WEBHOOK_WA", 10), win),
        (re.compile(r"^/api/v1/webhooks/company-lookup"), _env_int("RATE_LIMIT_WEBHOOK_LOOKUP", 30), win),
        (re.compile(r"^/api/v1/webhooks/start-dialog"), _env_int("RATE_LIMIT_WEBHOOK_CHAT", 60), win),
        (re.compile(r"^/api/v1/webhooks/"), _env_int("RATE_LIMIT_WEBHOOK", 90), win),
        (re.compile(r"^/api/v1/agent/"), _env_int("RATE_LIMIT_AGENT", 30), win),
        (re.compile(r"^/api/v1/nlu/"), _env_int("RATE_LIMIT_NLU", 40), win),
        (re.compile(r"^/api/v1/"), _env_int("RATE_LIMIT_GLOBAL", 180), win),
    ]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply Redis fixed-window limits by path + client IP."""

    def __init__(self, app, rules: Optional[List[RateRule]] = None):
        super().__init__(app)
        self.rules = rules if rules is not None else default_rules()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        enabled = os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        if not enabled or request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path or "/"
        # Health checks should never be throttled
        if path in ("/health", "/api/v1/health") or path.endswith("/health"):
            return await call_next(request)

        matched: Optional[Tuple[int, int, str]] = None
        for pattern, limit, window in self.rules:
            if pattern.search(path):
                matched = (limit, window, pattern.pattern)
                break

        if matched is None:
            return await call_next(request)

        limit, window, rule_name = matched
        ip = client_ip(request)
        # Bucket includes rule identity so overlapping prefixes don't share counters incorrectly
        bucket = f"mw:{rule_name}:{ip}"
        allowed, remaining, retry_after = hit(bucket, limit=limit, window_seconds=window)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

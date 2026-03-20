import time
from collections import defaultdict, deque

import redis
from fastapi import HTTPException, Request, status

from app.config import get_settings

settings = get_settings()

_memory_store: dict[str, deque[float]] = defaultdict(deque)
_redis_client: redis.Redis | None = None


def _get_redis_client() -> redis.Redis | None:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            _redis_client = None
    return _redis_client


def _extract_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _key(scope: str, request: Request, user_id: str | None = None) -> str:
    ip = _extract_ip(request)
    return f"rate_limit:{scope}:{user_id or 'anon'}:{ip}"


def _increment_memory(key: str, window_seconds: int) -> int:
    now = time.time()
    bucket = _memory_store[key]
    while bucket and bucket[0] <= now - window_seconds:
        bucket.popleft()
    bucket.append(now)
    return len(bucket)


def enforce_rate_limit(
    request: Request,
    scope: str,
    limit: int,
    window_seconds: int,
    user_id: str | None = None,
) -> None:
    key = _key(scope, request, user_id=user_id)
    current = None
    client = _get_redis_client()

    if client is not None:
        try:
            pipeline = client.pipeline()
            pipeline.incr(key)
            pipeline.expire(key, window_seconds, nx=True)
            current, _ = pipeline.execute()
            current = int(current)
        except Exception:
            current = None

    if current is None:
        current = _increment_memory(key, window_seconds)

    if current > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "detail": "Too many requests. Please wait and try again.",
                "code": "RATE_LIMITED",
            },
        )

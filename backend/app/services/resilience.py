import asyncio
import random
import time
from typing import Callable, TypeVar

import httpx

T = TypeVar("T")


def _is_retryable_http_error(exc: Exception) -> bool:
    if isinstance(exc, (httpx.RequestError, httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status in {408, 429} or status >= 500
    return False


def with_http_retries(
    fn: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 0.4,
    max_delay: float = 2.0,
) -> T:
    last_exc: Exception | None = None
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if not _is_retryable_http_error(exc):
                raise

        if attempt < attempts:
            jitter = random.uniform(0, 0.2)
            delay = min(base_delay * (2 ** (attempt - 1)) + jitter, max_delay)
            time.sleep(delay)

    assert last_exc is not None
    raise last_exc


async def with_http_retries_async(
    fn: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 0.4,
    max_delay: float = 2.0,
) -> T:
    last_exc: Exception | None = None
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if not _is_retryable_http_error(exc):
                raise

        if attempt < attempts:
            jitter = random.uniform(0, 0.2)
            delay = min(base_delay * (2 ** (attempt - 1)) + jitter, max_delay)
            await asyncio.sleep(delay)

    assert last_exc is not None
    raise last_exc

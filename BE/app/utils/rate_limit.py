"""Simple in-memory rate limiter utilities."""
import time
from collections import defaultdict, deque
from typing import Deque, DefaultDict

from fastapi import Request, HTTPException, status

WINDOW_SECONDS = 60  # 1 minute window
MAX_REQUESTS = 100   # 100 requests per window


class RateLimiter:
    """In-memory sliding window limiter keyed by client identifier."""

    def __init__(self):
        self._requests: DefaultDict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str):
        now = time.time()
        window_start = now - WINDOW_SECONDS
        timestamps = self._requests[key]

        # Drop timestamps outside the current window
        while timestamps and timestamps[0] < window_start:
            timestamps.popleft()

        if len(timestamps) >= MAX_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many schedule requests, please try again later"
                    }
                }
            )

        timestamps.append(now)


schedule_rate_limiter = RateLimiter()


async def enforce_schedule_rate_limit(request: Request):
    """FastAPI dependency enforcing 100 requests/minute per client IP."""
    client_ip = request.client.host if request.client else "unknown"
    schedule_rate_limiter.check(client_ip)

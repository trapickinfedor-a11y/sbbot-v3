"""
Simple in-memory rate limiter for FastAPI.

Usage:
    from web_panel.utils.rate_limiter import RateLimiter

    seller_limiter = RateLimiter(max_calls=30, window_seconds=60)

    @router.get("/some-endpoint")
    async def handler(
        seller_actor: ... = Depends(get_current_seller_from_webapp),
        _: None = Depends(seller_limiter.by_seller_id(lambda req, actor: actor.seller.id)),
    ):
        ...
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable, Any

from fastapi import HTTPException, Request


class RateLimiter:
    """Token-bucket style rate limiter using a sliding window per key."""

    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        # key -> deque of timestamps
        self._calls: dict[Any, deque] = defaultdict(deque)

    def _is_allowed(self, key: Any) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        q = self._calls[key]
        # Evict stale entries
        while q and q[0] < window_start:
            q.popleft()
        if len(q) >= self.max_calls:
            return False
        q.append(now)
        return True

    def by_ip(self) -> Callable:
        """Returns a FastAPI Depends-compatible callable keyed by client IP."""
        limiter = self

        async def _dep(request: Request) -> None:
            ip = request.client.host if request.client else "unknown"
            if not limiter._is_allowed(ip):
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded: max {limiter.max_calls} requests per {limiter.window_seconds}s",
                )

        return _dep

    def by_key(self, key_fn: Callable[..., Any]) -> Callable:
        """
        Returns a FastAPI Depends-compatible callable that derives the key via key_fn.
        key_fn receives (request, *args) — all positional args from Depends chain.
        """
        limiter = self

        async def _dep(request: Request) -> None:
            key = key_fn(request)
            if not limiter._is_allowed(key):
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded: max {limiter.max_calls} requests per {limiter.window_seconds}s",
                )

        return _dep


# Pre-configured limiters
# 60 req/min per IP for general endpoints
general_ip_limiter = RateLimiter(max_calls=60, window_seconds=60)

# 10 req/min per IP for auth endpoints
auth_ip_limiter = RateLimiter(max_calls=10, window_seconds=60)

# 30 req/min per seller_id (used inside seller_mini_app with a custom dep)
seller_mini_app_limiter = RateLimiter(max_calls=30, window_seconds=60)

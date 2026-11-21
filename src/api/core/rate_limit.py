"""
Fixed-window, in-process rate limiter for the public auth endpoints.

The API runs as a single process (one uvicorn worker), so in-memory counters are enough and avoid
a Redis dependency. If the API is ever scaled to several workers, move this to a shared store.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import math
import threading
import time


@dataclass(frozen=True, slots=True)
class RateRule:
    limit: int
    window_seconds: int


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Too many requests")
        self.retry_after_seconds = retry_after_seconds


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic, max_keys: int = 50_000) -> None:
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, tuple[float, int]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, rule: RateRule) -> None:
        """Counts one attempt for `key`; raises RateLimitExceeded once the window's limit is used up."""
        now = self._clock()
        with self._lock:
            window_start, count = self._hits.get(key, (now, 0))
            if now - window_start >= rule.window_seconds:
                window_start, count = now, 0
            if count >= rule.limit:
                retry = math.ceil(rule.window_seconds - (now - window_start))
                raise RateLimitExceeded(max(1, retry))
            self._hits[key] = (window_start, count + 1)
            if len(self._hits) > self._max_keys:
                self._evict_expired(now, rule.window_seconds)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def _evict_expired(self, now: float, window_seconds: int) -> None:
        expired = [k for k, (start, _) in self._hits.items() if now - start >= window_seconds]
        for key in expired:
            del self._hits[key]

"""
Request authentication, applied to every route by default.

`authenticate_request` is registered as an app-wide dependency, so a new route is protected even if
its author forgets to ask for auth. Only endpoints decorated with `@public` skip it, and
tests/test_route_guard.py fails if any route outside the reviewed allowlist is public.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import threading
import time
from typing import TypeVar
import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from src.api.core.config import AppSettings
from src.api.core.rate_limit import RateLimiter, RateLimitExceeded, RateRule
from src.api.core.security import InvalidTokenError, decode_access_token
from src.api.db.models import User, utc_now
from src.api.mail.sender import EmailSender

PUBLIC_ATTR = "__solarsense_public__"
_Endpoint = TypeVar("_Endpoint", bound=Callable[..., object])


def public(endpoint: _Endpoint) -> _Endpoint:
    """Marks a route as reachable without a token. Every use must be on the reviewed allowlist."""
    setattr(endpoint, PUBLIC_ATTR, True)
    return endpoint


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: uuid.UUID
    token_version: int


class TokenVersionCache:
    """
    Remembers each user's token_version for a short time so compute routes don't pay a database
    round trip per request (the Supabase hop alone would blow the 50 ms endpoint budget).
    Revocations made by this process invalidate the entry immediately.
    """

    def __init__(self, ttl_seconds: float = 60.0, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._entries: dict[uuid.UUID, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def get(self, user_id: uuid.UUID) -> int | None:
        with self._lock:
            entry = self._entries.get(user_id)
            if entry is None or entry[1] <= self._clock():
                return None
            return entry[0]

    def put(self, user_id: uuid.UUID, version: int) -> None:
        with self._lock:
            self._entries[user_id] = (version, self._clock() + self._ttl)

    def invalidate(self, user_id: uuid.UUID) -> None:
        with self._lock:
            self._entries.pop(user_id, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="not_authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _is_public(request: Request) -> bool:
    route = request.scope.get("route")
    endpoint = getattr(route, "endpoint", None) or request.scope.get("endpoint")
    return bool(getattr(endpoint, PUBLIC_ATTR, False))


def _bearer_token(request: Request) -> str:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized()
    return token.strip()


def _current_token_version(request: Request, user_id: uuid.UUID) -> int | None:
    cache: TokenVersionCache = request.app.state.token_versions
    version = cache.get(user_id)
    if version is not None:
        return version
    factory: sessionmaker[Session] = request.app.state.read_session_factory
    with factory() as session:
        version = session.scalar(select(User.token_version).where(User.id == user_id))
    if version is not None:
        cache.put(user_id, version)
    return version


def authenticate_request(request: Request) -> None:
    """App-wide dependency: rejects the request with 401 unless the route is public or the token is valid."""
    if _is_public(request):
        return
    settings: AppSettings = request.app.state.settings
    try:
        claims = decode_access_token(settings, _bearer_token(request))
    except InvalidTokenError:
        raise _unauthorized() from None
    version = _current_token_version(request, claims.user_id)
    if version is None or version != claims.token_version:
        raise _unauthorized()
    request.state.current_user = CurrentUser(id=claims.user_id, token_version=version)


def get_current_user(request: Request) -> CurrentUser:
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise _unauthorized()
    return user


def get_settings(request: Request) -> AppSettings:
    return request.app.state.settings


def get_email_sender(request: Request) -> EmailSender:
    return request.app.state.email_sender


def get_rate_limiter(request: Request) -> RateLimiter:
    return request.app.state.rate_limiter


def get_token_versions(request: Request) -> TokenVersionCache:
    return request.app.state.token_versions


def client_ip(request: Request) -> str:
    """The caller's IP. X-Forwarded-For is honoured only when the direct peer is a trusted proxy."""
    settings: AppSettings = request.app.state.settings
    peer = request.client.host if request.client else "unknown"
    if peer in settings.trusted_proxies:
        forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return peer


def get_now() -> datetime:
    """Current UTC time; a dependency so tests can move the clock."""
    return utc_now()


def enforce_limit(limiter: RateLimiter, key: str, rule: RateRule) -> None:
    """Counts one attempt; answers 429 with Retry-After once the rule's limit is used up."""
    try:
        limiter.hit(key, rule)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate_limited",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from None

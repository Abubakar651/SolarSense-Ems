"""
Password hashing, access tokens and one-time (email) tokens.

- Passwords: bcrypt, cost 12. bcrypt only reads the first 72 bytes, so callers must reject longer
  passwords (see MAX_PASSWORD_BYTES) instead of letting two different passwords hash the same.
- Access tokens: HS256 JWTs. The algorithm list is pinned on decode, which blocks `alg=none` and
  RS/HS key-confusion tokens. `ver` carries the user's token_version so bumping it revokes every
  token issued before (password reset/change).
- One-time tokens: 32 random bytes sent by email; only their SHA-256 is stored, so a database
  leak does not hand out working reset links.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
import hashlib
import secrets
import uuid

import bcrypt
import jwt

from src.api.core.config import AppSettings

BCRYPT_ROUNDS = 12
MIN_PASSWORD_BYTES = 8
MAX_PASSWORD_BYTES = 72
JWT_ALGORITHM = "HS256"
JWT_LEEWAY_SECONDS = 10


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(BCRYPT_ROUNDS)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        # Malformed stored hash or an over-long password: never a match.
        return False


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(16))


def burn_password_check(password: str) -> None:
    """Spends the same bcrypt time as a real check, so unknown emails can't be told apart by timing."""
    verify_password(password, _dummy_hash())


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    token_version: int


class InvalidTokenError(Exception):
    """The bearer token is missing, malformed, expired, or was signed for someone else."""


def create_access_token(
    settings: AppSettings,
    user_id: uuid.UUID,
    token_version: int,
    ttl: timedelta,
    now: datetime,
) -> str:
    payload = {
        "sub": str(user_id),
        "ver": token_version,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(settings: AppSettings, token: str) -> AccessTokenClaims:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=JWT_LEEWAY_SECONDS,
            options={"require": ["sub", "ver", "iss", "aud", "iat", "exp"]},
        )
        user_id = uuid.UUID(str(payload["sub"]))
        version = payload["ver"]
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise InvalidTokenError from exc
    if not isinstance(version, int) or isinstance(version, bool):
        raise InvalidTokenError
    return AccessTokenClaims(user_id=user_id, token_version=version)


def new_one_time_token() -> tuple[str, str]:
    """Returns (raw token for the email link, hash to store)."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_one_time_token(raw)


def hash_one_time_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

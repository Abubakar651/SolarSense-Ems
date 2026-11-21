"""
Runtime settings for the account, auth and persistence layer, read once from the environment.

Missing or weak secrets stop the process at import time: an API that silently starts without a
JWT secret or database would either crash on the first request or, worse, sign tokens with a
guessable key.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import os
from pathlib import Path
from typing import Literal, Mapping

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]

MIN_JWT_SECRET_BYTES = 32


class ConfigError(RuntimeError):
    """Raised at startup when a required setting is missing or unsafe."""


@dataclass(frozen=True, slots=True)
class AppSettings:
    database_url: str
    jwt_secret: str
    jwt_issuer: str
    jwt_audience: str
    access_token_ttl: timedelta
    remember_token_ttl: timedelta
    # "resend" sends real email; "console" (local development only) prints the links to the server log.
    email_delivery: Literal["resend", "console"]
    resend_api_key: str
    email_from: str
    # False (development only) lets accounts log in without confirming their email.
    require_email_verification: bool
    frontend_url: str
    cors_origins: tuple[str, ...]
    # Peers allowed to set X-Forwarded-For (the Next.js server); everyone else is keyed by socket IP.
    trusted_proxies: frozenset[str]
    # Seconds between inverter polls for the telemetry log; 0 switches the logger off (tests, machines off the home LAN).
    inverter_poll_seconds: int
    # The account (verified email, lower case) that owns the recorded station dataset LHR-RES-01. None: nobody.
    station_owner_email: str | None


def _require(env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        raise ConfigError(f"Environment variable {key} is required (see .env.example).")
    return value


def _positive_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer, got {raw!r}.") from exc
    if value <= 0:
        raise ConfigError(f"{key} must be positive, got {value}.")
    return value


def _non_negative_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer, got {raw!r}.") from exc
    if value < 0:
        raise ConfigError(f"{key} must be zero or positive, got {value}.")
    return value


def load_settings(env: Mapping[str, str] | None = None) -> AppSettings:
    """Builds settings from `env` (defaults to the process environment plus the repo's .env)."""
    if env is None:
        # Real environment variables win over .env, so tests and containers can override it.
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        env = os.environ

    jwt_secret = _require(env, "JWT_SECRET")
    if len(jwt_secret.encode("utf-8")) < MIN_JWT_SECRET_BYTES:
        raise ConfigError(f"JWT_SECRET must be at least {MIN_JWT_SECRET_BYTES} bytes.")

    frontend_url = _require(env, "FRONTEND_URL").rstrip("/")
    cors_raw = env.get("CORS_ORIGINS", "").strip()
    cors_origins = tuple(o.strip().rstrip("/") for o in cors_raw.split(",") if o.strip()) or (frontend_url,)
    if "*" in cors_origins:
        raise ConfigError("CORS_ORIGINS must list explicit origins; '*' is not allowed with credentials.")

    # Real email is the default; printing one-time links to the log has to be asked for explicitly,
    # so a production server missing its Resend key fails to start instead of leaking reset links.
    email_delivery = env.get("EMAIL_DELIVERY", "resend").strip().lower() or "resend"
    if email_delivery not in ("resend", "console"):
        raise ConfigError(f"EMAIL_DELIVERY must be 'resend' or 'console', got {email_delivery!r}.")
    if email_delivery == "resend":
        resend_api_key, email_from = _require(env, "RESEND_API_KEY"), _require(env, "EMAIL_FROM")
    else:
        resend_api_key, email_from = "", env.get("EMAIL_FROM", "").strip()

    # On unless explicitly switched off, so production can't lose verification by omission.
    verification_raw = env.get("REQUIRE_EMAIL_VERIFICATION", "true").strip().lower() or "true"
    if verification_raw not in ("true", "false"):
        raise ConfigError(f"REQUIRE_EMAIL_VERIFICATION must be 'true' or 'false', got {verification_raw!r}.")

    return AppSettings(
        database_url=_require(env, "DATABASE_URL"),
        jwt_secret=jwt_secret,
        jwt_issuer=env.get("JWT_ISSUER", "solarsense-api"),
        jwt_audience=env.get("JWT_AUDIENCE", "solarsense-web"),
        access_token_ttl=timedelta(hours=_positive_int(env, "ACCESS_TOKEN_TTL_HOURS", 12)),
        remember_token_ttl=timedelta(days=_positive_int(env, "REMEMBER_TOKEN_TTL_DAYS", 30)),
        email_delivery=email_delivery,  # type: ignore[arg-type]
        resend_api_key=resend_api_key,
        email_from=email_from,
        require_email_verification=verification_raw == "true",
        frontend_url=frontend_url,
        cors_origins=cors_origins,
        trusted_proxies=frozenset(p.strip() for p in env.get("TRUSTED_PROXIES", "").split(",") if p.strip()),
        inverter_poll_seconds=_non_negative_int(env, "INVERTER_POLL_SECONDS", 300),
        station_owner_email=env.get("STATION_OWNER_EMAIL", "").strip().lower() or None,
    )

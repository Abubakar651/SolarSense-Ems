"""
Account authentication: signup, email verification, login, password reset and change.

Error `detail` values are stable machine codes (`invalid_credentials`, `email_not_verified`,
`invalid_token`, ...) that the frontend maps to copy. Endpoints that take only an email
(resend, forgot) always answer 202 so they can't be used to discover which emails have accounts.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Annotated
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.account_schemas import (
    ChangePasswordRequest,
    EmailRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenRequest,
    TokenResponse,
    UserOut,
)
from src.api.core.config import AppSettings
from src.api.core.rate_limit import RateLimiter, RateRule
from src.api.core.security import (
    burn_password_check,
    create_access_token,
    hash_one_time_token,
    hash_password,
    new_one_time_token,
    verify_password,
)
from src.api.db.models import ActionToken, Site, User
from src.api.db.session import get_db
from src.api.deps import (
    CurrentUser,
    TokenVersionCache,
    client_ip,
    enforce_limit,
    get_current_user,
    get_email_sender,
    get_now,
    get_rate_limiter,
    get_settings,
    get_token_versions,
    public,
)
from src.api.mail.sender import (
    EmailDeliveryError,
    EmailMessage,
    EmailSender,
    password_reset_email,
    verification_email,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])

VERIFY_TOKEN_TTL = timedelta(hours=24)
RESET_TOKEN_TTL = timedelta(minutes=30)

LOGIN_PER_EMAIL = RateRule(limit=5, window_seconds=15 * 60)
LOGIN_PER_IP = RateRule(limit=30, window_seconds=15 * 60)
EMAIL_SEND_PER_EMAIL = RateRule(limit=3, window_seconds=15 * 60)
EMAIL_SEND_PER_IP = RateRule(limit=20, window_seconds=15 * 60)
SIGNUP_PER_IP = RateRule(limit=10, window_seconds=60 * 60)
TOKEN_PER_IP = RateRule(limit=30, window_seconds=15 * 60)
CHANGE_PASSWORD_PER_USER = RateRule(limit=5, window_seconds=15 * 60)

DbSession = Annotated[Session, Depends(get_db)]
Settings = Annotated[AppSettings, Depends(get_settings)]
Limiter = Annotated[RateLimiter, Depends(get_rate_limiter)]
Mailer = Annotated[EmailSender, Depends(get_email_sender)]
Versions = Annotated[TokenVersionCache, Depends(get_token_versions)]


Now = Annotated[datetime, Depends(get_now)]


def user_out(session: Session, user: User) -> UserOut:
    onboarded = bool(session.scalar(select(exists().where(Site.user_id == user.id))))
    return UserOut(id=user.id, name=user.name, email=user.email, phone=user.phone, onboarded=onboarded)


def token_response(session: Session, settings: AppSettings, user: User, remember: bool, now: datetime) -> TokenResponse:
    ttl = settings.remember_token_ttl if remember else settings.access_token_ttl
    token = create_access_token(settings, user.id, user.token_version, ttl, now)
    return TokenResponse(access_token=token, expires_in=int(ttl.total_seconds()), user=user_out(session, user))


def _issue_action_token(session: Session, user_id: uuid.UUID, purpose: str, ttl: timedelta, now: datetime) -> str:
    """Creates a one-time token and cancels any earlier unused one with the same purpose."""
    session.execute(
        update(ActionToken)
        .where(ActionToken.user_id == user_id, ActionToken.purpose == purpose, ActionToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw, token_hash = new_one_time_token()
    session.add(ActionToken(user_id=user_id, purpose=purpose, token_hash=token_hash, expires_at=now + ttl))
    return raw


def _consume_action_token(session: Session, raw: str, purpose: str, now: datetime) -> uuid.UUID:
    """Marks the token used in one statement, so two concurrent requests can't both redeem it."""
    user_id = session.execute(
        update(ActionToken)
        .where(
            ActionToken.token_hash == hash_one_time_token(raw),
            ActionToken.purpose == purpose,
            ActionToken.used_at.is_(None),
            ActionToken.expires_at > now,
        )
        .values(used_at=now)
        .returning(ActionToken.user_id)
    ).scalar_one_or_none()
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_token")
    return user_id


def _deliver(mailer: EmailSender, message: EmailMessage) -> None:
    """Runs after the response. Failures are logged, not raised: the user can ask for another email."""
    try:
        mailer.send(message)
    except EmailDeliveryError:
        logger.error("Could not send email: %s", message.subject)


def _send_later(tasks: BackgroundTasks, mailer: EmailSender, message: EmailMessage) -> None:
    # Sending after the response keeps "account exists" and "no account" equally fast.
    tasks.add_task(_deliver, mailer, message)


def _find_user(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=UserOut)
@public
def signup(body: SignupRequest, request: Request, session: DbSession, settings: Settings, limiter: Limiter, mailer: Mailer, tasks: BackgroundTasks, now: Now) -> UserOut:
    enforce_limit(limiter, f"signup:ip:{client_ip(request)}", SIGNUP_PER_IP)
    if _find_user(session, body.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email_taken")
    user = User(email=body.email, name=body.name, password_hash=hash_password(body.password), phone="")
    session.add(user)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email_taken") from None
    if not settings.require_email_verification:
        session.commit()
        return UserOut(id=user.id, name=user.name, email=user.email, phone=user.phone, onboarded=False)
    raw = _issue_action_token(session, user.id, "verify_email", VERIFY_TOKEN_TTL, now)
    session.commit()
    link = f"{settings.frontend_url}/verify?token={raw}"
    _send_later(tasks, mailer, verification_email(user.email, user.name, link))
    return UserOut(id=user.id, name=user.name, email=user.email, phone=user.phone, onboarded=False)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
@public
def verify_email(body: TokenRequest, request: Request, session: DbSession, limiter: Limiter, now: Now) -> None:
    enforce_limit(limiter, f"token:ip:{client_ip(request)}", TOKEN_PER_IP)
    user_id = _consume_action_token(session, body.token, "verify_email", now)
    session.execute(
        update(User).where(User.id == user_id, User.email_verified_at.is_(None)).values(email_verified_at=now)
    )
    session.commit()


@router.post("/verify-email/resend", status_code=status.HTTP_202_ACCEPTED)
@public
def resend_verification(body: EmailRequest, request: Request, session: DbSession, settings: Settings, limiter: Limiter, mailer: Mailer, tasks: BackgroundTasks, now: Now) -> None:
    enforce_limit(limiter, f"send:ip:{client_ip(request)}", EMAIL_SEND_PER_IP)
    enforce_limit(limiter, f"send:email:{body.email}", EMAIL_SEND_PER_EMAIL)
    user = _find_user(session, body.email)
    if user is None or user.email_verified_at is not None:
        return
    raw = _issue_action_token(session, user.id, "verify_email", VERIFY_TOKEN_TTL, now)
    session.commit()
    link = f"{settings.frontend_url}/verify?token={raw}"
    _send_later(tasks, mailer, verification_email(user.email, user.name, link))


@router.post("/login", response_model=TokenResponse)
@public
def login(body: LoginRequest, request: Request, session: DbSession, settings: Settings, limiter: Limiter, now: Now) -> TokenResponse:
    enforce_limit(limiter, f"login:ip:{client_ip(request)}", LOGIN_PER_IP)
    enforce_limit(limiter, f"login:email:{body.email}", LOGIN_PER_EMAIL)
    user = _find_user(session, body.email)
    if user is None:
        burn_password_check(body.password)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    # Checked only after the password, so this can't reveal whether an email is registered.
    if settings.require_email_verification and user.email_verified_at is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="email_not_verified")
    return token_response(session, settings, user, body.remember, now)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@public
def forgot_password(body: EmailRequest, request: Request, session: DbSession, settings: Settings, limiter: Limiter, mailer: Mailer, tasks: BackgroundTasks, now: Now) -> None:
    enforce_limit(limiter, f"send:ip:{client_ip(request)}", EMAIL_SEND_PER_IP)
    enforce_limit(limiter, f"send:email:{body.email}", EMAIL_SEND_PER_EMAIL)
    user = _find_user(session, body.email)
    if user is None:
        return
    raw = _issue_action_token(session, user.id, "reset_password", RESET_TOKEN_TTL, now)
    session.commit()
    link = f"{settings.frontend_url}/reset?token={raw}"
    _send_later(tasks, mailer, password_reset_email(user.email, link))


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@public
def reset_password(body: ResetPasswordRequest, request: Request, session: DbSession, limiter: Limiter, versions: Versions, now: Now) -> None:
    enforce_limit(limiter, f"token:ip:{client_ip(request)}", TOKEN_PER_IP)
    user_id = _consume_action_token(session, body.token, "reset_password", now)
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_token")
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1  # signs out every existing session
    if user.email_verified_at is None:
        user.email_verified_at = now  # the reset link proved they own the inbox
    session.commit()
    versions.invalidate(user.id)


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    body: ChangePasswordRequest,
    session: DbSession,
    settings: Settings,
    limiter: Limiter,
    versions: Versions,
    now: Now,
    current: Annotated[CurrentUser, Depends(get_current_user)],
) -> TokenResponse:
    """Changes the password, signs out other sessions and returns a fresh token for this one."""
    enforce_limit(limiter, f"change-password:user:{current.id}", CHANGE_PASSWORD_PER_USER)
    user = session.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_current_password")
    user.password_hash = hash_password(body.new_password)
    user.token_version += 1
    session.commit()
    versions.invalidate(user.id)
    return token_response(session, settings, user, remember=False, now=now)

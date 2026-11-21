"""
Transactional email (verify address, reset password) through Resend's HTTP API.

Resend is called directly with httpx (already a dependency) instead of its SDK. Link URLs carry
one-time tokens, so they are never logged; failures log only the status code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape
import logging
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"
RESEND_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    html: str


class EmailDeliveryError(Exception):
    """The email provider rejected the message or could not be reached."""


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class ResendEmailSender:
    def __init__(self, api_key: str, sender: str, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._sender = sender
        self._client = client or httpx.Client(timeout=RESEND_TIMEOUT_SECONDS)

    def send(self, message: EmailMessage) -> None:
        try:
            response = self._client.post(
                RESEND_ENDPOINT,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "from": self._sender,
                    "to": [message.to],
                    "subject": message.subject,
                    "text": message.text,
                    "html": message.html,
                },
            )
        except httpx.HTTPError as exc:
            logger.error("Resend request failed: %s", type(exc).__name__)
            raise EmailDeliveryError("Email provider unreachable") from exc
        if response.status_code >= 400:
            logger.error("Resend rejected email: status=%s", response.status_code)
            raise EmailDeliveryError(f"Email provider returned {response.status_code}")


class ConsoleEmailSender:
    """
    Local development without an email provider (EMAIL_DELIVERY=console): prints the message,
    including its one-time link, to the server log so the developer can open it. Never for production.
    """

    def send(self, message: EmailMessage) -> None:
        logger.warning(
            "EMAIL_DELIVERY=console, not sending. To: %s | %s\n%s", message.to, message.subject, message.text
        )


@dataclass
class FakeEmailSender:
    """Collects messages in memory; used by tests."""

    sent: list[EmailMessage] = field(default_factory=list)

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


def _link_email(to: str, subject: str, intro: str, link: str, action: str, expiry: str) -> EmailMessage:
    text = f"{intro}\n\n{action}: {link}\n\nThis link expires in {expiry}. If you didn't ask for this, ignore this email."
    html = (
        f"<p>{escape(intro)}</p>"
        f'<p><a href="{escape(link, quote=True)}">{escape(action)}</a></p>'
        f"<p>This link expires in {escape(expiry)}. If you didn't ask for this, ignore this email.</p>"
    )
    return EmailMessage(to=to, subject=subject, text=text, html=html)


def verification_email(to: str, name: str, link: str) -> EmailMessage:
    return _link_email(
        to,
        "Confirm your SolarSense email",
        f"Hi {name}, confirm your email address to finish setting up SolarSense.",
        link,
        "Confirm email",
        "24 hours",
    )


def password_reset_email(to: str, link: str) -> EmailMessage:
    return _link_email(
        to,
        "Reset your SolarSense password",
        "We received a request to reset your SolarSense password.",
        link,
        "Choose a new password",
        "30 minutes",
    )

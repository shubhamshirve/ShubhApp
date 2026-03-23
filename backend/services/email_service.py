"""Email delivery helpers backed by Resend with SMTP fallback support."""
import asyncio
import logging
import os
import smtplib
from email.message import EmailMessage

import httpx
from services.global_settings_store import get_global_settings_doc


logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


class EmailServiceError(Exception):
    """Raised when email delivery is unavailable or fails."""


class ResendEmailService:
    """Minimal Resend API client for transactional emails."""

    def __init__(self, api_key: str, from_email: str):
        self.api_key = (api_key or "").strip()
        self.from_email = (from_email or "").strip()
        if not self.api_key:
            raise EmailServiceError("RESEND_API_KEY is not configured")
        if not self.from_email:
            raise EmailServiceError("RESEND_FROM_EMAIL is not configured")

    async def send_email(self, *, to_email: str, subject: str, html: str, text: str = ""):
        payload = {
            "from": self.from_email,
            "to": [to_email],
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(RESEND_API_URL, headers=headers, json=payload)

        if response.status_code >= 400:
            logger.warning("Resend email send failed: %s %s", response.status_code, response.text)
            raise EmailServiceError("Failed to send email with Resend")

        return {"provider": "resend", "response": response.json()}


class SMTPEmailService:
    """SMTP fallback transport using standard library smtplib."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        from_email: str,
        use_tls: bool = True,
    ):
        self.host = (host or "").strip()
        self.port = int(port or 0)
        self.username = (username or "").strip()
        self.password = password or ""
        self.from_email = (from_email or "").strip()
        self.use_tls = bool(use_tls)
        if not self.host:
            raise EmailServiceError("SMTP host is not configured")
        if not self.port:
            raise EmailServiceError("SMTP port is not configured")
        if not self.from_email:
            raise EmailServiceError("SMTP from email is not configured")

    async def send_email(self, *, to_email: str, subject: str, html: str, text: str = ""):
        return await asyncio.to_thread(
            self._send_sync,
            to_email=to_email,
            subject=subject,
            html=html,
            text=text,
        )

    def _send_sync(self, *, to_email: str, subject: str, html: str, text: str = ""):
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.from_email
        message["To"] = to_email
        message.set_content(text or "Please view this email in an HTML-compatible client.")
        message.add_alternative(html, subtype="html")

        with smtplib.SMTP(self.host, self.port, timeout=20) as smtp:
            smtp.ehlo()
            if self.use_tls:
                if not smtp.has_extn("starttls"):
                    raise EmailServiceError("SMTP server does not support STARTTLS. Disable TLS or use a TLS-capable SMTP server.")
                smtp.starttls()
                smtp.ehlo()
            if self.username:
                if smtp.has_extn("auth"):
                    smtp.login(self.username, self.password)
                else:
                    logger.warning(
                        "SMTP server %s:%s does not advertise AUTH; continuing without SMTP login.",
                        self.host,
                        self.port,
                    )
            smtp.send_message(message)

        return {"provider": "smtp"}


class FallbackEmailService:
    """Primary email service with optional fallback transport."""

    def __init__(self, primary=None, fallback=None):
        self.primary = primary
        self.fallback = fallback
        if not self.primary and not self.fallback:
            raise EmailServiceError("No email delivery provider is configured")

    async def send_email(self, *, to_email: str, subject: str, html: str, text: str = ""):
        primary_error = None
        if self.primary:
            try:
                return await self.primary.send_email(
                    to_email=to_email,
                    subject=subject,
                    html=html,
                    text=text,
                )
            except Exception as exc:
                primary_error = exc
                logger.warning("Primary email delivery failed, trying fallback: %s", exc)

        if self.fallback:
            try:
                return await self.fallback.send_email(
                    to_email=to_email,
                    subject=subject,
                    html=html,
                    text=text,
                )
            except Exception as exc:
                logger.warning("Fallback email delivery failed: %s", exc)
                if primary_error:
                    raise EmailServiceError(f"Primary and fallback email delivery failed: {exc}") from exc
                raise EmailServiceError("Fallback email delivery failed") from exc

        if primary_error:
            raise EmailServiceError(str(primary_error)) from primary_error
        raise EmailServiceError("No email delivery provider is configured")


def _build_smtp_service_from_settings(settings: dict):
    host = (settings.get("smtp_host") or "").strip()
    from_email = (settings.get("smtp_from_email") or settings.get("resend_from_email") or "").strip()
    if not host:
        return None
    try:
        return SMTPEmailService(
            host=host,
            port=int(settings.get("smtp_port") or 587),
            username=settings.get("smtp_username", ""),
            password=settings.get("smtp_password", ""),
            from_email=from_email,
            use_tls=bool(settings.get("smtp_use_tls", True)),
        )
    except EmailServiceError:
        return None


def _build_resend_service_from_settings(settings: dict):
    api_key = (settings.get("resend_api_key") or os.environ.get("RESEND_API_KEY", "")).strip()
    from_email = (settings.get("resend_from_email") or os.environ.get("RESEND_FROM_EMAIL", "")).strip()
    if not api_key:
        return None
    try:
        return ResendEmailService(api_key=api_key, from_email=from_email)
    except EmailServiceError:
        return None


def get_email_service():
    """Build the email service using environment variables only."""
    settings = {
        "resend_api_key": os.environ.get("RESEND_API_KEY", ""),
        "resend_from_email": os.environ.get("RESEND_FROM_EMAIL", ""),
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": os.environ.get("SMTP_PORT", "587"),
        "smtp_username": os.environ.get("SMTP_USERNAME", ""),
        "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
        "smtp_from_email": os.environ.get("SMTP_FROM_EMAIL", ""),
        "smtp_use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() != "false",
    }
    return FallbackEmailService(
        primary=_build_resend_service_from_settings(settings),
        fallback=_build_smtp_service_from_settings(settings),
    )


async def get_email_service_async():
    """
    Build the email service, checking DB first (`global_settings.key = email_settings`)
    and then falling back to environment variables.
    """
    settings = {}
    try:
        doc = await get_global_settings_doc({"key": "email_settings"}, {"_id": 0})
        if doc:
            settings.update(doc)
    except Exception as exc:
        logger.warning("Failed to load email settings from DB, falling back to env: %s", exc)

    return FallbackEmailService(
        primary=_build_resend_service_from_settings(settings),
        fallback=_build_smtp_service_from_settings(settings),
    )


async def get_email_providers_async():
    """
    Load and build the primary and fallback email providers using DB settings first
    and environment variables as a fallback.
    """
    settings = {
        "resend_api_key": os.environ.get("RESEND_API_KEY", ""),
        "resend_from_email": os.environ.get("RESEND_FROM_EMAIL", ""),
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": os.environ.get("SMTP_PORT", "587"),
        "smtp_username": os.environ.get("SMTP_USERNAME", ""),
        "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
        "smtp_from_email": os.environ.get("SMTP_FROM_EMAIL", ""),
        "smtp_use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() != "false",
    }
    try:
        doc = await get_global_settings_doc({"key": "email_settings"}, {"_id": 0})
        if doc:
            settings.update(doc)
    except Exception as exc:
        logger.warning("Failed to load email settings from DB, falling back to env: %s", exc)

    return {
        "primary": _build_resend_service_from_settings(settings),
        "fallback": _build_smtp_service_from_settings(settings),
    }

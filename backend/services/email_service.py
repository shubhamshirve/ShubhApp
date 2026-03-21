"""Email delivery helpers backed by Resend."""
import logging
import os

import httpx


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
            raise EmailServiceError("Failed to send email OTP")

        return response.json()


def get_email_service() -> ResendEmailService:
    """Build a Resend email client from env vars."""
    return ResendEmailService(
        api_key=os.environ.get("RESEND_API_KEY", ""),
        from_email=os.environ.get("RESEND_FROM_EMAIL", ""),
    )


async def get_email_service_async() -> ResendEmailService:
    """
    Build a Resend email client, checking the DB first (global_settings key='email_settings'),
    then falling back to OS environment variables.
    """
    try:
        from database import db
        doc = await db.global_settings.find_one({"key": "email_settings"}, {"_id": 0})
        if doc and doc.get("resend_api_key"):
            return ResendEmailService(
                api_key=doc["resend_api_key"],
                from_email=doc.get("resend_from_email", os.environ.get("RESEND_FROM_EMAIL", "")),
            )
    except Exception:
        pass
    # Fall back to env vars
    return ResendEmailService(
        api_key=os.environ.get("RESEND_API_KEY", ""),
        from_email=os.environ.get("RESEND_FROM_EMAIL", ""),
    )

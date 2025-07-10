from __future__ import annotations

"""Send a daily summary email using SendGrid."""

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from .config import get_settings
from .agent import get_daily_summary


def send_daily_email() -> None:
    """Send the formatted daily summary via email."""
    settings = get_settings()
    summary = get_daily_summary()

    message = Mail(
        from_email=settings.email_sender,
        to_emails=settings.email_recipient,
        subject="Your Daily Digest",
        html_content=f"<strong>Here's your daily summary:</strong><br>{summary}",
    )

    try:
        sg = SendGridAPIClient(settings.smtp_password or "")
        sg.send(message)
    except Exception as exc:  # pragma: no cover - network issues
        # Log or print is omitted to keep this helper minimal
        pass

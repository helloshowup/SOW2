import os
import smtplib
import ssl
import structlog
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = structlog.get_logger()


class EmailSender:
    """Utility class for sending HTML summary emails."""

    def __init__(
        self,
        smtp_server: str | None = None,
        smtp_port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        sender_email: str | None = None,
        receiver_email: str | None = None,
    ) -> None:
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER")
        self.smtp_port = int(smtp_port or os.getenv("SMTP_PORT", 587))
        self.username = username or os.getenv("SMTP_USERNAME")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.sender_email = sender_email or os.getenv("SENDER_EMAIL")
        self.receiver_email = receiver_email or os.getenv(
            "RECEIVER_EMAIL", "recipient@example.com"
        )

        if not all(
            [
                self.smtp_server,
                self.username,
                self.password,
                self.sender_email,
                self.receiver_email,
            ]
        ):
            log.critical(
                "Email configuration missing. SMTP functions will not work.",
                smtp_server=bool(self.smtp_server),
                smtp_username=bool(self.username),
                smtp_password=bool(self.password),
                sender_email=bool(self.sender_email),
                receiver_email=bool(self.receiver_email),
            )

    def _build_html(self, results: dict[str, list[dict]], run_id: int) -> str:
        """Return HTML body for the summary email."""

        def list_items(items: list[dict]) -> str:
            if not items:
                return "<li>No results found.</li>"
            return "".join(
                (
                    f"<li><strong>{i+1}. {r.get('item', 'N/A')}</strong> "
                    f"(Score: {r.get('score', 'N/A'):.2f})</li>"
                )
                for i, r in enumerate(items)
            )

        brand_section = (
            f"<h3>Brand Health Report</h3>"
            f"<ul>{list_items(results.get('brand_health', []))}</ul>"
        )
        market_section = (
            f"<h3>Market Intelligence Briefing</h3>"
            f"<ul>{list_items(results.get('market_intelligence', []))}</ul>"
        )

        return (
            f"<html>"
            f"<body style=\"font-family: Arial, sans-serif; line-height:1.4;\">"
            f"<h2 style=\"color:#333;\">AI Agent Daily Summary - Run {run_id}</h2>"
            f"{brand_section}{market_section}"
            f"<p>"
            f"<a href='http://localhost:8000/feedback?run_id={run_id}&feedback=yes'>Yes, it was helpful!</a> | "
            f"<a href='http://localhost:8000/feedback?run_id={run_id}&feedback=no'>No, it was not helpful.</a>"
            f"</p>"
            f"</body></html>"
        )

    def send_summary_email(self, results: dict[str, list[dict]], run_id: int) -> None:
        """Send an email summary with basic HTML styling."""
        if not all(
            [
                self.smtp_server,
                self.username,
                self.password,
                self.sender_email,
                self.receiver_email,
            ]
        ):
            log.error("Email configuration is incomplete. Skipping email sending.")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"AI Agent Daily Summary - Run {run_id}"
        msg["From"] = self.sender_email
        msg["To"] = self.receiver_email

        html_content = self._build_html(results, run_id)
        msg.attach(MIMEText(html_content, "html"))

        context = ssl.create_default_context()
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)
            log.info(
                "Email summary sent successfully",
                run_id=run_id,
                recipient=self.receiver_email,
            )
        except Exception as e:  # pragma: no cover - network failures
            log.error("Failed to send email summary", exc_info=e, run_id=run_id)


def send_summary_email(results: dict[str, list[dict]], run_id: int) -> None:
    """Backward-compatible wrapper for EmailSender."""
    EmailSender().send_summary_email(results, run_id)


import os
import smtplib
import ssl
import structlog
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import get_settings
from .brand_parser import load_brand_config

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


    def _build_html(
        self,
        run_id: int,
        on_brand_specific_links: list[dict] | None = None,
        brand_relevant_links: list[dict] | None = None,
        brand_system_prompt: str | None = None,
        market_system_prompt: str | None = None,
        user_prompt: str | None = None,
        search_terms_generated: list[str] | None = None,
        num_search_calls: int | None = None,
        search_times: list[str] | None = None,
        content_summaries: list[str] | None = None,
        brand_display_name: str | None = None,
    ) -> str:
        """Return HTML body for the summary email using the new template."""

        def list_links(links: list[dict] | None, include_feedback: bool = False) -> str:
            if not links:
                return "<li>No links found.</li>"
            items = []
            settings = get_settings()
            base = settings.app_base_url.rstrip("/")
            for item in links:
                url = item.get("link") or item.get("url")
                headline = item.get("headline") or item.get("snappy_heading", url)
                emoji = item.get("emoji", "")
                feedback = (
                    (
                        f" - <a href='{base}/feedback?run_id={run_id}&feedback=yes'>Yes 👍, it was helpful!</a> | "
                        f"<a href='{base}/feedback?run_id={run_id}&feedback=no'>No👎, it was not helpful.</a>"
                    )
                    if include_feedback
                    else ""
                )
                items.append(
                    f"<li>{emoji} <a href='{url}'>{headline}</a>{feedback}</li>"
                )
            return "".join(items)

        def list_str(values: list[str] | None) -> str:
            return ", ".join(values) if values else "N/A"

        def truncate(value: str | None, length: int = 300) -> str:
            if not value:
                return "N/A"
            return value[:length] + ("..." if len(value) > length else "")

        summaries_html = (
            "".join([f"<li>{s}</li>" for s in content_summaries])
            if content_summaries
            else "<li>N/A</li>"
        )

        if not on_brand_specific_links and not brand_relevant_links:
            name = brand_display_name or "the brand"
            return (
                "<html><body style='font-family: Arial, sans-serif; line-height:1.4;'>"
                f"<h3>No brand-specific or brand-relevant news was found for {name} today.</h3>"
                "</body></html>"
            )

        html_sections = [
            "<html>",
            "<body style='font-family: Arial, sans-serif; line-height:1.4;'>",
            f"<h3>Hi there</h3>",
            "<h3><strong>Below are links that the AI thinks are on brand specific</strong></h3>",
            f"<ul>{list_links(on_brand_specific_links, include_feedback=True)}</ul>",
            "<h3><strong>Below are 3 links that AI thinks are brand relevant but not brand specific</strong></h3>",
            f"<ul>{list_links(brand_relevant_links)}</ul>",
            "<h3>Prompt Engineering Metadata</h3>",
            f"<p><strong>Brand System Prompt:</strong> {brand_system_prompt or 'N/A'}</p>",
            f"<p><strong>Market System Prompt:</strong> {market_system_prompt or 'N/A'}</p>",
            f"<p><strong>User Prompt:</strong> {user_prompt or 'N/A'}</p>",
            f"<p><strong>Search Terms Generated:</strong> {list_str(search_terms_generated)}</p>",
            "<h3>Content Scraped Since last email</h3>",
            f"<p><strong>Number of Search Calls:</strong> {num_search_calls if num_search_calls is not None else 'N/A'}</p>",
            f"<p><strong>Searches Run At:</strong> {list_str(search_times)}</p>",
            "<p><strong>Summaries:</strong></p>",
            f"<ul>{summaries_html}</ul>",
            "</body></html>",
        ]

        return "".join(html_sections)

    def send_summary_email(
        self,
        run_id: int,
        *,
        on_brand_specific_links: list[dict] | None = None,
        brand_relevant_links: list[dict] | None = None,
        brand_system_prompt: str | None = None,
        market_system_prompt: str | None = None,
        user_prompt: str | None = None,
        search_terms_generated: list[str] | None = None,
        num_search_calls: int | None = None,
        search_times: list[str] | None = None,
        content_summaries: list[str] | None = None,
        brand_display_name: str | None = None,
    ) -> None:
        """Send an email summary using the new template."""
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

        if brand_display_name is None:
            brand_id = os.getenv("BRAND_ID", "debonairs")
            config = load_brand_config(brand_id) or {}
            brand_display_name = config.get("display_name", brand_id)

        no_news = not on_brand_specific_links and not brand_relevant_links

        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            "Daily Summary: No News for Today"
            if no_news
            else f"AI Agent Daily Summary - Run {run_id}"
        )
        msg["From"] = self.sender_email
        msg["To"] = self.receiver_email

        html_content = self._build_html(
            run_id,
            on_brand_specific_links=on_brand_specific_links,
            brand_relevant_links=brand_relevant_links,
            brand_system_prompt=brand_system_prompt,
            market_system_prompt=market_system_prompt,
            user_prompt=user_prompt,
            search_terms_generated=search_terms_generated,
            num_search_calls=num_search_calls,
            search_times=search_times,
            content_summaries=content_summaries,
            brand_display_name=brand_display_name,
        )
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


def send_summary_email(run_id: int, **kwargs) -> None:
    """Convenience wrapper for ``EmailSender``."""
    EmailSender().send_summary_email(run_id, **kwargs)


def send_email(subject: str, body: str) -> None:
    """Send a plain text email."""
    sender = EmailSender()
    if not all([
        sender.smtp_server,
        sender.username,
        sender.password,
        sender.sender_email,
        sender.receiver_email,
    ]):
        log.error("Email configuration is incomplete. Skipping email sending.")
        return

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender.sender_email
    msg["To"] = sender.receiver_email
    msg.attach(MIMEText(body, "plain"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(sender.smtp_server, sender.smtp_port) as server:
            server.starttls(context=context)
            server.login(sender.username, sender.password)
            server.send_message(msg)
        log.info("Email sent", subject=subject, recipient=sender.receiver_email)
    except Exception as e:  # pragma: no cover - network failures
        log.error("Failed to send email", exc_info=e)

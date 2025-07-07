import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import structlog

from .config import config

log = structlog.get_logger()


def send_summary_email(top_five_results: list[dict], run_id: int) -> None:
    """Send an HTML summary email with feedback links."""
    if not all(
        [
            config.SMTP_SERVER,
            config.SMTP_USERNAME,
            config.SMTP_PASSWORD,
            config.SENDER_EMAIL,
            config.RECEIVER_EMAIL,
        ]
    ):
        log.error("email_config.incomplete")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AI Agent Daily Summary - Run {run_id}"
    msg["From"] = config.SENDER_EMAIL
    msg["To"] = config.RECEIVER_EMAIL

    html_content = [
        "<html><body>",
        f"<h2>AI Agent Daily Summary - Run {run_id}</h2>",
        "<p>Here are the top 5 results from the latest agent run:</p>",
        "<ul>",
    ]
    for i, result in enumerate(top_five_results):
        item = result.get("item", "N/A")
        score = result.get("score", "N/A")
        html_content.append(f"<li><strong>{i + 1}. {item}</strong> (Score: {score})</li>")
    html_content.append("</ul>")

    base_url = config.FEEDBACK_BASE_URL.rstrip("/")
    html_content.extend(
        [
            "<h3>Was this summary helpful?</h3>",
            f'<p><a href="{base_url}?run_id={run_id}&feedback=yes">Yes, it was helpful!</a> | '
            f'<a href="{base_url}?run_id={run_id}&feedback=no">No, it was not helpful.</a></p>',
            "</body></html>",
        ]
    )

    msg.attach(MIMEText("\n".join(html_content), "html"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.send_message(msg)
        log.info("email.sent", run_id=run_id, recipient=config.RECEIVER_EMAIL)
    except Exception as exc:
        log.error("email.failed", error=str(exc), run_id=run_id)

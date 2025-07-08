import os
import smtplib
import ssl
import structlog
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = structlog.get_logger()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "recipient@example.com")

if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL, RECEIVER_EMAIL]):
    log.critical(
        "Email configuration missing. SMTP functions will not work.",
        smtp_server=bool(SMTP_SERVER),
        smtp_username=bool(SMTP_USERNAME),
        smtp_password=bool(SMTP_PASSWORD),
        sender_email=bool(SENDER_EMAIL),
        receiver_email=bool(RECEIVER_EMAIL),
    )

def send_summary_email(top_five_results: list[dict], run_id: int) -> None:
    """Send an email summary of the top five results with feedback links."""
    if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL, RECEIVER_EMAIL]):
        log.error("Email configuration is incomplete. Skipping email sending.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AI Agent Daily Summary - Run {run_id}"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    html_content = f"""
    <html>
        <body>
            <h2>AI Agent Daily Summary - Run {run_id}</h2>
            <p>Here are the top 5 results from the latest agent run:</p>
            <ul>
    """
    for i, result in enumerate(top_five_results):
        html_content += f"<li><strong>{i+1}. {result.get('item', 'N/A')}</strong> (Score: {result.get('score', 'N/A'):.2f})</li>"
    html_content += f"""
            </ul>
            <h3>Was this summary helpful?</h3>
            <p>
                <a href=\"http://localhost:8000/feedback?run_id={run_id}&feedback=yes\">Yes, it was helpful!</a> |
                <a href=\"http://localhost:8000/feedback?run_id={run_id}&feedback=no\">No, it was not helpful.</a>
            </p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html_content, "html"))

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        log.info("Email summary sent successfully", run_id=run_id, recipient=RECEIVER_EMAIL)
    except Exception as e:
        log.error("Failed to send email summary", exc_info=e, run_id=run_id)

from dataclasses import dataclass
import os

from dotenv import load_dotenv
import structlog

load_dotenv()
log = structlog.get_logger()

@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    BRAND_REPO_PATH: str = os.getenv("BRAND_REPO_PATH", "dev-research/brand_repo.yaml")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "")
    RECEIVER_EMAIL: str = os.getenv("RECEIVER_EMAIL", "recipient@example.com")
    FEEDBACK_BASE_URL: str = os.getenv("FEEDBACK_BASE_URL", "http://localhost:8000/feedback")
    FEEDBACK_DB_FILE: str = os.getenv("FEEDBACK_DB_FILE", "feedback.db")


config = Config()

if not os.path.exists(config.BRAND_REPO_PATH):
    log.warning("Brand repository file not found", path=config.BRAND_REPO_PATH)

if not all(
    [
        config.SMTP_SERVER,
        config.SMTP_USERNAME,
        config.SMTP_PASSWORD,
        config.SENDER_EMAIL,
        config.RECEIVER_EMAIL,
    ]
):
    log.critical(
        "email_config.missing",
        smtp_server=bool(config.SMTP_SERVER),
        smtp_username=bool(config.SMTP_USERNAME),
        smtp_password=bool(config.SMTP_PASSWORD),
        sender_email=bool(config.SENDER_EMAIL),
        receiver_email=bool(config.RECEIVER_EMAIL),
    )

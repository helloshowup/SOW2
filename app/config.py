from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    DATABASE_URL: str  # This is the correct line
    # REMOVE the line below
    # database_url: str = "sqlite:///./development.db"

    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    agent_run_interval_minutes: int = 60
    brand_repo_path: str = "dev-research/debonair_brand.yaml"
    openai_api_key: str | None = None
    serpapi_api_key: str | None = None
    email_recipient: str | None = None
    email_sender: str | None = None
    smtp_server: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    daily_email_hour: int = 6
    daily_email_minute: int = 0
    max_daily_searches: int = 90
    app_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
@lru_cache()
def get_settings() -> Settings:
    return Settings()

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
    agent_run_interval_minutes: int = 10
    brand_repo_path: str = "dev-research/debonair_brand.yaml"
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
@lru_cache()
def get_settings() -> Settings:
    return Settings()

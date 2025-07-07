from functools import lru_cache
from pydantic import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str = "sqlite:///./development.db"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    agent_run_interval_minutes: int = 10
    brand_repo_path: str = "dev-research/brand_repo.yaml"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

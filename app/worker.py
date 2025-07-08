from redis import Redis
from rq import Worker, Queue

import asyncio
import json
import logging
import os

from .config import get_settings
from .database import engine
from .agent import run_agent_iteration
from .openai_evaluator import evaluate_content
from .daily_email_compiler import compile_and_send_daily_email as compile_daily_email
import structlog

# Configure logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

log = structlog.get_logger()


def load_search_config(config_path: str = "search_config.json") -> dict:
    """Load search configuration from a JSON file in the project root."""
    search_request_data: dict = {}
    full_path = os.path.join(os.getcwd(), config_path)
    if os.path.exists(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                search_request_data = json.load(f)
        except FileNotFoundError:
            logging.error(
                "Configuration file not found at %s. Please create it.", full_path
            )
        except json.JSONDecodeError:
            logging.error(
                "Error decoding JSON from %s. Please check its format.", full_path
            )
    else:
        logging.info("search_config.json not found at %s", full_path)
    return search_request_data


def run_agent_logic(run_id: int, search_request: dict | None = None) -> None:
    """Execute the agent iteration synchronously for RQ."""
    log.info("Executing agent logic", run_id=run_id)
    if search_request is None:
        search_request = load_search_config()
    asyncio.run(run_agent_iteration(run_id, search_request))


def compile_and_send_daily_email() -> None:
    """Compile and send the daily market intelligence email."""
    log.info("Starting daily email compilation and sending process")
    asyncio.run(compile_daily_email())


def run_worker() -> None:
    """Start an RQ worker using configuration from environment variables."""
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    worker = Worker([Queue(connection=redis_conn)], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    run_worker()

from redis import Redis
from rq import Worker, Queue, Connection

from .config import get_settings
import structlog

log = structlog.get_logger()

def run_agent_logic(run_id: int) -> None:
    """Placeholder for the actual agent logic."""
    log.info("Executing agent logic", run_id=run_id)


def run_worker() -> None:
    """Start an RQ worker using configuration from environment variables."""
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    with Connection(redis_conn):
        worker = Worker([Queue(connection=redis_conn)])
        worker.work()


if __name__ == "__main__":
    run_worker()

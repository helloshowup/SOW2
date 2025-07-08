from redis import Redis
from rq import Worker, Queue, Connection

from .config import get_settings
from .email_sender import EmailSender
import structlog

log = structlog.get_logger()

def run_agent_logic(run_id: int) -> None:
    """Placeholder agent logic that emails a summary."""
    log.info("Executing agent logic", run_id=run_id)
    top_results = [
        {"item": f"Result {i+1}", "score": 1 - i * 0.1} for i in range(5)
    ]
    EmailSender().send_summary_email(top_results, run_id)


def run_worker() -> None:
    """Start an RQ worker using configuration from environment variables."""
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    with Connection(redis_conn):
        worker = Worker([Queue(connection=redis_conn)])
        worker.work()


if __name__ == "__main__":
    run_worker()

import asyncio
import structlog

from .worker import run_agent_logic

log = structlog.get_logger()

async def run_agent_iteration(run_id: int, search_request: dict | None = None) -> None:
    """Execute one iteration of the agent logic with robust error handling."""
    try:
        await asyncio.to_thread(run_agent_logic, run_id, search_request)
    except Exception as exc:  # pragma: no cover - runtime safety
        log.error("Agent iteration failed", run_id=run_id, error=str(exc), exc_info=True)

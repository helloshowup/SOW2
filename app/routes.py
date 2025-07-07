from fastapi import APIRouter
import structlog

router = APIRouter()
log = structlog.get_logger()

@router.post("/run-agent")
async def run_agent():
    """Trigger the agent run (placeholder)."""
    log.info("run_agent.triggered")
    return {"message": "agent enqueued"}

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
import structlog

from .database import get_session
from .models import AgentRun, Feedback

router = APIRouter()
log = structlog.get_logger()

@router.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


@router.post("/feedback")
async def receive_feedback(
    run_id: int = Query(..., description="Agent run ID"),
    feedback: str = Query(..., regex="^(yes|no)$", description="yes or no"),
    session: Session = Depends(get_session),
):
    """Record yes/no feedback for a run."""
    run = session.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="AgentRun not found")
    fb = Feedback(run_id=run_id, value=feedback.lower())
    session.add(fb)
    session.commit()
    log.info("Feedback received", run_id=run_id, feedback=feedback)
    return {"message": "Feedback recorded"}

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession
import structlog

from .database import get_session
from .models import AgentRun, Feedback

router = APIRouter()
log = structlog.get_logger()


class FeedbackPayload(BaseModel):
    run_id: int = Field(..., description="Agent run ID")
    feedback: str = Field(..., pattern="^(yes|no)$", description="yes or no")


async def _store_feedback(session: AsyncSession, run_id: int, feedback: str) -> None:
    run = await session.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="AgentRun not found")
    fb = Feedback(run_id=run_id, value=feedback.lower())
    session.add(fb)
    await session.commit()
    log.info("Feedback received", run_id=run_id, feedback=feedback)

@router.post("/feedback")
async def receive_feedback(payload: FeedbackPayload, session: AsyncSession = Depends(get_session)):
    """Record yes/no feedback for a run via POST."""
    await _store_feedback(session, payload.run_id, payload.feedback)
    return {"message": "Feedback recorded"}


@router.get("/feedback")
async def receive_feedback_get(
    run_id: int = Query(..., description="Agent run ID"),
    feedback: str = Query(..., pattern="^(yes|no)$", description="yes or no"),
    session: AsyncSession = Depends(get_session),
):
    """Record yes/no feedback for a run via GET (from email links)."""
    await _store_feedback(session, run_id, feedback)
    return {"message": "Feedback recorded"}

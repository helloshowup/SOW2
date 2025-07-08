from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession
import structlog
from typing import List, Optional
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

@router.get("/runs/{run_id}/results")
async def get_run_results(run_id: int, session: AsyncSession = Depends(get_session)):
    """Retrieve the detailed results (outputs and search terms) for a specific agent run."""
    run = await session.get(AgentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="AgentRun not found")
    
    if run.result is None:
        return {"message": "Results not yet available or run failed", "status": run.status}

    return {
        "run_id": run.id,
        "status": run.status,
        "completed_at": run.completed_at,
        "results": run.result
    }

@router.get("/runs")
async def get_all_runs(
    limit: int = Query(10, description="Limit the number of runs returned"),
    offset: int = Query(0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session)
):
    """Retrieve a list of all agent runs, optionally with limit and offset."""
    statement = select(AgentRun).order_by(AgentRun.started_at.desc()).offset(offset).limit(limit)
    runs = (await session.exec(statement)).all()
    
    return [
        {
            "id": run.id,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "status": run.status,
            "error_message": run.error_message,
            "has_results": run.result is not None # Indicate if results exist without sending full JSON
        }
        for run in runs
    ]


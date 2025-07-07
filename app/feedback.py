from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel, Field, Session, create_engine
from typing import Optional
from datetime import datetime
import structlog

from .config import config

log = structlog.get_logger()

# Database engine for SQLite feedback store
FEEDBACK_DATABASE_URL = f"sqlite:///{config.FEEDBACK_DB_FILE}"
engine = create_engine(FEEDBACK_DATABASE_URL, echo=False)


class Feedback(SQLModel, table=True):
    """Simple table to capture yes/no feedback for agent runs."""

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int
    feedback: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


def create_feedback_db_and_tables() -> None:
    """Create tables if they do not exist."""
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


feedback_router = APIRouter()


@feedback_router.get("/feedback")
async def collect_feedback(
    run_id: int,
    feedback: str,
    session: Session = Depends(get_session),
):
    """Store yes/no feedback and return a thank you message."""
    value = feedback.lower()
    if value not in {"yes", "no"}:
        log.warning("feedback.invalid", run_id=run_id, feedback=feedback)
        raise HTTPException(status_code=400, detail="Feedback must be 'yes' or 'no'.")

    try:
        fb = Feedback(run_id=run_id, feedback=value)
        session.add(fb)
        session.commit()
        log.info("feedback.recorded", run_id=run_id, feedback=value)
        return {"message": "Thank you for your feedback!"}
    except Exception as exc:
        log.error("feedback.save_failed", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to record feedback")

# Ensure table exists on import
create_feedback_db_and_tables()


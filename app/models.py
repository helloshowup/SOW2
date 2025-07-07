from datetime import datetime
from typing import Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

class AgentRun(SQLModel, table=True):
    """Table to track each agent execution."""

    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    completed_at: Optional[datetime] = None
    status: str
    result: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    error_message: Optional[str] = None

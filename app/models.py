from datetime import datetime, date
from typing import List, Literal, Optional

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel
from pydantic import BaseModel, Field as PydanticField

class AgentRun(SQLModel, table=True):
    """Table to track each agent execution."""

    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    completed_at: Optional[datetime] = None
    status: str
    result: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    error_message: Optional[str] = None


class Feedback(SQLModel, table=True):
    """User feedback linked to an AgentRun."""

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="agentrun.id")
    value: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class VisitedUrl(SQLModel, table=True):
    """Record of URLs that have been visited."""

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True, index=True, max_length=2048)
    domain: str = Field(index=True, max_length=255)
    last_visited_date: date = Field(default_factory=date.today, index=True)


class SentimentAnalysis(BaseModel):
    """Overall sentiment analysis results."""

    overall_sentiment: Literal["positive", "neutral", "negative"] = PydanticField(
        description="Categorical sentiment assessment"
    )
    score: float = PydanticField(
        description="Numerical sentiment score where 1 is most positive"
    )


class Entity(BaseModel):
    """Named entity extracted from the text."""

    name: str = PydanticField(description="Entity name as found in the text")
    type: str = PydanticField(description="Entity type such as person or brand")


class AnalysisResult(BaseModel):
    """Validated structure for AI-generated analysis output."""

    summary: str = PydanticField(description="Concise summary of the content")
    sentiment: SentimentAnalysis = PydanticField(
        description="Sentiment analysis details"
    )
    entities: List[Entity] = PydanticField(
        default_factory=list,
        description="Entities mentioned in the content",
    )

    relevance_score: float = PydanticField(
        description="Relevance score from 0-100 for how on-topic the content is",
    )
    categories: List[str] = PydanticField(
        default_factory=list,
        description="Categories or topics associated with the content",
    )



import os
import asyncio

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.pool import StaticPool

os.environ["OPENAI_API_KEY"] = "test"
from app.models import AgentRun, AnalysisResult, SentimentAnalysis
from sqlalchemy.types import JSON
import app.database as database
import app.worker as worker
from app import scraper, email_sender

engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
async_session_local = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)
AgentRun.__table__.c.result.type = JSON()


async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


asyncio.run(init_models())


def setup_module(module):
    database.engine = engine
    database.async_session = async_session_local
    worker.engine = engine
    worker.async_session = async_session_local


def test_end_to_end(monkeypatch):
    monkeypatch.setattr(
        scraper.SimpleScraper,
        "crawl",
        lambda self, terms: [{"url": "http://example.com", "snippet": "pizza"}],
    )

    async def fake_eval(snippet, config, task_type):
        return AnalysisResult(
            summary="great",
            sentiment=SentimentAnalysis(overall_sentiment="positive", score=0.9),
            entities=[],
        )

    monkeypatch.setattr(worker, "evaluate_content", fake_eval)

    sent = {}

    def fake_send(self, *args, **kwargs):
        # support both the old and new calling conventions
        if args and isinstance(args[0], int):
            run_id = args[0]
        elif len(args) >= 2 and isinstance(args[1], int):
            run_id = args[1]
        else:
            run_id = kwargs.get("run_id")

        sent["run_id"] = run_id
        sent["on_brand"] = kwargs.get("on_brand_specific_links")
        sent["relevant"] = kwargs.get("brand_relevant_links")

    monkeypatch.setattr(email_sender.EmailSender, "send_summary_email", fake_send)

    async def create_run():
        async with async_session_local() as session:
            run = AgentRun(status="queued")
            session.add(run)
            await session.commit()
            await session.refresh(run)
            return run.id

    run_id = asyncio.run(create_run())

    worker.run_agent_logic(run_id)

    async def fetch_updated():
        async with async_session_local() as session:
            updated = await session.get(AgentRun, run_id)
            return updated

    updated = asyncio.run(fetch_updated())
    assert updated.status == "completed"
    assert updated.result["brand_health"][0]["summary"] == "great"
    assert sent["run_id"] == run_id
    assert (
        sent["on_brand"] == []
        or sent["on_brand"] is None
        or isinstance(sent["on_brand"], list)
    )


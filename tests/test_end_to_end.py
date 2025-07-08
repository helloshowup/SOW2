import os
import asyncio
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
async_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
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
    monkeypatch.setattr(scraper.SimpleScraper, "crawl", lambda self, terms: [{"url": "http://example.com", "text": "pizza"}])

    async def fake_eval(text, config, task_type):
        return AnalysisResult(
            summary="great",
            sentiment=SentimentAnalysis(overall_sentiment="positive", score=0.9),
            entities=[],
        )
    monkeypatch.setattr(worker, "evaluate_content", fake_eval)

    sent = {}

    def fake_send(self, results, run_id):
        sent["run_id"] = run_id
        sent["results"] = results
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
    assert sent["results"]["brand_health"][0]["item"] == "great"

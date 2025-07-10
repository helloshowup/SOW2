import os
import asyncio
import random
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import JSON

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("OPENAI_API_KEY", "test")

import app.database as database
from app.models import AgentRun, AnalysisResult, SentimentAnalysis
from app.agent import run_agent_iteration
from app import scraper, worker, email_sender

engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
async_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
AgentRun.__table__.c.result.type = JSON()

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

asyncio.run(init_models())

database.engine = engine
database.async_session = async_session_local
worker.engine = engine
worker.async_session = async_session_local


def test_market_queries_mix(monkeypatch):
    monkeypatch.setattr(random, "sample", lambda seq, k: list(seq)[:k])
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])

    captured_terms = []

    async def fake_crawl(self, session, terms, max_results=5):
        captured_terms.append(list(terms))
        return [{"url": "http://example.com", "snippet": "pizza"}]

    monkeypatch.setattr(scraper.SimpleScraper, "crawl", fake_crawl)

    async def fake_eval(snippet, config, task_type, custom_params=None):
        return AnalysisResult(
            summary="ok",
            snappy_heading="H",
            sentiment=SentimentAnalysis(overall_sentiment="positive", score=1.0),
            entities=[],
            relevance_score=90.0,
            categories=["News"],
        )

    monkeypatch.setattr(worker, "evaluate_content", fake_eval)
    monkeypatch.setattr(email_sender.EmailSender, "send_summary_email", lambda *a, **k: None)

    async def create_run():
        async with async_session_local() as session:
            run = AgentRun(status="queued")
            session.add(run)
            await session.commit()
            await session.refresh(run)
            return run.id

    run_id = asyncio.run(create_run())

    search_request = {
        "market_intelligence_queries": ["tech trend"],
        "rotating_search_phrases": ["analysis"],
        "max_search_terms_generated": 3,
    }

    asyncio.run(run_agent_iteration(run_id, search_request))

    assert captured_terms[0] == [
        "Debonairs Pizza analysis",
        "Debonairs Pizza analysis",
    ]

    assert captured_terms[1] == [
        "pizza tech trend",
        "pizza analysis",
        "culture tech trend",
    ]

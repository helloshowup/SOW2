import os
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("OPENAI_API_KEY", "test")
import asyncio
from sqlmodel import SQLModel, select
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.pool import StaticPool

from app.routes import router
from app.database import get_session
from app.models import AgentRun, Feedback
from sqlalchemy.types import JSON

# JSONB is unsupported in SQLite, patch to generic JSON for tests
AgentRun.__table__.c.result.type = JSON()

engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
async_session_local = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

asyncio.run(init_models())

app = FastAPI()


async def get_session_override():
    async with async_session_local() as session:
        yield session

app.dependency_overrides[get_session] = get_session_override
app.include_router(router)
client = TestClient(app)


def test_receive_feedback():
    # create a run to reference
    async def create_run():
        async with async_session_local() as session:
            run = AgentRun(status="completed")
            session.add(run)
            await session.commit()
            await session.refresh(run)
            return run.id

    run_id = asyncio.run(create_run())

    resp = client.post("/feedback", json={"run_id": run_id, "feedback": "yes"})
    assert resp.status_code == 200

    async def fetch_fb():
        async with async_session_local() as session:
            result = await session.exec(select(Feedback).where(Feedback.run_id == run_id))
            fb = result.first()
            return fb

    fb = asyncio.run(fetch_fb())
    assert fb is not None
    assert fb.value == "yes"


def test_receive_feedback_get():
    async def create_run2():
        async with async_session_local() as session:
            run = AgentRun(status="completed")
            session.add(run)
            await session.commit()
            await session.refresh(run)
            return run.id

    run_id = asyncio.run(create_run2())

    resp = client.get("/feedback", params={"run_id": run_id, "feedback": "no"})
    assert resp.status_code == 200

    async def fetch_fb2():
        async with async_session_local() as session:
            result = await session.exec(
                select(Feedback).where(Feedback.run_id == run_id).order_by(Feedback.id.desc())
            )
            return result.first()

    fb = asyncio.run(fetch_fb2())
    assert fb is not None
    assert fb.value == "no"


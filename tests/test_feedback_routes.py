from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy.pool import StaticPool

from app.routes import router
from app.database import get_session
from app.models import AgentRun, Feedback
from sqlalchemy.types import JSON

# JSONB is unsupported in SQLite, patch to generic JSON for tests
AgentRun.__table__.c.result.type = JSON()

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SQLModel.metadata.create_all(engine)

app = FastAPI()


def get_session_override():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = get_session_override
app.include_router(router)
client = TestClient(app)


def test_receive_feedback():
    # create a run to reference
    with Session(engine) as session:
        run = AgentRun(status="completed")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    resp = client.post("/feedback", params={"run_id": run_id, "feedback": "yes"})
    assert resp.status_code == 200

    with Session(engine) as session:
        fb = session.exec(select(Feedback).where(Feedback.run_id == run_id)).first()
        assert fb is not None
        assert fb.value == "yes"

import types
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.models import AgentRun
from sqlalchemy.types import JSON
import app.database as database
import app.worker as worker
from app import scraper, email_sender

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
AgentRun.__table__.c.result.type = JSON()
SQLModel.metadata.create_all(engine)

def setup_module(module):
    database.engine = engine
    worker.engine = engine

def test_end_to_end(monkeypatch):
    monkeypatch.setattr(scraper.SimpleScraper, "crawl", lambda self, terms: [{"url": "http://example.com", "text": "pizza"}])

    async def fake_eval(text, config, task_type):
        return {"summary": "great"}
    monkeypatch.setattr(worker, "evaluate_content", fake_eval)

    sent = {}

    def fake_send(self, results, run_id):
        sent["run_id"] = run_id
        sent["results"] = results
    monkeypatch.setattr(email_sender.EmailSender, "send_summary_email", fake_send)

    with Session(engine) as session:
        run = AgentRun(status="queued")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id

    worker.run_agent_logic(run_id)

    with Session(engine) as session:
        updated = session.get(AgentRun, run_id)
        assert updated.status == "completed"
        assert updated.result["evaluations"][0]["summary"] == "great"
    assert sent["run_id"] == run_id
    assert sent["results"][0]["item"] == "great"

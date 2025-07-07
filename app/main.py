import logging
import sys

from fastapi import FastAPI, Depends, HTTPException
from redis import Redis
from rq import Queue
from sqlmodel import SQLModel, Session, create_engine
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import httpx

from .config import get_settings

from .routes import router as api_router
from .models import AgentRun

settings = get_settings()

DATABASE_URL = settings.database_url
engine = create_engine(DATABASE_URL, echo=True)
redis_conn = Redis.from_url(settings.redis_url)
task_queue = Queue(connection=redis_conn)
scheduler = AsyncIOScheduler()

def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)

def setup_logging() -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level,
    )
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.log_level)),
    )

def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI(title="AI Agent Backend")

async def trigger_run_agent() -> None:
    """Scheduler job that calls the /run-agent endpoint."""
    log = structlog.get_logger()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://localhost:8000/run-agent")
            response.raise_for_status()
            log.info("Scheduled run-agent trigger succeeded", status_code=response.status_code)
    except Exception as exc:
        log.error("Scheduled run-agent trigger failed", error=str(exc), exc_info=True)


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database and scheduler on startup."""
    setup_logging()
    create_db_and_tables()
    scheduler.add_job(
        trigger_run_agent,
        IntervalTrigger(minutes=settings.agent_run_interval_minutes),
        id="agent_run_scheduler",
        replace_existing=True,
        misfire_grace_time=60,
    )
    scheduler.start()
    structlog.get_logger().info(
        "APScheduler started", interval=settings.agent_run_interval_minutes
    )

@app.on_event("shutdown")
def on_shutdown() -> None:
    scheduler.shutdown()

app.include_router(api_router)

# Default root path
@app.get("/")
async def read_root():
    return {"message": "AI Agent Backend"}


@app.post("/run-agent")
async def run_agent(session: Session = Depends(get_session)):
    """Manually trigger an agent run and enqueue worker job."""
    log = structlog.get_logger()
    try:
        new_run = AgentRun(status="queued")
        session.add(new_run)
        session.commit()
        session.refresh(new_run)
        task_queue.enqueue("app.worker.run_agent_logic", run_id=new_run.id)
        log.info("Agent run enqueued", run_id=new_run.id)
        return {"run_id": new_run.id}
    except Exception as exc:
        log.error("Failed to enqueue agent run", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to enqueue agent run")


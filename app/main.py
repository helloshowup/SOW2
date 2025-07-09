import logging
import sys

from fastapi import FastAPI, Depends, HTTPException
from redis import Redis
from rq import Queue
from sqlmodel.ext.asyncio.session import AsyncSession
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import httpx

from .config import get_settings
from .database import get_session, init_db

from .routes import router as api_router, admin_router
from .models import AgentRun

settings = get_settings()

redis_conn = Redis.from_url(settings.redis_url)
task_queue = Queue(connection=redis_conn)
scheduler = AsyncIOScheduler()

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

app = FastAPI(title="AI Agent Backend")

async def trigger_run_agent() -> None:
    """Scheduler job that calls the /run-agent endpoint."""
    log = structlog.get_logger()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post("http://localhost:8000/run-agent")
            response.raise_for_status()
            log.info(
                "Scheduled run-agent trigger succeeded",
                status_code=response.status_code,
            )
    except Exception as exc:
        log.error(
            "Scheduled run-agent trigger failed", error=str(exc), exc_info=True
        )

# New function to trigger daily email
async def trigger_daily_email_job() -> None:
    """Scheduler job that enqueues the daily email compilation task."""
    log = structlog.get_logger()
    try:
        task_queue.enqueue("app.worker.compile_and_send_daily_email")
        log.info("Daily email compilation job enqueued successfully.")
    except Exception as exc:
        log.error(
            "Failed to enqueue daily email compilation job",
            error=str(exc),
            exc_info=True,
        )


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database and scheduler on startup."""
    setup_logging()
    await init_db()
    scheduler.add_job(
        trigger_run_agent,
        IntervalTrigger(minutes=settings.agent_run_interval_minutes),
        id="agent_run_scheduler",
        replace_existing=True,
        misfire_grace_time=60,
    )
    scheduler.add_job(
        trigger_daily_email_job,
        CronTrigger(
            hour=settings.daily_email_hour,
            minute=settings.daily_email_minute,
        ),
        id="daily_email_scheduler",
        replace_existing=True,
        misfire_grace_time=600,
    )
    scheduler.start()
    structlog.get_logger().info(
        "APScheduler started",
        interval=settings.agent_run_interval_minutes,
        daily_email_time=f"{settings.daily_email_hour:02d}:{settings.daily_email_minute:02d}",
    )

@app.on_event("shutdown")
def on_shutdown() -> None:
    scheduler.shutdown()

app.include_router(api_router)
app.include_router(admin_router)  # Include the new admin router

# Default root path
@app.get("/")
async def read_root():
    return {"message": "AI Agent Backend"}

# Health check endpoint
@app.get("/health", status_code=200)
async def health_check():
    """Provide simple health status for monitoring."""
    return {"status": "ok"}


@app.post("/run-agent")
async def run_agent(session: AsyncSession = Depends(get_session)):
    """Manually trigger an agent run and enqueue worker job."""
    log = structlog.get_logger()
    try:
        new_run = AgentRun(status="queued")
        session.add(new_run)
        await session.commit()
        await session.refresh(new_run)
        task_queue.enqueue("app.worker.run_agent_logic", run_id=new_run.id)
        log.info("Agent run enqueued", run_id=new_run.id)
        return {"run_id": new_run.id}
    except Exception as exc:
        log.error("Failed to enqueue agent run", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to enqueue agent run")


"""FastAPI app with in-app APScheduler."""

import httpx
import structlog
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .routes import router as api_router
from .feedback import feedback_router

log = structlog.get_logger()
scheduler = AsyncIOScheduler()

async def trigger_run_agent():
    """Call the internal /run-agent endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post("http://localhost:8000/run-agent")
            resp.raise_for_status()
            log.info("scheduler.triggered", status=resp.status_code)
    except Exception as exc:
        log.error("scheduler.failed", error=str(exc))

def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(api_router)
    app.include_router(feedback_router)

    @app.on_event("startup")
    async def start_scheduler():
        scheduler.add_job(
            trigger_run_agent,
            IntervalTrigger(minutes=10),
            id="run_agent_job",
            replace_existing=True,
        )
        scheduler.start()
        log.info("scheduler.started")

    @app.on_event("shutdown")
    async def stop_scheduler():
        if scheduler.running:
            scheduler.shutdown()
            log.info("scheduler.stopped")

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

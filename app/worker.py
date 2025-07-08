from redis import Redis
from rq import Worker, Queue

import asyncio
import os
from datetime import datetime
from sqlmodel import Session

from .config import get_settings
from .email_sender import EmailSender
from .scraper import (
    SimpleScraper,
    load_brand_keywords,
    generate_search_terms,
)
from .brand_parser import load_brand_config
from .openai_evaluator import evaluate_content
from .database import engine
from .models import AgentRun
import structlog

log = structlog.get_logger()


def run_agent_logic(run_id: int) -> None:
    """Scrape the web, evaluate content, store results, and send an email."""
    log.info("Executing agent logic", run_id=run_id)

    # mark run as running
    with Session(engine) as session:
        run = session.get(AgentRun, run_id)
        if not run:
            log.error("AgentRun not found", run_id=run_id)
            return
        run.status = "running"
        session.add(run)
        session.commit()

    brand_id = os.getenv("BRAND_ID", "debonairs")
    brand_config = load_brand_config(brand_id) or {}
    keywords = load_brand_keywords(brand_id)
    search_terms = generate_search_terms(keywords)

    scraper = SimpleScraper()
    pages = scraper.crawl(search_terms)

    evaluations = []
    for page in pages:
        if not page.get("text"):
            continue
        result = asyncio.run(evaluate_content(page["text"], brand_config))
        if result:
            result["url"] = page.get("url")
            evaluations.append(result)

    # store completed results
    with Session(engine) as session:
        run = session.get(AgentRun, run_id)
        if run:
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.result = {"evaluations": evaluations}
            session.add(run)
            session.commit()

    # prepare simple summary for email
    top_results = [
        {"item": ev.get("summary", ev.get("url", "")), "score": 1.0}
        for ev in evaluations[:5]
    ]
    EmailSender().send_summary_email(top_results, run_id)


def run_worker() -> None:
    """Start an RQ worker using configuration from environment variables."""
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    worker = Worker([Queue(connection=redis_conn)], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    run_worker()

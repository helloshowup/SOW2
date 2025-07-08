from redis import Redis
from rq import Worker, Queue

import asyncio
import os
import json
import logging
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

# Configure logging for better visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

log = structlog.get_logger()


def load_search_config(config_path: str = "search_config.json") -> dict | None:
    """Load search configuration from a JSON file."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(
            "Configuration file not found at %s. Please create it.", config_path
        )
    except json.JSONDecodeError:
        logging.error(
            "Error decoding JSON from %s. Please check its format.", config_path
        )
    return None


def run_agent_logic(run_id: int, search_request: dict | None = None) -> None:
    """Scrape the web, evaluate content, store results, and send an email.

    If ``search_request`` is provided, it should contain ``brand_health_queries``
    and ``market_intelligence_queries`` lists which will be used instead of the
    default keyword-generated search terms.
    """
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

    scraper = SimpleScraper()

    brand_evals: list[dict] = []
    market_evals: list[dict] = []

    def crawl_and_evaluate(queries: list[str], task_type: str) -> None:
        pages = scraper.crawl(queries)
        for page in pages:
            if not page.get("text"):
                continue
            result = asyncio.run(
                evaluate_content(page["text"], brand_config, task_type)
            )
            if result:
                result["url"] = page.get("url")
                if task_type == "market_intelligence":
                    market_evals.append(result)
                else:
                    brand_evals.append(result)

    if search_request:
        brand_queries = search_request.get("brand_health_queries") or []
        if brand_queries:
            log.info("Starting Brand Health analysis", queries=brand_queries)
            crawl_and_evaluate(brand_queries, "brand_health")

        market_queries = search_request.get("market_intelligence_queries") or []
        if market_queries:
            log.info("Starting Market Intelligence analysis", queries=market_queries)
            crawl_and_evaluate(market_queries, "market_intelligence")

        if not brand_queries and not market_queries:
            search_terms = generate_search_terms(keywords)
            crawl_and_evaluate(search_terms, "brand_health")
    else:
        search_terms = generate_search_terms(keywords)
        crawl_and_evaluate(search_terms, "brand_health")

    # store completed results
    with Session(engine) as session:
        run = session.get(AgentRun, run_id)
        if run:
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.result = {
                "brand_health": brand_evals,
                "market_intelligence": market_evals,
            }
            session.add(run)
            session.commit()

    # prepare simple summary for email
    brand_top = [
        {"item": ev.get("summary", ev.get("url", "")), "score": 1.0}
        for ev in brand_evals[:5]
    ]
    market_top = [
        {"item": ev.get("summary", ev.get("url", "")), "score": 1.0}
        for ev in market_evals[:5]
    ]
    EmailSender().send_summary_email(
        {"brand_health": brand_top, "market_intelligence": market_top},
        run_id,
    )


def run_worker() -> None:
    """Start an RQ worker using configuration from environment variables."""
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    worker = Worker([Queue(connection=redis_conn)], connection=redis_conn)
    worker.work()


if __name__ == "__main__":
    run_worker()

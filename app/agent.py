import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List

import structlog

from .email_sender import EmailSender
from .scraper import SimpleScraper, load_brand_keywords, generate_search_terms
from .brand_parser import load_brand_config
from .openai_evaluator import _construct_prompt_messages
from . import database
from .models import AgentRun

log = structlog.get_logger()

async def _process_batch(pages: List[Dict[str, Any]], brand_config: Dict[str, Any], task_type: str) -> List[Dict[str, Any]]:
    from . import worker  # allows monkeypatching evaluate_content in tests

    tasks = []
    valid_pages = []
    for page in pages:
        if page.get("snippet"):
            valid_pages.append(page)
            tasks.append(
                worker.evaluate_content(page["snippet"], brand_config, task_type)
            )
    results = await asyncio.gather(*tasks)
    processed: List[Dict[str, Any]] = []
    for page, res in zip(valid_pages, results):
        if res:
            result = res.model_dump()
            result["url"] = page.get("url")
            processed.append(result)
    return processed

async def run_agent_iteration(run_id: int, search_request: dict | None = None) -> None:
    """Execute one iteration of the agent logic collecting rich metadata."""
    try:
        # mark run as running
        async with database.async_session() as session:
            run = await session.get(AgentRun, run_id)
            if not run:
                log.error("AgentRun not found", run_id=run_id)
                return
            run.status = "running"
            session.add(run)
            await session.commit()

        brand_id = os.getenv("BRAND_ID", "debonairs")
        brand_config = load_brand_config(brand_id) or {}
        keywords = load_brand_keywords(brand_id)

        scraper = SimpleScraper()
        search_terms_generated: List[str] = []
        search_times: List[str] = []
        brand_pages: List[Dict[str, Any]] = []
        market_pages: List[Dict[str, Any]] = []

        if search_request:
            brand_queries = search_request.get("brand_health_queries") or []
            market_queries = search_request.get("market_intelligence_queries") or []
        else:
            brand_queries = generate_search_terms(keywords)
            market_queries = []

        search_terms_generated.extend(brand_queries)
        search_terms_generated.extend(market_queries)

        def crawl_terms(terms: List[str]) -> List[Dict[str, Any]]:
            pages: List[Dict[str, Any]] = []
            if not terms:
                return pages
            search_times.extend([datetime.utcnow().isoformat() for _ in terms])
            for page in scraper.crawl(terms):
                pages.append(page)
            return pages

        brand_pages = crawl_terms(brand_queries)
        market_pages = crawl_terms(market_queries)

        brand_evals: List[Dict[str, Any]] = []
        market_evals: List[Dict[str, Any]] = []
        if brand_pages:
            brand_evals = await _process_batch(brand_pages, brand_config, "brand_health")
        if market_pages:
            market_evals = await _process_batch(market_pages, brand_config, "market_intelligence")

        brand_terms = [brand_config.get("display_name", "").lower()] + [k.lower() for k in keywords]
        on_brand_specific_links: List[str] = []
        brand_relevant_links: List[str] = []
        all_pages = brand_pages + market_pages
        all_evals = brand_evals + market_evals
        for page, res in zip(all_pages, all_evals):
            snippet = page.get("snippet", "").lower()
            url = page.get("url")
            if any(term in snippet for term in brand_terms):
                on_brand_specific_links.append(url)
            else:
                brand_relevant_links.append(url)

        content_summaries = [ev.get("summary", "") for ev in all_evals]
        user_prompt = all_pages[0]["snippet"] if all_pages else ""
        brand_system_prompt = _construct_prompt_messages("brand_health", brand_config, "")[0]["content"]
        market_system_prompt = _construct_prompt_messages("market_intelligence", brand_config, "")[0]["content"]

        # store results
        async with database.async_session() as session:
            run = await session.get(AgentRun, run_id)
            if run:
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                run.result = {
                    "brand_health": brand_evals,
                    "market_intelligence": market_evals,
                }
                session.add(run)
                await session.commit()

        EmailSender().send_summary_email(
            run_id=run_id,
            on_brand_specific_links=on_brand_specific_links,
            brand_relevant_links=brand_relevant_links,
            brand_system_prompt=brand_system_prompt,
            market_system_prompt=market_system_prompt,
            user_prompt=user_prompt,
            search_terms_generated=search_terms_generated,
            num_search_calls=len(search_terms_generated),
            search_times=search_times,
            content_summaries=content_summaries,
        )
    except Exception as exc:  # pragma: no cover - runtime safety
        log.error("Agent iteration failed", run_id=run_id, error=str(exc), exc_info=True)

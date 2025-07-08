import asyncio
import os
import random
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

        max_generated_terms = (
            search_request.get("max_search_terms_generated", 5) if search_request else 5
        )

        brand_queries: List[str] = []
        market_queries: List[str] = []

        custom_query_phrases = (
            search_request.get("custom_query_phrases") if search_request else None
        )

        if custom_query_phrases and keywords:
            sampled_keywords = random.sample(
                keywords, min(max_generated_terms, len(keywords))
            )
            generated_custom_queries: List[str] = []
            for kw in sampled_keywords:
                for phrase in custom_query_phrases:
                    generated_custom_queries.append(f"{kw} {phrase}")
                    if len(generated_custom_queries) >= max_generated_terms:
                        break
                if len(generated_custom_queries) >= max_generated_terms:
                    break
            if generated_custom_queries:
                brand_queries = generated_custom_queries
                log.info(
                    "Generated custom queries from search_config.json",
                    num_queries=len(brand_queries),
                )

        if not brand_queries:
            brand_queries = brand_config.get("search_queries", {}).get(
                "brand_health", []
            )
            market_queries = brand_config.get("search_queries", {}).get(
                "market_intelligence", []
            )
            if brand_queries or market_queries:
                log.info(
                    "Using generic default queries from brand config",
                    num_brand_queries=len(brand_queries),
                    num_market_queries=len(market_queries),
                )

        if not brand_queries and not market_queries:
            brand_queries = generate_search_terms(
                keywords, max_terms=max_generated_terms
            )
            log.info(
                "Using simple 'news' queries as fallback",
                num_queries=len(brand_queries),
            )

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

        # limit for number of links to send
        max_email_links = search_request.get("max_email_links", 10) if search_request else 10

        evaluated_pages_with_scores: List[Dict[str, Any]] = []
        all_pages = brand_pages + market_pages
        all_evals = brand_evals + market_evals
        for page, res in zip(all_pages, all_evals):
            if (
                res
                and page.get("url")
                and "relevance_score" in res
                and "categories" in res
            ):
                evaluated_pages_with_scores.append(
                    {
                        "url": page.get("url"),
                        "snippet": page.get("snippet", ""),
                        "evaluation": res,
                    }
                )

        on_brand_specific_items: List[Dict[str, Any]] = []
        brand_relevant_items: List[Dict[str, Any]] = []

        for item in evaluated_pages_with_scores:
            url = item["url"]
            snippet = item["snippet"].lower()
            score = item["evaluation"].get("relevance_score", 0)

            if any(term in snippet for term in brand_terms):
                on_brand_specific_items.append({"url": url, "score": score})
            else:
                brand_relevant_items.append({"url": url, "score": score})

        on_brand_specific_items.sort(key=lambda x: x["score"], reverse=True)
        brand_relevant_items.sort(key=lambda x: x["score"], reverse=True)

        on_brand_specific_links = [i["url"] for i in on_brand_specific_items[:max_email_links]]
        brand_relevant_links = [i["url"] for i in brand_relevant_items[:max_email_links]]

        content_summaries = [
            item["evaluation"].get("summary", "")
            for item in evaluated_pages_with_scores
        ]
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

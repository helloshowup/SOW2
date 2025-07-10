import asyncio
import os
import json
import random
from datetime import datetime, date
from typing import Any, Dict, List, Iterable, Optional
from urllib.parse import urlparse

import structlog
from .email_sender import EmailSender
from .scraper import (
    SimpleScraper,
    load_brand_keywords,
    load_search_config,
)
from .brand_parser import load_brand_config
from .openai_evaluator import _construct_prompt_messages
from . import database
from .database import get_db
from .models import AgentRun, VisitedUrl, EvaluatedSnippet
from .config import get_settings
from sqlmodel.ext.asyncio.session import AsyncSession

log = structlog.get_logger()

# limit concurrent OpenAI evaluations
MAX_CONCURRENT_EVALUATIONS = 10
# limit number of pages processed per batch
MAX_BATCH_SIZE = 20

# minimum relevance required for a snippet to be considered
MIN_RELEVANCE_SCORE = 60

# file to persist daily search count
SEARCH_COUNT_FILE = "search_count.json"


def _chunked(seq: List[Dict[str, Any]], size: int) -> Iterable[List[Dict[str, Any]]]:
    """Yield successive ``size``-sized chunks from ``seq``."""
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _load_daily_search_count() -> int:
    """Return today's search count stored in SEARCH_COUNT_FILE."""
    path = os.path.join(os.getcwd(), SEARCH_COUNT_FILE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("date") == date.today().isoformat():
                return int(data.get("count", 0))
    except FileNotFoundError:
        return 0
    except Exception as exc:  # pragma: no cover - read failures
        log.warning("Failed to load search count", error=str(exc))
    return 0


def _save_daily_search_count(count: int) -> None:
    """Persist today's search count to SEARCH_COUNT_FILE."""
    path = os.path.join(os.getcwd(), SEARCH_COUNT_FILE)
    data = {"date": date.today().isoformat(), "count": count}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as exc:  # pragma: no cover - write failures
        log.warning("Failed to save search count", error=str(exc))


async def run_searches(
    scraper: SimpleScraper, session: AsyncSession, terms: List[str]
) -> tuple[list[dict], list[str]]:
    """Run Google searches for the provided terms respecting the daily limit."""

    if not terms:
        return [], []

    settings = get_settings()
    current = _load_daily_search_count()
    remaining = settings.max_daily_searches - current
    if remaining <= 0:
        log.warning("Daily search quota exhausted", limit=settings.max_daily_searches)
        return [], []

    limited_terms = list(terms)[:remaining]
    if len(limited_terms) < len(terms):
        log.info(
            "Truncating search terms due to daily limit",
            attempted=len(terms),
            executed=len(limited_terms),
        )

    pages = await scraper.crawl(session, limited_terms)
    _save_daily_search_count(current + len(limited_terms))
    return pages, limited_terms

async def _process_batch(
    pages: List[Dict[str, Any]],
    brand_config: Dict[str, Any],
    task_type: str,
    custom_params: Optional[dict] = None,
) -> List[Dict[str, Any]]:
    from . import worker  # allows monkeypatching evaluate_content in tests

    semaphore = asyncio.BoundedSemaphore(MAX_CONCURRENT_EVALUATIONS)

    async def evaluate_with_semaphore(snippet: str):
        async with semaphore:
            return await worker.evaluate_content(
                snippet, brand_config, task_type, custom_params
            )

    tasks = []
    valid_pages = []
    for page in pages:
        if page.get("snippet"):
            valid_pages.append(page)
            tasks.append(evaluate_with_semaphore(page["snippet"]))

    results = await asyncio.gather(*tasks)
    processed: List[Dict[str, Any]] = []
    for page, res in zip(valid_pages, results):
        if res:
            result = res.model_dump()
            result["url"] = page.get("url")
            processed.append(result)
    return processed

async def run_agent_iteration(
    run_id: int,
    search_request: dict | None = None,
    custom_params: Optional[dict] = None,
) -> None:
    """Execute one iteration of the agent logic collecting rich metadata."""
    if custom_params is None:
        custom_params = {}

    async with database.async_session() as session:
        try:
            run = await session.get(AgentRun, run_id)
            if not run:
                log.error("AgentRun not found", run_id=run_id)
                return
            run.status = "running"
            session.add(run)
            await session.commit()
            await session.refresh(run)

            brand_id = os.getenv("BRAND_ID", "debonairs")
            brand_config = load_brand_config(brand_id) or {}
            keywords = load_brand_keywords(brand_id)

            scraper = SimpleScraper()
            search_terms_generated: List[str] = []
            search_times: List[str] = []
            brand_pages: List[Dict[str, Any]] = []
            market_pages: List[Dict[str, Any]] = []
    
            # Load search config for dynamic phrases
            current_search_config = load_search_config()
            rotating_search_phrases = current_search_config.get(
                "rotating_search_phrases", ["news", "updates", "trends"]
            )
    
            max_generated_terms = (
                search_request.get("max_search_terms_generated", 5) if search_request else 5
            )
    
            brand_queries: List[str] = []
            market_phrase_list: List[str] = (

                search_request.get("market_intelligence_queries", [])
                if search_request
                else []
            )
            rotating_phrases_override: List[str] = (
                search_request.get("rotating_search_phrases", [])
                if search_request
                else []
            )
            rotating_phrases = (
                rotating_phrases_override or rotating_search_phrases
            )
            market_queries: List[str] = []

    
            custom_query_phrases = None
            if search_request:
                custom_query_phrases = search_request.get("custom_query_phrases")
                if not custom_query_phrases:
                    custom_query_phrases = search_request.get("brand_health_queries")
    
            if custom_query_phrases and keywords:
                sampled_keywords = random.sample(
                    keywords, min(max_generated_terms, len(keywords))
                )
                generated_custom_queries: List[str] = []
                for kw in sampled_keywords:
                    # Mix and match with rotating search phrases
                    random_phrase = random.choice(rotating_phrases)

                    generated_custom_queries.append(f"{kw} {random_phrase}")
                    if len(generated_custom_queries) >= max_generated_terms:
                        break
                if generated_custom_queries:
                    brand_queries = generated_custom_queries
                    log.info(
                        "Generated custom queries from search_config.json with rotating phrases",
                        num_queries=len(brand_queries),
                    )

            if market_phrase_list and keywords:
                sampled_keywords = random.sample(
                    keywords, min(max_generated_terms, len(keywords))
                )
                combined_phrases = market_phrase_list + rotating_phrases
                generated_market_queries: List[str] = []
                for kw in sampled_keywords:
                    for phrase in combined_phrases:
                        generated_market_queries.append(f"{kw} {phrase}")
                        if len(generated_market_queries) >= max_generated_terms:
                            break
                    if len(generated_market_queries) >= max_generated_terms:
                        break
                if generated_market_queries:
                    market_queries = generated_market_queries
                    log.info(
                        "Generated market intelligence queries from search_config.json",
                        num_queries=len(market_queries),
                    )

    
            defaults_used = False
            if not brand_queries:
                brand_queries = brand_config.get("search_queries", {}).get(
                    "brand_health", []
                )
                defaults_used = defaults_used or bool(brand_queries)
            if not market_queries:
                market_queries = brand_config.get("search_queries", {}).get(
                    "market_intelligence", []
                )
                defaults_used = defaults_used or bool(market_queries)
            if defaults_used:
                log.info(
                    "Using generic default queries from brand config",
                    num_brand_queries=len(brand_queries),
                    num_market_queries=len(market_queries),
                )
    
            if not brand_queries and not market_queries:
                # If no specific queries, generate from keywords + rotating phrases
                generated_fallback_queries: List[str] = []
                if keywords:
                    sampled_keywords = random.sample(
                        keywords, min(max_generated_terms, len(keywords))
                    )
                    for kw in sampled_keywords:
                        random_phrase = random.choice(rotating_phrases)

                        generated_fallback_queries.append(f"{kw} {random_phrase}")
                        if len(generated_fallback_queries) >= max_generated_terms:
                            break
                brand_queries = generated_fallback_queries or ["latest news"]
                log.info(
                    "Using generated queries from keywords and rotating phrases as fallback",
                    num_queries=len(brand_queries),
                )
    
            async def crawl_terms(terms: List[str]) -> List[Dict[str, Any]]:
                pages, executed_terms = await run_searches(scraper, session, terms)
                if executed_terms:
                    search_terms_generated.extend(executed_terms)
                    search_times.extend(
                        [datetime.utcnow().isoformat() for _ in executed_terms]
                    )
                return pages

            brand_pages = await crawl_terms(brand_queries)
            market_pages = await crawl_terms(market_queries)
    
            # Store visited URLs
            current_date = date.today()
            for page in brand_pages + market_pages:
                try:
                    parsed = urlparse(page["url"])
                    domain = parsed.netloc
                    url_obj = VisitedUrl(
                        url=page["url"], domain=domain, last_visited_date=current_date
                    )
                    session.add(url_obj)
                    await session.commit()
                    await session.refresh(url_obj)
                except Exception as e:
                    log.warning(
                        f"Could not add URL to VisitedUrl table: {page['url']}, Error: {e}"
                    )
                    await session.rollback()
    
            brand_evals: List[Dict[str, Any]] = []
            market_evals: List[Dict[str, Any]] = []

            if brand_pages:
                for chunk in _chunked(brand_pages, MAX_BATCH_SIZE):
                    brand_evals.extend(
                        await _process_batch(
                            chunk, brand_config, "brand_health", custom_params
                        )
                    )
            if market_pages:
                for chunk in _chunked(market_pages, MAX_BATCH_SIZE):
                    market_evals.extend(
                        await _process_batch(
                            chunk,
                            brand_config,
                            "market_intelligence",
                            custom_params,
                        )
                    )

            # Persist evaluated snippets
            try:
                db_gen = get_db()
                db = next(db_gen)
                for ev in brand_evals:
                    new_snippet = EvaluatedSnippet(
                        url=ev.get("url"),
                        title=ev.get("snappy_heading"),
                        content_summary=ev.get("summary"),
                        relevance_score=ev.get("relevance_score"),
                        category="brand_health",
                    )
                    db.add(new_snippet)
                for ev in market_evals:
                    new_snippet = EvaluatedSnippet(
                        url=ev.get("url"),
                        title=ev.get("snappy_heading"),
                        content_summary=ev.get("summary"),
                        relevance_score=ev.get("relevance_score"),
                        category="market_intelligence",
                    )
                    db.add(new_snippet)
                db.commit()
            except Exception as e:
                if 'db' in locals():
                    db.rollback()
                log.error("Failed to store evaluated snippets", error=str(e))
            finally:
                if 'db' in locals():
                    db.close()
    
            brand_display_name = brand_config.get("display_name", "").lower()
            brand_terms = [k.lower() for k in keywords]
    
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
                heading = item["evaluation"].get("snappy_heading", "")

                if score < MIN_RELEVANCE_SCORE:
                    continue

                if brand_display_name and brand_display_name in snippet:
                    on_brand_specific_items.append({"url": url, "score": score, "snappy_heading": heading})
                else:
                    brand_relevant_items.append({"url": url, "score": score, "snappy_heading": heading})
    
            on_brand_specific_items.sort(key=lambda x: x["score"], reverse=True)
            brand_relevant_items.sort(key=lambda x: x["score"], reverse=True)
    
            on_brand_specific_links = [
                {"url": i["url"], "snappy_heading": i.get("snappy_heading", "")}
                for i in on_brand_specific_items[:max_email_links]
            ]
            brand_relevant_links = [
                {"url": i["url"], "snappy_heading": i.get("snappy_heading", "")}
                for i in brand_relevant_items[:max_email_links]
            ]
    
            content_summaries = [
                item["evaluation"].get("summary", "")
                for item in evaluated_pages_with_scores
            ]
            user_prompt = all_pages[0]["snippet"] if all_pages else ""
            brand_system_prompt = custom_params.get("brand_system_prompt") or _construct_prompt_messages(
                "brand_health", brand_config, ""
            )[0]["content"]
            market_system_prompt = custom_params.get("market_system_prompt") or _construct_prompt_messages(
                "market_intelligence", brand_config, ""
            )[0]["content"]
    
            # store results
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
            run = await session.get(AgentRun, run_id)
            if run:
                run.status = "failed"
                run.error_message = str(exc)
                session.add(run)
                await session.commit()

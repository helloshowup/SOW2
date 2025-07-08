import os
import random
from dataclasses import dataclass
from typing import Iterable
import json
from urllib.parse import urlparse

from googlesearch import search as google_search  # Interacts with Google Search
# Ensure usage complies with Google's Terms of Service regarding automated access
# and data handling.
import yaml
import structlog

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import get_settings
from .models import VisitedUrl

log = structlog.get_logger(__name__)


@dataclass
class ScrapedContent:
    """Represents content scraped from a single source."""

    content: str
    source_url: str
    search_query: str


def load_brand_keywords(brand_id: str, repo_path: str | None = None) -> list[str]:
    """Return the list of keywords for a brand defined in the YAML repository."""
    settings = get_settings()
    path = repo_path or getattr(settings, "brand_repo_path", "dev-research/brand_repo.yaml")
    if not os.path.exists(path):
        log.error("Brand repository not found", path=path)
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - invalid YAML
        log.error("Failed to parse brand repository", error=str(exc))
        return []
    for brand in data.get("brands", []):
        if brand.get("id") == brand_id or brand.get("display_name") == brand_id:
            keywords = brand.get("keywords", {})
            return list(keywords.get("core", [])) + list(keywords.get("extended", []))
    log.warning("Brand id not found", brand_id=brand_id)
    return []


def generate_search_terms(keywords: list[str], max_terms: int = 5) -> list[str]:
    """Create search terms from brand keywords with simple variations."""
    if not keywords or max_terms <= 0:
        return []
    sampled = random.sample(keywords, min(max_terms, len(keywords)))
    return [f"{kw} news" for kw in sampled]


def load_search_config(config_path: str = "search_config.json") -> dict:
    """Load search configuration from a JSON file in the project root."""
    search_request_data: dict = {}
    full_path = os.path.join(os.getcwd(), config_path)
    if os.path.exists(full_path):
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                search_request_data = json.load(f)
        except FileNotFoundError:
            log.error("Configuration file not found at %s. Please create it.", full_path)
        except json.JSONDecodeError:
            log.error("Error decoding JSON from %s. Please check its format.", full_path)
    else:
        log.info("search_config.json not found at %s", full_path)
    return search_request_data


class SimpleScraper:
    """Utility class that surfaces Google SERP snippets for given queries."""

    def __init__(self) -> None:
        self.search_config = load_search_config()
        self.blacklisted_domains = set(
            self.search_config.get("blacklisted_domains", [])
        )

    async def _is_url_blacklisted(self, url: str) -> bool:
        """Check if a URL belongs to a blacklisted domain."""
        try:
            domain = urlparse(url).netloc
            if domain.startswith("www."):
                domain = domain[4:]
            return domain in self.blacklisted_domains
        except Exception as e:  # pragma: no cover - malformed URL
            log.warning(f"Could not parse domain for URL {url}: {e}")
            return False

    async def _is_url_visited(self, session: AsyncSession, url: str) -> bool:
        """Check if a URL has already been visited."""
        statement = select(VisitedUrl).where(VisitedUrl.url == url)
        result = await session.exec(statement)
        return result.first() is not None

    async def search(
        self, session: AsyncSession, term: str, max_results: int = 5
    ) -> list[dict]:
        """Search Google and return structured results with snippets, applying filters."""
        log.info("Searching Google for term", term=term)
        try:
            raw_results = list(
                google_search(term, num_results=max_results, advanced=True)
            )
        except Exception as exc:  # pragma: no cover - network failures
            log.error("Google search failed", term=term, error=str(exc))
            return []

        results = []
        for res in raw_results:
            url = getattr(res, "url", "") or ""
            url = url.strip()

            snippet = getattr(res, "description", "")
            if snippet is None:
                snippet = ""
            snippet = snippet.strip()
            source_title = getattr(res, "title", "").strip()
            publication_time = getattr(res, "publication_date", None)

            if not url or not snippet:
                log.warning(
                    "Skipping SERP result due to missing URL or snippet",
                    url_present=bool(url),
                    snippet_present=bool(snippet),
                    term=term,
                )
                continue

            if await self._is_url_blacklisted(url):
                log.info("Skipping blacklisted URL", url=url)
                continue

            if await self._is_url_visited(session, url):
                log.info("Skipping already visited URL", url=url)
                continue

            results.append(
                {
                    "url": url,
                    "snippet": snippet,
                    "source_title": source_title,
                    "publication_time": publication_time,
                }
            )
            if len(results) >= max_results:
                break
        return results

    async def crawl(
        self, session: AsyncSession, terms: Iterable[str], max_results: int = 5
    ) -> list[dict]:
        """Return SERP snippet dictionaries for each provided term."""
        pages: list[dict] = []
        for term in terms:
            for page_data in await self.search(session, term, max_results=max_results):
                pages.append(page_data)
        return pages

import os
import random
from dataclasses import dataclass
from typing import Iterable

from googlesearch import search as google_search
import yaml
import structlog

from .config import get_settings

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


class SimpleScraper:
    """Utility class that surfaces Google SERP snippets for given queries."""

    def __init__(self) -> None:  # pragma: no cover - trivial initializer
        pass

    def search(self, term: str, max_results: int = 5) -> list[dict]:
        """Search Google and return structured results with snippets."""
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
            results.append(
                {
                    "url": getattr(res, "url", ""),
                    "snippet": getattr(res, "description", ""),
                    "source_title": getattr(res, "title", ""),
                    "publication_time": getattr(res, "publication_date", None),
                }
            )
        return results

    def crawl(self, terms: Iterable[str], max_results: int = 5) -> list[dict]:
        """Return SERP snippet dictionaries for each provided term."""
        pages: list[dict] = []
        for term in terms:
            for page_data in self.search(term, max_results=max_results):
                pages.append(page_data)
        return pages

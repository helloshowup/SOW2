import os
import random
from dataclasses import dataclass
from typing import Iterable

import requests
from bs4 import BeautifulSoup
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
    """Very small utility class for basic web searching and scraping."""

    def __init__(self) -> None:
        self.session = requests.Session()

    def _get(self, url: str) -> str:
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        return response.text

    def search(self, term: str, max_results: int = 5) -> list[str]:
        """Return a list of result URLs from DuckDuckGo HTML search."""
        query = requests.utils.quote(term)
        html = self._get(f"https://duckduckgo.com/html/?q={query}")
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []
        for a in soup.select("a.result__a"):
            href = a.get("href")
            if href:
                links.append(href)
                if len(links) >= max_results:
                    break
        return links

    def scrape_page(self, url: str) -> str:
        """Fetch a page and return all paragraph text separated by newlines."""
        html = self._get(url)
        soup = BeautifulSoup(html, "html.parser")
        texts = [p.get_text(strip=True) for p in soup.find_all("p")]
        return "\n".join(texts)

    def crawl(self, terms: Iterable[str], max_results: int = 5) -> list[dict]:
        """Search for each term and yield scraped text dictionaries."""
        pages: list[dict] = []
        for term in terms:
            for link in self.search(term, max_results=max_results):
                text = self.scrape_page(link)
                pages.append({"url": link, "text": text})
        return pages

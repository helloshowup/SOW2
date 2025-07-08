import logging
import random
import time
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
import yaml

log = logging.getLogger(__name__)

BRAND_REPO_PATH = "dev-research/debonair_brand.yaml"


def load_brand_keywords(brand_id: str, brand_repo_path: str = BRAND_REPO_PATH) -> List[str]:
    """Return a list of keywords for the given brand id."""
    try:
        with open(brand_repo_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        log.error("Brand repo not found", path=brand_repo_path)
        return []
    except yaml.YAMLError as exc:
        log.error("Failed to parse brand repo", error=str(exc))
        return []

    for brand in data.get("brands", []):
        if brand.get("id") == brand_id:
            keywords = brand.get("keywords", {})
            core = keywords.get("core", [])
            extended = keywords.get("extended", [])
            return core + extended
    log.warning("Brand id not found in repo", brand_id=brand_id)
    return []


def generate_search_terms(keywords: List[str], max_terms: int = 5) -> List[str]:
    """Return a small set of search queries derived from brand keywords."""
    if not keywords:
        return []
    sample = random.sample(keywords, min(max_terms, len(keywords)))
    return [f"{kw} news" for kw in sample]


class SimpleScraper:
    """Basic scraper with retry logic and DuckDuckGo search."""

    def __init__(self, retries: int = 3, backoff: int = 2) -> None:
        self.session = requests.Session()
        self.retries = retries
        self.backoff = backoff

    def _get(self, url: str) -> Optional[str]:
        delay = 1
        for attempt in range(self.retries):
            try:
                resp = self.session.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                return resp.text
            except requests.RequestException as exc:
                log.warning(
                    "Request failed", url=url, attempt=attempt + 1, error=str(exc)
                )
                if attempt == self.retries - 1:
                    log.error("Max retries reached", url=url)
                    return None
                time.sleep(delay)
                delay *= self.backoff
        return None

    def search(self, query: str, max_results: int = 5) -> List[str]:
        """Return a list of result links from DuckDuckGo for the query."""
        search_url = f"https://duckduckgo.com/html/?q={requests.utils.quote(query)}"
        html = self._get(search_url)
        if not html:
            return []
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.select("a.result__a"):
            href = a.get("href")
            if href and href.startswith("http") and "duckduckgo.com" not in href:
                links.append(href)
                if len(links) >= max_results:
                    break
        return links

    def scrape_page(self, url: str) -> str:
        """Fetch a page and return extracted text."""
        html = self._get(url)
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        paragraphs = [p.get_text(strip=True) for p in soup.find_all("p")]
        if paragraphs:
            return "\n".join(paragraphs)
        return soup.get_text(strip=True)

    def crawl(
        self,
        search_terms: List[str],
        max_results_per_term: int = 3,
        max_pages: int = 10,
    ) -> List[dict]:
        """Search and scrape a limited number of pages."""
        pages = []
        for term in search_terms:
            links = self.search(term, max_results=max_results_per_term)
            for link in links:
                if len(pages) >= max_pages:
                    return pages
                text = self.scrape_page(link)
                pages.append({"url": link, "text": text})
                time.sleep(1)
        return pages

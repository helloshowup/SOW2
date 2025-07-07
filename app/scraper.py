import random
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup
import structlog

log = structlog.get_logger()

# Basic headers to mimic a real browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}

def fetch_html(url: str, *, retries: int = 3, backoff_factor: float = 1.0) -> Optional[str]:
    """Fetch HTML from ``url`` with basic retry and exponential backoff."""
    delay = backoff_factor
    for attempt in range(1, retries + 1):
        try:
            log.info("fetch_html.attempt", url=url, attempt=attempt)
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            log.info("fetch_html.success", url=url, status_code=response.status_code)
            return response.text
        except requests.RequestException as exc:
            log.warning("fetch_html.error", url=url, attempt=attempt, error=str(exc))
            if attempt == retries:
                break
            sleep_for = delay + random.uniform(0, 0.5)
            log.info("fetch_html.retry", url=url, next_delay=sleep_for)
            time.sleep(sleep_for)
            delay *= 2
    log.error("fetch_html.failed", url=url)
    return None

def parse_content(html: str, *, selector: str = "body") -> str:
    """Extract cleaned text from ``html`` using ``selector``."""
    soup = BeautifulSoup(html, "html.parser")
    elements = soup.select(selector)
    text = "\n".join(elem.get_text(separator=" ", strip=True) for elem in elements)
    log.info("parse_content.complete", selector=selector, length=len(text))
    return text

def scrape_content(url: str, *, selector: str = "body") -> Optional[dict]:
    """High level helper to fetch and parse content from ``url``."""
    html = fetch_html(url)
    if html is None:
        return None
    return {
        "url": url,
        "raw_html": html,
        "text_content": parse_content(html, selector=selector),
    }

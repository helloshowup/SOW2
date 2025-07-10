from __future__ import annotations

"""Simple Google search helper used for the daily summary flow."""

from dataclasses import dataclass
from typing import List

from googlesearch import search as google_search
import structlog

log = structlog.get_logger(__name__)


@dataclass
class SearchResult:
    snippet: str
    url: str


def search_google(query: str = "latest news", max_results: int = 5) -> List[SearchResult]:
    """Return a list of SearchResult from Google."""
    results: List[SearchResult] = []
    try:
        raw = list(google_search(query, num_results=max_results, advanced=True))
    except Exception as exc:  # pragma: no cover - network issues
        log.error("Google search failed", error=str(exc))
        return results

    for r in raw:
        url = getattr(r, "url", "") or ""
        snippet = getattr(r, "description", "") or ""
        if url and snippet:
            results.append(SearchResult(snippet=snippet.strip(), url=url.strip()))
    return results

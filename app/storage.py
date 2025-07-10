from __future__ import annotations

"""Utility functions to persist daily search results to a JSON file."""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List


DATA_FILE = Path("search_results.json")


@dataclass
class StoredResult:
    snippet: str
    url: str


def save_search_results(results: List[StoredResult]) -> None:
    """Save today's search results to DATA_FILE."""
    data = {
        "date": date.today().isoformat(),
        "results": [r.__dict__ for r in results],
    }
    try:
        DATA_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:  # pragma: no cover - write failures
        pass


def get_search_results_for_today() -> List[StoredResult]:
    """Return search results saved for today, if any."""
    if not DATA_FILE.exists():
        return []
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:  # pragma: no cover - read failures
        return []
    if data.get("date") != date.today().isoformat():
        return []
    return [StoredResult(**item) for item in data.get("results", [])]

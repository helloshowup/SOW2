import os
from typing import Optional, Dict, Any

import yaml
import structlog

from .config import get_settings

log = structlog.get_logger()


def load_brand_config(brand_id: str, brand_repo_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load configuration for a specific brand from the YAML repository."""
    settings = get_settings()
    repo_path = brand_repo_path or getattr(settings, "brand_repo_path", "dev-research/brand_repo.yaml")
    if not os.path.exists(repo_path):
        log.error("Brand repository not found", path=repo_path)
        return None
    try:
        with open(repo_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        log.error("Failed to parse brand repository", error=str(exc))
        return None

    for brand in data.get("brands", []):
        if brand.get("id") == brand_id or brand.get("display_name") == brand_id:
            return brand
    log.warning("Brand id not found", brand_id=brand_id)
    return None

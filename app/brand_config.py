"""Utilities for loading brand configuration from YAML."""

from typing import Optional
import os
import yaml
import structlog

from .config import config

log = structlog.get_logger()


def load_brand_config(brand_id: str) -> Optional[dict]:
    """Load configuration for ``brand_id`` from the brand repository.

    Parameters
    ----------
    brand_id: str
        Identifier of the brand (matches ``id`` in YAML).

    Returns
    -------
    Optional[dict]
        The brand configuration dictionary if found, otherwise ``None``.
    """
    path = config.BRAND_REPO_PATH
    if not os.path.exists(path):
        log.critical("brand_repo.missing", path=path)
        return None

    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
            brands = data.get("brands", [])
            for brand in brands:
                if brand.get("id") == brand_id or brand.get("display_name") == brand_id:
                    log.info("brand_repo.loaded", brand_id=brand_id)
                    return brand
            log.error("brand_repo.not_found", brand_id=brand_id)
            return None
    except yaml.YAMLError as exc:
        log.error("brand_repo.parse_error", error=str(exc), path=path)
        return None
    except Exception as exc:
        log.error("brand_repo.error", error=str(exc), path=path)
        return None

from fastapi import APIRouter, HTTPException
import yaml
import os
import structlog

from .models import BrandConfigForm
from .config import get_settings

router = APIRouter()
log = structlog.get_logger(__name__)


def _get_config_path() -> str:
    settings = get_settings()
    return getattr(settings, "brand_repo_path", "dev-research/debonair_brand.yaml")


@router.get("/config")
async def read_config():
    """Return brand configuration from the YAML file as JSON."""
    path = _get_config_path()
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Configuration file not found")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError:
        log.error("Invalid YAML format", path=path)
        raise HTTPException(status_code=500, detail="Invalid YAML format")
    return data


@router.post("/config")
async def write_config(config: BrandConfigForm):
    """Persist brand configuration back to the YAML file."""
    path = _get_config_path()
    try:
        yaml_content = yaml.safe_dump(
            config.dict(), allow_unicode=True, sort_keys=False
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(yaml_content)
    except Exception as exc:  # pragma: no cover - unexpected IO errors
        log.error("Failed to write configuration", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to update configuration")
    return {"status": "ok"}

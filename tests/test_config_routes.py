import os
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import get_settings

from app import config_routes

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("OPENAI_API_KEY", "test")


def test_config_endpoints(tmp_path, monkeypatch):
    config_path = tmp_path / "brand.yaml"
    initial = {"display_name": "X"}
    config_path.write_text(yaml.safe_dump(initial))

    monkeypatch.setenv("BRAND_REPO_PATH", str(config_path))
    get_settings.cache_clear()

    app = FastAPI()
    app.include_router(config_routes.router)
    client = TestClient(app)

    resp = client.get("/config")
    assert resp.status_code == 200
    assert resp.json() == initial

    new_data = {
        "display_name": "New",
        "persona": "cool",
        "tone": "casual",
        "keywords": ["a"],
        "banned_words": ["b"],
    }
    resp = client.post("/config", json=new_data)
    assert resp.status_code == 200
    saved = yaml.safe_load(config_path.read_text())
    assert saved == new_data

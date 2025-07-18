import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("OPENAI_API_KEY", "test")
import app.worker as worker


def test_run_agent_logic_loads_search_config(tmp_path, monkeypatch):
    config = {
        "brand_health_queries": ["foo"],
        "market_intelligence_queries": ["bar"],
        "max_email_links": 5,
    }
    path = tmp_path / "search_config.json"
    path.write_text(json.dumps(config))
    monkeypatch.chdir(tmp_path)

    captured = {}

    async def fake_run_agent_iteration(run_id, search_request=None):
        captured["run_id"] = run_id
        captured["search_request"] = search_request

    monkeypatch.setattr(worker, "run_agent_iteration", fake_run_agent_iteration)

    worker.run_agent_logic(1)

    assert captured["run_id"] == 1
    assert captured["search_request"] == config



from types import SimpleNamespace
import os
import sys

import openai
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import evaluation

@pytest.mark.asyncio
async def test_evaluate_content_no_key(monkeypatch):
    monkeypatch.setattr(evaluation.config, "OPENAI_API_KEY", None)
    result = await evaluation.evaluate_content("text", {})
    assert result is None

@pytest.mark.asyncio
async def test_evaluate_content_success(monkeypatch):
    monkeypatch.setattr(evaluation.config, "OPENAI_API_KEY", "test-key")

    async def fake_acreate(**kwargs):
        content = '{"summary":"ok"}'
        choice = SimpleNamespace(message=SimpleNamespace(content=content))
        return SimpleNamespace(choices=[choice])

    monkeypatch.setattr(openai.ChatCompletion, "acreate", fake_acreate)
    result = await evaluation.evaluate_content("text", {"display_name": "Test"})
    assert result == {"summary": "ok"}

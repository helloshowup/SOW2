import json
import types
import pytest

from app import openai_evaluator

class DummyChoice:
    def __init__(self, content):
        self.message = types.SimpleNamespace(content=content)

class DummyResponse:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]

async def dummy_acreate(*args, **kwargs):
    return DummyResponse(json.dumps({"summary": "ok"}))

@pytest.mark.asyncio
async def test_evaluate_content(monkeypatch):
    brand_config = {
        "display_name": "TestBrand",
        "keywords": {"core": ["pizza"], "extended": ["culture"]},
        "banned_words": ["foo"],
        "tone": {"persona": "friendly", "style_guide": "casual"},
    }
    monkeypatch.setattr(openai_evaluator, "OPENAI_API_KEY", "test")
    monkeypatch.setattr(openai_evaluator.openai.ChatCompletion, "acreate", dummy_acreate)

    result = await openai_evaluator.evaluate_content("sample text", brand_config)
    assert result == {"summary": "ok"}

import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ["OPENAI_API_KEY"] = "test"
from app import openai_evaluator
from app.models import AnalysisResult, SentimentAnalysis


async def dummy_create(*args, **kwargs):
    return AnalysisResult(
        summary="ok",
        sentiment=SentimentAnalysis(overall_sentiment="positive", score=0.9),
        entities=[],
    )

@pytest.mark.asyncio
async def test_evaluate_content(monkeypatch):
    brand_config = {
        "display_name": "TestBrand",
        "keywords": {"core": ["pizza"], "extended": ["culture"]},
        "banned_words": ["foo"],
        "tone": {"persona": "friendly", "style_guide": "casual"},
    }
    monkeypatch.setattr(openai_evaluator, "OPENAI_API_KEY", "test")
    monkeypatch.setattr(
        openai_evaluator.client.chat.completions, "create", dummy_create
    )

    result = await openai_evaluator.evaluate_content(
        "sample text", brand_config, "brand_health"
    )
    assert isinstance(result, AnalysisResult)
    assert result.summary == "ok"


@pytest.mark.asyncio
async def test_evaluate_content_repair(monkeypatch):
    brand_config = {
        "display_name": "TestBrand",
        "keywords": {"core": ["pizza"], "extended": ["culture"]},
        "banned_words": ["foo"],
        "tone": {"persona": "friendly", "style_guide": "casual"},
    }

    async def failing_create(*args, **kwargs):
        assert kwargs.get("max_retries") == 2
        raise Exception("bad json")

    async def dummy_repair(text: str):
        return AnalysisResult(
            summary="fixed",
            sentiment=SentimentAnalysis(overall_sentiment="positive", score=1.0),
            entities=[],
        )

    monkeypatch.setattr(openai_evaluator, "OPENAI_API_KEY", "test")
    monkeypatch.setattr(
        openai_evaluator.client.chat.completions,
        "create",
        failing_create,
    )
    monkeypatch.setattr(openai_evaluator, "repair_json_with_llm", dummy_repair)

    result = await openai_evaluator.evaluate_content(
        "sample text",
        brand_config,
        "brand_health",
    )
    assert result.summary == "fixed"


from typing import Any, Dict, Optional, List

import instructor
from openai import AsyncOpenAI
import json
import asyncio
from collections import OrderedDict
from instructor.client import HookName
import structlog

from .config import get_settings
from .models import AnalysisResult
from pydantic import BaseModel, Field

log = structlog.get_logger()

settings = get_settings()
OPENAI_API_KEY = settings.openai_api_key
if not OPENAI_API_KEY:
    log.critical(
        "OPENAI_API_KEY environment variable is not set. OpenAI API calls may fail."
    )

client = instructor.from_openai(AsyncOpenAI(api_key=OPENAI_API_KEY))

def _log_retry(event: Exception) -> None:
    """Log when instructor triggers a retry due to an error."""

    log.warning("Retry triggered", error=str(event))


client.on(HookName.PARSE_ERROR, _log_retry)
client.on(HookName.COMPLETION_ERROR, _log_retry)
client.on(
    HookName.COMPLETION_LAST_ATTEMPT,
    lambda e: log.error("All retries exhausted", error=str(e)),
)


class EvaluatedSnippet(BaseModel):
    """Simplified summary used for daily emails."""

    emoji: str = Field(description="Relevant emoji for quick context")
    headline: str = Field(description="One sentence summary of the content")
    link: str = Field(description="URL associated with the content")


def alru_cache(maxsize: int = 128):
    """A lightweight async-aware LRU cache decorator."""

    def decorator(func):
        cache: "OrderedDict[str, Any]" = OrderedDict()
        lock = asyncio.Lock()

        async def wrapper(text: str, brand_config: Dict[str, Any], task_type: str = "brand_health"):
            base = {"t": text, "b": brand_config, "tt": task_type, "cid": id(client.chat.completions.create)}
            key = json.dumps(base, sort_keys=True)
            async with lock:
                if key in cache:
                    cache.move_to_end(key)
                    log.info("Cache hit for evaluate_content")
                    return cache[key]

            result = await func(text, brand_config, task_type)

            async with lock:
                cache[key] = result
                cache.move_to_end(key)
                if len(cache) > maxsize:
                    cache.popitem(last=False)
            return result

        return wrapper

    return decorator


def _construct_prompt_messages(
    task_type: str, brand_config: Dict[str, Any], user_input: str
) -> List[Dict[str, str]]:
    """Build the message list for the OpenAI chat completion call."""

    keywords = brand_config.get("keywords", {})
    all_keywords = ", ".join(keywords.get("core", []) + keywords.get("extended", []))
    banned_words = ", ".join(brand_config.get("banned_words", []))
    tone = brand_config.get("tone", {})
    persona = tone.get("persona", "")
    style = tone.get("style_guide", "")

    focus_line = (
        "Focus on market trends, competitor strategies and opportunities like "
        "emerging delivery tech or ghost kitchens."
        if task_type == "market_intelligence"
        else "Focus on sentiment, customer service issues, product feedback and "
        "direct competitor comparisons."
    )

    system_message = (
        f"You are an expert marketing assistant and conter writer analyzing text for {brand_config.get('display_name', '')}. "
        f"Use a {persona} {style} tone. {focus_line} "
        f"Keywords to monitor: {all_keywords}. Avoid these banned words: {banned_words}. "
        "Respond in JSON only. Also generate a 'snappy_heading' field: a short, engaging title for the content, that tells a story and is not a heading."
    )

    examples_key = (
        "brand_health_examples" if task_type == "brand_health" else "market_intel_examples"
    )
    examples = brand_config.get(examples_key, [])

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_message}]

    for ex in examples:
        messages.append({"role": "user", "content": ex.get("input", "")})
        messages.append({"role": "assistant", "content": ex.get("output", "")})

    messages.append({"role": "user", "content": user_input})
    return messages


async def evaluate_snippets_for_brand_fit(url: str, text: str) -> Optional[EvaluatedSnippet]:
    """Return a concise email-friendly summary for a snippet."""

    if not OPENAI_API_KEY:
        log.error("OpenAI API key is missing. Cannot evaluate snippet.")
        return None

    system_prompt = (
        "Summarize the content into a brief, one-sentence headline. "
        "Start the summary with a relevant emoji. The goal is to provide quick, scannable context. "
        "Respond in JSON only."
    )

    try:
        result = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
            temperature=0.2,
            response_model=EvaluatedSnippet,
            max_retries=2,
        )
        result.link = url
        return result
    except Exception as exc:  # pragma: no cover - runtime safety
        log.error("OpenAI API error during snippet summary", error=str(exc))
    return None


async def repair_json_with_llm(text: str) -> Optional[AnalysisResult]:
    """Attempt to repair invalid JSON using the LLM itself."""

    log.info("Attempting to repair JSON with LLM")
    try:
        return await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Fix the JSON so it conforms to the AnalysisResult schema."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            response_model=AnalysisResult,
        )
    except Exception as exc:  # pragma: no cover - network failures
        log.error("Repair attempt failed", error=str(exc))
    return None

@alru_cache(maxsize=128)
async def evaluate_content(
    text: str,
    brand_config: Dict[str, Any],
    task_type: str = "brand_health",
) -> Optional[AnalysisResult]:
    """Evaluate text with OpenAI using brand-specific context.

    The ``task_type`` determines whether the analysis focuses on
    brand health or broader market intelligence.
    """
    if not OPENAI_API_KEY:
        log.error("OpenAI API key is missing. Cannot evaluate content.")
        return None

    log.info(
        "Evaluating snippet",
        snippet_length=len(text),
        task_type=task_type,
    )

    messages = _construct_prompt_messages(task_type, brand_config, text)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
            response_model=AnalysisResult,
            max_retries=2,
        )
        return response
    except Exception as exc:
        log.error("OpenAI API error during evaluation", error=str(exc))
        repaired = await repair_json_with_llm(text)
        if repaired:
            return repaired
    return None

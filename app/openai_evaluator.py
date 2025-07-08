from typing import Any, Dict, Optional

import instructor
from openai import AsyncOpenAI
from instructor.client import HookName
import structlog

from .config import get_settings
from .models import AnalysisResult

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


async def repair_json_with_llm(text: str) -> Optional[AnalysisResult]:
    """Attempt to repair invalid JSON using the LLM itself."""

    log.info("Attempting to repair JSON with LLM")
    try:
        return await client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
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

    keywords = brand_config.get("keywords", {})
    core = keywords.get("core", [])
    extended = keywords.get("extended", [])
    all_keywords = ", ".join(core + extended)
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

    prompt = f"""
You are a helpful assistant that evaluates online text for the brand {brand_config.get('display_name', '')}.
The content should align with a {persona} {style} tone.
{focus_line}
Focus on these keywords: {all_keywords}.
Avoid these banned words: {banned_words}.

Provide your response in JSON with the following fields:
{{
    "categories": [],
    "sentiment": "",
    "summary": "",
    "keywords_present": [],
    "banned_words_found": []
}}
---
{text}
---
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You only respond in JSON."},
                {"role": "user", "content": prompt},
            ],
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

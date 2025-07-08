from typing import Any, Dict, Optional, List

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
        f"You are an expert assistant analyzing text for {brand_config.get('display_name', '')}. "
        f"Use a {persona} {style} tone. {focus_line} "
        f"Keywords to monitor: {all_keywords}. Avoid these banned words: {banned_words}. "
        "Respond in JSON only."
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

    messages = _construct_prompt_messages(task_type, brand_config, text)

    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
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

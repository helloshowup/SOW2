import json
from typing import Optional, Sequence

import openai
import structlog

from .config import config

log = structlog.get_logger()

async def evaluate_content(text: str, brand_config: dict) -> Optional[dict]:
    """Evaluate ``text`` using OpenAI and brand-specific guidance."""
    if not config.OPENAI_API_KEY:
        log.error("openai.key_missing")
        return None

    openai.api_key = config.OPENAI_API_KEY

    keywords: Sequence[str] = []
    kw = brand_config.get("keywords", {})
    if isinstance(kw, dict):
        keywords = list(kw.get("core", [])) + list(kw.get("extended", []))
    elif isinstance(kw, list):
        keywords = kw

    brand_keywords = ", ".join(keywords)
    banned_words = ", ".join(brand_config.get("banned_words", []))
    brand_tone = brand_config.get("tone", {}).get("persona", "neutral")
    brand_name = brand_config.get("display_name", brand_config.get("id", "Brand"))

    prompt = f"""
You are an AI assistant specialized in content evaluation for the brand \"{brand_name}\".
Analyze the provided text and perform the following tasks:

1. Categorization: assign one or more categories.
2. Sentiment Analysis: determine overall sentiment.
3. Summarization: provide a concise summary in a {brand_tone} tone.
4. Keyword Presence: check for brand keywords: {brand_keywords}.
5. Banned Word Check: identify if these banned words appear: {banned_words}.

Respond in JSON format.
---
{text}
---
"""

    messages = [
        {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
        {"role": "user", "content": prompt},
    ]

    try:
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo-0125",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        return json.loads(response.choices[0].message.content)
    except openai.error.OpenAIError as exc:
        log.error("openai.request_failed", error=str(exc))
        return None
    except json.JSONDecodeError as exc:
        log.error(
            "openai.json_parse_error",
            error=str(exc),
            content=response.choices[0].message.content,
        )
        return None
    except Exception as exc:
        log.error("openai.unexpected_error", error=str(exc))
        return None

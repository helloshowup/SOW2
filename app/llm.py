from __future__ import annotations

"""Simple wrapper around the OpenAI API used for text completions."""

import openai
import structlog

from .config import get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

if settings.openai_api_key:
    openai.api_key = settings.openai_api_key
else:
    log.warning("OPENAI_API_KEY is not configured; get_completion will return empty string")


def get_completion(prompt: str) -> str:
    """Return the LLM completion for the given prompt.

    If the OpenAI API key is missing or an error occurs, an empty string is returned.
    """
    if not settings.openai_api_key:
        return ""

    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:  # pragma: no cover - network or API issues
        log.error("OpenAI completion failed", error=str(exc))
        return ""

import os
import json
from typing import Dict, Any, Optional

import openai
import structlog

log = structlog.get_logger()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    log.critical("OPENAI_API_KEY environment variable is not set. OpenAI API calls may fail.")

openai.api_key = OPENAI_API_KEY

async def evaluate_content(text: str, brand_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Evaluate text with OpenAI using brand-specific context."""
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

    prompt = f"""
You are a helpful assistant that evaluates online text for the brand {brand_config.get('display_name', '')}.
The content should align with a {persona} {style} tone.
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
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You only respond in JSON."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        return json.loads(response.choices[0].message.content)
    except openai.error.OpenAIError as exc:
        log.error("OpenAI API error during evaluation", error=str(exc))
    except json.JSONDecodeError as exc:
        log.error("Failed to parse OpenAI response as JSON", error=str(exc))
    except Exception as exc:
        log.error("Unexpected error during OpenAI evaluation", error=str(exc))
    return None

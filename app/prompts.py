from __future__ import annotations

"""Prompt templates for the summarization flow."""


def get_summarize_prompt(search_results_and_links: str) -> str:
    """Return prompt instructing the LLM to format search results.

    Each result should be summarized in one sentence with two relevant emojis
    followed by the original link.
    """
    return (
        "Please summarize the following search results. For each result, provide "
        "a brief, one-sentence headline that captures the main point, two relevant "
        "emojis, and the original link.\n"
        "Format each result as follows:\n"
        "[two relevant emojis] [one-sentence headline] [link]\n\n"
        "Here are the search results:\n" + search_results_and_links
    )

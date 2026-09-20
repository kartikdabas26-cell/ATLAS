from __future__ import annotations

import html
import os
import re
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
OPENAI_BASE_URL = os.environ.get(
    "ATLAS_AI_BASE_URL",
    "https://api.openai.com/v1",
).rstrip("/")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    context: dict[str, Any] = Field(default_factory=dict)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def search_public_sources(query: str, limit: int = 5) -> list[dict[str, str]]:
    """Retrieve compact, attributable public context from Wikipedia."""
    response = httpx.get(
        WIKIPEDIA_API,
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "origin": "*",
        },
        headers={"User-Agent": "ATLAS-consequence-simulation/1.0"},
        timeout=6.0,
    )
    response.raise_for_status()
    payload = response.json()

    results = []
    for item in payload.get("query", {}).get("search", []):
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        results.append(
            {
                "title": title,
                "snippet": _clean_text(item.get("snippet", "")),
                "url": "https://en.wikipedia.org/wiki/"
                + quote(title.replace(" ", "_")),
            }
        )
    return results


def _fallback_answer(question: str, sources: list[dict[str, str]]) -> str:
    lowered = question.lower()
    if "atlas" in lowered or "scenario" in lowered or "shock" in lowered:
        return (
            "ATLAS is a what-if tool. Choose where a supply change starts, "
            "choose how large it is, and choose how much backup supply exists. "
            "It then shows modeled effects through trade links over time. "
            "These are indicators, not guaranteed forecasts."
        )
    if sources:
        source_text = sources[0]["snippet"]
        return (
            f"Here is the closest public-source context I found: {source_text} "
            "Use the sources below to read the full details."
        )
    return (
        "I could not find a public source for that question yet. "
        "Try adding a country, crop, trade route, or a more specific question."
    )


def _model_answer(
    question: str,
    sources: list[dict[str, str]],
    user_context: dict[str, Any] | None = None,
) -> str | None:
    api_key = os.environ.get("ATLAS_AI_API_KEY", "").strip()
    if not api_key:
        return None

    source_context = "\n".join(
        f"- {item['title']}: {item['snippet']} ({item['url']})"
        for item in sources
    ) or "No public source result was found."
    context = user_context or {}
    prompt = (
        "You are Ask ATLAS, a careful global food-systems research assistant. "
        "Answer in plain language suitable for a curious student. Separate "
        "observed facts from assumptions. Never invent numbers or sources. "
        "Mention uncertainty when evidence is incomplete.\n\n"
        f"Question: {question}\n"
        f"Current ATLAS context: {context}\n"
        f"Public source context:\n{source_context}"
    )

    response = httpx.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.environ.get("ATLAS_AI_MODEL", "gpt-4o-mini"),
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": "Give concise, source-conscious answers.",
                },
                {"role": "user", "content": prompt},
            ],
        },
        timeout=20.0,
    )
    response.raise_for_status()
    content = response.json().get("choices", [{}])[0].get("message", {}).get("content")
    return _clean_text(content) if content else None


def answer_question(
    question: str,
    user_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question = question.strip()
    if not question:
        raise ValueError("Ask a question first.")
    if len(question) > 500:
        raise ValueError("Please keep your question under 500 characters.")

    try:
        sources = search_public_sources(question)
    except (httpx.HTTPError, ValueError):
        sources = []

    try:
        answer = _model_answer(question, sources, user_context)
        mode = "ai_with_public_sources" if answer else "public_source_summary"
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        answer = None
        mode = "public_source_summary"

    return {
        "answer": answer or _fallback_answer(question, sources),
        "sources": sources,
        "mode": mode,
        "disclaimer": "Public-source context and modeled ATLAS results are informational, not professional advice.",
    }

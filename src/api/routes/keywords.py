from __future__ import annotations

import json
import logging

import anthropic
from fastapi import APIRouter
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/keywords", tags=["keywords"])

_PROMPT_TEMPLATE = (
    "Dado el nicho '{niche_name}', generá 15 keywords relevantes para analizar tendencias, "
    "oportunidades de contenido y señales de mercado. "
    "Devolvé solo la lista en JSON: [\"kw1\", \"kw2\", ...]. Sin explicaciones."
)

_NICHES_PROMPT_TEMPLATE = (
    "Dado la categoría '{category}', sugerí 6 nichos concretos y rentables para crear contenido "
    "o productos digitales. Para cada uno: name (conciso, 1-3 palabras), description (qué es, 1 oración), "
    "why_profitable (por qué tiene oportunidad de monetización, 1 oración). "
    'Devolvé solo JSON: [{{"name": "...", "description": "...", "why_profitable": "..."}}, ...]. Sin explicaciones.'
)


class SuggestKeywordsRequest(BaseModel):
    niche_name: str


class SuggestKeywordsResponse(BaseModel):
    keywords: list[str]


class SuggestNichesRequest(BaseModel):
    category: str


class NicheSuggestion(BaseModel):
    name: str
    description: str
    why_profitable: str


class SuggestNichesResponse(BaseModel):
    niches: list[NicheSuggestion]


@router.post("/suggest", response_model=SuggestKeywordsResponse)
async def suggest_keywords(body: SuggestKeywordsRequest) -> SuggestKeywordsResponse:
    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": _PROMPT_TEMPLATE.format(niche_name=body.niche_name),
                }
            ],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        keywords: list[str] = json.loads(raw)
        if not isinstance(keywords, list):
            keywords = []
    except Exception as exc:
        logger.error("suggest_keywords failed for niche_name=%r: %s", body.niche_name, exc)
        keywords = []

    return SuggestKeywordsResponse(keywords=keywords)


niches_router = APIRouter(prefix="/niches", tags=["niches"])


@niches_router.post("/suggest", response_model=SuggestNichesResponse)
async def suggest_niches(body: SuggestNichesRequest) -> SuggestNichesResponse:
    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": _NICHES_PROMPT_TEMPLATE.format(category=body.category),
                }
            ],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        parsed: list[dict] = json.loads(raw)
        if not isinstance(parsed, list):
            parsed = []
        niches = [
            NicheSuggestion(
                name=item.get("name", ""),
                description=item.get("description", ""),
                why_profitable=item.get("why_profitable", ""),
            )
            for item in parsed
            if isinstance(item, dict)
        ]
    except Exception as exc:
        logger.error("suggest_niches failed for category=%r: %s", body.category, exc)
        niches = []

    return SuggestNichesResponse(niches=niches)

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import requests

from .constants import DEFAULT_MODEL
from .models import AIArticle, AIPlayer, SourceArticle


def build_response_schema() -> dict:
    return {
        "type": "json_schema",
        "name": "cbs_article_structured_output",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "article_type": {
                    "type": "string",
                    "enum": ["sleeper_hitters", "sleeper_pitchers", "two_start_pitchers"],
                },
                "week": {"type": ["integer", "null"]},
                "article_summary_zh_tw": {"type": "string"},
                "players": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "rank": {"type": "integer"},
                            "name_en": {"type": "string"},
                            "summary_en": {"type": "string"},
                            "summary_zh_tw": {"type": "string"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["rank", "name_en", "summary_en", "summary_zh_tw", "tags"],
                    },
                },
            },
            "required": ["article_type", "week", "article_summary_zh_tw", "players"],
        },
    }


def build_input_messages(article: SourceArticle) -> list[dict]:
    instructions = (
        "You extract structured fantasy baseball article data.\n"
        "Return valid JSON only.\n"
        "Keep player names in English.\n"
        "Each summary_zh_tw must be exactly one Traditional Chinese sentence.\n"
        "Do not invent players, ranks, matchups, or claims not present in the source.\n"
        "Prefer concise, frontend-ready summaries."
    )
    payload = {
        "source": article.source,
        "article_type_hint": article.article_type,
        "week_hint": article.week,
        "title_en": article.title_en,
        "dek_en": article.dek_en,
        "body_en": article.body_en,
        "player_cards": [
            {
                "rank": card.rank,
                "name_en": card.name_en,
                "position": card.position,
                "mlb_team": card.mlb_team,
                "matchup": card.matchup,
                "rostered_pct": card.rostered_pct,
                "blurb_en": card.blurb_en,
            }
            for card in article.player_cards
        ],
    }
    return [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": instructions}],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Extract the article into structured player data.\n"
                        "Article payload:\n"
                        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
                    ),
                }
            ],
        },
    ]


def parse_response_json(response_payload: dict) -> dict:
    if response_payload.get("output_text"):
        return json.loads(response_payload["output_text"])
    output = response_payload.get("output", [])
    for item in output:
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return json.loads(content["text"])
    raise ValueError("OpenAI response did not contain JSON output text")


def generate_ai_article(article: SourceArticle, *, api_key: str | None = None, model: str | None = None) -> AIArticle:
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required unless --skip-ai is used")

    model = model or os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": build_input_messages(article),
            "text": {"format": build_response_schema()},
        },
        timeout=120,
    )
    response.raise_for_status()
    data = parse_response_json(response.json())

    players = [
        AIPlayer(
            rank=item["rank"],
            name_en=item["name_en"],
            summary_en=item["summary_en"],
            summary_zh_tw=item["summary_zh_tw"],
            tags=item.get("tags", []),
        )
        for item in data["players"]
    ]
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return AIArticle(
        article_type=data["article_type"],
        week=data.get("week"),
        article_summary_zh_tw=data["article_summary_zh_tw"],
        players=players,
        model=model,
        generated_at=generated_at,
    )

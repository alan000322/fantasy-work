from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .constants import DEFAULT_OUTPUT_DIR, PIPELINE_VERSION
from .crawler import fetch_target_articles
from .models import AIArticle, ArticleDocument, SourceArticle
from .openai_client import generate_ai_article

AI_ENABLED_TYPES = {"sleeper_hitters", "sleeper_pitchers"}


def output_filename(article: SourceArticle) -> str:
    date_part = "undated"
    if article.published_at:
        date_part = article.published_at[:10]
    return f"{date_part}-{article.slug}.json"


def build_pending_ai_payload(article: SourceArticle) -> dict:
    reason = "AI enrichment skipped"
    if article.article_type not in AI_ENABLED_TYPES:
        reason = f"AI enrichment disabled for {article.article_type}"
    return {
        "status": "pending",
        "reason": reason,
        "article_type": article.article_type,
        "week": article.week,
    }


def build_document(article: SourceArticle, ai_article: AIArticle | None) -> ArticleDocument:
    if ai_article is None:
        pending_ai = build_pending_ai_payload(article)
        players: list[dict] = []
        ai_section: dict | AIArticle = pending_ai
    else:
        players = [asdict(player) for player in ai_article.players]
        ai_section = ai_article

    return ArticleDocument(
        source_article=article,
        ai_article=ai_section,
        players=players,
        pipeline={
            "version": PIPELINE_VERSION,
            "status": "complete" if ai_article else "source_only",
        },
    )


def validate_document(payload: dict) -> None:
    source = payload.get("source_article", {})
    if not source.get("title_en") or not source.get("url") or not source.get("body_en"):
        raise ValueError("source_article is missing required fields")

    ai_article = payload.get("ai_article", {})
    if ai_article.get("status") == "pending":
        return

    players = payload.get("players", [])
    if not players:
        raise ValueError("players must not be empty when AI enrichment is enabled")

    for player in players:
        if not player.get("name_en") or not player.get("summary_en") or not player.get("summary_zh_tw"):
            raise ValueError("player is missing required fields")


def write_document(output_dir: Path, payload: dict, article: SourceArticle) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / output_filename(article)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def run_pipeline(
    *,
    limit: int | None = None,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    skip_ai: bool = False,
    model: str | None = None,
) -> list[Path]:
    articles = fetch_target_articles(limit=limit)
    written_paths: list[Path] = []
    base_path = Path(output_dir)

    for article in articles:
        ai_article = None
        if not skip_ai and article.article_type in AI_ENABLED_TYPES:
            ai_article = generate_ai_article(article, model=model)
        document = build_document(article, ai_article)
        payload = document.to_dict()
        validate_document(payload)
        written_paths.append(write_document(base_path, payload, article))

    return written_paths

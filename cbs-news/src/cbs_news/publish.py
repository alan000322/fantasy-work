from __future__ import annotations

import json
import shutil
from pathlib import Path


SUPPORTED_DOC_TYPES = {"sleeper_hitters", "sleeper_pitchers"}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def article_sort_key(item: dict) -> tuple:
    published_at = item.get("published_at") or ""
    week = item.get("week") or 0
    title = item.get("title_en") or ""
    return (published_at, week, title)


def export_articles_to_docs(source_dir: Path, docs_dir: Path) -> dict:
    docs_articles_dir = docs_dir / "articles"
    docs_articles_dir.mkdir(parents=True, exist_ok=True)

    exported_entries: list[dict] = []
    latest_week_by_type: dict[str, int] = {}

    for source_path in sorted(source_dir.glob("*.json")):
        payload = load_json(source_path)
        source_article = payload.get("source_article", {})
        article_type = source_article.get("article_type")
        if article_type not in SUPPORTED_DOC_TYPES:
            continue

        if not payload.get("players"):
            continue

        destination_path = docs_articles_dir / source_path.name
        shutil.copyfile(source_path, destination_path)

        week = source_article.get("week")
        if isinstance(week, int):
            latest_week_by_type[article_type] = max(latest_week_by_type.get(article_type, 0), week)

        exported_entries.append(
            {
                "article_type": article_type,
                "week": week,
                "title_en": source_article.get("title_en"),
                "published_at": source_article.get("published_at"),
                "source_url": source_article.get("url"),
                "path": "./data/cbs-news/articles/" + source_path.name,
                "player_count": len(payload.get("players", [])),
            }
        )

    exported_entries.sort(key=article_sort_key, reverse=True)

    index_payload = {
        "generated_at": exported_entries[0]["published_at"] if exported_entries else None,
        "latest_week_by_type": latest_week_by_type,
        "articles": exported_entries,
    }
    (docs_dir / "index.json").write_text(
        json.dumps(index_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return index_payload

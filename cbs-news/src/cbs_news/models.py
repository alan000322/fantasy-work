from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ArticleLink:
    article_type: str
    title: str
    url: str


@dataclass
class SourcePlayerCard:
    rank: int | None
    name_en: str
    position: str | None
    mlb_team: str | None
    matchup: str | None
    rostered_pct: str | None
    blurb_en: str


@dataclass
class SourceArticle:
    source: str
    article_type: str
    week: int | None
    title_en: str
    url: str
    canonical_url: str
    slug: str
    author: str | None
    published_at: str | None
    dek_en: str | None
    body_en: str
    fetched_at: str
    player_cards: list[SourcePlayerCard] = field(default_factory=list)


@dataclass
class AIPlayer:
    rank: int
    name_en: str
    summary_en: str
    summary_zh_tw: str
    tags: list[str] = field(default_factory=list)


@dataclass
class AIArticle:
    article_type: str
    week: int | None
    article_summary_zh_tw: str
    players: list[AIPlayer]
    model: str
    generated_at: str


@dataclass
class ArticleDocument:
    source_article: SourceArticle
    ai_article: dict[str, Any] | AIArticle
    players: list[dict[str, Any]] | list[AIPlayer]
    pipeline: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload

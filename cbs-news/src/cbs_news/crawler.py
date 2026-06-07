from __future__ import annotations

import json
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .constants import BASE_URL, NEWS_PATH_RE, REQUEST_HEADERS, TARGET_PATTERNS
from .models import ArticleLink, SourceArticle, SourcePlayerCard


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_published_at(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def extract_week(text: str) -> int | None:
    match = re.search(r"\bweek\s+(\d+)\b", text, re.I)
    if match:
        return int(match.group(1))
    return None


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.rsplit("/", 1)[-1]


def match_article_type(title: str, url: str = "") -> str | None:
    haystack = f"{normalize_text(title)} {slug_from_url(url).replace('-', ' ')}".strip()
    for article_type, pattern in TARGET_PATTERNS:
        if pattern.search(haystack):
            return article_type
    return None


def fetch_html(url: str, timeout: int = 30) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def parse_listing(html: str) -> list[ArticleLink]:
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    results: list[ArticleLink] = []

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        if not NEWS_PATH_RE.match(href):
            continue

        title = normalize_text(anchor.get_text(" ", strip=True))
        if not title:
            continue

        url = urljoin(BASE_URL, href)
        article_type = match_article_type(title, url)
        if not article_type or url in seen:
            continue

        seen.add(url)
        results.append(ArticleLink(article_type=article_type, title=title, url=url))

    return results


def extract_meta(soup: BeautifulSoup, *, prop: str | None = None, name: str | None = None) -> str | None:
    if prop:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            return normalize_text(tag["content"])
    if name:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return normalize_text(tag["content"])
    return None


def extract_json_ld_article(soup: BeautifulSoup) -> dict:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = script.string or script.get_text()
        if not text or "NewsArticle" not in text:
            continue
        try:
            payload = json.loads(text.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("@type") == "NewsArticle":
            return payload
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict) and item.get("@type") == "NewsArticle":
                    return item
    return {}


def collect_paragraphs(nodes: Iterable) -> list[str]:
    paragraphs: list[str] = []
    seen: set[str] = set()
    for node in nodes:
        text = normalize_text(node.get_text(" ", strip=True))
        if not text or len(text) < 30 or text in seen:
            continue
        seen.add(text)
        paragraphs.append(text)
    return paragraphs


def parse_player_cards(soup: BeautifulSoup) -> list[SourcePlayerCard]:
    cards: list[SourcePlayerCard] = []
    for index, node in enumerate(soup.select(".PlayerObjectV4"), start=1):
        name_node = node.select_one(".PlayerName a")
        blurb_node = node.select_one(".AnalysisContent, .PlayerObjectV4-analysis, .CellPlayerAnalysis")
        if not name_node or not blurb_node:
            continue

        position_node = node.select_one(".PlayerObjectV4-playerPosition")
        team_node = node.select_one(".PlayerObjectV4-playerInfoName--short")
        blurb = normalize_text(blurb_node.get_text(" ", strip=True))
        if not blurb:
            continue

        matchup = None
        rostered_pct = None
        labels = node.select(".PlayerObjectV4-label")
        for label in labels:
            label_text = normalize_text(label.get_text(" ", strip=True)).lower()
            parent = label.parent
            parent_text = normalize_text(parent.get_text(" ", strip=True)) if parent else ""
            if label_text == "matchup":
                matchup = normalize_text(parent_text.replace(label.get_text(" ", strip=True), "", 1))
            if label_text == "rostered":
                rostered_pct = normalize_text(parent_text.replace(label.get_text(" ", strip=True), "", 1))

        cards.append(
            SourcePlayerCard(
                rank=index,
                name_en=normalize_text(name_node.get_text(" ", strip=True)),
                position=normalize_text(position_node.get_text(" ", strip=True)) if position_node else None,
                mlb_team=normalize_text(team_node.get_text(" ", strip=True)) if team_node else None,
                matchup=matchup or None,
                rostered_pct=rostered_pct or None,
                blurb_en=blurb,
            )
        )

    return cards


def parse_article(link: ArticleLink) -> SourceArticle:
    html = fetch_html(link.url)
    soup = BeautifulSoup(html, "html.parser")
    json_ld = extract_json_ld_article(soup)

    canonical_url = extract_meta(soup, prop="og:url") or link.url
    title = (
        json_ld.get("headline")
        or extract_meta(soup, prop="og:title")
        or (normalize_text(soup.title.get_text(" ", strip=True)) if soup.title else link.title)
    )
    author = None
    if isinstance(json_ld.get("author"), dict):
        author = normalize_text(json_ld["author"].get("name", ""))
    elif isinstance(json_ld.get("author"), list) and json_ld["author"]:
        first = json_ld["author"][0]
        if isinstance(first, dict):
            author = normalize_text(first.get("name", ""))
    if not author:
        author = extract_meta(soup, name="author")

    published_at = json_ld.get("datePublished") or extract_meta(soup, prop="article:published_time")
    dek = extract_meta(soup, name="description") or extract_meta(soup, prop="og:description")

    container_selectors = [
        "article",
        "[data-component='ArticleBody']",
        ".Article-body",
        ".article-body",
        ".content__body",
        ".Article-content",
    ]

    paragraphs: list[str] = []
    for selector in container_selectors:
        container = soup.select_one(selector)
        if not container:
            continue
        paragraphs = collect_paragraphs(container.find_all(["p", "li"]))
        if paragraphs:
            break

    if not paragraphs:
        paragraphs = collect_paragraphs(soup.find_all("p"))

    player_cards = parse_player_cards(soup)
    json_ld_body = normalize_text(json_ld.get("articleBody", "")) if json_ld.get("articleBody") else ""
    body_parts: list[str] = []
    intro_body = json_ld_body or "\n\n".join(paragraphs)
    if intro_body:
        body_parts.append(intro_body)
    if player_cards:
        card_lines = [
            (
                f"{card.rank}. {card.name_en}"
                + (f" ({card.position})" if card.position else "")
                + (f" - {card.blurb_en}" if card.blurb_en else "")
            )
            for card in player_cards
        ]
        body_parts.append("\n".join(card_lines))
    body = "\n\n".join(part for part in body_parts if part)
    week = extract_week(title) or extract_week(dek or "") or extract_week(body[:400])

    return SourceArticle(
        source="CBS Sports",
        article_type=link.article_type,
        week=week,
        title_en=title,
        url=link.url,
        canonical_url=canonical_url,
        slug=slug_from_url(canonical_url),
        author=author or None,
        published_at=published_at,
        dek_en=dek,
        body_en=body,
        player_cards=player_cards,
        fetched_at=iso_now(),
    )


def fetch_target_articles(
    limit: int | None = None,
    skip_slugs: set[str] | None = None,
) -> list[SourceArticle]:
    listing_html = fetch_html(BASE_URL)
    links = parse_listing(listing_html)
    if skip_slugs:
        links = [link for link in links if slug_from_url(link.url) not in skip_slugs]
    articles = [parse_article(link) for link in links]
    articles.sort(
        key=lambda article: (
            parse_published_at(article.published_at),
            article.week or -1,
            article.slug,
        ),
        reverse=True,
    )
    if limit is not None:
        return articles[: max(limit, 0)]
    return articles

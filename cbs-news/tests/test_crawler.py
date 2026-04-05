from __future__ import annotations

import unittest
from unittest.mock import patch

from cbs_news.crawler import fetch_target_articles
from cbs_news.models import ArticleLink, SourceArticle


def build_article(link: ArticleLink, published_at: str, week: int) -> SourceArticle:
    return SourceArticle(
        source="CBS Sports",
        article_type=link.article_type,
        week=week,
        title_en=link.title,
        url=link.url,
        canonical_url=link.url,
        slug=link.url.rstrip("/").rsplit("/", 1)[-1],
        author="Scott White",
        published_at=published_at,
        dek_en=None,
        body_en="body",
        fetched_at="2026-04-05T00:00:00+00:00",
        player_cards=[],
    )


class FetchTargetArticlesTest(unittest.TestCase):
    def test_limit_applies_after_sorting_by_publish_time(self) -> None:
        links = [
            ArticleLink("two_start_pitchers", "Week 3 two-start pitcher rankings", "https://example.com/week-3-two-start"),
            ArticleLink("sleeper_pitchers", "Week 3 sleeper pitchers", "https://example.com/week-3-sleeper-pitchers"),
            ArticleLink("sleeper_hitters", "Week 2 sleeper hitters", "https://example.com/week-2-sleeper-hitters"),
            ArticleLink("sleeper_hitters", "Week 3 sleeper hitters", "https://example.com/week-3-sleeper-hitters"),
        ]
        parsed_by_url = {
            links[0].url: build_article(links[0], "2026-04-03T13:43:00+00:00", 3),
            links[1].url: build_article(links[1], "2026-04-03T14:29:00+00:00", 3),
            links[2].url: build_article(links[2], "2026-03-30T10:56:00+00:00", 2),
            links[3].url: build_article(links[3], "2026-04-03T16:00:00+00:00", 3),
        }

        with (
            patch("cbs_news.crawler.fetch_html", return_value="<html></html>"),
            patch("cbs_news.crawler.parse_listing", return_value=links),
            patch("cbs_news.crawler.parse_article", side_effect=lambda link: parsed_by_url[link.url]),
        ):
            articles = fetch_target_articles(limit=3)

        self.assertEqual(
            [article.slug for article in articles],
            [
                "week-3-sleeper-hitters",
                "week-3-sleeper-pitchers",
                "week-3-two-start",
            ],
        )


if __name__ == "__main__":
    unittest.main()

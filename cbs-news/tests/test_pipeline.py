from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cbs_news.pipeline import run_pipeline


ARTICLE = {
    "source": "CBS Sports",
    "article_type": "sleeper_hitters",
    "week": 3,
    "title_en": "Fantasy Baseball Week 3 Preview: Top 10 sleeper hitters highlight TJ Rumfield, Daylen Lile",
    "url": "https://www.cbssports.com/fantasy/baseball/news/fantasy-baseball-week-3-preview-top-10-sleeper-hitters-highlight-tj-rumfield-daylen-lile/",
    "canonical_url": "https://www.cbssports.com/fantasy/baseball/news/fantasy-baseball-week-3-preview-top-10-sleeper-hitters-highlight-tj-rumfield-daylen-lile/",
    "slug": "fantasy-baseball-week-3-preview-top-10-sleeper-hitters-highlight-tj-rumfield-daylen-lile",
    "author": "Scott White",
    "published_at": "2026-04-04T19:20:36+00:00",
    "dek_en": "Best hitter matchups for this week include the Rockies, Padres and Reds",
    "body_en": "body",
    "fetched_at": "2026-04-05T00:00:00+00:00",
    "player_cards": [],
}

EXISTING_PAYLOAD = {
    "source_article": ARTICLE,
    "ai_article": {
        "article_type": "sleeper_hitters",
        "week": 3,
        "article_summary_zh_tw": "既有摘要。",
        "players": [
            {
                "rank": 1,
                "name_en": "TJ Rumfield",
                "summary_en": "Existing summary.",
                "summary_zh_tw": "既有翻譯。",
                "tags": ["power"],
            }
        ],
        "model": "gpt-5.4-mini",
        "generated_at": "2026-04-05T00:00:00+00:00",
    },
    "players": [
        {
            "rank": 1,
            "name_en": "TJ Rumfield",
            "summary_en": "Existing summary.",
            "summary_zh_tw": "既有翻譯。",
            "tags": ["power"],
        }
    ],
    "pipeline": {
        "version": "1.0",
        "status": "complete",
    },
}


class RunPipelineTest(unittest.TestCase):
    def test_existing_output_file_is_reused_without_regenerating(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            existing_path = output_dir / "2026-04-04-fantasy-baseball-week-3-preview-top-10-sleeper-hitters-highlight-tj-rumfield-daylen-lile.json"
            existing_path.write_text(json.dumps(EXISTING_PAYLOAD, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            original_content = existing_path.read_text(encoding="utf-8")

            with (
                patch("cbs_news.pipeline.fetch_target_articles", return_value=[type("Article", (), ARTICLE)()]),
                patch("cbs_news.pipeline.generate_ai_article") as mock_generate_ai_article,
            ):
                written = run_pipeline(limit=1, output_dir=tmpdir)

            self.assertEqual(written, [existing_path])
            self.assertFalse(mock_generate_ai_article.called)
            self.assertEqual(existing_path.read_text(encoding="utf-8"), original_content)


if __name__ == "__main__":
    unittest.main()

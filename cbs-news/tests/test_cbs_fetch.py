#!/usr/bin/env python3
"""Quick CBS Fantasy Baseball crawler smoke test."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cbs_news.crawler import fetch_target_articles


def main() -> int:
    parser = argparse.ArgumentParser(description="CBS Fantasy Baseball crawl smoke test")
    parser.add_argument("--limit", type=int, default=3, help="number of matched articles to fetch")
    parser.add_argument("--json", action="store_true", help="print parsed results as JSON")
    args = parser.parse_args()

    parsed = fetch_target_articles(limit=args.limit)

    if args.json:
        print(json.dumps([asdict(item) for item in parsed], ensure_ascii=False, indent=2))
        return 0

    print(f"Listing matches: {len(parsed)}")
    for index, item in enumerate(parsed, start=1):
        preview = item.body_en[:500].replace("\n", " ")
        print("=" * 80)
        print(f"[{index}] {item.article_type}")
        print(f"title: {item.title_en}")
        print(f"url: {item.url}")
        print(f"author: {item.author}")
        print(f"published_at: {item.published_at}")
        print(f"dek: {item.dek_en}")
        print(f"body_length: {len(item.body_en)}")
        print(f"preview: {preview}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

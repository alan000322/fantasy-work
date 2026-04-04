from __future__ import annotations

import argparse
import json
from dataclasses import asdict
import os
from pathlib import Path

from .constants import DEFAULT_OUTPUT_DIR
from .crawler import fetch_target_articles
from .pipeline import run_pipeline
from .publish import export_articles_to_docs


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if value and len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CBS Fantasy Baseball crawler and JSON pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    crawl = subparsers.add_parser("crawl", help="crawl CBS and print extracted source articles")
    crawl.add_argument("--limit", type=int, default=3)

    run = subparsers.add_parser("run", help="crawl CBS and write article JSON files")
    run.add_argument("--limit", type=int, default=3)
    run.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    run.add_argument("--skip-ai", action="store_true")
    run.add_argument("--model")

    publish = subparsers.add_parser("publish-docs", help="run the pipeline and sync sleeper JSON into docs/")
    publish.add_argument("--limit", type=int, default=6)
    publish.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    publish.add_argument("--docs-dir", default="../docs/data/cbs-news")
    publish.add_argument("--model")

    return parser


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")

    parser = build_parser()
    args = parser.parse_args()

    if args.command == "crawl":
        articles = fetch_target_articles(limit=args.limit)
        print(json.dumps([asdict(article) for article in articles], ensure_ascii=False, indent=2))
        return 0

    if args.command == "run":
        written = run_pipeline(
            limit=args.limit,
            output_dir=args.output_dir,
            skip_ai=args.skip_ai,
            model=args.model,
        )
        print(json.dumps({"written_files": [str(Path(path)) for path in written]}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "publish-docs":
        written = run_pipeline(
            limit=args.limit,
            output_dir=args.output_dir,
            skip_ai=False,
            model=args.model,
        )
        index_payload = export_articles_to_docs(
            Path(args.output_dir),
            Path(args.docs_dir),
        )
        print(
            json.dumps(
                {
                    "written_files": [str(Path(path)) for path in written],
                    "docs_index": str(Path(args.docs_dir) / "index.json"),
                    "exported_articles": len(index_payload.get("articles", [])),
                    "latest_week_by_type": index_payload.get("latest_week_by_type", {}),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

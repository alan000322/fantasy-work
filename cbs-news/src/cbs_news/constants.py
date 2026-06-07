from __future__ import annotations

import re


BASE_URL = "https://www.cbssports.com/fantasy/baseball/"
DEFAULT_OUTPUT_DIR = "output/articles"
DEFAULT_MODEL = "gpt-4.1-mini"
PIPELINE_VERSION = "1.0"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
}

NEWS_PATH_RE = re.compile(r"^/fantasy/baseball/news/")

TARGET_PATTERNS = [
    ("sleeper_pitchers", re.compile(r"\bweek\s+\d+\b.*\bsleeper\b.*\bpitcher", re.I)),
    ("sleeper_hitters", re.compile(r"\bweek\s+\d+\b.*\bsleeper\b.*\bhitter", re.I)),
    ("two_start_pitchers", re.compile(r"\bweek\s+\d+\b.*\btwo-start\b.*\bpitcher", re.I)),
    ("two_start_pitchers", re.compile(r"\btwo-start\b.*\bpitcher\b.*\bweek\s+\d+", re.I)),
]


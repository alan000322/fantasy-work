#!/bin/bash
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

PROJECT_ROOT="/Users/ct-blank/Desktop/fantasy-work"
CBS_DIR="$PROJECT_ROOT/cbs-news"
LOG="/tmp/cbs-news.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"; }

log "===== weekly-publish start ====="

local_count=$(ls "$CBS_DIR/output/articles"/*.json 2>/dev/null | wc -l | tr -d ' ')
docs_count=$(ls "$PROJECT_ROOT/docs/data/cbs-news/articles"/*.json 2>/dev/null | wc -l | tr -d ' ')
if [ "$local_count" -lt "$docs_count" ]; then
  log "ABORT: cbs-news/output/articles ($local_count files) has fewer JSON than docs/data/cbs-news/articles ($docs_count). Refusing to run — publish.py would wipe history. Restore output/articles/ first."
  exit 1
fi

cd "$CBS_DIR"
log "running publish-docs..."
PYTHONPATH=src .venv/bin/python run.py publish-docs --limit 6 >> "$LOG" 2>&1
status=$?
if [ $status -ne 0 ]; then
  log "publish-docs failed with exit $status"
  exit $status
fi

cd "$PROJECT_ROOT"
changed=$(git status --porcelain docs/data/cbs-news/)
if [ -z "$changed" ]; then
  log "no docs changes — nothing to commit"
  log "===== weekly-publish done ====="
  exit 0
fi

today=$(date '+%Y-%m-%d')
git add docs/data/cbs-news/ >> "$LOG" 2>&1
git commit -m "weekly sleeper update $today" >> "$LOG" 2>&1
git push >> "$LOG" 2>&1
push_status=$?
if [ $push_status -ne 0 ]; then
  log "git push failed with exit $push_status"
  exit $push_status
fi

log "pushed weekly sleeper update $today"
log "===== weekly-publish done ====="

# CBS News Pipeline

## What It Does
- 抓 CBS Fantasy Baseball 列表頁
- 自動辨識 `sleeper_hitters`、`sleeper_pitchers`、`two_start_pitchers`
- `sleeper_hitters` / `sleeper_pitchers` 會跑 AI，產出可給前端直接渲染的 `players[]`
- `two_start_pitchers` 只保留原始資料，不做 AI 翻譯
- 可把 sleeper JSON 同步到 `docs/data/cbs-news/`，讓 `docs/index.html` 直接讀取

## Setup
```bash
cd /Users/chiatzuho/Projects/fantasy-work/cbs-news
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp env.example .env
```

`.env` 至少要有：
```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4-mini
```

## Local Test
先只測 crawler：
```bash
cd /Users/chiatzuho/Projects/fantasy-work/cbs-news
PYTHONPATH=src .venv/bin/python run.py crawl --limit 3
```

跑完整 pipeline 並寫入 `cbs-news/output/articles`：
```bash
cd /Users/chiatzuho/Projects/fantasy-work/cbs-news
PYTHONPATH=src .venv/bin/python run.py run --limit 3 --output-dir output/articles
```

同步到 `docs/data/cbs-news/`：
```bash
cd /Users/chiatzuho/Projects/fantasy-work/cbs-news
PYTHONPATH=src .venv/bin/python run.py publish-docs --limit 6
```

本機測 `docs/index.html`：
```bash
cd /Users/chiatzuho/Projects/fantasy-work
python3 -m http.server 8000
```

然後打開：
`http://localhost:8000/docs/`

不要直接用 `file://` 開 `docs/index.html`，因為前端需要 `fetch` JSON。

## How Week Selection Works
前端目前不會只挑單一週，而是：
- 讀 `docs/data/cbs-news/index.json`
- 只取 `sleeper_hitters`、`sleeper_pitchers`
- 依 `published_at` 由新到舊排序
- 每張卡片顯示 `source_article.week`

也就是說，畫面上「先顯示哪一週」是由文章發佈時間決定，不是由 week 數字決定。

`index.json` 另外會保存：
- `latest_week_by_type`

這讓你之後如果想改成「每種類型只顯示最新一篇」，前端可以直接依這個欄位過濾。

## Maintenance
平常更新只要做這件事：
```bash
cd /Users/chiatzuho/Projects/fantasy-work/cbs-news
PYTHONPATH=src .venv/bin/python run.py publish-docs --limit 6
```

這會：
1. 重新抓 CBS 列表與文章
2. 對 sleeper 類跑 AI
3. 更新 `cbs-news/output/articles/`
4. 複製可顯示的 sleeper JSON 到 `docs/data/cbs-news/articles/`
5. 重建 `docs/data/cbs-news/index.json`

之後把 repo push 到 GitHub Pages 即可。

## Suggested Scheduling
如果你在本機或小主機上排程，可用 `cron`。

範例：每週一、四、六上午 8:10 更新一次：
```cron
10 8 * * 1,4,6 cd /Users/chiatzuho/Projects/fantasy-work/cbs-news && PYTHONPATH=src .venv/bin/python run.py publish-docs --limit 6 >> /tmp/cbs-news.log 2>&1
```

如果你只想在 MLB 週報常更新的時間點跑，也可以只排：
- 每週日晚上或週一早上：更新 sleeper / two-start 相關文章

## Notes
- `two_start_pitchers` 目前不做 AI，避免 source 不完整時誤抽球員
- 若 CBS 標題格式改動，優先調整 `src/cbs_news/constants.py` 的規則

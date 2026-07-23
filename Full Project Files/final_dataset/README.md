# final_dataset — deliverable snapshot

Final CSVs for the Marchand Index dataset, one subfolder per source, copied here
as each source is finalized. **Canonical source of truth stays `marchand_index/raw/`** —
code reads from there; this folder is the human-facing deliverable set. If a source
is re-fetched, re-copy here.

## Folder scheme

| Folder | Source | Contents | Finalized |
|---|---|---|---|
| `wiki/` | Wikipedia (en + intl editions, Wikimedia pageviews API) | wiki_pageviews.csv (774), wiki_daily.csv, wiki_intl_pageviews.csv (764), wiki_intl_daily.csv — A36 redirect-augmented | 2026-07-22 |
| `reddit/` | Local reddit_corpus scan (fetch_reddit.py) | pending — gated on A40/A41 amendment texts |
| `trends/` | Google Trends via pytrends (fetch_trends.py) | pending |
| `movers/` | NHL API + manual date research (build_mover_list.py, A38) | pending — skeleton stage |
| `youtube/` | YouTube Data API v3 | pending — blocked on API key |

Subfolders appear when their source finalizes (git doesn't track empty dirs).

"""A38 clause-3 date research: bulk-fill mover_dates.csv from the Wikipedia
season transaction pages (aggregator URL + the row's primary citation URL =
the 2 sources per mover; A20 pattern), leaving unmatched movers needs_date
for individual research.

Inputs : _wiki_trans_2526.html, _wiki_trans_2425.html (saved page HTML)
Outputs: mover_dates.csv updated in place (atomic), mover_dates_sources.md

Match rule (mechanical): a mover row (player, old_team, new_team) is dated
from a transaction row iff the folded player name appears in the row AND the
old/new team nicknames match the row's teams in the correct direction:
  trade      — player listed in the cell headed "To <team containing new>",
               other cell's team contains old;
  fa_signing — "New team" contains new, "Previous team" contains old;
  waiver     — same as fa_signing under the Waivers heading.
Conflicting multi-date matches are left needs_date (reported).
"""
from __future__ import annotations

import datetime as dt
import re
import sys
import unicodedata
from pathlib import Path

from lxml import html as lhtml

sys.path.insert(0, str(Path(__file__).parent))
from _common import atomic_write_csv, load_csv  # noqa: E402

MI = Path(__file__).parent
PAGES = [
    ("https://en.wikipedia.org/wiki/2025%E2%80%9326_NHL_transactions",
     MI / "_wiki_trans_2526.html"),
    ("https://en.wikipedia.org/wiki/2024%E2%80%9325_NHL_transactions",
     MI / "_wiki_trans_2425.html"),
]
FIELDS = ["player_id", "full_name", "nhl_player_id", "old_team", "new_team",
          "move_type", "event_date", "url_1", "url_2", "status"]
_DATE_RE = re.compile(r"([A-Z][a-z]+ \d{1,2}, \d{4})")


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).casefold()


def cite_map(tree) -> dict[str, str]:
    """cite_note id -> first external URL in that reference."""
    out = {}
    for li in tree.xpath('//li[starts-with(@id, "cite_note")]'):
        for a in li.xpath('.//a[starts-with(@href, "http")]'):
            out[li.get("id")] = a.get("href")
            break
    return out


def row_cite_urls(tr, cites) -> list[str]:
    urls = []
    for sup in tr.xpath('.//sup[contains(@class, "reference")]/a'):
        note = (sup.get("href") or "").lstrip("#")
        if note in cites:
            urls.append(cites[note])
    return urls


def parse_page(path: Path, page_url: str) -> list[dict]:
    """All transaction candidates on one page."""
    tree = lhtml.parse(str(path))
    cites = cite_map(tree)
    events: list[dict] = []
    h2 = h3 = ""
    for el in tree.xpath("//h2 | //h3 | //table[contains(@class,'wikitable')]"):
        if el.tag == "h2":
            h2, h3 = fold(el.text_content()), ""
            continue
        if el.tag == "h3":
            h3 = fold(el.text_content())
            continue
        if "free agency" in h2 and "import" not in h3:
            kind = "fa_signing"
        elif "waiver" in h2:
            kind = "waiver"
        elif "trade" in h2:
            kind = "trade"
        else:
            continue
        cur_date = ""
        for tr in el.xpath(".//tr"):
            tds = tr.xpath("./td")
            if not tds:
                continue
            texts = [" ".join(td.text_content().split()) for td in tds]
            m = _DATE_RE.search(texts[0])
            if m:
                cur_date = m.group(1)
                cells = texts[1:]
                cell_nodes = tds[1:]
            else:
                cells = texts
                cell_nodes = tds
            if not cur_date or not cells:
                continue
            try:
                iso = dt.datetime.strptime(cur_date, "%B %d, %Y").date().isoformat()
            except ValueError:
                continue
            events.append({
                "kind": kind, "date": iso,
                "cells": [fold(c) for c in cells],
                "urls": row_cite_urls(tr, cites),
                "page": page_url,
            })
    return events


def _alias(nick: str) -> str:
    """A22 rename rule: Utah Hockey Club and Utah Mammoth are one franchise."""
    return "utah" if ("utah" in nick or "mammoth" in nick) else nick


def match_mover(row: dict, events: list[dict]) -> list[dict]:
    name = fold(row["full_name"])
    old = _alias(fold(row["old_team"]))
    new = _alias(fold(row["new_team"]))
    hits = []
    for ev in events:
        cells = ev["cells"]
        joined = " | ".join(cells)
        if name not in joined:
            continue
        if ev["kind"] == "trade":
            # Destination = any cell containing player AND new nickname;
            # old nickname must sit in a DIFFERENT cell (covers 3-team trades).
            ok = False
            for i, c in enumerate(cells):
                if name in c and new in c:
                    if any(old in o for j, o in enumerate(cells) if j != i):
                        ok = True
            if ok:
                hits.append(ev)
        else:
            # fa/waiver: [player, new team, prev team, ...]
            if new in joined and old in joined:
                hits.append(ev)
    return hits


def main() -> None:
    rows = load_csv(MI / "mover_dates.csv")
    events: list[dict] = []
    for url, path in PAGES:
        evs = parse_page(path, url)
        print(f"{path.name}: {len(evs)} transaction rows parsed")
        events.extend(evs)

    dated = 0
    conflicts: list[str] = []
    unmatched: list[str] = []
    src_lines = ["# A38 mover date sources (bulk pass, 2026-07-22)",
                 "", "Aggregator: Wikipedia season transaction pages; "
                 "primary: the row's citation.", ""]
    renames = 0
    for r in rows:
        if r.get("status") == "dated":
            continue
        # A22 rename rule: Utah Hockey Club -> Mammoth is the same franchise;
        # such rows are derivation artifacts, not moves.
        if _alias(fold(r["old_team"])) == _alias(fold(r["new_team"])):
            r["status"] = "excluded_rename_artifact"
            renames += 1
            continue
        hits = match_mover(r, events)
        dates = sorted({h["date"] for h in hits})
        if not hits:
            unmatched.append(f"{r['full_name']} {r['old_team']}->{r['new_team']}")
            continue
        if len(dates) > 1:
            conflicts.append(f"{r['full_name']} {r['old_team']}->{r['new_team']}"
                             f" dates={dates}")
            continue
        h = hits[0]
        cite = next(iter(h["urls"]), "")
        r["event_date"] = h["date"]
        r["move_type"] = h["kind"]
        r["url_1"] = cite
        r["url_2"] = h["page"]
        r["status"] = "dated" if cite else "needs_second_url"
        dated += 1
        src_lines.append(f"- **{r['full_name']}** {r['old_team']} -> "
                         f"{r['new_team']}: {h['date']} ({h['kind']}) — "
                         f"[primary]({cite or 'MISSING'}) · [wiki]({h['page']})")

    atomic_write_csv(MI / "mover_dates.csv", rows, FIELDS)
    (MI / "mover_dates_sources.md").write_text(
        "\n".join(src_lines) + "\n", encoding="utf-8")
    print(f"dated: {dated}; rename-artifacts excluded: {renames}; "
          f"conflicts: {len(conflicts)}; unmatched: {len(unmatched)}")
    for c in conflicts:
        print("  CONFLICT", c)
    for u in unmatched:
        print("  UNMATCHED", u)


if __name__ == "__main__":
    main()

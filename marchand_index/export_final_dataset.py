"""Build ../final_dataset/ from the canonical sources.

`marchand_index/raw/` (plus a few files at the package root) is the single source
of truth; `final_dataset/` is the human-facing deliverable snapshot. It used to be
maintained by hand-copying, which drifted: on 2026-08-26 the tracked copy of
trends.csv disagreed with raw/ on 34 rows and nothing recorded which was correct.

The snapshot is now generated, not committed. Run this before shipping the
dataset (submission, hand-off, archive):

    python export_final_dataset.py            # write ../final_dataset/
    python export_final_dataset.py --check    # verify without writing; exit 1 on drift

final_dataset/README.md is authored, not generated, and is left untouched.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "final_dataset"

# (source path relative to HERE, destination subfolder)
DELIVERABLES: list[tuple[str, str]] = [
    ("raw/wiki_pageviews.csv", "wiki"),
    ("raw/wiki_daily.csv", "wiki"),
    ("raw/wiki_intl_pageviews.csv", "wiki"),
    ("raw/wiki_intl_daily.csv", "wiki"),
    ("raw/reddit_counts.csv", "reddit"),
    ("raw/reddit_detail.csv", "reddit"),
    ("raw/trends.csv", "trends"),
    ("attention_affiliation.csv", "affiliation"),
    ("mover_dates.csv", "movers"),
    ("mover_dates_sources.md", "movers"),
]


def copy_atomic(src: Path, dst: Path) -> None:
    """Vault convention: write .tmp, then rename. Never overwrite mid-write."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copy2(src, tmp)
    tmp.replace(dst)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="report drift between sources and the snapshot; write nothing")
    args = ap.parse_args()

    missing, drifted, written = [], [], []
    for rel, sub in DELIVERABLES:
        src = HERE / rel
        dst = OUT / sub / Path(rel).name
        if not src.exists():
            missing.append(rel)
            continue
        if args.check:
            if not dst.exists():
                drifted.append(f"{sub}/{dst.name}: absent from snapshot")
            elif not filecmp.cmp(src, dst, shallow=False):
                drifted.append(f"{sub}/{dst.name}: differs from {rel}")
        else:
            copy_atomic(src, dst)
            written.append(f"{sub}/{dst.name}")

    for m in missing:
        print(f"MISSING SOURCE: {m}", file=sys.stderr)
    if args.check:
        for d in drifted:
            print(f"DRIFT: {d}")
        ok = not drifted and not missing
        print("snapshot is current" if ok else f"{len(drifted)} drifted, {len(missing)} missing")
        return 0 if ok else 1

    for w in written:
        print(f"wrote final_dataset/{w}")
    print(f"{len(written)} files exported to {OUT}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())

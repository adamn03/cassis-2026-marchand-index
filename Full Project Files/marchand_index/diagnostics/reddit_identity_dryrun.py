"""A21 acceptance dry-run: print every identity-collision structure derived
from players.csv BEFORE the matcher runs, for owner eyeball (A21 execution
notes: "owner eyeballs the printed pair list").

Writes raw/reddit_identity_pairs.md and prints the same content.
No Reddit data touched — pool + NHL-API roster derivation only.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import RAW_DIR, atomic_write_text, load_players, session  # noqa: E402
from fetch_reddit import (build_groups, build_surname_map, counting_subs,  # noqa: E402
                          fold, load_team_maps, window_teams)


def main() -> None:
    players = load_players()
    surname_map = build_surname_map(players)
    name_to_code, nickname = load_team_maps()
    sess = session(expire_hours=24 * 7)
    wteams = {p["player_id"]: window_teams(sess, p, name_to_code) for p in players}
    groups = build_groups(players, wteams, nickname, surname_map)
    by_pid = {p["player_id"]: p for p in players}

    lines = ["# A21/A22 identity dry-run (owner eyeball before matcher run)", ""]

    lines.append("## Fully non-discriminable pairs (A21 rule 3 — all mentions ambiguous)")
    flagged = [(sn, m) for sn, g in groups.items() for m in g if m["identity_ambiguous"]]
    for sn, m in sorted(flagged, key=lambda x: x[0]):
        p = by_pid[m["pid"]]
        lines.append(f"- {p['full_name']} (pid {m['pid']}, teams {sorted(m['teams'])})")
    if not flagged:
        lines.append("- NONE")

    lines.append("")
    lines.append("## Prefix-colliding first names (A21 rule 1 — evidence non-discriminating)")
    for sn, g in sorted(groups.items()):
        col = [m for m in g if not m["discriminating"]]
        if len(g) >= 2 and col:
            names = ", ".join(f"{by_pid[m['pid']]['full_name']} ({sorted(m['teams'])})"
                              for m in col)
            lines.append(f"- {sn}: {names}")

    lines.append("")
    lines.append("## All shared-surname groups (A15)")
    for sn, g in sorted(groups.items()):
        if len(g) >= 2:
            names = ", ".join(f"{by_pid[m['pid']]['full_name']}" for m in g)
            lines.append(f"- {sn} (n={len(g)}): {names}")

    lines.append("")
    lines.append("## A22 multi-sub players (window-rostered on >1 team, or UTA)")
    for p in players:
        subs = counting_subs(wteams[p["player_id"]])
        if len(subs) > 2:
            lines.append(f"- {p['full_name']}: {'|'.join(subs)} "
                         f"(teams {sorted(wteams[p['player_id']])})")

    text = "\n".join(lines) + "\n"
    atomic_write_text(RAW_DIR / "reddit_identity_pairs.md", text)
    print(text)
    print(f"Written to {RAW_DIR / 'reddit_identity_pairs.md'}")


if __name__ == "__main__":
    main()

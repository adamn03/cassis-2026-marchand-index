"""A39 diagnostic: attention-concentration descriptive panel.

Superstar-economics statistics (Rosen 1981; Adler 1985) on `wiki_12mo`
(post-A36, the one composite component with NO censoring), contrasted with
`cap_hit_M` payroll concentration, plus the between-team ANOVA share
(Bell et al. 2016 driver-vs-constructor analog). DESCRIPTIVE per A39 --
no floor, no gate, not a validation pathway.

Pure functions (gini, top_share, between_team_r2) are tested without I/O.
`engagement_raw` secondary row requires oaq_pilot.csv (Phase-2) and is
skipped with a notice before then. Output:
diagnostics/attention_concentration_report.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/

BOOT_SEED = 20260526
N_BOOT = 1000
TOP_K_1PCT = 8      # ceil(1% of 774)
TOP_K_10PCT = 77    # ceil(10% of 774)


def gini(values: list[float]) -> float:
    """Discrete Gini: sum_i sum_j |xi-xj| / (2 n^2 mean). Requires n>0, mean>0."""
    n = len(values)
    mean = sum(values) / n
    num = sum(abs(a - b) for a in values for b in values)
    return num / (2 * n * n * mean)


def top_share(values: list[float], k: int) -> float:
    """Share of total held by the k largest values."""
    s = sorted(values, reverse=True)
    return sum(s[:k]) / sum(s)


def between_team_r2(values: list[float], teams: list[str]) -> float:
    """One-way ANOVA R^2 = SS_between / SS_total of values grouped by teams."""
    from collections import defaultdict
    grand = sum(values) / len(values)
    groups = defaultdict(list)
    for v, t in zip(values, teams):
        groups[t].append(v)
    ss_total = sum((v - grand) ** 2 for v in values)
    ss_between = sum(len(g) * ((sum(g) / len(g)) - grand) ** 2 for g in groups.values())
    return ss_between / ss_total if ss_total > 0 else 0.0


# --------------------------------------------------------------------------- #
# main() -- report generation                                                  #
# --------------------------------------------------------------------------- #
def _gini_fast(x) -> float:
    """Sort-based Gini, algebraically equal to the discrete pairwise formula;
    O(n log n) so the 1,000-draw bootstrap stays fast."""
    import numpy as np
    x = np.sort(np.asarray(x, dtype=float))
    n = x.size
    i = np.arange(1, n + 1)
    return float(((2 * i - n - 1) * x).sum() / (n * n * x.mean()))


def main() -> None:
    import numpy as np
    import pandas as pd

    from _common import PILOT_DIR, RAW_DIR, atomic_write_text, load_csv

    diag_dir = PILOT_DIR / "diagnostics"
    rng = np.random.default_rng(BOOT_SEED)

    def boot_ci(vals, fn):
        vals = np.asarray(vals, dtype=float)
        n = vals.size
        stats = [fn(vals[rng.integers(0, n, n)]) for _ in range(N_BOOT)]
        lo, hi = np.percentile(stats, [2.5, 97.5])
        return float(lo), float(hi)

    def conc_block(label, vals, n_excl, excl_label):
        vals = np.asarray(vals, dtype=float)
        g = _gini_fast(vals)
        t8 = top_share(list(vals), TOP_K_1PCT)
        t77 = top_share(list(vals), TOP_K_10PCT)
        g_ci = boot_ci(vals, _gini_fast)
        t8_ci = boot_ci(vals, lambda v: top_share(list(v), TOP_K_1PCT))
        t77_ci = boot_ci(vals, lambda v: top_share(list(v), TOP_K_10PCT))
        return [
            f"## {label} (n = {vals.size}; {excl_label} = {n_excl})",
            f"- top-{TOP_K_1PCT} share  = {t8:.4f}  "
            f"[{t8_ci[0]:.4f}, {t8_ci[1]:.4f}]",
            f"- top-{TOP_K_10PCT} share = {t77:.4f}  "
            f"[{t77_ci[0]:.4f}, {t77_ci[1]:.4f}]",
            f"- Gini = {g:.4f}  [{g_ci[0]:.4f}, {g_ci[1]:.4f}]",
            "",
        ]

    lines = ["# A39 attention-concentration panel (DESCRIPTIVE -- no floor)",
             f"Bootstrap: {N_BOOT} player-level resamples, seed {BOOT_SEED}; "
             "95% percentile CIs.", ""]

    # 1-3. wiki_12mo (base quantity, fixed by A39).
    wiki = load_csv(RAW_DIR / "wiki_pageviews.csv")
    wvals = [float(r["wiki_12mo"]) for r in wiki if (r["wiki_12mo"] or "").strip()]
    n_null = len(wiki) - len(wvals)
    lines += conc_block("wiki_12mo (en, post-A36 canonical+redirect)",
                        wvals, n_null, "NULL rows excluded")

    # 4. cap_hit_M contrast.
    caps = load_csv(RAW_DIR / "cap_hits.csv")
    n_low = sum(1 for r in caps if (r.get("cap_quality") or "").strip() == "low")
    cvals = [float(r["cap_hit_M"]) for r in caps
             if (r.get("cap_quality") or "").strip() != "low"
             and (r.get("cap_hit_M") or "").strip()]
    n_cexcl = len(caps) - len(cvals)
    lines += conc_block("cap_hit_M (payroll contrast; Lazear-Rosen framing)",
                        cvals, n_cexcl,
                        f"excluded (cap_quality=low: {n_low}; blank: "
                        f"{n_cexcl - n_low})")

    # 5. Between-team ANOVA share of log1p(wiki_12mo).
    team_of = {r["player_id"]: r["team_code"]
               for r in load_csv(PILOT_DIR / "players.csv")}
    pairs = [(np.log1p(float(r["wiki_12mo"])), team_of[r["player_id"]])
             for r in wiki
             if (r["wiki_12mo"] or "").strip() and r["player_id"] in team_of]
    lv = np.array([p[0] for p in pairs])
    lt = np.array([p[1] for p in pairs])
    r2 = between_team_r2(list(lv), list(lt))

    def r2_of(idx):
        return between_team_r2(list(lv[idx]), list(lt[idx]))
    r2_stats = [r2_of(rng.integers(0, len(lv), len(lv))) for _ in range(N_BOOT)]
    r2_lo, r2_hi = np.percentile(r2_stats, [2.5, 97.5])
    lines += [f"## Between-team share of attention variance "
              f"(one-way ANOVA R^2 on log1p(wiki_12mo); n = {len(lv)})",
              f"- R^2 = {r2:.4f}  [{r2_lo:.4f}, {r2_hi:.4f}]", ""]

    # Secondary row: engagement_raw (censoring caveat) -- Phase-2 only.
    oaq_path = PILOT_DIR / "oaq_pilot.csv"
    if oaq_path.exists():
        oaq = pd.read_csv(oaq_path)
        if "engagement_raw" in oaq.columns:
            evals = oaq["engagement_raw"].to_numpy(dtype=float)
            evals = evals[np.isfinite(evals)]
            emin = float(evals.min())
            shifted = evals - emin  # z-composite can be negative; shares/Gini
            lines += conc_block(
                "engagement_raw (SECONDARY; min-shifted z-composite; Reddit "
                "1,000-cap censoring floors star counts -- A23 caveat)",
                shifted, int(len(oaq) - evals.size), "non-finite excluded")
    else:
        lines += ["## engagement_raw secondary row: SKIPPED -- oaq_pilot.csv "
                  "absent (predates Phase-2 compute).", ""]

    lines += ["Presentation rule (A39): descriptive market facts in one "
              "designated panel; never a ranking, never the headline unless "
              "shipping-matrix rows 6-8 apply (then explicitly labeled "
              "descriptive)."]

    atomic_write_text(diag_dir / "attention_concentration_report.md",
                      "\n".join(lines) + "\n")
    print(f"Wrote {diag_dir / 'attention_concentration_report.md'}")


if __name__ == "__main__":
    main()

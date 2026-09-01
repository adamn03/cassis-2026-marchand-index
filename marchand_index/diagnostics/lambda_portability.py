"""A38 diagnostic: empirical lambda anchor from in-window team-changers.

Event-study construction (MacKinlay 1997): abnormal attention change of movers
vs their K=10 non-mover peers, scaled by the cross-sectional market gradient.
DESCRIPTIVE per A38 -- no floor, cannot alter the lambda = 0.5 primary.

Pure functions (event_windows, delta_log_attention, lambda_emp) are tested
without I/O. `main()` RUNS AFTER the Phase-2 compute (needs oaq_pilot.csv);
it exits with a notice before then. Output:
diagnostics/lambda_portability_report.md.
"""
from __future__ import annotations

import sys
from pathlib import Path
import sys as _sys, pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent.parent))
import _common as _C  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/

WINDOW_START_ORD = 0          # index of _C.WINDOW_START_DATE
WINDOW_LEN = _C.WINDOW_DAYS   # A51: 921, was 365
BOOT_SEED = 20260526
N_BOOT = 1000
MIN_PEERS = 5


def event_windows(t_idx: int, n: int = WINDOW_LEN) -> tuple[range, range]:
    """Pre/post day-index ranges for an event at vector index t_idx, clipped to
    [0, n): pre=[t-63, t-8], post=[t+8, t+63], the +/-7 days around the event
    excluded.

    `n` defaults to the collection window but MUST be overridden with the actual
    series length when one is in hand. Clipping to a module constant while
    indexing a caller-supplied list assumes every vector is exactly that long;
    when A51 widened the window from 365 to 921 that assumption broke and this
    function began indexing past the end of any shorter series.
    """
    pre = range(max(0, t_idx - 63), max(0, t_idx - 7))       # t-63 .. t-8
    post = range(min(n, t_idx + 8), min(n, t_idx + 64))
    return pre, post


def delta_log_attention(daily: list[int], t_idx: int, min_days: int = 30) -> float | None:
    """log1p(mean post) - log1p(mean pre); None if either side < min_days days."""
    import math
    pre, post = event_windows(t_idx, len(daily))
    if len(pre) < min_days or len(post) < min_days:
        return None
    mp = sum(daily[i] for i in pre) / len(pre)
    mq = sum(daily[i] for i in post) / len(post)
    return math.log1p(mq) - math.log1p(mp)


def lambda_emp(beta: float, gamma: float) -> float | None:
    """clip(beta/gamma, 0, 1); None when gamma <= 0 (undefined per A38)."""
    if gamma <= 0:
        return None
    return min(1.0, max(0.0, beta / gamma))


# --------------------------------------------------------------------------- #
# main() -- Phase-2 execution only                                             #
# --------------------------------------------------------------------------- #
def _team_code_map(raw_dir) -> dict[str, str]:
    """Mover team-name (lowercased common name) -> team_code.

    Keys: full slug name ("toronto maple leafs"), nickname token ("leafs"),
    plus the A22 Utah rename alias. Common names from seasonTotals match on
    either form.
    """
    from _common import load_csv
    m: dict[str, str] = {}
    for t in load_csv(raw_dir / "teams.csv"):
        words = t["team_slug"].replace("-", " ").lower().split()
        m[" ".join(words)] = t["team_code"]
        m[words[-1]] = t["team_code"]
    m["utah hockey club"] = "UTA"
    m["mammoth"] = "UTA"
    return m


def _lookup_code(name: str, m: dict[str, str]) -> str | None:
    key = name.strip().lower()
    if key in m:
        return m[key]
    last = key.split()[-1] if key.split() else ""
    return m.get(last)


def _ols_beta(dm, da) -> float:
    """Slope of OLS da = alpha + beta*dm."""
    import numpy as np
    return float(np.polyfit(np.asarray(dm, float), np.asarray(da, float), 1)[0])


def _gamma_hat(y, X) -> float:
    """market_z coefficient (column 1) of OLS y ~ [1, market_z, pos_D, S6]."""
    import numpy as np
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(coef[1])


def main() -> None:
    import csv
    import datetime as dt

    import numpy as np
    import pandas as pd

    from _common import PILOT_DIR, RAW_DIR, atomic_write_text, load_csv
    import compute_oaq as co

    diag_dir = PILOT_DIR / "diagnostics"
    oaq_path = PILOT_DIR / "oaq_pilot.csv"
    movers_path = PILOT_DIR / "mover_dates.csv"
    if not oaq_path.exists():
        print("lambda_portability: oaq_pilot.csv absent -- this diagnostic "
              "runs AFTER the Phase-2 compute (A38). Nothing done.")
        return
    if not movers_path.exists():
        print("lambda_portability: mover_dates.csv absent -- run "
              "build_mover_list.py + date research first (A38). Nothing done.")
        return

    window_start = dt.date(2025, 4, 18)
    excl = {k: 0 for k in (
        "excluded_no_source", "needs_date", "bad_date", "out_of_window",
        "short_window", "no_vector", "few_peers", "team_unmapped")}

    # Daily vectors (post-A36 zero-filled 365-day, index 0 = 2025-04-18).
    daily: dict[int, list[int]] = {}
    for r in load_csv(RAW_DIR / "wiki_daily.csv"):
        v = [int(x) for x in r["daily_views"].split("|")] if r["daily_views"] else []
        if len(v) == WINDOW_LEN:
            daily[int(r["player_id"])] = v

    mover_rows = load_csv(movers_path)
    mover_ids = {int(r["player_id"]) for r in mover_rows}   # ANY move row

    oaq = pd.read_csv(oaq_path, dtype={"player_id": int})
    oaq_by_id = oaq.set_index("player_id")
    players = {int(r["player_id"]): r for r in load_csv(PILOT_DIR / "players.csv")}
    name2code = _team_code_map(RAW_DIR)

    # team_code -> market_z (identical across a team's players).
    team_z: dict[str, float] = {}
    team_z_locked: dict[str, float] = {}
    for pid, prow in players.items():
        if pid in oaq_by_id.index:
            team_z.setdefault(prow["team_code"],
                              float(oaq_by_id.loc[pid, "market_z"]))
            if "market_z_lockedv1" in oaq.columns:
                team_z_locked.setdefault(
                    prow["team_code"],
                    float(oaq_by_id.loc[pid, "market_z_lockedv1"]))

    def collect(zmap: dict[str, float]):
        """Eligible movers -> (dm, da_tilde, move_type) lists. Counts excl."""
        dms, das, kinds = [], [], []
        for r in mover_rows:
            st = (r.get("status") or "").strip()
            if st == "excluded_no_source":
                excl["excluded_no_source"] += 1
                continue
            if not (r.get("event_date") or "").strip():
                excl["needs_date"] += 1
                continue
            try:
                t = dt.date.fromisoformat(r["event_date"].strip())
            except ValueError:
                excl["bad_date"] += 1
                continue
            t_idx = (t - window_start).days
            if not (0 <= t_idx < WINDOW_LEN):
                excl["out_of_window"] += 1
                continue
            pid = int(r["player_id"])
            if pid not in daily:
                excl["no_vector"] += 1
                continue
            da = delta_log_attention(daily[pid], t_idx)
            if da is None:
                excl["short_window"] += 1
                continue
            peer_str = str(oaq_by_id.loc[pid, "peer_player_ids"]) \
                if pid in oaq_by_id.index else ""
            peer_das = []
            for ps in peer_str.split("|"):
                if not ps.strip().isdigit():
                    continue
                q = int(ps)
                if q in mover_ids or q not in daily:
                    continue
                pda = delta_log_attention(daily[q], t_idx)
                if pda is not None:
                    peer_das.append(pda)
            if len(peer_das) < MIN_PEERS:
                excl["few_peers"] += 1
                continue
            oc = _lookup_code(r["old_team"], name2code)
            nc = _lookup_code(r["new_team"], name2code)
            if oc not in zmap or nc not in zmap:
                excl["team_unmapped"] += 1
                continue
            dms.append(zmap[nc] - zmap[oc])
            das.append(da - sum(peer_das) / len(peer_das))
            kinds.append((r.get("move_type") or "").strip())
        return dms, das, kinds

    # Non-mover cross-section for gamma_hat.
    df = co.load_inputs()
    S = co._standardize_skill(df)                       # across the full pool
    zcol = oaq.set_index("player_id")["market_z"]
    mz = df["player_id"].map(zcol).to_numpy(dtype=float)
    mz_locked = (df["player_id"].map(
        oaq.set_index("player_id")["market_z_lockedv1"]).to_numpy(dtype=float)
        if "market_z_lockedv1" in oaq.columns else np.full(len(df), np.nan))
    is_d = (df["position"].astype(str) == "D").to_numpy(dtype=float)
    y_all = np.log1p(df["wiki_12mo"].to_numpy(dtype=float))
    nonmover = ~df["player_id"].isin(mover_ids).to_numpy()

    def gamma_for(mzv):
        mask = nonmover & np.isfinite(y_all) & np.isfinite(mzv)
        X = np.column_stack([np.ones(mask.sum()), mzv[mask], is_d[mask],
                             S[mask]])
        return _gamma_hat(y_all[mask], X), mask

    gamma, nm_mask = gamma_for(mz)
    dms, das, kinds = collect(team_z)
    n_mov = len(dms)

    lines = ["# A38 lambda-portability diagnostic (DESCRIPTIVE -- no floor)", ""]
    lines.append(f"Eligible movers n = {n_mov}; non-movers in gamma "
                 f"regression n = {int(nm_mask.sum())}")
    lines.append("Exclusions: " + ", ".join(f"{k}={v}" for k, v in excl.items()))
    lines.append("")

    if n_mov < 2:
        lines.append("n too small to estimate beta -- diagnostic reported "
                     "as UNAVAILABLE (A38 guardrail; rules not loosened).")
        atomic_write_text(diag_dir / "lambda_portability_report.md",
                          "\n".join(lines) + "\n")
        print(f"Wrote {diag_dir / 'lambda_portability_report.md'} (n={n_mov})")
        return

    beta = _ols_beta(dms, das)
    lam = lambda_emp(beta, gamma)

    # Bootstrap: resample movers (beta) and non-movers (gamma); seed 20260526.
    rng = np.random.default_rng(BOOT_SEED)
    y_nm = y_all[nm_mask]
    X_nm = np.column_stack([np.ones(nm_mask.sum()), mz[nm_mask],
                            is_d[nm_mask], S[nm_mask]])
    dms_a, das_a = np.asarray(dms), np.asarray(das)
    lams, n_undef = [], 0
    for _ in range(N_BOOT):
        mi = rng.integers(0, n_mov, n_mov)
        ni = rng.integers(0, len(y_nm), len(y_nm))
        try:
            b = _ols_beta(dms_a[mi], das_a[mi])
            g = _gamma_hat(y_nm[ni], X_nm[ni])
        except Exception:
            n_undef += 1
            continue
        lv = lambda_emp(b, g)
        if lv is None:
            n_undef += 1
        else:
            lams.append(lv)

    lam_txt = (f"{lam:.3f}" if lam is not None
               else f"undefined (non-positive market gradient; gamma={gamma:.4f})")
    lines.append(f"beta_hat  = {beta:.4f}")
    lines.append(f"gamma_hat = {gamma:.4f}")
    lines.append(f"lambda_emp = {lam_txt}")
    if lams:
        lo, hi = np.percentile(lams, [2.5, 97.5])
        lines.append(f"lambda_emp 95% CI = [{lo:.3f}, {hi:.3f}] "
                     f"({len(lams)} defined draws; {n_undef} undefined)")
    lines.append("")
    if n_mov < 10:
        lines.append("**n too small to anchor** (A38 guardrail): reported, "
                     "not interpreted; rules not loosened to grow n.")
    lines.append("Disclosed bias: post-move novelty inflates post-attention, "
                 "biasing beta toward 0 (the portable conclusion).")
    lines.append("")

    # Secondary cut: trade-only movers.
    tsel = [i for i, k in enumerate(kinds) if k == "trade"]
    if len(tsel) >= 2:
        bt = _ols_beta(dms_a[tsel], das_a[tsel])
        lt = lambda_emp(bt, gamma)
        lt_txt = f"{lt:.3f}" if lt is not None else "undefined"
        lines.append(f"Trade-only cut: n = {len(tsel)}, beta = {bt:.4f}, "
                     f"lambda_emp = {lt_txt}")
    else:
        lines.append(f"Trade-only cut: n = {len(tsel)} -- too small, skipped.")

    # Sensitivity: market_z_lockedv1.
    if team_z_locked and np.isfinite(mz_locked).any():
        g2, _ = gamma_for(mz_locked)
        d2, a2, _ = collect(team_z_locked)
        if len(d2) >= 2:
            b2 = _ols_beta(d2, a2)
            l2 = lambda_emp(b2, g2)
            l2_txt = f"{l2:.3f}" if l2 is not None else "undefined"
            lines.append(f"Sensitivity (market_z_lockedv1): beta = {b2:.4f}, "
                         f"gamma = {g2:.4f}, lambda_emp = {l2_txt}")
    lines.append("")
    lines.append("Per A38: the primary lambda = 0.5 is unchanged under every "
                 "outcome; not a validation pathway.")

    atomic_write_text(diag_dir / "lambda_portability_report.md",
                      "\n".join(lines) + "\n")
    print(f"Wrote {diag_dir / 'lambda_portability_report.md'} (n={n_mov})")


if __name__ == "__main__":
    main()

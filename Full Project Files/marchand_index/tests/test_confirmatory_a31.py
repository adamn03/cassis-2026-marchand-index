"""A31: confirmatory hierarchy — stratified V1b draws, paired dAUC, power,
MWU companion, permutation p-values, BH secondary family, results emit."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
import compute_oaq as co  # noqa: E402


# --------------------------------------------------------------------------- #
# helper-level tests                                                           #
# --------------------------------------------------------------------------- #
def test_stratified_draws_always_finite_with_single_positive():
    # Naive iid bootstrap would draw 0-positive resamples (AUC undefined);
    # the stratified scheme must never do that.
    rng = np.random.default_rng(0)
    scores = rng.normal(size=12)
    labels = np.zeros(12)
    labels[3] = 1
    draws = co.stratified_auc_draws({"s": scores}, labels, n_draws=200, seed=1)
    assert np.isfinite(draws["s"]).all()


def test_paired_delta_auc_identical_scores_is_degenerate_zero():
    rng = np.random.default_rng(1)
    scores = rng.normal(size=30)
    labels = np.zeros(30)
    labels[:8] = 1
    draws = co.stratified_auc_draws(
        {"a": scores, "b": scores.copy()}, labels, n_draws=100, seed=2)
    diff = draws["a"] - draws["b"]
    assert np.all(diff == 0.0)
    assert co._pct_ci(diff) == [0.0, 0.0]


def test_bh_step_up_all_supported():
    out = co.bh_step_up({"A": 0.01, "B": 0.03, "C": 0.04}, q=0.05)
    assert all(out[k]["supported"] for k in "ABC")


def test_bh_step_up_partial():
    # p_(2)=0.03 <= 2/3*0.05; p_(3)=0.5 > 0.05 -> first two supported.
    out = co.bh_step_up({"A": 0.01, "B": 0.03, "C": 0.5}, q=0.05)
    assert out["A"]["supported"]
    assert out["B"]["supported"]
    assert not out["C"]["supported"]


def test_bh_step_up_rejects_above_own_threshold():
    # 0.04 > 2/3*0.05 = 0.0333 and 0.5 > 0.05 -> only the first survives.
    out = co.bh_step_up({"A": 0.01, "B": 0.04, "C": 0.5}, q=0.05)
    assert out["A"]["supported"]
    assert not out["B"]["supported"]
    assert not out["C"]["supported"]


def test_bh_step_up_nan_never_supported():
    out = co.bh_step_up({"A": 0.01, "B": float("nan")}, q=0.05)
    assert not out["B"]["supported"]
    assert np.isnan(out["B"]["p"])
    assert out["A"]["supported"]


def test_power_statement_pins_and_monotone():
    # A31 text pins at 12/762: SE0 = 0.084, critical AUC = 0.638,
    # power 0.77 @ floor 0.70 and 0.98 @ target 0.80.
    p = co.a31_power_statement(12, 762)
    assert round(p["se_null"], 3) == 0.084
    assert round(p["critical_auc"], 3) == 0.638
    assert round(p["power_at_floor"], 2) == 0.77
    assert round(p["power_at_target"], 2) == 0.98
    assert p["power_at_target"] > p["power_at_floor"]


def test_mwu_one_sided_p_in_unit_interval():
    rng = np.random.default_rng(3)
    scores = rng.normal(size=40)
    labels = np.zeros(40)
    labels[:10] = 1
    p = co.mwu_one_sided_p(scores, labels)
    assert 0.0 < p < 1.0


def test_perm_p_spearman_agreement_sign_flip():
    # V1a coding: rank 1 = best, so agreement is NEGATIVE rho; with
    # agreement_sign=-1 a perfectly aligned pair must give a tiny p.
    x = np.arange(20, dtype=float)
    y_rank = 20.0 - x
    p = co.perm_p_spearman(x, y_rank, n_perm=500, seed=4, agreement_sign=-1.0)
    assert p < 0.05


def test_perm_p_membership_auc_detects_separation():
    scores = np.concatenate([np.zeros(15), np.full(5, 10.0)])
    labels = np.concatenate([np.zeros(15), np.ones(5)])
    p = co.perm_p_membership_auc(scores, labels, n_perm=500, seed=5)
    assert p < 0.05


# --------------------------------------------------------------------------- #
# external_validation wiring                                                   #
# --------------------------------------------------------------------------- #
def _df(port, jersey_mem, seed=7):
    """Fixture pool. jersey_rank (1=best) and asg2024 membership are aligned
    with OAQ_portable so the agreement direction is exercised."""
    n = len(port)
    port = np.asarray(port, dtype=float)
    rng = np.random.default_rng(seed)
    order = np.argsort(-port)
    jersey_rank = np.full(n, np.nan)
    for r, i in enumerate(order[:8], 1):
        jersey_rank[i] = r
    asg = np.zeros(n)
    asg[order[:3]] = 1
    return pd.DataFrame({
        "full_name": [f"P{i}" for i in range(n)],
        "team_code": [f"T{i % 6}" for i in range(n)],
        "OAQ_portable": port,
        "OAQ_observed": port + rng.normal(0, 0.1, n),
        "engagement_raw": rng.normal(size=n),
        "ppg": rng.uniform(0.2, 1.4, n),
        "jersey_rank": jersey_rank,
        "jersey_list_member": np.asarray(jersey_mem, dtype=float),
        "asg2024_member": asg,
    })


def _strong_fixture():
    # 3 members clearly above all 19 non-members -> AUC 1 on every draw.
    port = np.concatenate([np.full(3, 20.0) + [0, 1, 2],
                           np.arange(19, dtype=float) * 0.4])
    mem = np.zeros(22)
    mem[:3] = 1
    return _df(port, mem)


def test_external_validation_emits_perm_p_and_bh(tmp_path, monkeypatch):
    monkeypatch.setattr(co, "PILOT_DIR", tmp_path)  # no team_outcomes.csv
    res = co.external_validation(_strong_fixture(), n_draws=100, seed=9,
                                 n_perm=200)
    assert 0.0 < res["V1a"]["perm_p"] <= 1.0
    assert 0.0 < res["V2"]["perm_p"] <= 1.0
    assert np.isnan(res["V3"]["perm_p"])
    bh = res["BH_secondary"]
    assert set(bh) == {"V1a", "V2", "V3"}
    assert not bh["V3"]["supported"]
    # Aligned fixture: V1a and V2 are real effects at n_perm=200.
    assert bh["V1a"]["p"] < 0.05
    assert bh["V2"]["p"] < 0.05


def test_v3_perm_p_wired_and_in_bh(tmp_path, monkeypatch):
    monkeypatch.setattr(co, "PILOT_DIR", tmp_path)
    df = _strong_fixture()
    team_sums = df.groupby("team_code")["OAQ_observed"].sum()
    pd.DataFrame({
        "team_code": team_sums.index,
        "wiki_12mo": team_sums.to_numpy() * 100 + 50,  # monotone outcome
    }).to_csv(tmp_path / "team_outcomes.csv", index=False)
    res = co.external_validation(df, n_draws=50, seed=9, n_perm=200)
    assert np.isfinite(res["V3"]["perm_p"])
    assert res["BH_secondary"]["V3"]["p"] == res["V3"]["perm_p"]


def test_verdict_class_strong(tmp_path, monkeypatch):
    monkeypatch.setattr(co, "PILOT_DIR", tmp_path)
    res = co.external_validation(_strong_fixture(), n_draws=100, seed=9,
                                 n_perm=200)
    assert res["V1b"]["verdict_class"] == "V1b-strong"


def test_verdict_class_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(co, "PILOT_DIR", tmp_path)
    port = np.concatenate([np.full(3, -20.0), np.arange(19, dtype=float)])
    mem = np.zeros(22)
    mem[:3] = 1
    res = co.external_validation(_df(port, mem), n_draws=100, seed=9,
                                 n_perm=200)
    assert res["V1b"]["verdict_class"] == "V1b-fail"


def test_verdict_class_point(tmp_path, monkeypatch):
    # One member above all negatives, one mid-pack: point AUC = 0.75 (>= floor)
    # but the 2-positive stratified CI reaches below 0.50 -> V1b-point.
    monkeypatch.setattr(co, "PILOT_DIR", tmp_path)
    port = np.concatenate([[12.0, 4.5], np.arange(10, dtype=float)])
    mem = np.zeros(12)
    mem[:2] = 1
    res = co.external_validation(_df(port, mem), n_draws=400, seed=9,
                                 n_perm=200)
    assert abs(res["V1b"]["value"] - 0.75) < 1e-9
    assert res["V1b"]["ci95"][0] <= 0.50
    assert res["V1b"]["verdict_class"].startswith("V1b-point")


# --------------------------------------------------------------------------- #
# results emit                                                                 #
# --------------------------------------------------------------------------- #
def test_a31_results_lines_section(tmp_path, monkeypatch):
    monkeypatch.setattr(co, "PILOT_DIR", tmp_path)
    res = co.external_validation(_strong_fixture(), n_draws=100, seed=9,
                                 n_perm=200)
    txt = "\n".join(co._a31_results_lines(res))
    assert "## A31 confirmatory hierarchy (V1b primary)" in txt
    assert "V1b-strong" in txt
    assert "critical AUC" in txt              # power statement sentence
    assert "Mann-Whitney" in txt              # descriptive companion
    assert "| engagement_raw |" in txt        # baseline AUC table
    assert "minus engagement_raw" in txt      # paired dAUC table
    assert "| V1a |" in txt and "| V2 |" in txt and "| V3 |" in txt  # BH table
    assert "floors still govern" in txt


def test_write_results_md_calls_a31_section():
    import inspect
    assert "_a31_results_lines" in inspect.getsource(co.write_results_md)

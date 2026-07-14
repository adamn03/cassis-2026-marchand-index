"""A26: 7-day circular block bootstrap for the wiki daily vectors."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # marchand_index/
from compute_oaq import block_resample  # noqa: E402


def test_block_resample_shape_and_membership():
    rng = np.random.default_rng(1)
    arr = np.arange(365, dtype=float)
    out = block_resample(arr, rng)
    assert out.size == 365
    assert set(out).issubset(set(arr))


def test_block_resample_preserves_week_runs():
    # Interior 7-day windows of the output must be contiguous (mod 365) runs
    # of the source ring wherever they fall entirely inside one block.
    rng = np.random.default_rng(2)
    arr = np.arange(365, dtype=float)
    out = block_resample(arr, rng)
    # Check block 0 (indices 0..6): must be consecutive mod 365.
    diffs = np.diff(out[:7]) % 365
    assert (diffs == 1).all()


def test_block_resample_empty_and_short():
    rng = np.random.default_rng(3)
    assert block_resample(np.empty(0), rng).size == 0
    out = block_resample(np.array([5.0, 6.0, 7.0]), rng)
    assert out.size == 3


def test_autocorrelated_vector_wider_ci_under_block_than_iid():
    """E7: iid resampling understates variance for autocorrelated series.
    The bootstrap sd of the resampled SUM must be larger under 7-day blocks."""
    rng_gen = np.random.default_rng(20260526)
    # Strongly autocorrelated series: weekly news-cycle square wave + noise.
    n = 365
    base = np.repeat(rng_gen.uniform(0, 1000, -(-n // 7)), 7)[:n]
    series = base + rng_gen.normal(0, 5, n)

    draws = 400
    rng_iid = np.random.default_rng(11)
    rng_blk = np.random.default_rng(11)
    sums_iid = np.array([
        series[rng_iid.integers(0, n, n)].sum() for _ in range(draws)])
    sums_blk = np.array([
        block_resample(series, rng_blk).sum() for _ in range(draws)])
    assert sums_blk.std(ddof=1) > sums_iid.std(ddof=1)


def test_deterministic_under_fixed_seed():
    a = block_resample(np.arange(365, dtype=float),
                       np.random.default_rng(20260526))
    b = block_resample(np.arange(365, dtype=float),
                       np.random.default_rng(20260526))
    np.testing.assert_array_equal(a, b)

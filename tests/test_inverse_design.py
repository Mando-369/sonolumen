"""Tests for `cavplasma.suggestions.inverse_design` — the target → params flow.

The heuristic is fast and should always produce a Scenario that runs.
The refinement is slow but must converge to a regime that respects the
target's must_be_stable_spherical filter when one exists in the search
neighbourhood.
"""
from __future__ import annotations

import pytest

from cavplasma.scenario import presets
from cavplasma.suggestions import (
    DesignConstraints,
    DesignTarget,
    initial_design,
    refine_design,
)


def test_initial_design_returns_runnable_scenario():
    target = DesignTarget(T_peak_K=20_000.0)
    scenario, diag = initial_design(target)
    # Scenario is well-formed: required fields, drive on a chamber mode,
    # bubble seed in the SBSL band.
    assert scenario.bubble_population.seed is not None
    assert 2.0e-6 <= scenario.bubble_population.seed.R0 <= 8.0e-6
    drv = next(iter(scenario.drive.waveforms.values()))
    assert 1.0 * 101_325.0 <= drv.P_A <= 1.8 * 101_325.0
    # The diagnostic dict must explain each choice
    assert "drive_freq_rationale" in diag
    assert "R0_rationale" in diag
    assert "P_A_rationale" in diag


def test_initial_design_picks_chamber_mode_n2():
    """The heuristic should land the drive on the n=2 radial mode of
    the SBSL canonical chamber (5 cm sphere, c≈1482 m/s in water →
    f_n=2 ≈ 29.6 kHz)."""
    target = DesignTarget(T_peak_K=20_000.0)
    scenario, diag = initial_design(target)
    drv = next(iter(scenario.drive.waveforms.values()))
    # The chamber's n=2 mode for water (c ≈ 1482) should be ~29640 Hz.
    assert 28_000 < drv.f < 31_000, (
        f"drive freq {drv.f} Hz not at chamber mode n=2 (~29.6 kHz)"
    )


def test_initial_design_higher_T_target_means_higher_P_A():
    """The empirical P_A ↔ T_peak interpolation should be monotone."""
    s_lo, _ = initial_design(DesignTarget(T_peak_K=10_000.0))
    s_mid, _ = initial_design(DesignTarget(T_peak_K=20_000.0))
    s_hi, _ = initial_design(DesignTarget(T_peak_K=40_000.0))
    pa_lo = next(iter(s_lo.drive.waveforms.values())).P_A
    pa_mid = next(iter(s_mid.drive.waveforms.values())).P_A
    pa_hi = next(iter(s_hi.drive.waveforms.values())).P_A
    assert pa_lo < pa_mid < pa_hi, (
        f"P_A not monotone in target T_peak: lo={pa_lo}, mid={pa_mid}, hi={pa_hi}"
    )


@pytest.mark.timeout(60)
def test_refine_design_stays_in_stable_band():
    """The refinement should pick a stable_spherical hit when one exists
    in the grid neighbourhood (T_peak ~ 20 kK around the heuristic).
    """
    target = DesignTarget(T_peak_K=20_000.0, must_be_stable_spherical=True,
                            feasible_transducer_atm=10.0)
    seed_scenario, _ = initial_design(target)
    refined, diag = refine_design(seed_scenario, target,
                                    n_amplitude=3, n_R0=3)
    assert "best_summary" in diag
    assert diag["best_summary"] is not None, (
        f"refinement found nothing (grid had {diag.get('n_evaluations')} "
        f"evaluations); first row: {diag['grid_results'][:1]}"
    )
    best = diag["best_summary"]
    # Must converge to a stable regime when the target asks for it.
    assert best["regime"] == "stable_spherical", (
        f"refinement landed in {best['regime']!r} regime; "
        f"target required stable_spherical"
    )


@pytest.mark.timeout(60)
def test_refine_design_grid_size_matches_request():
    target = DesignTarget(T_peak_K=15_000.0)
    seed_scenario, _ = initial_design(target)
    _refined, diag = refine_design(seed_scenario, target,
                                    n_amplitude=2, n_R0=2)
    # 2×2 grid = 4 evaluations
    assert diag["n_evaluations"] == 4

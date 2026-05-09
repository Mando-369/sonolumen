"""§14.8 acceptance tests for the suggestions engine.

Six tests from `cavitation_research/14_suggestions_engine.md`:

  1. test_classifier_sbsl_canonical    — regime → 'stable_spherical'-ish
  2. test_classifier_sub_blake         — sub-Blake config → 'sub_blake'
  3. test_R1_fires_on_subblake         — R1 returns suggested 1.5× P_A
  4. test_R6_fires_on_off_resonance    — R6 fires when drive ≠ chamber f
  5. test_caveat_C1_always_on_for_plasma — every T > 5000 K run has C1
  6. test_priority_ordering            — errors first, regime entry, optimisation
"""

from __future__ import annotations

import dataclasses

import pytest

from sonolumen.scenario import Scenario, presets
from sonolumen.scenario.observers import PMTObserver
from sonolumen.suggestions import (
    SuggestionsEngine,
    classify_regime,
    suggest_next_experiment,
)


# ---------------------------------------------------------------------------
# 1. Classifier — SBSL canonical
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_classifier_sbsl_canonical():
    """§14.8 #1 — sbsl_canonical().run() classified into the SBSL band.

    Note: v1's canonical SBSL hits Mach ≈ 0.59 (above 0.3 threshold), so
    §14.2 strictly classifies it as 'violent_spherical' (mapped to public
    'marginal'). 'stable_spherical' is the textbook label; v2's actual
    numerical result reflects the §10.5 stronger-than-textbook regime.
    """
    s = presets.sbsl_canonical()
    r = s.run()
    public, internal = classify_regime(s, r)
    assert public in ("stable_spherical", "marginal"), (
        f"public regime {public!r} unexpected for SBSL canonical"
    )
    assert internal in ("stable_spherical", "violent_spherical"), (
        f"internal regime {internal!r} unexpected"
    )


# ---------------------------------------------------------------------------
# 2. Classifier — sub-Blake
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_classifier_returns_rationale_audit_trail():
    """The rationale list must walk through every check in order, with
    the matched check marked FIRED and the rest PASS/SKIP. Lets the UI
    show 'why this regime?' under the regime card."""
    from sonolumen.suggestions.regime import classify_with_rationale
    s = presets.sbsl_canonical()
    r = s.run()
    public, internal, rationale = classify_with_rationale(s, r)
    assert isinstance(rationale, list) and len(rationale) > 0, (
        "rationale must be a non-empty list of (check, status, detail)"
    )
    statuses = [entry[1] for entry in rationale]
    assert "FIRED" in statuses, (
        f"rationale must contain a FIRED entry, got statuses {statuses}"
    )
    # FIRED must be exactly once and must be the *last* entry (we early-
    # return on FIRED).
    fired_idx = [i for i, s_ in enumerate(statuses) if s_ == "FIRED"]
    assert fired_idx == [len(statuses) - 1], (
        f"FIRED must terminate the audit, found at indices {fired_idx} "
        f"of {len(statuses)} entries"
    )


def test_r6_off_resonance_scans_multiple_modes():
    """R6 used to only check the geometric fundamental, missing drives
    aimed at the n=2 / n=3 radial mode. Verify the message now lists
    multiple modes and identifies the closest one."""
    import dataclasses
    from sonolumen.config import AcousticDrive
    from sonolumen.scenario.types import DriveSchedule
    from sonolumen.scenario.scenario import _check_off_resonance

    s = presets.sbsl_canonical()
    drv = next(iter(s.drive.waveforms.values()))
    # 1 MHz drive — far from every mode of a 5 cm sphere.
    drv_far = dataclasses.replace(drv, f=1.0e6, P_A=2.0 * 101_325.0)
    s_far = dataclasses.replace(
        s,
        drive=DriveSchedule(waveforms={list(s.drive.waveforms.keys())[0]: drv_far}),
    )
    warnings = _check_off_resonance(s_far)
    assert warnings, "1 MHz drive must trip R6"
    msg = warnings[0].message
    # Message must enumerate at least 4 scanned modes and identify the
    # closest one with its mode index.
    assert "n=1" in msg and "n=2" in msg and "n=3" in msg and "n=4" in msg, (
        f"R6 must list multiple modes, got message: {msg}"
    )
    assert "closest is mode" in msg, (
        f"R6 must identify the closest mode, got message: {msg}"
    )


def test_regime_strip_renders_one_tile_per_entry():
    """Notebook regime strip — one coloured tile per run, tooltipped
    with the entry's regime + headline numbers."""
    from sonolumen.ui.callbacks import render_notebook_regime_strip
    notebook = [
        {"regime": "sub_blake",        "T_peak_K": 300, "R_max_um": 5,
         "wall_mach": 0.001, "photons_4pi": 0},
        {"regime": "linear_oscillation", "T_peak_K": 800, "R_max_um": 8,
         "wall_mach": 0.01, "photons_4pi": 1e-50},
        {"regime": "stable_spherical", "T_peak_K": 18000, "R_max_um": 38,
         "wall_mach": 0.5, "photons_4pi": 1e6},
    ]
    out = render_notebook_regime_strip(notebook)
    # Walk children to count tiles
    strip_div = out.children[1]
    assert len(strip_div.children) == 3, (
        f"expected 3 tiles, got {len(strip_div.children)}"
    )
    # Tile colours match REGIME_COLOR
    from sonolumen.ui.style import REGIME_COLOR
    for tile, entry in zip(strip_div.children, notebook):
        expected = REGIME_COLOR.get(entry["regime"])
        actual = tile.style["backgroundColor"]
        assert actual == expected, (
            f"tile colour mismatch: regime={entry['regime']}, "
            f"expected {expected}, got {actual}"
        )


def test_classifier_linear_oscillation_off_resonance():
    """Regression for the false-positive 'stable_spherical' bug:
    a 1 MHz drive on a 26.5 kHz chamber + small bubble lands in the
    near-Minnaert linear-oscillation regime where T_peak ~ 850 K and
    nothing collapses. The classifier used to fall through to
    'stable_spherical' (green); it must now mark it 'linear_oscillation'
    (yellow) so the user knows the bubble isn't actually doing SBSL.
    """
    import dataclasses
    from sonolumen.config import AcousticDrive
    from sonolumen.scenario.types import DriveSchedule
    from sonolumen.suggestions.regime import classify as classify_regime

    s = presets.sbsl_canonical()
    drv = next(iter(s.drive.waveforms.values()))
    # 1 MHz off-resonance + 2 atm — same shape as the user's preset.
    drv_far = dataclasses.replace(drv, f=1.0e6, P_A=2.0 * 101_325.0)
    s_lin = dataclasses.replace(
        s,
        drive=DriveSchedule(waveforms={list(s.drive.waveforms.keys())[0]: drv_far}),
    )
    r = s_lin.run()
    public, internal = classify_regime(s_lin, r)
    assert public == "linear_oscillation", (
        f"off-resonance bubble must read 'linear_oscillation', got {public!r}. "
        f"T_peak={r.summary.T_peak_K:.0f} K, "
        f"R_max/R0={r.summary.R_max / s_lin.bubble_population.seed.R0:.2f}, "
        f"Mach={r.summary.wall_mach_peak:.3f}"
    )
    assert internal == "linear_oscillation"


def test_classifier_sub_blake():
    """§14.8 #2 — drive amplitude well below the Blake threshold for the
    nucleus → regime classified as 'sub_blake'."""
    s = presets.sbsl_canonical()
    # Drop drive amplitude to 0.01 atm — guaranteed sub-Blake for any R₀
    new_waveforms = {}
    for name, drv in s.drive.waveforms.items():
        new_waveforms[name] = dataclasses.replace(drv, P_A=1_000.0)
    s = dataclasses.replace(
        s, drive=dataclasses.replace(s.drive, waveforms=new_waveforms),
    )
    r = s.run()
    public, internal = classify_regime(s, r)
    assert public == "sub_blake", f"expected 'sub_blake', got {public!r}"
    assert internal == "sub_blake"


# ---------------------------------------------------------------------------
# 3. R1 — sub-Blake → suggest 1.5× P_A
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_R1_fires_on_subblake():
    """§14.8 #3 — R1 fires on sub-Blake regime and proposes 1.5× drive."""
    s = presets.sbsl_canonical()
    new_waveforms = {}
    for name, drv in s.drive.waveforms.items():
        new_waveforms[name] = dataclasses.replace(drv, P_A=1_000.0)
    s = dataclasses.replace(
        s, drive=dataclasses.replace(s.drive, waveforms=new_waveforms),
    )
    r = s.run()
    rule_ids = [sg.rule_id for sg in r.suggestions]
    assert "R1" in rule_ids, (
        f"R1 did not fire on sub-Blake; got {rule_ids}"
    )
    R1 = next(sg for sg in r.suggestions if sg.rule_id == "R1")
    assert R1.severity == "warning"
    assert R1.suggested_change is not None
    # The suggested change should set drive P_A to 1.5× current (1500 Pa)
    new_P = next(iter(R1.suggested_change.values()))
    assert abs(new_P - 1.5 * 1_000.0) < 1e-6


# ---------------------------------------------------------------------------
# 4. R6 — off-resonance
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_R6_fires_on_off_resonance():
    """§14.8 #4 — drive at 0.5× chamber eigenmode → R6 fires.

    SBSL canonical chamber is a 100 mL sphere with f_eigen ≈ 14.8 kHz.
    Setting drive to 100 Hz is well outside the Q-bandwidth; R6 fires.
    """
    s = presets.sbsl_canonical()
    new_waveforms = {}
    for name, drv in s.drive.waveforms.items():
        new_waveforms[name] = dataclasses.replace(drv, f=100.0)
    s = dataclasses.replace(
        s, drive=dataclasses.replace(s.drive, waveforms=new_waveforms),
    )
    r = s.run()
    rule_ids = [sg.rule_id for sg in r.suggestions]
    assert "R6" in rule_ids, f"R6 did not fire off-resonance; got {rule_ids}"


# ---------------------------------------------------------------------------
# 5. C1 — always-on for plasma runs
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_caveat_C1_always_on_for_plasma():
    """§14.8 #5 — any run with T_peak > 5000 K includes C1 in caveats."""
    s = presets.sbsl_canonical()
    r = s.run()
    assert r.summary.T_peak_K > 5000.0
    rule_ids = [sg.rule_id for sg in r.suggestions]
    assert "C1" in rule_ids, f"C1 not present despite T_peak > 5000 K; got {rule_ids}"


# ---------------------------------------------------------------------------
# 6. Priority ordering
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_priority_ordering():
    """§14.8 #6 — errors and regime-entry rules outrank optimisation; caveats last.

    Per §14.5: "Caveats last — they're context, not action items." So
    severity is non-decreasing *within* each group (action items / caveats),
    but the boundary between the two groups can flip back to a high-severity
    caveat (e.g. C7 'warning') after info-severity action items.
    """
    s = presets.sbsl_canonical()
    r = s.run()
    severities = [sg.severity for sg in r.suggestions]
    categories = [sg.category for sg in r.suggestions]
    rank = {"error": 0, "warning": 1, "info": 2}

    if "caveat" in categories:
        first_caveat = categories.index("caveat")
        action_severities = [rank[s] for s in severities[:first_caveat]]
        caveat_severities = [rank[s] for s in severities[first_caveat:]]
    else:
        action_severities = [rank[s] for s in severities]
        caveat_severities = []

    assert action_severities == sorted(action_severities), (
        f"action-item severities not in non-decreasing order: "
        f"{severities[:len(action_severities)]}"
    )
    assert caveat_severities == sorted(caveat_severities), (
        f"caveat severities not in non-decreasing order: "
        f"{severities[len(action_severities):]}"
    )
    # All caveats appear contiguously at the end (or there are none)
    if "caveat" in categories:
        first_caveat = categories.index("caveat")
        assert all(c == "caveat" for c in categories[first_caveat:]), (
            f"non-caveat categories appear after first caveat: {categories}"
        )


# ---------------------------------------------------------------------------
# Bonus — engine returns a fully populated SuggestionsReport
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_engine_returns_report():
    s = presets.sbsl_canonical()
    r = s.run()
    report = SuggestionsEngine(s, r).analyze()
    assert report.regime in (
        "sub_blake", "stable_spherical", "marginal",
        "unstable_likely", "transducer_limited",
    )
    assert isinstance(report.suggestions, list)
    assert isinstance(report.caveats, list)
    # Caveat list is non-empty for plasma runs (C1)
    assert len(report.caveats) >= 1


# ---------------------------------------------------------------------------
# Bonus — next_experiment runs end-to-end
# ---------------------------------------------------------------------------
@pytest.mark.timeout(60)
def test_next_experiment_runs():
    """§14.6 — finite-difference suggestor returns a Suggestion or None.

    Cheap by design (≤ 2 perturbation runs). Skipped if it can't decide
    a direction (very flat metric).
    """
    s = presets.sbsl_canonical()
    r = s.run()
    out = suggest_next_experiment(s, r, goal="maximize_T")
    if out is not None:
        assert out.rule_id == "next_experiment"
        assert out.suggested_change is not None

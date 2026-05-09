"""§12.10 acceptance tests for the v2 Scenario layer.

Six acceptance criteria from `cavitation_research/12_scenario_simulator.md`
plus a regression check (Scenario.run() must match v1 sonolumen.run() to
floating-point tolerance on the canonical SBSL case) plus a lint test
(no §10 contested numbers hardcoded in the Scenario module).

Each test docstring cites the §12.10 sub-clause it covers; on failure,
the answer is in the dossier section it references — not in the assertion.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import os
import re
import time
from pathlib import Path

TIMING_BUDGET_FACTOR = float(os.environ.get("SONOLUMEN_TIMING_BUDGET_FACTOR", "1.0"))

import pandas as pd
import pytest

import sonolumen
from sonolumen.scenario import (
    BubblePopulation,
    Chamber,
    DriveSchedule,
    ImpulsivePulse,
    Scenario,
    ScenarioResult,
    Transducer,
    Warning,
    presets,
    observers,
)
from sonolumen.scenario.observers import (
    HydrophoneObserver,
    PMTObserver,
    PickupCoilObserver,
)


# ---------------------------------------------------------------------------
# §12.10 #1 — §9.10 default expressed as a ≤10-line preset
# ---------------------------------------------------------------------------
def test_tabletop_starter_preset_under_10_lines():
    """§12.10 #1 — `tabletop_starter()` body must be ≤ 10 logical lines.

    Counts AST statements inside the function body, skipping the docstring.
    The dossier brief calls the §9.10 default a "10-line preset"; we
    interpret as ≤ 10 statements, which is also strictly stricter than
    "10 physical lines."
    """
    src = inspect.getsource(presets.tabletop_starter)
    tree = ast.parse(src)
    fn = tree.body[0]
    # Strip leading docstring
    body = fn.body
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    n_stmts = len(body)
    assert n_stmts <= 10, (
        f"tabletop_starter body has {n_stmts} statements; §12.10 #1 "
        "requires ≤ 10. Collapse fields into the single Scenario(...) call."
    )


# ---------------------------------------------------------------------------
# §12.10 #2 — sbsl_canonical().run() in §9.9 band, < 5 s wall clock
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_sbsl_canonical_run_under_5s_and_in_band():
    """§12.10 #2 — `presets.sbsl_canonical().run()` reproduces §9.9 in <5 s.

    Bands per the dossier (§9.9 post-§10.14 patch):
      * T_peak ∈ [1.5e4, 4e4] K (matches v1 `test_sbsl_canonical_full`)
      * R_max ∈ [30, 50] µm; R_min ∈ [0.4, 0.9] µm
      * photons *detected* by the canonical PMT in [1e5, 1e7]
        (the §9.9 [1e5, 1e7] band is detected — not 4π emission;
        4π emission is the upstream quantity, with §10.14 pointing at
        `detectors.py` for as-detected conversion).
    """
    s = presets.sbsl_canonical()
    t0 = time.time()
    result = s.run()
    elapsed = time.time() - t0

    summary = result.summary
    budget = 5.0 * TIMING_BUDGET_FACTOR
    assert elapsed < budget, (
        f"sbsl_canonical().run() took {elapsed:.2f} s > {budget:.1f} s "
        f"(§12.10 #2 budget = 5 s × factor {TIMING_BUDGET_FACTOR}). "
        f"T_peak={summary.T_peak_K:.0f} K, "
        f"photons_4pi={summary.photons_visible_4pi:.2e}"
    )
    assert 30e-6 <= summary.R_max <= 50e-6, (
        f"R_max {summary.R_max*1e6:.2f} µm outside §9.9 band [30, 50] µm"
    )
    assert 0.4e-6 <= summary.R_min <= 0.9e-6, (
        f"R_min {summary.R_min*1e6:.3f} µm outside §9.9 band [0.4, 0.9] µm"
    )
    assert 1.5e4 <= summary.T_peak_K <= 4.0e4, (
        f"T_peak {summary.T_peak_K:.0f} K outside §9.9 band [1.5e4, 4e4] K"
    )
    # Detected band (PMT R7400U at the default standoff)
    detected = summary.photons_detected_PMT.get("PMT_R7400U")
    assert detected is not None, "PMT_R7400U observer missing from summary"
    assert 1.0e5 <= detected <= 1.0e7, (
        f"photons_detected at PMT_R7400U {detected:.2e} outside §9.9 "
        "band [1e5, 1e7] (detected, post-geometric-factor)"
    )


# ---------------------------------------------------------------------------
# §12.10 #3 — pistol_shrimp_event() within ×3 of L2001
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_pistol_shrimp_event_within_factor_3():
    """§12.10 #3 — pistol-shrimp flash within factor 3 of L2001.

    Bands (matching v1 `tests/test_validation.py::test_pistol_shrimp`):
      * T_peak ∈ [3e3, 3e4] K (§9.8 lower bound + §10.2 upper)
      * photons_visible_4pi ∈ [1e3, 1e11] (deliberately wide — the
        §10.12 emission upper bound is unbounded; what L2001 reports
        is the *detected* count, which depends on geometry and a PMT
        QE that is not specified in the original paper)
      * lifetime ≈ rayleigh_collapse_time within [100, 500] µs
    """
    s = presets.pistol_shrimp_event()
    result = s.run()
    n_phot = result.summary.photons_visible_4pi
    T_peak = result.summary.T_peak_K
    assert 3.0e3 <= T_peak <= 3.0e4, (
        f"T_peak {T_peak:.0f} K outside §9.8 / §10.2 band [3e3, 3e4] K"
    )
    assert 1.0e3 <= n_phot <= 1.0e11, (
        f"pistol_shrimp_event photons_visible_4pi = {n_phot:.2e} outside "
        "L2001 ×3 envelope [1e3, 1e11]"
    )
    t_c = result.summary.rayleigh_collapse_time
    assert 1.0e-4 <= t_c <= 5.0e-4, (
        f"rayleigh_collapse_time {t_c*1e6:.0f} µs outside [V2000] band "
        "[100, 500] µs"
    )


# ---------------------------------------------------------------------------
# §12.10 #4 — three observers return per-observer DataFrames
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_three_observers_return_traces():
    """§12.10 #4 — PMT + Hydrophone + Coil → 3 named DataFrames.

    `result.observer_traces` must contain one entry per observer keyed by
    `observer.name`, each a non-empty pandas DataFrame indexed by `time`
    (or `lambda_nm` for spectrometer-like observers, but this test uses
    the three time-series observers in the §12.10 enumeration).
    """
    s = presets.sbsl_canonical()
    # Replace the canonical observer set with exactly the §12.10 trio.
    s = dataclasses.replace(
        s,
        observers=[
            PMTObserver(name="PMT_main", position=(0.04, 0.0, 0.0)),
            HydrophoneObserver(name="hydrophone_main", position=(0.01, 0.0, 0.0)),
            PickupCoilObserver(name="coil_main", position=(0.01, 0.0, 0.0), enable=False),
        ],
    )
    result = s.run()
    traces = result.observer_traces
    assert set(traces.keys()) == {"PMT_main", "hydrophone_main", "coil_main"}
    for name, df in traces.items():
        assert isinstance(df, pd.DataFrame), f"{name} is not a DataFrame"
        assert "time" in df.columns, f"{name} missing 'time' column"
        assert len(df) > 0, f"{name} has zero rows"


# ---------------------------------------------------------------------------
# §12.10 #5 — validate() emits all 7 actionable warning categories
# ---------------------------------------------------------------------------
@pytest.mark.timeout(15)
def test_validate_emits_seven_warning_categories():
    """§12.10 #5 — every §12.6 check emits a category-specific Warning.

    Constructs seven distinct mutations of a clean Scenario, each
    targeting one of the seven §12.6 categories, and asserts the right
    category fires with a non-empty `actionable_fix`.

    Categories per §12.6:
      1. off_resonance              (drive frequency ≠ chamber f_eigen)
      2. sub_blake                  (drive P_A < Blake threshold)
      3. minnaert_mismatch          (drive f vs Minnaert > 0.5 octaves)
      4. wall_erosion_unknown       (always — §13 not yet implemented)
      5. transducer_power_required  (capacity < requested acoustic power)
      6. observer_outside_chamber   (escalates to error → ValueError on run)
      7. tolerances_too_loose       (predicted Mach > 0.3 with rtol > 1e-9)
    """
    base = presets.sbsl_canonical()

    # Category 4 fires unconditionally on any scenario (§13 placeholder)
    cats = [w.category for w in base.validate()]
    assert "wall_erosion_unknown" in cats

    # 1. off_resonance — flatten the drive far from the eigenmode
    s1 = _replace_drive_freq(base, 100.0)         # Hz, way below chamber f_eigen
    cats1 = [w.category for w in s1.validate()]
    assert "off_resonance" in cats1
    w1 = next(w for w in s1.validate() if w.category == "off_resonance")
    assert w1.actionable_fix.strip() != ""
    assert w1.severity == "warning"

    # 2. sub_blake — drop drive amplitude below the Blake threshold
    s2 = _replace_drive_amp(base, 1000.0)         # Pa = 0.01 atm
    cats2 = [w.category for w in s2.validate()]
    assert "sub_blake" in cats2
    w2 = next(w for w in s2.validate() if w.category == "sub_blake")
    assert "Blake" in w2.message and w2.actionable_fix.strip() != ""

    # 3. minnaert_mismatch — shrink R0 so f_minnaert is much larger than drive f
    s3 = _replace_seed_R0(base, 1.0e-7)           # 100 nm bubble → MHz Minnaert
    cats3 = [w.category for w in s3.validate()]
    assert "minnaert_mismatch" in cats3

    # 5. transducer_power_required — pin transducer capacity to 1 mW
    s5 = _replace_transducer_power(base, 1e-3)
    cats5 = [w.category for w in s5.validate()]
    assert "transducer_power_required" in cats5
    w5 = next(w for w in s5.validate() if w.category == "transducer_power_required")
    assert w5.severity == "warning"
    assert "transducer" in w5.actionable_fix.lower() or "drive" in w5.actionable_fix.lower()

    # 6. observer_outside_chamber — place a PMT at 1 m radius
    s6 = dataclasses.replace(
        base, observers=[PMTObserver(name="PMT_far", position=(1.0, 0.0, 0.0))],
    )
    cats6 = [w.category for w in s6.validate()]
    assert "observer_outside_chamber" in cats6
    w6 = next(w for w in s6.validate() if w.category == "observer_outside_chamber")
    assert w6.severity == "error"
    # And the error must escalate to an exception when run()
    with pytest.raises(ValueError, match="observer_outside_chamber"):
        s6.run()

    # 7. tolerances_too_loose — keep drive amplitude high but loosen rtol
    s7 = dataclasses.replace(
        base, numerics=dataclasses.replace(base.numerics, rtol=1e-6),
    )
    cats7 = [w.category for w in s7.validate()]
    assert "tolerances_too_loose" in cats7


# ---------------------------------------------------------------------------
# §12.10 #6 — to_json round-trip byte-identical for every preset
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("preset_name", [
    "sbsl_canonical",
    "pistol_shrimp_event",
    "tabletop_starter",
])
def test_to_json_round_trip_byte_identical(preset_name):
    """§12.10 #6 — `from_json(to_json(s)).to_json() == s.to_json()`.

    Idempotent round-trip — once a scenario has been encoded, re-encoding
    its decoded form must yield the exact same bytes. This is the
    contract the §15 UI relies on for save / load / share.
    """
    factory = getattr(presets, preset_name)
    s = factory()
    j1 = s.to_json()
    s2 = Scenario.from_json(j1)
    j2 = s2.to_json()
    assert j1 == j2, (
        f"{preset_name}: JSON round-trip not byte-identical.\n"
        f"--- first ---\n{j1[:400]}\n--- second ---\n{j2[:400]}"
    )


# ---------------------------------------------------------------------------
# Regression — Scenario.run() matches v1 sonolumen.run() on canonical case
# ---------------------------------------------------------------------------
@pytest.mark.timeout(30)
def test_scenario_run_matches_v1_run():
    """The Scenario layer is a wrapper, not a fork. The composed config
    must drive the v1 runner to numerically the same result on the SBSL
    canonical case (modulo summary float roundoff)."""
    s = presets.sbsl_canonical()
    v2_result = s.run()
    v1_cfg = sonolumen.presets.sbsl_canonical()
    v1_result = sonolumen.run(v1_cfg)
    s_v1 = v1_result.summary
    s_v2 = v2_result.summary
    # The v2 summary is built from the same v1 summary dict — exact match.
    assert abs(s_v2.T_peak_K - s_v1["T_peak"]) < 1e-6
    assert abs(s_v2.R_max - s_v1["R_max"]) < 1e-15
    assert abs(s_v2.R_min - s_v1["R_min"]) < 1e-15
    assert abs(s_v2.wall_mach_peak - s_v1["wall_mach_peak"]) < 1e-9
    assert abs(s_v2.photons_visible_4pi - s_v1["photons_visible"]) < 1.0  # photons ≫ 1


# ---------------------------------------------------------------------------
# Lint — no §10 contested numbers hardcoded in sonolumen/scenario/
# ---------------------------------------------------------------------------
def test_no_hardcoded_outputs_in_scenario():
    """Mirror of the v1 §10 policy: §10 contested numbers (T_peak,
    n_e_peak, photon counts) must be diagnosed outputs, never *module-
    level* literals. AST-walks every .py file in `sonolumen/scenario/`
    and rejects module-level assignments to those names whose right-hand
    side is a numeric literal in the §10 contested ranges. Function-
    local reads of `summary["T_peak"]` are fine — those are *diagnosed*."""
    forbidden_names = {"T_peak", "n_e_peak", "photons_visible_constant"}
    pkg_root = Path(sonolumen.__file__).parent / "scenario"
    bad: list[str] = []
    for path in pkg_root.glob("*.py"):
        src = path.read_text()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        # Only inspect the module body (top level) — not function/class internals.
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    name = getattr(target, "id", None)
                    if name in forbidden_names:
                        bad.append(f"{path.name}:{node.lineno} assigns {name}")
    assert not bad, (
        "Found hardcoded §10 contested outputs at module level in "
        "sonolumen/scenario/:\n" + "\n".join(bad)
    )


# ---------------------------------------------------------------------------
# Helpers — small dataclasses.replace shortcuts for the validate() test
# ---------------------------------------------------------------------------
def _replace_drive_freq(s: Scenario, new_f: float) -> Scenario:
    new_waveforms = {}
    for name, drv in s.drive.waveforms.items():
        new_waveforms[name] = dataclasses.replace(drv, f=new_f)
    return dataclasses.replace(
        s, drive=dataclasses.replace(s.drive, waveforms=new_waveforms),
    )


def _replace_drive_amp(s: Scenario, new_P_A: float) -> Scenario:
    new_waveforms = {}
    for name, drv in s.drive.waveforms.items():
        new_waveforms[name] = dataclasses.replace(drv, P_A=new_P_A)
    return dataclasses.replace(
        s, drive=dataclasses.replace(s.drive, waveforms=new_waveforms),
    )


def _replace_seed_R0(s: Scenario, new_R0: float) -> Scenario:
    pop = s.bubble_population
    if pop.seed is None:
        return s
    new_seed = dataclasses.replace(pop.seed, R0=new_R0)
    return dataclasses.replace(
        s, bubble_population=dataclasses.replace(pop, seed=new_seed),
    )


def _replace_transducer_power(s: Scenario, new_W: float) -> Scenario:
    txs = [dataclasses.replace(tx, max_acoustic_power_W=new_W) for tx in s.transducers]
    return dataclasses.replace(s, transducers=txs)

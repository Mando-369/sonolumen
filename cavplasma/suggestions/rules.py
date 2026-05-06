"""Suggestion rules R1–R17. §14.3.

Each rule is a function `(scenario, result, regime_internal) →
Optional[Suggestion]`. Returning `None` means the rule did not fire.
The engine collects all firings, sorts by §14.5 priority, and exposes
them on `ScenarioResult.suggestions`.

The rules read `ScenarioSummary` and `result.warnings` for triggers,
and propose concrete `suggested_change` dicts pointing at `Scenario`
field paths (double-underscore notation, matching the v1 sweep API:
e.g. `{"drive__waveforms__pzt4_ring__P_A": 1.98e5}`).
"""

from __future__ import annotations

import math
from typing import Any, Optional

from cavplasma.scenario.types import Suggestion


# ---------------------------------------------------------------------------
# Helper: nominal frequency / amplitude readout for a scenario
# ---------------------------------------------------------------------------
def _drive_freq_amp(scenario: Any) -> tuple[float, float, str]:
    """Return (freq_Hz, P_A_Pa, primary_transducer_name) for the scenario.

    For multi-transducer scenarios returns the *first* transducer's drive;
    suggestions point at that transducer by name. Returns (0, 0, '') if
    no drive is configured.
    """
    waveforms = scenario.drive.waveforms
    if not waveforms:
        return 0.0, 0.0, ""
    name, drv = next(iter(waveforms.items()))
    return drv.f, drv.P_A, name


def _atm(P_Pa: float) -> float:
    return P_Pa / 101_325.0


# ---------------------------------------------------------------------------
# R1 — sub-Blake → increase drive amplitude
# ---------------------------------------------------------------------------
def R1_sub_blake_increase_drive(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    if regime != "sub_blake":
        return None
    f, P_A, tx = _drive_freq_amp(scenario)
    if not tx:
        return None
    new_P = 1.5 * P_A
    return Suggestion(
        severity="warning",
        category="parameter",
        rule_id="R1",
        message=(
            f"Drive amplitude {_atm(P_A):.2f} atm sits below the Blake "
            f"threshold for the current nucleus. Try {_atm(new_P):.2f} atm."
        ),
        rationale="§3.4 — Blake threshold E4. Raising P_A pushes the "
                  "rarefaction below the threshold so the nucleus can grow.",
        dossier_ref="§3.4 / §14.3 R1",
        suggested_change={f"drive__waveforms__{tx}__P_A": new_P},
        expected_effect="cavitation onset",
    )


# ---------------------------------------------------------------------------
# R2 — sub-Blake → smaller nucleus
# ---------------------------------------------------------------------------
def R2_sub_blake_smaller_nucleus(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    if regime != "sub_blake":
        return None
    pop = scenario.bubble_population
    if pop.seed is None:
        return None
    R0 = pop.seed.R0
    new_R0 = R0 / 2.0
    return Suggestion(
        severity="info",
        category="parameter",
        rule_id="R2",
        message=(
            f"Alternative to R1: shrink R₀ from {R0*1e6:.2f} µm to "
            f"{new_R0*1e6:.2f} µm. Smaller nuclei have a lower Blake threshold."
        ),
        rationale="§3.4 — P_B(R₀) decreases with R₀ per E4 surface-tension term.",
        dossier_ref="§3.4 / §14.3 R2",
        suggested_change={"bubble_population__seed__R0": new_R0},
        expected_effect="cavitation onset at current drive",
    )


# ---------------------------------------------------------------------------
# R3 — linear regime → increase P_A toward inertial
# ---------------------------------------------------------------------------
def R3_linear_increase_drive(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    if regime != "linear_oscillation":
        return None
    f, P_A, tx = _drive_freq_amp(scenario)
    if not tx:
        return None
    new_P = 1.5 * P_A
    return Suggestion(
        severity="info",
        category="parameter",
        rule_id="R3",
        message=(
            f"Linear-oscillation regime — drive at {_atm(P_A):.2f} atm not "
            f"strong enough for inertial collapse. Try {_atm(new_P):.2f} atm "
            "to push R_max/R₀ past 5."
        ),
        rationale="§3.7 — empirical thresholds for vigorous cavitation.",
        dossier_ref="§3.7 / §14.3 R3",
        suggested_change={f"drive__waveforms__{tx}__P_A": new_P},
        expected_effect="enters stable_spherical regime",
    )


# ---------------------------------------------------------------------------
# R4 — stable_spherical, low T → switch gas to argon
# ---------------------------------------------------------------------------
def R4_low_T_switch_to_argon(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    if regime != "stable_spherical":
        return None
    if result.summary.T_peak_K >= 8000.0:
        return None
    pop = scenario.bubble_population
    if pop.seed is None:
        return None
    gas = pop.seed.gas_composition or {}
    if gas.get("Ar", 0.0) >= 0.5:
        return None       # already argon-dominated
    return Suggestion(
        severity="info",
        category="parameter",
        rule_id="R4",
        message=(
            f"T_peak {result.summary.T_peak_K:.0f} K is in the low end. "
            "Switching to argon-saturated water typically buys 2× T_peak."
        ),
        rationale="§4.5 — Ar's high γ + monatomic energy partition raises "
                  "compression heating; air's diatomic modes drain it.",
        dossier_ref="§4.5 / §14.3 R4",
        suggested_change={
            "bubble_population__seed__gas_composition": {"Ar": 0.99, "H2O": 0.01},
        },
        expected_effect="T_peak ×2",
    )


# ---------------------------------------------------------------------------
# R5 — stable_spherical, low T → switch liquid to H₂SO₄ + Xe
# ---------------------------------------------------------------------------
def R5_low_T_switch_to_H2SO4(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    if regime != "stable_spherical":
        return None
    if result.summary.T_peak_K >= 12000.0:
        return None
    if scenario.liquid.name == "sulfuric_98":
        return None
    return Suggestion(
        severity="info",
        category="parameter",
        rule_id="R5",
        message=(
            "Switch liquid to 95% H₂SO₄ + Xe to reach T_peak 30–40 kK "
            "(versus the current ≈ "
            f"{result.summary.T_peak_K:.0f} K)."
        ),
        rationale="§4.6 — concentrated sulfuric acid + xenon is the "
                  "published-peak SBSL configuration.",
        dossier_ref="§4.6 / §14.3 R5",
        suggested_change={"liquid__name": "sulfuric_98"},
        expected_effect="T_peak ×3 (at the cost of chemistry burden)",
    )


# ---------------------------------------------------------------------------
# R6 — frequency mismatch with chamber resonance
# ---------------------------------------------------------------------------
def R6_off_resonance(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    for w in result.warnings:
        if w.category == "off_resonance":
            f, P_A, tx = _drive_freq_amp(scenario)
            if not tx:
                return None
            return Suggestion(
                severity="warning",
                category="hardware",
                rule_id="R6",
                message=w.message,
                rationale="§3.2 — off-resonance reduces in-cell P_A by "
                          "factor (1 + (Δf · 2Q/f)²)^½.",
                dossier_ref="§3.2 / §14.3 R6",
                suggested_change=None,   # eigenmode value lives in actionable_fix
                expected_effect="in-cell P_A boosted by ≈ Q at resonance",
            )
    return None


# ---------------------------------------------------------------------------
# R7 — bubble far from Minnaert resonance
# ---------------------------------------------------------------------------
def R7_minnaert_mismatch(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    summary = result.summary
    f_drive, _, tx = _drive_freq_amp(scenario)
    if f_drive <= 0.0 or summary.minnaert_freq <= 0.0:
        return None
    octave_diff = abs(math.log2(f_drive / summary.minnaert_freq))
    if octave_diff <= 0.5:
        return None
    pop = scenario.bubble_population
    if pop.seed is None:
        return None
    # Solve minnaert backwards — approximate Minnaert for ideal gas:
    # f0 ≈ 1/(2π R₀) · sqrt(3 κ p_∞ / ρ)
    rho_L = scenario.liquid.rho
    kappa = pop.seed.kappa
    p_inf = scenario.ambient.p_inf
    target_R0 = math.sqrt(3.0 * kappa * p_inf / rho_L) / (2.0 * math.pi * f_drive)
    return Suggestion(
        severity="info",
        category="parameter",
        rule_id="R7",
        message=(
            f"Drive {f_drive:.0f} Hz vs Minnaert {summary.minnaert_freq:.0f} Hz "
            f"(|Δ| = {octave_diff:.2f} octaves). Try R₀ = {target_R0*1e6:.2f} µm "
            "to put the bubble at linear resonance."
        ),
        rationale="§3.5 E5 — resonant bubble couples maximum energy from the "
                  "drive into the radial mode.",
        dossier_ref="§3.5 / §14.3 R7",
        suggested_change={"bubble_population__seed__R0": target_R0},
        expected_effect="R_max grows; collapse is more violent",
    )


# ---------------------------------------------------------------------------
# R8 — violent regime, near shape-instability boundary
# ---------------------------------------------------------------------------
def R8_violent_near_instability(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    if regime != "violent_spherical":
        return None
    psi = result.summary.parametric_stability_index
    if psi is None or psi < 0.7:
        return None
    f, P_A, tx = _drive_freq_amp(scenario)
    if not tx:
        return None
    new_P = 0.9 * P_A
    return Suggestion(
        severity="warning",
        category="parameter",
        rule_id="R8",
        message=(
            f"parametric_stability_index = {psi:.2f} (above 0.7). "
            f"Drop drive from {_atm(P_A):.2f} to {_atm(new_P):.2f} atm — "
            "over-driving fragments the bubble and suppresses brightness."
        ),
        rationale="§10.5 — over-driving past parametric ≈ 1 fragments the "
                  "bubble into a cloud; brightness drops despite higher T_peak.",
        dossier_ref="§10.5 / §14.3 R8",
        suggested_change={f"drive__waveforms__{tx}__P_A": new_P},
        expected_effect="more reproducible flashes",
    )


# ---------------------------------------------------------------------------
# R9 — shape-unstable regime → smaller R₀
# ---------------------------------------------------------------------------
def R9_shape_unstable_smaller_R0(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    if regime != "shape_unstable":
        return None
    pop = scenario.bubble_population
    if pop.seed is None:
        return None
    R0 = pop.seed.R0
    new_R0 = R0 / 1.5
    return Suggestion(
        severity="warning",
        category="parameter",
        rule_id="R9",
        message=(
            f"Shape-unstable regime. Reduce R₀ from {R0*1e6:.2f} µm to "
            f"{new_R0*1e6:.2f} µm — smaller bubbles are parametrically stable."
        ),
        rationale="§10.5 — parametric stability scales with R_max/R₀; "
                  "shrinking R₀ keeps the index below 1.",
        dossier_ref="§10.5 / §14.3 R9",
        suggested_change={"bubble_population__seed__R0": new_R0},
        expected_effect="regime → stable_spherical",
    )


# ---------------------------------------------------------------------------
# R10 — wall-material erosion warning
# ---------------------------------------------------------------------------
def R10_wall_erosion(
    scenario: Any, result: Any, regime: str,
    *, target_lifetime_hours: float = 100.0,
) -> Optional[Suggestion]:
    erosion = result.erosion
    if erosion is None:
        return None
    T_inc = erosion.T_inc_hours
    if T_inc >= target_lifetime_hours:
        return None
    return Suggestion(
        severity="warning",
        category="hardware",
        rule_id="R10",
        message=(
            f"Predicted incubation time {T_inc:.1f} h is below the "
            f"{target_lifetime_hours:.0f} h target. Severity factor "
            f"S = {erosion.severity:.2e}; switch to a harder wall material."
        ),
        rationale="§13 — current severity factor predicts wall erosion within "
                  "the target horizon. T_inc ∝ 1/S, so harder material extends it.",
        dossier_ref="§13.4 / §14.3 R10",
        suggested_change={"chamber__wall_material__name": "stainless_316"},
        expected_effect="T_inc ↑ by factor of harder-material reference ratio",
    )


# ---------------------------------------------------------------------------
# R11 — transducer overdrive
# ---------------------------------------------------------------------------
def R11_transducer_overdrive(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    if regime != "transducer_limited":
        return None
    return Suggestion(
        severity="error",
        category="hardware",
        rule_id="R11",
        message=(
            "Transducer cannot deliver requested acoustic power. Spec a "
            "bigger transducer, raise chamber Q, or use multiple transducers."
        ),
        rationale="§3.3 / §6.4 — drive amplitude bounded by (P_acoustic, Q, "
                  "geometry); current request exceeds the geometric envelope.",
        dossier_ref="§3.3 / §6.4 / §14.3 R11",
        suggested_change=None,
        expected_effect="achievable in-cell P_A",
    )


# ---------------------------------------------------------------------------
# R12 — over-EOS (Mach > 1) → switch equation
# ---------------------------------------------------------------------------
def R12_over_eos(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    if regime != "over_eos":
        return None
    return Suggestion(
        severity="warning",
        category="numerics",
        rule_id="R12",
        message=(
            f"Wall Mach {result.summary.wall_mach_peak:.2f} exceeds KME "
            "validity (≈ 0.3). Switch to Gilmore + NASG."
        ),
        rationale="§2.3 / §2.4 — KME assumes Ṙ/c < 0.3; Gilmore + NASG is "
                  "the published baseline for super-Mach collapse.",
        dossier_ref="§2.3 / §2.4 / §14.3 R12",
        suggested_change={
            "physics_options__bubble_eq": "gilmore",
            "physics_options__liquid_eos": "nasg",
        },
        expected_effect="T_peak corrected (typically ↓ 5–20%)",
    )


# ---------------------------------------------------------------------------
# R13 — convergence not yet adequate
# ---------------------------------------------------------------------------
def R13_convergence_inadequate(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    conv = result.summary.convergence_diagnostic
    if not isinstance(conv, dict):
        return None
    if conv.get("relative_change", 0.0) <= 0.05:
        return None
    return Suggestion(
        severity="warning",
        category="numerics",
        rule_id="R13",
        message=(
            f"convergence ΔT_peak/T_peak = {conv['relative_change']:.1%} "
            "exceeds 5 %. Tighten tolerances by 10×."
        ),
        rationale="§2.6 — sub-ns collapse resolution requires tight rtol/atol.",
        dossier_ref="§2.6 / §14.3 R13",
        suggested_change={
            "numerics__rtol": scenario.numerics.rtol * 0.1,
            "numerics__atol": scenario.numerics.atol * 0.01,
        },
        expected_effect="ΔT_peak < 5 % across tightening",
    )


# ---------------------------------------------------------------------------
# R14 — observer position outside chamber
# ---------------------------------------------------------------------------
def R14_observer_outside(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    for w in result.warnings:
        if w.category == "observer_outside_chamber":
            return Suggestion(
                severity="error",
                category="hardware",
                rule_id="R14",
                message=w.message,
                rationale="Physical impossibility — observers must be inside "
                          "the chamber.",
                dossier_ref="§14.3 R14",
                suggested_change=None,
                expected_effect="None — fix observer position before re-running",
            )
    return None


# ---------------------------------------------------------------------------
# R15 — bath thermal runaway
# ---------------------------------------------------------------------------
def R15_thermal_runaway(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    th = result.thermal_state
    if th is None or not th.will_boil:
        return None
    return Suggestion(
        severity="warning",
        category="safety",
        rule_id="R15",
        message=(
            f"Predicted steady-state liquid temperature {th.T_steady_K-273.15:.0f} °C "
            "exceeds boiling. Enable cooling jacket, reduce duty cycle, or "
            "lower drive amplitude."
        ),
        rationale="§6.5 / §13.8 — energy balance acoustic-in vs convective-out; "
                  "sub-cooled liquid avoids vapour cavitation taking over.",
        dossier_ref="§6.5 / §13.8 / §14.3 R15",
        suggested_change={"chamber__cooling": "water_jacket"},
        expected_effect="T_liquid stable below boiling",
    )


# ---------------------------------------------------------------------------
# R16 — high humidity / vapour-dominated bubble
# ---------------------------------------------------------------------------
def R16_high_vapour(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    pop = scenario.bubble_population
    if pop.seed is None:
        return None
    gas = pop.seed.gas_composition or {}
    if gas.get("H2O", 0.0) <= 0.5:
        return None
    return Suggestion(
        severity="info",
        category="parameter",
        rule_id="R16",
        message=(
            "Bubble gas is vapour-dominated; vapour-cap quenches T_peak. "
            "Degas the liquid more aggressively or pick a lower-vapour-pressure "
            "fluid."
        ),
        rationale="§4.3 — Storey–Szeri vapour cap reflects endothermic "
                  "dissociation that drains compression energy.",
        dossier_ref="§4.3 / §14.3 R16",
        suggested_change={
            "bubble_population__seed__gas_composition": {"Ar": 0.99, "H2O": 0.01},
        },
        expected_effect="T_peak ×2",
    )


# ---------------------------------------------------------------------------
# R17 — Saha vs Stewart–Pyatt disagreement
# ---------------------------------------------------------------------------
def R17_ideal_saha_at_high_gamma(
    scenario: Any, result: Any, regime: str,
) -> Optional[Suggestion]:
    if scenario.physics_options.ionization_model != "ideal_saha":
        return None
    if result.summary.Gamma_peak < 0.3:
        return None
    return Suggestion(
        severity="warning",
        category="numerics",
        rule_id="R17",
        message=(
            f"Γ_peak = {result.summary.Gamma_peak:.2f} > 0.3 with ideal Saha. "
            "Continuum lowering matters here — switch to Stewart–Pyatt."
        ),
        rationale="§4.2 / §10.4 — ideal Saha overestimates ionization at "
                  "warm-dense-matter conditions where ΔE_cont is significant.",
        dossier_ref="§4.2 / §10.4 / §14.3 R17",
        suggested_change={
            "physics_options__ionization_model": "stewart_pyatt",
        },
        expected_effect="ionization fraction shifts (typically +30–100 %)",
    )


# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------
ALL_RULES = [
    R1_sub_blake_increase_drive,
    R2_sub_blake_smaller_nucleus,
    R3_linear_increase_drive,
    R4_low_T_switch_to_argon,
    R5_low_T_switch_to_H2SO4,
    R6_off_resonance,
    R7_minnaert_mismatch,
    R8_violent_near_instability,
    R9_shape_unstable_smaller_R0,
    R10_wall_erosion,
    R11_transducer_overdrive,
    R12_over_eos,
    R13_convergence_inadequate,
    R14_observer_outside,
    R15_thermal_runaway,
    R16_high_vapour,
    R17_ideal_saha_at_high_gamma,
]

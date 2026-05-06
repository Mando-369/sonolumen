"""Caveat rules C1–C7 — surface §10 uncertainties relevant to the run. §14.4.

Caveats don't change parameters; they remind the user what's unknown.
Each rule returns a `Suggestion` with `category='caveat'` when triggered.
The engine surfaces these in the "Caveats for this run" UI panel.
"""

from __future__ import annotations

from typing import Any, Optional

from cavplasma.scenario.types import Suggestion


# ---------------------------------------------------------------------------
# C1 — peak temperature uncertainty (always-on for plasma runs)
# ---------------------------------------------------------------------------
def C1_T_peak_uncertainty(scenario: Any, result: Any) -> Optional[Suggestion]:
    if result.summary.T_peak_K < 5000.0:
        return None
    band = result.summary.T_peak_band
    return Suggestion(
        severity="info",
        category="caveat",
        rule_id="C1",
        message=(
            f"Literature reports factor 2–3 spread on T_peak in this regime. "
            f"Treat the simulator's T_peak = {result.summary.T_peak_K:.0f} K as "
            f"the centre of a band: [{band[0]:.0f}, {band[1]:.0f}] K."
        ),
        rationale="§10.1 — multi-model spread on SBSL T_peak: Toegel vs full "
                  "PDE, vapour cap on/off, Saha vs Stewart–Pyatt all produce "
                  "different peak temperatures within a factor 2–3 envelope.",
        dossier_ref="§10.1 / §14.4 C1",
    )


# ---------------------------------------------------------------------------
# C2 — pistol-shrimp T_peak weakly constrained
# ---------------------------------------------------------------------------
def C2_pistol_shrimp_weakly_constrained(scenario: Any, result: Any) -> Optional[Suggestion]:
    if scenario.bubble_population.kind != "impulsive":
        return None
    return Suggestion(
        severity="info",
        category="caveat",
        rule_id="C2",
        message=(
            "Pistol-shrimp (impulsive) T_peak is weakly constrained: "
            "[L2001] gives only a lower bound (≈ 5 000 K). Actual peak "
            "could be anywhere in 5–20 kK."
        ),
        rationale="§10.2 — only a single-photon detection-based lower bound "
                  "is published; spectrum-resolved measurements are absent.",
        dossier_ref="§10.2 / §14.4 C2",
    )


# ---------------------------------------------------------------------------
# C3 — gas content drift not modeled
# ---------------------------------------------------------------------------
def C3_gas_drift_not_modeled(scenario: Any, result: Any) -> Optional[Suggestion]:
    drv = scenario.drive
    if not drv.waveforms:
        return None
    f = next(iter(drv.waveforms.values())).f
    t_total = scenario.numerics.t_total
    n_cycles = f * t_total
    if n_cycles < 100:
        return None
    if not scenario.bubble_population.rectified_diffusion:
        return None
    return Suggestion(
        severity="info",
        category="caveat",
        rule_id="C3",
        message=(
            f"Run covers {n_cycles:.0f} acoustic cycles. Bubble gas "
            "composition drifts toward 99 % Ar in air-saturated water — your "
            "initial composition may not be the steady-state composition."
        ),
        rationale="§10.3 — rectified-diffusion + Lohse–Hilgenfeldt mass "
                  "transfer eventually leaves only argon in long-running SBSL.",
        dossier_ref="§10.3 / §14.4 C3",
    )


# ---------------------------------------------------------------------------
# C4 — toroidal cavitation not modeled
# ---------------------------------------------------------------------------
def C4_toroidal_not_modeled(scenario: Any, result: Any) -> Optional[Suggestion]:
    if scenario.bubble_population.kind != "impulsive":
        return None
    return Suggestion(
        severity="info",
        category="caveat",
        rule_id="C4",
        message=(
            "Real impulsive collapses (pistol-shrimp-style) are toroidal. "
            "Spherical simulator over-estimates T_peak by ~30 %."
        ),
        rationale="§10.9 — toroidal collapse modes redistribute kinetic "
                  "energy across azimuthal directions, lowering peak compression.",
        dossier_ref="§10.9 / §14.4 C4",
    )


# ---------------------------------------------------------------------------
# C5 — multi-bubble shielding not modeled (cloud, deferred to v3)
# ---------------------------------------------------------------------------
def C5_multibubble_not_modeled(scenario: Any, result: Any) -> Optional[Suggestion]:
    if scenario.bubble_population.kind != "cloud":
        return None
    return Suggestion(
        severity="warning",
        category="caveat",
        rule_id="C5",
        message=(
            "Multi-bubble cloud: the v2 simulator runs each bubble "
            "independently and does not model bubble–bubble shielding. "
            "The current result is an upper bound on per-bubble brightness."
        ),
        rationale="§10.10 / §12.5 — Bjerknes coupling + crowding suppress "
                  "per-bubble conditions in dense clouds.",
        dossier_ref="§10.10 / §14.4 C5",
    )


# ---------------------------------------------------------------------------
# C6 — Margulis transients are contested
# ---------------------------------------------------------------------------
def C6_margulis_contested(scenario: Any, result: Any) -> Optional[Suggestion]:
    if not scenario.physics_options.include_margulis_transient:
        return None
    return Suggestion(
        severity="warning",
        category="caveat",
        rule_id="C6",
        message=(
            "Margulis transient model is on. The output coil V(t) is "
            "predicted from a parametric model with weak literature support — "
            "treat as 'this much at most'."
        ),
        rationale="§10.6 — Margulis-style electrical transients are reported "
                  "but not consistently replicated; v1 emits a parametric "
                  "rectangular pulse.",
        dossier_ref="§10.6 / §14.4 C6",
    )


# ---------------------------------------------------------------------------
# C7 — Tait EOS limits at extreme compression
# ---------------------------------------------------------------------------
def C7_tait_limits(scenario: Any, result: Any) -> Optional[Suggestion]:
    if scenario.physics_options.liquid_eos != "tait":
        return None
    if result.summary.wall_mach_peak <= 0.5:
        return None
    return Suggestion(
        severity="warning",
        category="caveat",
        rule_id="C7",
        message=(
            f"wall Mach {result.summary.wall_mach_peak:.2f} > 0.5 with Tait EOS. "
            "Tait becomes inaccurate above ~10 GPa — switch to NASG for the "
            "collapse phase if T_peak prediction matters."
        ),
        rationale="§10.11 — Tait EOS is a low-pressure fit; NASG (Le Métayer "
                  "et al. 2004) extends to multi-GPa collapse regimes.",
        dossier_ref="§10.11 / §14.4 C7",
    )


ALL_CAVEATS = [
    C1_T_peak_uncertainty,
    C2_pistol_shrimp_weakly_constrained,
    C3_gas_drift_not_modeled,
    C4_toroidal_not_modeled,
    C5_multibubble_not_modeled,
    C6_margulis_contested,
    C7_tait_limits,
]

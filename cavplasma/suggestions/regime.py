"""Regime classifier. §14.2.

Discrete classification of a `ScenarioResult` into one of:

    sub_blake, linear_oscillation, stable_spherical, violent_spherical,
    shape_unstable, transducer_limited, over_eos, numerical_warning

The thresholds are fixed in §14.2 and are simple comparisons over
`ScenarioSummary` fields. This module is read-only on the Scenario; it
does not mutate the result.
"""

from __future__ import annotations

from typing import Any

from cavplasma.scenario.types import RegimeLabel


# Extra labels beyond §12 RegimeLabel — used internally and exposed in
# Suggestion.message but not on ScenarioSummary.regime (which is a §12
# Literal). When the classifier picks one of these, we map it to the
# closest §12 label and surface the precise label via Suggestion.message.
#
# Note: `linear_oscillation` used to map to `stable_spherical` (public),
# which was misleading — a near-resonance bubble that barely collapses
# is "stable" only in the trivial sense that nothing dramatic happens.
# It now maps to its own public label so the regime card can show
# yellow ("nothing's collapsing — move the drive") instead of green.
_INTERNAL_TO_PUBLIC: dict[str, RegimeLabel] = {
    "sub_blake": "sub_blake",
    "linear_oscillation": "linear_oscillation",
    "stable_spherical": "stable_spherical",
    "violent_spherical": "marginal",
    "shape_unstable": "unstable_likely",
    "transducer_limited": "transducer_limited",
    "over_eos": "marginal",
    "numerical_warning": "marginal",
}


def classify(scenario: Any, result: Any) -> tuple[RegimeLabel, str]:
    """Return (`public_label`, `internal_label`). §14.2.

    `public_label` matches the §12 `RegimeLabel` literal and is what
    `ScenarioResult.summary.regime` is set to. `internal_label` is the
    finer §14.2 classification carried in suggestions for display.
    """
    summary = result.summary
    R_max = summary.R_max
    R_min = summary.R_min
    Mach = summary.wall_mach_peak

    # Ratio R_max / R₀ for inertial test
    seed = scenario._effective_seed()
    R0 = seed.R0 if seed is not None else 1.0
    growth_ratio = R_max / max(R0, 1e-15)

    # Derived sub-Blake test: minimum (p_∞ + p_a) over the integration.
    # If the rarefaction never reaches the Blake threshold the bubble
    # cannot start cavitating. Use min_p_minus_pa exposed by §12.
    sub_blake = False
    if summary.min_p_minus_pa is not None:
        from cavplasma.seed import blake_threshold
        # Blake threshold for the *current* R₀ in the *current* liquid.
        try:
            P_B = blake_threshold(R0, scenario.liquid, scenario.ambient)
        except Exception:
            P_B = 1e6
        # min_p_minus_pa is the minimum of (p_∞ + p_a). For sub-Blake we
        # need: min(p_∞ + p_a) > -P_B  i.e. the rarefaction never digs
        # below ambient by more than the Blake margin. min_p − p_inf < -P_B
        # means we DID exceed the Blake threshold; otherwise sub_blake.
        rarefaction = scenario.ambient.p_inf - summary.min_p_minus_pa
        sub_blake = rarefaction < P_B
    if sub_blake:
        return _INTERNAL_TO_PUBLIC["sub_blake"], "sub_blake"

    # Numerical warning — convergence diagnostic > 5 %
    conv = summary.convergence_diagnostic
    if isinstance(conv, dict) and conv.get("relative_change", 0.0) > 0.05:
        return _INTERNAL_TO_PUBLIC["numerical_warning"], "numerical_warning"

    # over_eos: Mach > 1 means KME has broken down
    if Mach > 1.0:
        return _INTERNAL_TO_PUBLIC["over_eos"], "over_eos"

    # transducer_limited — flagged via the §12 validate() warnings list
    for w in result.warnings:
        if w.category == "transducer_power_required":
            return _INTERNAL_TO_PUBLIC["transducer_limited"], "transducer_limited"

    # shape_unstable: parametric or RT index > 1
    if (summary.parametric_stability_index is not None
            and summary.parametric_stability_index > 1.0):
        return _INTERNAL_TO_PUBLIC["shape_unstable"], "shape_unstable"
    if summary.RT_index is not None and summary.RT_index > 1.0:
        return _INTERNAL_TO_PUBLIC["shape_unstable"], "shape_unstable"

    # T_peak gate — without measurable plasma temperature, the bubble is
    # not really "collapsing" in the sense SBSL asks for. < 1500 K means
    # ambient-ish gas; treat as linear oscillation regardless of the
    # geometric metrics. Real SBSL hits 1.5e4 – 4e4 K.
    T_peak = summary.T_peak_K or 0.0
    if T_peak < 1500.0:
        return _INTERNAL_TO_PUBLIC["linear_oscillation"], "linear_oscillation"

    # linear oscillation: bubble doesn't collapse meaningfully. This catches
    # off-resonance / near-Minnaert sloshing where R_max/R₀ stays small
    # OR the wall barely moves. Used to require Mach < 0.01 (too tight) —
    # widened to 0.05 so configurations like "1 MHz drive on a 26.5 kHz
    # chamber" don't slip into stable_spherical.
    if growth_ratio < 3.0 or Mach < 0.05:
        return _INTERNAL_TO_PUBLIC["linear_oscillation"], "linear_oscillation"

    # violent_spherical: Mach > 0.3 with stable shape
    if Mach > 0.3:
        return _INTERNAL_TO_PUBLIC["violent_spherical"], "violent_spherical"

    # stable_spherical: 5 ≤ R_max/R₀ ≤ 20 AND Mach < 0.3 — textbook SBSL
    if 5.0 <= growth_ratio <= 20.0 and Mach < 0.3:
        return _INTERNAL_TO_PUBLIC["stable_spherical"], "stable_spherical"

    # Fallback: nothing matched cleanly. Don't pretend it's stable —
    # admit uncertainty and route to "marginal". Was previously the
    # source of false-positive green "stable_spherical" labels for
    # weakly-collapsing or near-resonance configurations.
    return _INTERNAL_TO_PUBLIC["over_eos"], "numerical_warning"

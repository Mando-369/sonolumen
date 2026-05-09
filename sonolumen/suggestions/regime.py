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

from sonolumen.scenario.types import RegimeLabel


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

    Use `classify_with_rationale(...)` instead if you want the
    audit-trail list of "why this label" — the UI renders that under
    the regime card.
    """
    public, internal, _rationale = classify_with_rationale(scenario, result)
    return public, internal


def classify_with_rationale(
    scenario: Any, result: Any,
) -> tuple[RegimeLabel, str, list[tuple[str, str, str]]]:
    """Same as `classify` but also returns the per-check audit trail.

    Each rationale entry is `(check_name, status, detail)` where status
    is one of {"FIRED", "PASS", "SKIP"}:

      * "FIRED" — this check matched and produced the final label
      * "PASS"  — check ran but did not match; classifier proceeded
      * "SKIP"  — check did not run (e.g. no data available)

    The first FIRED entry is the one that determined the label. PASS
    entries before it explain why earlier rules did not match. The UI
    renders this as a small expandable explanation under the regime
    chip so the user can audit the assignment.
    """
    summary = result.summary
    R_max = summary.R_max
    Mach = summary.wall_mach_peak

    seed = scenario._effective_seed()
    R0 = seed.R0 if seed is not None else 1.0
    growth_ratio = R_max / max(R0, 1e-15)

    audit: list[tuple[str, str, str]] = []

    def _emit(internal: str, name: str, detail: str
              ) -> tuple[RegimeLabel, str, list[tuple[str, str, str]]]:
        audit.append((name, "FIRED", detail))
        return _INTERNAL_TO_PUBLIC[internal], internal, audit

    # 1. sub-Blake — rarefaction never crosses the Blake threshold.
    if summary.min_p_minus_pa is not None:
        from sonolumen.seed import blake_threshold
        try:
            P_B = blake_threshold(R0, scenario.liquid, scenario.ambient)
        except Exception:                                                # noqa: BLE001
            P_B = 1e6
        rarefaction = scenario.ambient.p_inf - summary.min_p_minus_pa
        sub_blake = rarefaction < P_B
        detail = (f"rarefaction {rarefaction/1e3:.1f} kPa vs Blake "
                  f"threshold {P_B/1e3:.1f} kPa")
        if sub_blake:
            return _emit("sub_blake", "sub-Blake check", detail)
        audit.append(("sub-Blake check", "PASS", detail))
    else:
        audit.append(("sub-Blake check", "SKIP", "min_p_minus_pa not recorded"))

    # 2. Numerical warning — convergence diagnostic > 5 %.
    conv = summary.convergence_diagnostic
    if isinstance(conv, dict):
        rel = conv.get("relative_change", 0.0)
        detail = f"relative_change = {rel:.3f}"
        if rel > 0.05:
            return _emit("numerical_warning", "convergence check", detail)
        audit.append(("convergence check", "PASS", detail))
    else:
        audit.append(("convergence check", "SKIP", "no diagnostic available"))

    # 3. over-EOS — Mach > 1 means KME has broken down.
    detail = f"wall Mach = {Mach:.3f}"
    if Mach > 1.0:
        return _emit("over_eos", "over-EOS check", detail + " (> 1.0)")
    audit.append(("over-EOS check", "PASS", detail + " ≤ 1.0"))

    # 4. transducer_limited — flagged via the §12 validate() warnings list.
    for w in result.warnings:
        if w.category == "transducer_power_required":
            return _emit("transducer_limited", "transducer power",
                         "§12 validate() flagged P_required > capacity")
    audit.append(("transducer power", "PASS", "within transducer capacity"))

    # 5. shape_unstable — parametric or RT index > 1.
    psi = summary.parametric_stability_index
    rti = summary.RT_index
    detail = f"parametric idx = {psi}, RT idx = {rti}"
    if psi is not None and psi > 1.0:
        return _emit("shape_unstable", "shape stability",
                     f"parametric_stability_index = {psi:.2f} > 1")
    if rti is not None and rti > 1.0:
        return _emit("shape_unstable", "shape stability",
                     f"RT_index = {rti:.2f} > 1")
    audit.append(("shape stability", "PASS", detail))

    # 6. T_peak gate — no plasma → not SBSL.
    T_peak = summary.T_peak_K or 0.0
    detail = f"T_peak = {T_peak:.0f} K"
    if T_peak < 1500.0:
        return _emit("linear_oscillation", "T_peak gate",
                     detail + " < 1500 K (no plasma)")
    audit.append(("T_peak gate", "PASS", detail + " ≥ 1500 K"))

    # 7. Linear oscillation gate — geometric and Mach.
    detail = f"R_max/R₀ = {growth_ratio:.2f}, Mach = {Mach:.3f}"
    if growth_ratio < 3.0 or Mach < 0.05:
        return _emit("linear_oscillation", "linear oscillation gate",
                     detail + " (R_max/R₀ < 3 OR Mach < 0.05)")
    audit.append(("linear oscillation gate", "PASS",
                  detail + " (R_max/R₀ ≥ 3 AND Mach ≥ 0.05)"))

    # 8. Violent spherical — Mach > 0.3.
    detail = f"wall Mach = {Mach:.3f}"
    if Mach > 0.3:
        return _emit("violent_spherical", "violence gate",
                     detail + " > 0.3")
    audit.append(("violence gate", "PASS", detail + " ≤ 0.3"))

    # 9. Stable spherical — textbook SBSL band.
    detail = f"R_max/R₀ = {growth_ratio:.2f}, Mach = {Mach:.3f}"
    if 5.0 <= growth_ratio <= 20.0 and Mach < 0.3:
        return _emit("stable_spherical", "SBSL band",
                     detail + " (5 ≤ R_max/R₀ ≤ 20, Mach < 0.3)")
    audit.append(("SBSL band", "PASS",
                  detail + " (outside 5-20 / Mach < 0.3 box)"))

    # Fallback: nothing matched cleanly — admit uncertainty.
    return _emit("over_eos", "fallback",
                 "no rule matched; routing to 'marginal' rather than "
                 "false-positive 'stable_spherical'")

"""`suggest_next_experiment(result, goal)`. §14.6.

Identifies the *most informative* parameter change for a stated user
goal by running a small finite-difference sweep around the last completed
configuration. Default: only sweep two cheap parameters (drive amplitude
and bubble seed R₀); the user can extend the parameter list when they
have time for a wider sweep.

Cheap by design: each perturbation runs the v1 KME at the canonical
tolerances. Three runs ≈ 3 × scenario.run() time.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any, Literal, Optional

from sonolumen.scenario.types import Suggestion


Goal = Literal[
    "maximize_T",
    "maximize_n_e",
    "maximize_photons",
    "maximize_lifetime",
    "minimize_drive",
    "characterize_regime",
]


_GOAL_TO_FIELD: dict[str, str] = {
    "maximize_T": "T_peak_K",
    "maximize_n_e": "n_e_peak",
    "maximize_photons": "photons_visible_4pi",
}


def _read_metric(summary: Any, goal: Goal) -> float:
    field = _GOAL_TO_FIELD.get(goal)
    if field is None:
        return 0.0
    return float(getattr(summary, field, 0.0))


def suggest_next_experiment(
    scenario: Any,
    result: Any,
    goal: Goal = "maximize_T",
    *,
    perturbation: float = 0.1,
    runner: Optional[Any] = None,
) -> Optional[Suggestion]:
    """§14.6 — return a single Suggestion proposing the most informative
    next change. If no perturbation exists or all sensitivities are zero,
    returns None.

    `runner` is for testability — defaults to the live scenario.run().
    """
    if goal in ("maximize_lifetime", "minimize_drive", "characterize_regime"):
        # These goals need §13 erosion + a cost model; v2.0 returns a
        # placeholder Suggestion so the UI surface is stable.
        return Suggestion(
            severity="info",
            category="parameter",
            rule_id="next_experiment",
            message=(
                f"goal={goal!r} not yet implemented in v2.0 next_experiment "
                "engine — see §14.6 roadmap."
            ),
            rationale="§14.6 v3 roadmap.",
            dossier_ref="§14.6",
        )

    waveforms = scenario.drive.waveforms
    if not waveforms:
        return None
    tx_name, drv = next(iter(waveforms.items()))
    pop = scenario.bubble_population
    if pop.seed is None:
        return None

    base = _read_metric(result.summary, goal)
    if base <= 0.0:
        return None

    # Build two perturbations: ΔP_A and ΔR₀.
    perturbations: list[tuple[str, dict, float]] = []
    if drv.P_A > 0.0:
        new_drive = dataclasses.replace(drv, P_A=drv.P_A * (1.0 + perturbation))
        new_waveforms = dict(waveforms)
        new_waveforms[tx_name] = new_drive
        new_drive_schedule = dataclasses.replace(scenario.drive, waveforms=new_waveforms)
        perturbations.append((
            f"drive__waveforms__{tx_name}__P_A",
            {"drive": new_drive_schedule},
            drv.P_A,
        ))
    if pop.seed.R0 > 0.0:
        new_seed = dataclasses.replace(pop.seed, R0=pop.seed.R0 * (1.0 + perturbation))
        new_pop = dataclasses.replace(pop, seed=new_seed)
        perturbations.append((
            "bubble_population__seed__R0",
            {"bubble_population": new_pop},
            pop.seed.R0,
        ))

    if not perturbations:
        return None

    best_field: Optional[str] = None
    best_logsens = 0.0
    best_sign = 0
    best_value = 0.0
    for field, mut, base_value in perturbations:
        try:
            mutated = dataclasses.replace(scenario, **mut)
            new_result = (runner or mutated.run)()
        except Exception:
            continue
        new_metric = _read_metric(new_result.summary, goal)
        if new_metric <= 0.0:
            continue
        # Logarithmic sensitivity ∂log(metric)/∂log(param)
        log_sens = math.log(new_metric / base) / math.log1p(perturbation)
        if abs(log_sens) > abs(best_logsens):
            best_logsens = log_sens
            best_field = field
            best_sign = 1 if log_sens > 0 else -1
            best_value = base_value * (1.0 + best_sign * 0.5 * perturbation)

    if best_field is None:
        return None

    direction = "increase" if best_sign > 0 else "decrease"
    return Suggestion(
        severity="info",
        category="parameter",
        rule_id="next_experiment",
        message=(
            f"To {goal.replace('_', ' ')}, {direction} {best_field} "
            f"(logarithmic sensitivity ≈ {best_logsens:+.2f})."
        ),
        rationale="§14.6 — finite-difference sensitivity over the current "
                  "scenario, picking the parameter with the largest "
                  "|∂log(metric)/∂log(param)|.",
        dossier_ref="§14.6",
        suggested_change={best_field: best_value},
        expected_effect=f"sensitivity {best_logsens:+.2f}",
    )

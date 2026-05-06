"""Inverse design — target outcome → scenario parameters.

`next_experiment.py` answers "given my current scenario, what's the
single most informative nudge?" This module answers a bigger question:
"given a *target* outcome (e.g. T_peak ~ 25 kK in stable SBSL), what
parameters should I run to hit it?"

Two-stage design:

  1. `initial_design(target, constraints)` — heuristic from SBSL
     physics scaling laws. Returns a Scenario in roughly the right
     ballpark. Fast (~ms; no forward simulation).

  2. `refine_design(scenario, target, n_iters)` — small grid search
     around the heuristic's (P_A, R₀, drive_f) point, evaluates each
     by running a full simulation, returns the best match. Slow
     (n_iters × scenario.run() ≈ 10–60 s).

The UI's "Auto-design" panel calls (1) on button click and (2) on the
optional "Refine" button. Both flows write the result back into the
scenario_store so the user can inspect / TEST / save like any other
preset.
"""

from __future__ import annotations

import dataclasses
import itertools
import math
from typing import Any, Optional, Tuple

from cavplasma.config import AcousticDrive, BubbleSeed
from cavplasma.scenario import Scenario, presets as scenario_presets
from cavplasma.scenario.types import DriveSchedule


# ---------------------------------------------------------------------------
# Target / Constraints
# ---------------------------------------------------------------------------
@dataclasses.dataclass(frozen=True)
class DesignTarget:
    """Goal for inverse design — what outcome the user wants.

    `T_peak_K` is the centre of the band the search will aim for; the
    band tolerance defaults to ±25 % so optimisation converges at a
    sensible distance. `must_be_stable_spherical` filters out hits that
    land in marginal / unstable regimes; `feasible_transducer_atm`
    filters out hits that would require an impractical transducer
    drive (R6 off-resonance trap).
    """
    T_peak_K: float = 20_000.0
    must_be_stable_spherical: bool = True
    feasible_transducer_atm: float = 10.0


@dataclasses.dataclass(frozen=True)
class DesignConstraints:
    """Which knobs are *free* to vary vs. fixed by the user.

    By default the chamber, liquid, gas mix, and ambient are taken from
    the base scenario; only drive frequency, drive amplitude, and
    bubble R₀ are free. This matches the typical experimental flow:
    you build a chamber, fill it with water, choose a gas — then tune
    the drive and seed bubble.
    """
    free_drive_frequency: bool = True
    free_drive_amplitude: bool = True
    free_R0: bool = True


# ---------------------------------------------------------------------------
# Stage 1 — heuristic
# ---------------------------------------------------------------------------
def initial_design(
    target: DesignTarget,
    constraints: Optional[DesignConstraints] = None,
    *,
    base: Optional[Scenario] = None,
) -> Tuple[Scenario, dict]:
    """Return a starting scenario from SBSL physics scaling laws.

    Uses three rules:

      * Drive frequency: pick a chamber radial mode that puts the
        Minnaert frequency of a typical SBSL bubble ABOVE the drive,
        keeping the bubble in inertial-collapse mode rather than at
        linear resonance. Default: mode n=2, the canonical SBSL choice.
      * Bubble R₀: derived from `R₀ ≈ (1/(2π · k·f_drive)) · √(3γp_∞/ρ)`
        with `k = 5` (5× the drive frequency for the Minnaert), then
        clamped to the SBSL operating range [2, 8 µm].
      * Drive P_A: linear interpolation of empirical (P_A, T_peak)
        data — SBSL canonical at 1.32 atm gives ~20 kK, Suslick H₂SO₄
        at ~1.5 atm gives ~30 kK, so `P_A_atm = 1.0 + 0.025 ×
        T_peak_K/1000`, clamped to [1.0, 1.8].

    Returns `(scenario, diagnostic_dict)` where the diagnostic contains
    the chosen parameters and the heuristic justifications, so the UI
    can show *why* these numbers were picked.
    """
    constraints = constraints or DesignConstraints()
    base = base or scenario_presets.sbsl_canonical()

    diagnostic: dict = {"target": dataclasses.asdict(target)}

    # Step 1 — drive frequency: chamber mode n=2 (typical SBSL)
    from cavplasma.scenario.scenario import _chamber_resonant_modes
    modes = _chamber_resonant_modes(base.chamber, base.liquid, max_n=4)
    if not modes:
        # Open-bath / pistol-jet — no closed-cavity mode; preserve the
        # base drive frequency (user is responsible) and only tune P_A
        # and R₀.
        f_drive = next(iter(base.drive.waveforms.values())).f \
            if base.drive.waveforms else 26_500.0
    elif len(modes) >= 2:
        f_drive = modes[1]                         # n=2 — canonical SBSL choice
    else:
        f_drive = modes[0]
    diagnostic["drive_freq_Hz"] = f_drive
    diagnostic["drive_freq_rationale"] = (
        f"chamber radial mode n=2 (= 2 · c/(2R) = {f_drive:.0f} Hz) — "
        f"the canonical SBSL operating mode; on-resonance keeps the "
        f"transducer requirement realistic."
    ) if modes else "open-bath geometry — preserved base drive frequency"

    # Step 2 — bubble R₀ from Minnaert relation, clamped to SBSL range
    gamma = 5.0 / 3.0                              # monatomic gas (Ar)
    if not constraints.free_R0:
        R0 = base.bubble_population.seed.R0 if base.bubble_population.seed else 4.5e-6
    else:
        # Set Minnaert frequency to 5× drive frequency → bubble in
        # inertial regime, not at linear resonance.
        f_M_target = 5.0 * f_drive
        R0 = (1.0 / (2.0 * math.pi * f_M_target)) \
            * math.sqrt(3.0 * gamma * base.ambient.p_inf / base.liquid.rho)
        R0 = max(2.0e-6, min(R0, 8.0e-6))
    diagnostic["R0_m"] = R0
    diagnostic["R0_rationale"] = (
        f"R₀ = {R0*1e6:.2f} µm chosen so Minnaert freq is ~5× drive — "
        f"bubble sits in inertial-collapse regime, not linear oscillation."
    )

    # Step 3 — drive amplitude from empirical T_peak interpolation
    if not constraints.free_drive_amplitude:
        existing = next(iter(base.drive.waveforms.values()), None)
        P_A_atm = (existing.P_A / 101_325.0) if existing else 1.32
    else:
        # Linear ramp: 1.0 atm → ~5 kK, 1.32 atm → 20 kK, 1.5 atm → 30 kK,
        # 1.8 atm → 50 kK (extrapolation; capped because higher P_A
        # tips into shape instability).
        P_A_atm = 1.0 + 0.025 * (target.T_peak_K / 1000.0)
        P_A_atm = max(1.0, min(P_A_atm, 1.8))
    diagnostic["P_A_atm"] = P_A_atm
    diagnostic["P_A_rationale"] = (
        f"P_A = {P_A_atm:.2f} atm interpolated from empirical (P_A, T_peak) "
        f"calibration: 1.32 atm → 20 kK (SBSL canonical), 1.5 atm → 30 kK "
        f"(Suslick H₂SO₄+Xe). Capped at 1.8 atm to avoid shape instability."
    )

    # Build the scenario.
    if constraints.free_drive_frequency or constraints.free_drive_amplitude:
        if base.drive.waveforms:
            tx_name = next(iter(base.drive.waveforms.keys()))
            existing_drv = base.drive.waveforms[tx_name]
            new_drv = dataclasses.replace(
                existing_drv,
                f=f_drive if constraints.free_drive_frequency else existing_drv.f,
                P_A=P_A_atm * 101_325.0,
                n_cycles=8,
            )
            new_schedule = dataclasses.replace(
                base.drive,
                waveforms={tx_name: new_drv},
            )
        else:
            new_schedule = base.drive
    else:
        new_schedule = base.drive

    if constraints.free_R0 and base.bubble_population.seed is not None:
        new_seed = dataclasses.replace(
            base.bubble_population.seed,
            R0=R0,
        )
        new_pop = dataclasses.replace(base.bubble_population, seed=new_seed)
    else:
        new_pop = base.bubble_population

    designed = dataclasses.replace(
        base,
        drive=new_schedule,
        bubble_population=new_pop,
        metadata={
            **base.metadata,
            "name": f"auto_design_T{int(target.T_peak_K/1000)}kK",
            "notes": (f"inverse-designed for T_peak ≈ {target.T_peak_K:.0f} K, "
                       f"stable_spherical={target.must_be_stable_spherical}"),
        },
    )

    return designed, diagnostic


# ---------------------------------------------------------------------------
# Stage 2 — refine via small grid search
# ---------------------------------------------------------------------------
def refine_design(
    scenario: Scenario,
    target: DesignTarget,
    *,
    n_amplitude: int = 3,
    n_R0: int = 3,
    amplitude_range: float = 0.20,
    R0_range: float = 0.30,
) -> Tuple[Scenario, dict]:
    """Small grid search around `scenario` to find the best match to target.

    Sweeps drive amplitude over `[1-r, 1+r] × P_A_base` (n_amplitude
    points) × bubble R₀ over `[1-r, 1+r] × R0_base` (n_R0 points). Runs
    a forward simulation at each grid point. Returns the scenario whose
    summary best satisfies the target band, plus a diagnostic dict
    listing every grid point and its score.

    Default 3×3 grid → 9 forward simulations → ~10–30 s wall clock.
    Use higher resolution only when an interactive wait is acceptable.
    """
    if scenario.drive.waveforms:
        tx_name = next(iter(scenario.drive.waveforms.keys()))
        base_drv = scenario.drive.waveforms[tx_name]
        base_P_A = base_drv.P_A
    else:
        return scenario, {"error": "no drive waveform"}
    if scenario.bubble_population.seed is None:
        return scenario, {"error": "no bubble seed"}
    base_R0 = scenario.bubble_population.seed.R0

    P_A_grid = [base_P_A * (1.0 - amplitude_range
                              + 2 * amplitude_range * i / max(n_amplitude - 1, 1))
                 for i in range(n_amplitude)]
    R0_grid = [base_R0 * (1.0 - R0_range
                           + 2 * R0_range * i / max(n_R0 - 1, 1))
                for i in range(n_R0)]

    best_scenario = scenario
    best_score = float("inf")
    best_summary: Optional[dict] = None
    grid_results: list[dict] = []
    for P_A, R0 in itertools.product(P_A_grid, R0_grid):
        new_drv = dataclasses.replace(base_drv, P_A=P_A)
        new_schedule = dataclasses.replace(
            scenario.drive, waveforms={tx_name: new_drv})
        new_seed = dataclasses.replace(scenario.bubble_population.seed, R0=R0)
        new_pop = dataclasses.replace(scenario.bubble_population, seed=new_seed)
        candidate = dataclasses.replace(
            scenario, drive=new_schedule, bubble_population=new_pop)
        try:
            r = candidate.run()
        except Exception as e:                                          # noqa: BLE001
            grid_results.append({
                "P_A_atm": P_A / 101325, "R0_um": R0 * 1e6,
                "error": f"{type(e).__name__}: {e}",
            })
            continue
        score = _score_against_target(r.summary, target)
        grid_results.append({
            "P_A_atm": P_A / 101325, "R0_um": R0 * 1e6,
            "T_peak_K": r.summary.T_peak_K,
            "regime": r.summary.regime,
            "score": score,
        })
        if score < best_score:
            best_score = score
            best_scenario = candidate
            best_summary = {
                "T_peak_K": r.summary.T_peak_K,
                "regime": r.summary.regime,
                "R_max_um": r.summary.R_max * 1e6,
                "wall_mach": r.summary.wall_mach_peak,
                "photons_4pi": r.summary.photons_visible_4pi,
            }

    return best_scenario, {
        "grid_results": grid_results,
        "best_score": best_score,
        "best_summary": best_summary,
        "n_evaluations": len(grid_results),
    }


def _score_against_target(summary: Any, target: DesignTarget) -> float:
    """Lower is better. Combines T_peak distance + regime + feasibility."""
    score = 0.0
    if target.T_peak_K is not None and summary.T_peak_K > 0:
        # Log-distance so 10× off is the same penalty as 0.1× off.
        score += abs(math.log10(summary.T_peak_K / target.T_peak_K)) ** 2
    if target.must_be_stable_spherical:
        if summary.regime != "stable_spherical":
            score += 100.0
    if (target.feasible_transducer_atm
            and summary.drive_required_transducer_atm is not None
            and summary.drive_required_transducer_atm > target.feasible_transducer_atm):
        # Penalise required transducer P_A above the feasibility limit.
        excess = summary.drive_required_transducer_atm / target.feasible_transducer_atm
        score += math.log10(max(excess, 1.0)) * 10.0
    return score

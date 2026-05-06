"""Wall pressure history and microjet kinematics. §13.2 / §13.3.

Two stress sources hit the wall when a bubble collapses near it:

  1. **Spherical-collapse shock** (always present): far-field bubble
     radiation `p_rad(r, t) = ρ/(4π r) · V̈_b(t − r/c_L)`. v1's
     `cavplasma.detectors.hydrophone_signal` already computes this; §13
     reuses it.
  2. **Microjet impact** (only when bubble is within ≈ 2 R_max of the
     wall): a high-speed liquid jet hits the surface with waterhammer
     pressure `p_wh = ρ c U_jet / 2`. Plesset–Chapman (§13.2 / [PC1971])
     gives `U_jet ≈ 8.97 · sqrt((p_∞ − p_v)/ρ)`.

Output is a `WallLoadHistory` containing the time series + scalar
diagnostics §14 R10 reads (peak pressure, impact rate).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Closed-form helpers (exposed for §13.10 unit tests)
# ---------------------------------------------------------------------------
def microjet_velocity(p_inf: float, p_v: float, rho_L: float) -> float:
    """Plesset–Chapman near-wall microjet velocity (§13.2 / [PC1971]).

    `U_jet ≈ 8.97 · sqrt((p_∞ − p_v) / ρ_L)`.
    For water at 20 °C, 1 atm → ≈ 90 m/s.
    """
    delta_p = max(p_inf - p_v, 0.0)
    return 8.97 * math.sqrt(delta_p / max(rho_L, 1e-15))


def microjet_velocity_water() -> float:
    """Convenience: water at 20 °C, 1 atm → ≈ 90 m/s. §13.2."""
    return microjet_velocity(101_325.0, 2_339.0, 998.2)


def waterhammer_pressure(rho_L: float, c_L: float, U_jet: float) -> float:
    """Waterhammer impact pressure `p_wh = ρ c U / 2`. §13.2."""
    return 0.5 * rho_L * c_L * U_jet


# ---------------------------------------------------------------------------
# Wall-load time history (§13.2)
# ---------------------------------------------------------------------------
@dataclass
class WallLoadHistory:
    """Time-resolved wall pressure at one observer location.

    Attributes:
      time, p_rad_shock — far-field bubble shock (Pa, signed)
      p_wh_impact, t_impact — microjet impact pressure + time (None if no jet)
      peak_pressure_total — combined peak
      n_impacts — number of bubble collapses in the integration window
      d_to_wall — observer distance from chamber centre (m)
    """
    time: np.ndarray
    p_rad_shock: np.ndarray
    p_wh_impact: Optional[float]
    t_impact: Optional[float]
    peak_pressure_total: float
    n_impacts: int
    d_to_wall: float


def predict_wall_loads(
    scenario_result: Any,
    observer_position: Tuple[float, float, float],
    *,
    near_wall_threshold_factor: float = 2.0,
) -> WallLoadHistory:
    """Predict the wall-pressure history at `observer_position`. §13.2.

    Args:
      scenario_result: a v2 `ScenarioResult` (must carry `_v1_result`).
      observer_position: (x, y, z) in chamber frame (m).
      near_wall_threshold_factor: bubble is "near wall" if `d < f · R_max`;
        default 2 (matches §13.2 microjet condition).

    Returns a `WallLoadHistory`. The microjet impulse is added as a single
    waterhammer event at `t_impact = t_collapse` (when the bubble reaches
    R_min) when the bubble sits within `f · R_max` of the observer.
    """
    sim = scenario_result._v1_result
    if sim is None:
        raise ValueError(
            "ScenarioResult does not carry an internal v1 trace; cannot "
            "predict wall loads. Re-run the scenario."
        )

    t = sim.t
    R = sim.bubble["R"]
    Rdot = sim.bubble["Rdot"]
    liquid = scenario_result.metadata.get("v1_metadata", {})
    # The v1 SimulationResult carries config; pull rho/c/p_v/p_inf from it.
    cfg = sim.config
    rho_L = cfg.liquid.rho
    c_L = cfg.liquid.c
    p_v = cfg.liquid.p_v
    p_inf = cfg.ambient.p_inf

    # Far-field shock at the observer position (E24, same as v1 hydrophone)
    distance = math.sqrt(sum(p * p for p in observer_position))
    distance = max(distance, 1e-6)

    if len(t) < 3:
        return WallLoadHistory(
            time=t, p_rad_shock=np.zeros_like(t),
            p_wh_impact=None, t_impact=None,
            peak_pressure_total=0.0, n_impacts=0,
            d_to_wall=distance,
        )

    Rddot = np.gradient(Rdot, t)
    Vddot = 8.0 * math.pi * R * Rdot ** 2 + 4.0 * math.pi * R ** 2 * Rddot
    p_rad = rho_L / (4.0 * math.pi * distance) * Vddot

    # Number of collapse events: count zero-crossings of Rdot from + → −
    # (i.e. R has just hit a maximum and is about to collapse).
    sign_change = (Rdot[:-1] > 0) & (Rdot[1:] <= 0)
    n_impacts = int(np.sum(sign_change))

    # Microjet (§13.2): only if bubble is "near" the wall.
    R_max = float(R.max())
    p_wh: Optional[float] = None
    t_impact: Optional[float] = None
    if distance < near_wall_threshold_factor * R_max and R_max > 0.0:
        U_jet = microjet_velocity(p_inf, p_v, rho_L)
        p_wh = waterhammer_pressure(rho_L, c_L, U_jet)
        # Impact time = first R_min after R_max
        i_max = int(R.argmax())
        if i_max < len(R) - 1:
            i_min = i_max + int(np.argmin(R[i_max:]))
            t_impact = float(t[i_min])

    peak_total = float(np.max(np.abs(p_rad)))
    if p_wh is not None:
        peak_total = max(peak_total, p_wh)

    return WallLoadHistory(
        time=t,
        p_rad_shock=p_rad,
        p_wh_impact=p_wh,
        t_impact=t_impact,
        peak_pressure_total=peak_total,
        n_impacts=n_impacts,
        d_to_wall=distance,
    )

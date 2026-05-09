"""ODE integration of the bubble equations.

§2.6 of the dossier: stiff, multi-scale problem. SciPy's `solve_ivp` with
LSODA is the v1 default; Radau/BDF available for extreme stiffness.

Phase B couples the bubble-radius and Toegel-thermal ODEs through a
common state vector. The state spec is provided by `select_equation`
in `bubble_dynamics.py`; this module just plumbs it through `solve_ivp`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
from scipy.integrate import solve_ivp

from sonolumen.config import (
    AcousticDrive,
    AmbientConditions,
    BubbleSeed,
    LiquidProperties,
    NumericsOptions,
    PhysicsOptions,
)


@dataclass
class BubbleTrace:
    """Time-resolved bubble state.

    `state` is a dict mapping name → 1-D array (length = len(t)). Always
    contains 'R' and 'Rdot'; contains 'T_g' if the thermal model is
    Toegel (Phase B). Phase C will append 'p_g' and plasma diagnostics.
    """
    t: np.ndarray
    state: dict
    success: bool
    message: str
    nfev: int
    t_events: list
    state_names: tuple[str, ...] = field(default_factory=tuple)

    @property
    def R(self) -> np.ndarray:
        return self.state["R"]

    @property
    def Rdot(self) -> np.ndarray:
        return self.state["Rdot"]

    @property
    def T_g(self) -> np.ndarray:
        return self.state["T_g"]


def integrate_bubble(
    seed: BubbleSeed,
    liquid: LiquidProperties,
    ambient: AmbientConditions,
    drive: AcousticDrive,
    physics: PhysicsOptions,
    numerics: NumericsOptions,
    t_span: Optional[tuple[float, float]] = None,
    t_eval: Optional[np.ndarray] = None,
    events: Optional[list[Callable]] = None,
) -> BubbleTrace:
    """Integrate the chosen bubble equation over the configured time span."""
    from sonolumen.bubble_dynamics import select_equation, temperature_from_trace

    rhs, spec, info = select_equation(physics, seed, liquid, ambient, drive)
    y0 = spec.initial

    if t_span is None:
        t_span = (0.0, numerics.t_total)
    if t_eval is None and numerics.n_output > 0:
        t_eval = _default_output_grid(t_span, numerics)

    sol = solve_ivp(
        rhs,
        t_span,
        y0,
        method=numerics.integrator,
        rtol=numerics.rtol,
        atol=numerics.atol,
        t_eval=t_eval,
        events=events,
        dense_output=False,
    )

    state: dict[str, np.ndarray] = {}
    for i, name in enumerate(spec.names):
        state[name] = sol.y[i]

    # Convenience post-hoc temperature for the polytropic model.
    if physics.thermal_model == "polytropic" and "T_g" not in state:
        T_post = np.array([
            temperature_from_trace(R, seed, physics)
            for R in state["R"]
        ])
        state["T_g"] = T_post

    return BubbleTrace(
        t=sol.t,
        state=state,
        success=bool(sol.success),
        message=sol.message,
        nfev=int(sol.nfev),
        t_events=list(sol.t_events) if sol.t_events is not None else [],
        state_names=spec.names,
    )


def _default_output_grid(t_span: tuple[float, float], numerics: NumericsOptions) -> np.ndarray:
    """Produce a (log-spaced if requested) grid over t_span."""
    t0, t1 = t_span
    n = numerics.n_output
    if n <= 1:
        return np.array([t0, t1])
    if numerics.output_log_spacing and t0 >= 0.0:
        lin = np.linspace(t0, t1, n // 2)
        eps = max(1e-12, (t1 - t0) * 1e-6)
        log_part = np.geomspace(t0 + eps, t1, n - n // 2)
        grid = np.unique(np.concatenate([lin, log_part]))
        return grid
    return np.linspace(t0, t1, n)

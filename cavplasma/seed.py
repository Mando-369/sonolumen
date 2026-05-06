"""Bubble seed conditions and Blake threshold gating.

§9.4 (initial conditions) and §3.4 (Blake threshold, equation E4).
"""

from __future__ import annotations

import math

from cavplasma.config import AmbientConditions, BubbleSeed, LiquidProperties


def blake_threshold(R0: float, liquid: LiquidProperties, ambient: AmbientConditions) -> float:
    """Quasi-static Blake threshold pressure (E4).

    Returns the magnitude (Pa) of the negative-pressure tension below which
    a gas-filled nucleus of equilibrium radius R0 grows unstably.

    With §9.1 water properties at R₀ = 1 µm: ≈ 1.40 atm (per §3.4 post-patch).
    """
    p_inf = ambient.p_inf
    p_v = liquid.p_v
    sigma = liquid.sigma
    A = p_inf - p_v
    B = 2.0 * sigma / R0
    inner = (2.0 * sigma) / (3.0 * R0 * (A + B))
    return A + (4.0 * sigma / (3.0 * R0)) * math.sqrt(inner)


def equilibrium_gas_pressure(R0: float, liquid: LiquidProperties, ambient: AmbientConditions) -> float:
    """p_g0 = p_∞ + 2σ/R₀ − p_v  (equilibrium gas partial pressure, §2.1)."""
    return ambient.p_inf + 2.0 * liquid.sigma / R0 - liquid.p_v


def initial_state(seed: BubbleSeed) -> tuple[float, float]:
    """Return (R(0), Ṙ(0)). Convenience for solver bootstrapping."""
    return seed.R0, seed.Rdot0


def is_blake_supercritical(
    drive_amplitude: float,
    seed: BubbleSeed,
    liquid: LiquidProperties,
    ambient: AmbientConditions,
) -> bool:
    """Quick check: does the drive amplitude exceed the Blake threshold for
    a quasi-static bubble of radius seed.R0? Used as an informational gate;
    the dynamic threshold (with viscosity / inertia delays) lies above the
    quasi-static one — see §3.4."""
    P_B = blake_threshold(seed.R0, liquid, ambient)
    # Drive amplitude is the peak negative pressure; threshold compared as
    # magnitude of |p_inf - p_min| at the trough.
    return drive_amplitude >= P_B

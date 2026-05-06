"""Lumped-capacity thermal balance for the chamber liquid. §13.8.

Energy balance (E from §13.8):

    ρ V c_p · dT/dt = P_acoustic_dissipated − U A (T − T_ambient)

Integrated to steady state:

    ΔT_steady = P_diss / (U A)
    τ        = ρ V c_p / (U A)

For tabletop SBSL at < 1 W/cm³ liquid this gives ΔT < 5 K and τ ~ minutes.
For industrial 1 kW horns the liquid can boil — §14 R15 reads the output
of this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from cavplasma.material.transducer import _U_W_PER_M2_K  # reuse coefficient table


CoolingMode = Literal["none", "free_air", "forced_air", "water_jacket"]


@dataclass
class ThermalState:
    """Predicted liquid thermal-equilibrium state. §13.8."""
    delta_T_steady_K: float
    time_constant_s: float
    P_acoustic_dissipated_W: float
    will_boil: bool
    T_steady_K: float


def predict_thermal_equilibrium(
    chamber_volume_m3: float,
    liquid_rho: float,
    liquid_cp_J_per_kg_K: float,
    chamber_surface_area_m2: float,
    P_acoustic_W: float,
    *,
    coupling_efficiency: float = 0.6,
    cooling: CoolingMode = "free_air",
    ambient_T_K: float = 293.15,
    boil_T_K: float = 373.15,
) -> ThermalState:
    """Lumped-capacity steady-state liquid temperature. §13.8.

    Args:
      chamber_volume_m3: liquid volume in the chamber.
      liquid_rho: density (kg/m³).
      liquid_cp_J_per_kg_K: specific heat capacity.
      chamber_surface_area_m2: heat-loss area (≈ chamber outer surface).
      P_acoustic_W: input *electrical* power that becomes acoustic at the
        face; acoustic-to-thermal conversion is then governed by
        coupling_efficiency.
      coupling_efficiency: fraction electrical → useful acoustic;
        the rest goes to dissipation in the liquid.
      cooling: heat-extraction mode (`'none'`, `'free_air'`,
        `'forced_air'`, `'water_jacket'`).
      ambient_T_K: surrounding air or coolant temperature.
      boil_T_K: liquid boiling point at ambient pressure.

    Returns a `ThermalState`; if the predicted steady-state liquid
    temperature exceeds `boil_T_K`, `will_boil = True` and §14 R15 fires.
    """
    if not (0.0 < coupling_efficiency <= 1.0):
        raise ValueError("coupling_efficiency must be in (0, 1]")
    P_dissipated = max(0.0, P_acoustic_W * (1.0 - coupling_efficiency)
                       + P_acoustic_W * 0.05)   # baseline 5 % residual loss
    U = _U_W_PER_M2_K.get(cooling, _U_W_PER_M2_K["free_air"])
    UA = U * max(chamber_surface_area_m2, 1e-9)

    delta_T = P_dissipated / max(UA, 1e-9)
    T_steady = ambient_T_K + delta_T

    rho_V_cp = liquid_rho * chamber_volume_m3 * liquid_cp_J_per_kg_K
    tau = rho_V_cp / max(UA, 1e-9)

    return ThermalState(
        delta_T_steady_K=delta_T,
        time_constant_s=tau,
        P_acoustic_dissipated_W=P_dissipated,
        will_boil=T_steady >= boil_T_K,
        T_steady_K=T_steady,
    )

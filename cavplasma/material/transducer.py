"""Transducer lifetime under sustained drive. §13.6.

Two failure modes per §13.6:

  1. **Cavitation pitting of the window** — handled by `predict_erosion_rate`
     when an observer is placed on the transducer face.
  2. **Piezo depoling under high mechanical Q** — internal heating from
     I²R + dielectric loss; lifetime drops sharply once the steady-state
     temperature approaches the Curie point.

This module models #2: input the piezo material grade, drive duty cycle,
acoustic loading, and cooling assumption; output a predicted lifetime
in hours.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Optional

from cavplasma.material.materials import PiezoMaterial, piezo


CoolingMode = Literal["none", "free_air", "forced_air", "water_jacket"]


# Heat-transfer coefficient catalog (§13.6 / §13.8 ranges)
_U_W_PER_M2_K: dict[str, float] = {
    "none":           5.0,        # passive radiation only
    "free_air":       10.0,       # free convection
    "forced_air":     50.0,
    "water_jacket":   1000.0,
}


@dataclass
class TransducerLifetime:
    """Predicted piezo lifetime under steady drive. §13.6."""
    grade: str
    duty_cycle: float
    cooling: CoolingMode
    average_power_W_per_cm2: float
    steady_state_T_K: float
    margin_to_Curie_K: float
    lifetime_hours: float
    notes: str = ""


def predict_transducer_lifetime(
    grade: str,
    drive_power_W_per_cm2: float,
    *,
    duty_cycle: float = 1.0,
    cooling: CoolingMode = "free_air",
    ambient_T_K: float = 293.15,
    impedance_matched: bool = True,
) -> TransducerLifetime:
    """Predict piezo lifetime in hours. §13.6.

    Args:
      grade: piezo material name, see `materials.list_piezo()`.
      drive_power_W_per_cm2: peak acoustic power density at the face.
      duty_cycle: fraction of time the drive is on (0–1).
      cooling: heat-extraction mode (`'none'`, `'free_air'`,
        `'forced_air'`, `'water_jacket'`).
      ambient_T_K: surrounding fluid / air temperature.
      impedance_matched: True if the transducer is loaded into matched
        impedance (no extra reflection heating). False multiplies the
        dissipated power by 1.5.

    Lifetime model (heuristic, §13.6 anchored):
      * average power = peak × duty_cycle
      * dissipated heat = average power × (1 − coupling_efficiency)
        + impedance-mismatch penalty
      * steady-state ΔT from a thin-film convection model
      * if T_steady > 0.7 × T_curie → lifetime ≪ 100 h (depoling)
      * otherwise: 50–500 h band per [APC, M2018], scaled by margin
    """
    p = piezo(grade)
    if not (0.0 <= duty_cycle <= 1.0):
        raise ValueError(f"duty_cycle {duty_cycle} not in [0, 1]")
    avg_power = drive_power_W_per_cm2 * duty_cycle

    # Effective coupling — dielectric loss + impedance mismatch.
    coupling = 1.0 - p.dielectric_loss
    if not impedance_matched:
        coupling *= 0.7
    P_dissipated_W_per_cm2 = avg_power * (1.0 - coupling)

    # Convert to W/m² for heat-transfer math
    P_W_per_m2 = P_dissipated_W_per_cm2 * 1e4
    U = _U_W_PER_M2_K.get(cooling, _U_W_PER_M2_K["free_air"])
    delta_T = P_W_per_m2 / U                      # ΔT = q / (U·A) per unit area
    T_steady = ambient_T_K + delta_T
    margin = p.T_curie_K - T_steady

    notes = ""
    if T_steady >= p.T_curie_K:
        # Above Curie: depoling immediate; lifetime hours.
        lifetime = 1.0
        notes = "T_steady ≥ T_curie — immediate depoling"
    elif T_steady >= 0.7 * p.T_curie_K:
        # Within 30 % of Curie: rapid degradation
        lifetime = 50.0 * (margin / (0.3 * p.T_curie_K))
        notes = "running near T_curie — rapid depoling"
    else:
        # Healthy regime: §13.6 reports 50–500 h at 50 % drive.
        # Anchor the lifetime to fraction-of-max-rated-power.
        rating = p.max_avg_power_W_per_cm2
        if avg_power < 1e-12:
            lifetime = 1e5
            notes = "negligible drive"
        else:
            rel = avg_power / rating
            # Inverse-cubic scaling per §13.6: lifetime ~ rating³ / load³
            lifetime = 500.0 / max(rel ** 3, 1e-3)
            lifetime = min(lifetime, 1e5)
            notes = "healthy"

    return TransducerLifetime(
        grade=grade,
        duty_cycle=duty_cycle,
        cooling=cooling,
        average_power_W_per_cm2=avg_power,
        steady_state_T_K=T_steady,
        margin_to_Curie_K=margin,
        lifetime_hours=lifetime,
        notes=notes,
    )

"""Erosion rate prediction. §13.3 / §13.4 / §13.5.

Three sub-models:

  * `single_event_pit_volume(p_wh, material, A_jet)` — §13.3, Plesset–
    Brennen formula for a hemispherical pit. Threshold: `p_wh > p_Y` or
    no pit.
  * `severity_factor(p_wall_peak, n_impacts, p_ref, n_ref, n_exp)` —
    §13.5 ASTM-relative severity scaling.
  * `predict_erosion_rate(wall_loads, material, drive_freq)` —
    `ErosionPrediction` with incubation time + steady MDPR + lifetime.

Reference erosion rates come from `materials.astm_reference()`. The
simulator scales the calibrated ASTM numbers by the predicted severity
factor, per §13.4 / §13.5.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from sonolumen.material.materials import astm_reference
from sonolumen.material.wall_loads import WallLoadHistory
from sonolumen.scenario.types import WallMaterial


# ---------------------------------------------------------------------------
# §13.3 — single-event pit volume
# ---------------------------------------------------------------------------
def single_event_pit_volume(
    p_wh: float, material: WallMaterial, A_jet: float = 1e-9,
) -> float:
    """Hemispherical pit volume from one waterhammer impact. §13.3.

    `V_pit ≈ (p_wh − p_Y)² · A_jet^(3/2) / H²` if p_wh > p_Y, else 0.
    A_jet defaults to 1 nm² (~ 30 µm jet diameter) per [PC1971].
    """
    if p_wh <= material.p_Y_dynamic:
        return 0.0
    delta_p = p_wh - material.p_Y_dynamic
    H = max(material.Vickers_H, 1.0)
    return (delta_p ** 2) * (A_jet ** 1.5) / (H ** 2)


# ---------------------------------------------------------------------------
# §13.5 — severity factor (ASTM-relative)
# ---------------------------------------------------------------------------
ASTM_REF_PRESSURE_PA = 5.0e7        # 50 MPa typical ASTM peak shock
ASTM_REF_IMPACT_RATE = 1.0e7         # /s/m² effective impacts in vibratory rig


def severity_factor(
    p_wall_peak: float,
    n_impacts: int,
    drive_freq: float,
    *,
    p_ref: float = ASTM_REF_PRESSURE_PA,
    N_ref: float = ASTM_REF_IMPACT_RATE,
    n_exp: float = 3.0,
) -> float:
    """ASTM-relative severity factor S. §13.5.

    `S = (p_peak / p_ref)^n · (N_eff / N_ref)`. n_exp ≈ 2.5–3.5 (default
    3 = plastic regime). N_eff scales with the drive frequency: at
    25 kHz with one bubble per cycle, `N_eff ≈ f` (per m² of cell wall).
    """
    p_term = (max(p_wall_peak, 0.0) / p_ref) ** n_exp
    # Effective impact rate per unit area: drive_freq × n_impacts / (4π R_chamber²)
    # — but observer-position dependent. Use n_impacts × drive_freq as a
    # scenario-scale proxy; the absolute number cancels with N_ref's units.
    N_eff = max(n_impacts, 1) * max(drive_freq, 1.0)
    n_term = N_eff / N_ref
    return p_term * n_term


# ---------------------------------------------------------------------------
# §13.4 — incubation + steady MDPR + lifetime prediction
# ---------------------------------------------------------------------------
@dataclass
class ErosionPrediction:
    """§13 erosion summary attached to `ScenarioResult.erosion`.

    Fields:
      severity                  — §13.5 severity factor S (dimensionless)
      T_inc_hours               — incubation time before mass loss
      MDPR_um_per_h             — steady mean depth of penetration rate
      lifetime_hours            — heuristic lifetime to wear through
                                  `wall_thickness` (None if MDPR is 0)
      sub_yield                 — True if no waterhammer impact reached
                                  the dynamic yield (no pit will form)
      single_event_pit_volume_m3— pit volume per impact (or 0 if sub-yield)
      material_name             — wall material name for traceability
      observer_distance_m       — observer→chamber-centre distance used
    """
    severity: float
    T_inc_hours: float
    MDPR_um_per_h: float
    lifetime_hours: Optional[float]
    sub_yield: bool
    single_event_pit_volume_m3: float
    material_name: str
    observer_distance_m: float


def predict_erosion_rate(
    wall_loads: WallLoadHistory,
    material: WallMaterial,
    drive_freq: float,
    wall_thickness_m: Optional[float] = None,
) -> ErosionPrediction:
    """Predict erosion T_inc + steady MDPR for the given wall loads.

    Scales the ASTM reference numbers from §13.4.2 by the severity
    factor §13.5: T_inc ∝ 1/S, MDPR ∝ S. Lifetime is the time to erode
    `wall_thickness_m` at the steady MDPR.
    """
    p_peak = wall_loads.peak_pressure_total
    if wall_loads.p_wh_impact is not None:
        p_peak = max(p_peak, wall_loads.p_wh_impact)
    n_impacts = max(wall_loads.n_impacts, 1)

    S = severity_factor(p_peak, n_impacts, drive_freq)
    ref = astm_reference(material.name)
    T_inc_ref = math.sqrt(ref.T_inc_lo_h * ref.T_inc_hi_h)            # geometric mean
    MDPR_ref = math.sqrt(ref.MDPR_lo_um_per_h * ref.MDPR_hi_um_per_h)

    # T_inc ∝ 1/S; MDPR ∝ S (§13.4 / §13.5 plastic-regime scaling).
    if S <= 0.0:
        T_inc_h = float("inf")
        MDPR = 0.0
    else:
        T_inc_h = T_inc_ref / S
        MDPR = MDPR_ref * S

    pit = 0.0
    sub_yield = True
    if wall_loads.p_wh_impact is not None:
        pit = single_event_pit_volume(wall_loads.p_wh_impact, material)
        sub_yield = wall_loads.p_wh_impact <= material.p_Y_dynamic

    lifetime: Optional[float] = None
    if MDPR > 0.0 and wall_thickness_m is not None and wall_thickness_m > 0.0:
        # MDPR is µm/h; thickness in m → convert.
        lifetime = (wall_thickness_m * 1e6) / MDPR
    elif MDPR == 0.0:
        lifetime = None  # effectively infinite — distinguish from "unknown"

    return ErosionPrediction(
        severity=S,
        T_inc_hours=T_inc_h,
        MDPR_um_per_h=MDPR,
        lifetime_hours=lifetime,
        sub_yield=sub_yield,
        single_event_pit_volume_m3=pit,
        material_name=material.name,
        observer_distance_m=wall_loads.d_to_wall,
    )

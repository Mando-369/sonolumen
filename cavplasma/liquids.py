"""Liquid presets. §9.1 / §3.6 of the dossier supply the numbers.

Also provides T/S/p correction helpers — see §17, §18, §19 of the
research dossier (Q4/Q11/Q12). The catalog `c` for each liquid is
calibrated at T = 20 °C, p = 1 atm; for sweeps in `T_inf` and
`p_inf`, use `corrected_sound_speed_for(...)` to get a `c` that
respects IAPWS (pure water) / Mackenzie (seawater) plus a Tait
pressure correction. The correction is *additive relative to
calibration*, so at the catalog reference conditions it returns
the catalog value exactly — this keeps the v1↔v2 regression test
(SBSL canonical) bit-identical and only modifies behaviour when
the user actually leaves the surface / room-temperature corner.
"""

from __future__ import annotations

import dataclasses
import math
from typing import TYPE_CHECKING

from cavplasma.config import LiquidProperties

if TYPE_CHECKING:
    from cavplasma.config import AmbientConditions


# Catalog calibration conditions (where the catalog `c` value is
# defined). All sound-speed corrections are deltas from this point.
_CALIBRATION_T_C = 20.0
_CALIBRATION_P_PA = 101_325.0


_PRESETS: dict[str, LiquidProperties] = {
    "water": LiquidProperties(
        name="water",
        rho=998.2, c=1482.0, mu=1.002e-3,
        sigma=7.28e-2, p_v=2339.0,
        B_tait=3.05e8, n_tait=7.15,
        beta_BoverA=3.5, alpha_dB_cm_MHz2=0.025,
    ),
    # §3.6: seawater (35 ‰), §9.8 default for pistol-shrimp benchmark
    "seawater": LiquidProperties(
        name="seawater",
        rho=1025.0, c=1530.0, mu=1.08e-3,
        sigma=7.50e-2, p_v=2300.0,
        B_tait=3.05e8, n_tait=7.15,         # Tait values not separately tabulated; reuse water
        beta_BoverA=3.5, alpha_dB_cm_MHz2=0.025,
    ),
    # §3.6 / §4.6: glycerin
    "glycerin": LiquidProperties(
        name="glycerin",
        rho=1261.0, c=1904.0, mu=1.412,
        sigma=6.34e-2, p_v=0.13,
        B_tait=3.5e8, n_tait=7.0,
        beta_BoverA=5.4, alpha_dB_cm_MHz2=0.6,
    ),
    # §4.6: 85 % H2SO4
    "sulfuric_98": LiquidProperties(
        name="sulfuric_98",
        rho=1840.0, c=1430.0, mu=24.0e-3,
        sigma=5.5e-2, p_v=1.0,
        B_tait=3.0e8, n_tait=7.0,
        beta_BoverA=4.5, alpha_dB_cm_MHz2=0.1,
    ),
    # §4.6: silicone oil 100 cSt
    "silicone_oil_100cSt": LiquidProperties(
        name="silicone_oil_100cSt",
        rho=965.0, c=980.0, mu=0.097,
        sigma=2.09e-2, p_v=1.0,
        B_tait=2.5e8, n_tait=7.0,
        beta_BoverA=6.5, alpha_dB_cm_MHz2=1.0,
    ),
}


def preset(name: str) -> LiquidProperties:
    """Look up a named preset. Returns a frozen LiquidProperties."""
    if name not in _PRESETS:
        raise KeyError(
            f"unknown liquid preset {name!r}; available: {sorted(_PRESETS)}"
        )
    return _PRESETS[name]


def available() -> list[str]:
    return sorted(_PRESETS)


# ---------------------------------------------------------------------------
# T / S / p correction for the liquid's bulk sound speed.
#
# Implements the combined Q4/Q11/Q12 patch from the research dossier
# (§17 sound speed, §18 water anomalies, §19 sound speed vs T).
#
# Pure water: IAPWS-95-derived polynomial (Lubbers & Graaff 1998),
#             with non-monotonic behaviour past 74 °C. Pressure
#             correction added via the same Tait integration the
#             KME / Gilmore solvers use — `c²(p) = c_0² + (n-1) H`.
#
# Seawater:   Mackenzie (1981) full empirical formula in (T, S, z).
#             Pressure → equivalent depth via z = (p − p_atm) / (ρ g).
#
# The function returns the **absolute** sound speed at the given
# conditions. To preserve catalog backwards-compatibility, the public
# entry `corrected_sound_speed_for(liquid, ambient)` returns a delta-
# corrected `c` (catalog value plus the difference from calibration),
# so SBSL canonical (20 °C, 1 atm, water) is bit-identical to v1.
# ---------------------------------------------------------------------------
def _iapws_water_sound_speed_at_1atm(T_C: float) -> float:
    """Pure water sound speed at 1 atm vs T (°C). Lubbers & Graaff 1998.

    Polynomial fit to the IAPWS-95 reference equation, valid 0–95 °C
    to better than 0.05 m/s. Captures the 74 °C maximum (§19).
    """
    T = T_C
    return (1402.385
            + 5.038813 * T
            - 5.799136e-2 * T ** 2
            + 3.287156e-4 * T ** 3
            - 1.398845e-6 * T ** 4
            + 2.787860e-9 * T ** 5)


def _mackenzie_seawater_sound_speed(T_C: float, S_ppt: float, z_m: float) -> float:
    """Seawater sound speed (m/s). Mackenzie 1981, full empirical form.

    Standard oceanographic reference; valid for typical ocean ranges
    (T 0–30 °C, S 25–40 ppt, z 0–8000 m). For deeper water (Mariana
    abyssal) the formula extrapolates gracefully but with a few-m/s
    error — adequate for our pattern-finding purposes.
    """
    T = T_C
    S = S_ppt
    z = z_m
    return (1448.96
            + 4.591 * T - 0.05304 * T * T + 2.374e-4 * T ** 3
            + 1.340 * (S - 35)
            + 0.0163 * z + 1.675e-7 * z * z
            - 0.01025 * T * (S - 35)
            - 7.139e-13 * T * z ** 3)


def _tait_pressure_correction(c_at_pref: float, p_Pa: float, p_ref_Pa: float,
                               liquid: LiquidProperties) -> float:
    """Lift `c_at_pref` from `p_ref_Pa` to `p_Pa` via the Tait EOS.

    Uses the same `c²(p) = c_0² + (n − 1) H(p_ref → p)` relation as
    `bubble_dynamics.tait_sound_speed`, so the bulk-liquid baseline
    is consistent with the wall sound speed during collapse.
    """
    n = liquid.n_tait
    B = liquid.B_tait
    rho_0 = liquid.rho
    if abs(p_Pa - p_ref_Pa) < 1.0:
        return c_at_pref
    pre = (n / (n - 1.0)) / rho_0 * (p_ref_Pa + B) ** (1.0 / n)
    H = pre * ((p_Pa + B) ** ((n - 1.0) / n)
               - (p_ref_Pa + B) ** ((n - 1.0) / n))
    val = c_at_pref * c_at_pref + (n - 1.0) * H
    return math.sqrt(max(val, 1.0))


def absolute_sound_speed(liquid: LiquidProperties, T_K: float, p_Pa: float) -> float:
    """Return the absolute T/S/p-corrected sound speed for `liquid`.

    Routes through IAPWS for fresh water and Mackenzie for seawater.
    For other liquids (glycerin, sulfuric, silicone oil) the catalog
    `c` is used as the temperature-independent baseline and only the
    Tait pressure correction is applied — these liquids don't have
    a tabulated empirical formula but the Tait part is still right.
    """
    T_C = T_K - 273.15
    name = liquid.name

    if name == "water":
        c_at_1atm = _iapws_water_sound_speed_at_1atm(T_C)
        return _tait_pressure_correction(c_at_1atm, p_Pa, _CALIBRATION_P_PA, liquid)

    if name == "seawater":
        # Mackenzie includes its own depth term, so we don't double-count
        # by stacking the Tait pressure correction on top — instead use
        # the equivalent-depth conversion p_Pa ↔ z_m via hydrostatic.
        z_m = max(0.0, (p_Pa - _CALIBRATION_P_PA) / (liquid.rho * 9.81))
        return _mackenzie_seawater_sound_speed(T_C, 35.0, z_m)

    # Other liquids: only the Tait pressure correction is applied.
    return _tait_pressure_correction(liquid.c, p_Pa, _CALIBRATION_P_PA, liquid)


def corrected_sound_speed_for(liquid: LiquidProperties,
                               ambient: "AmbientConditions") -> float:
    """Return a sound speed for `liquid` corrected to `ambient` conditions.

    Implements the **delta-from-calibration** scheme: the result is
    `liquid.c + (c_abs(T, p) − c_abs(T_cal, p_cal))`, so when the
    user is at calibration conditions (20 °C, 1 atm) the catalog
    value passes through unchanged. This keeps v1↔v2 regression
    bit-identical and only modifies behaviour when the user has
    actually moved off the calibration corner.
    """
    T_K = ambient.T_inf
    p_Pa = ambient.p_inf
    T_K_cal = _CALIBRATION_T_C + 273.15

    c_at_user = absolute_sound_speed(liquid, T_K, p_Pa)
    c_at_cal = absolute_sound_speed(liquid, T_K_cal, _CALIBRATION_P_PA)
    delta = c_at_user - c_at_cal
    return liquid.c + delta


def liquid_with_corrections(liquid: LiquidProperties,
                              ambient: "AmbientConditions") -> LiquidProperties:
    """Return a `LiquidProperties` with `c` corrected for the ambient.

    Thin wrapper around `corrected_sound_speed_for` that does the
    `dataclasses.replace`. v2 `Scenario._compose_simulation_config`
    calls this before handing the SimulationConfig to the v1 runner.
    """
    c_corr = corrected_sound_speed_for(liquid, ambient)
    return dataclasses.replace(liquid, c=c_corr)

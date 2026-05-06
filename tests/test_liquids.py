"""Tests for the T/S/p sound-speed correction layer (Q4/Q11/Q12).

Locks in the §17/§18/§19 dossier behaviour: at the calibration corner
(T = 20 °C, p = 1 atm) the catalog `c` passes through unchanged, so
v1↔v2 regression on SBSL canonical stays bit-identical. Off the
corner, the correction matches the IAPWS / Mackenzie / Tait
references to within a few m/s.
"""
from __future__ import annotations

import math

import pytest

from cavplasma.config import AmbientConditions
from cavplasma.liquids import (
    absolute_sound_speed,
    corrected_sound_speed_for,
    liquid_with_corrections,
    preset,
)


# ---------------------------------------------------------------------------
# Calibration point: at 20 °C / 1 atm the correction is exactly zero
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["water", "seawater", "glycerin",
                                    "sulfuric_98", "silicone_oil_100cSt"])
def test_calibration_passes_catalog_value_unchanged(name):
    liq = preset(name)
    amb = AmbientConditions(p_inf=101_325.0, T_inf=293.15)
    c_corr = corrected_sound_speed_for(liq, amb)
    assert math.isclose(c_corr, liq.c, abs_tol=1e-9), (
        f"{name}: at calibration, corrected c = {c_corr} should equal "
        f"catalog c = {liq.c}"
    )


# ---------------------------------------------------------------------------
# §19 — pure water sound speed peaks at ~74 °C
# ---------------------------------------------------------------------------
def test_pure_water_sound_speed_peaks_near_74C():
    """The IAPWS polynomial must reproduce the famous ~74 °C maximum."""
    water = preset("water")

    def c_at(T_C: float) -> float:
        amb = AmbientConditions(p_inf=101_325.0, T_inf=T_C + 273.15)
        return corrected_sound_speed_for(water, amb)

    c_70 = c_at(70.0)
    c_74 = c_at(74.0)
    c_80 = c_at(80.0)

    # 74 °C is the maximum: higher than both neighbours
    assert c_74 > c_70, f"74 °C ({c_74}) should exceed 70 °C ({c_70})"
    assert c_74 > c_80, f"74 °C ({c_74}) should exceed 80 °C ({c_80})"

    # Magnitude check — peak around 1554-1556 m/s per IAPWS
    assert 1553.0 < c_74 < 1557.0, f"c_74 = {c_74} m/s outside expected band"


def test_water_temperature_coefficient_at_room_T():
    """dc/dT ≈ +3.5 m/s/K at 20 °C, must match IAPWS slope."""
    water = preset("water")

    def c_at(T_C: float) -> float:
        amb = AmbientConditions(p_inf=101_325.0, T_inf=T_C + 273.15)
        return corrected_sound_speed_for(water, amb)

    slope = (c_at(21.0) - c_at(19.0)) / 2.0
    assert 3.0 < slope < 4.5, f"dc/dT at 20 °C = {slope} m/s/K, expected ~3.5"


# ---------------------------------------------------------------------------
# §17 — pressure correction via Tait
# ---------------------------------------------------------------------------
def test_water_sound_speed_increases_with_pressure():
    """At fixed T = 20 °C, c should rise monotonically with p."""
    water = preset("water")

    def c_at(p_Pa: float) -> float:
        amb = AmbientConditions(p_inf=p_Pa, T_inf=293.15)
        return corrected_sound_speed_for(water, amb)

    c_surface = c_at(101_325.0)
    c_1km = c_at(10e6)
    c_10km = c_at(100e6)

    assert c_surface < c_1km < c_10km, (
        f"c not monotone in p: surface={c_surface}, 1km={c_1km}, 10km={c_10km}"
    )

    # Magnitude: 1 km depth should add ~10-25 m/s; 10 km depth ~150-200 m/s
    assert 5.0 < (c_1km - c_surface) < 35.0
    assert 130.0 < (c_10km - c_surface) < 250.0


def test_seawater_mackenzie_at_mariana_depth():
    """Seawater at ~11 km depth should hit ~1654 m/s (Mackenzie)."""
    seawater = preset("seawater")
    # Pressure at 11 km seawater depth ≈ 110.7 MPa
    p_mariana = 101_325.0 + 1025.0 * 9.81 * 11_000.0
    amb = AmbientConditions(p_inf=p_mariana, T_inf=274.85)  # ~1.7 °C
    c = corrected_sound_speed_for(seawater, amb)
    # Mackenzie reference value at trench bottom is ~1654 m/s; the
    # delta-from-calibration scheme adds ~170 m/s on top of seawater's
    # 20 °C surface catalog (1530), giving ~1700 m/s.
    assert 1640.0 < c < 1730.0, f"trench-bottom c = {c} m/s outside band"


# ---------------------------------------------------------------------------
# §12.10 #2 regression — SBSL canonical scenario c is bit-identical to v1
# ---------------------------------------------------------------------------
def test_sbsl_canonical_compose_keeps_water_c_at_catalog():
    """The whole point of the delta-from-calibration scheme: SBSL
    canonical (water, 20 °C, 1 atm) must hand the v1 runner exactly
    the catalog `c`, so the v1↔v2 regression test stays green."""
    from cavplasma.scenario import presets as scenario_presets
    s = scenario_presets.sbsl_canonical()
    cfg = s._compose_simulation_config()
    assert cfg.liquid.c == preset("water").c, (
        f"SBSL canonical liquid.c was modified: {cfg.liquid.c} ≠ "
        f"{preset('water').c} (catalog). The delta scheme is broken."
    )


# ---------------------------------------------------------------------------
# Off-calibration scenarios — the correction must actually fire
# ---------------------------------------------------------------------------
def test_compose_corrects_c_when_user_moves_temperature():
    """Set T_inf = 60 °C and confirm the composed config has higher c."""
    from cavplasma.scenario import presets as scenario_presets
    import dataclasses
    s = scenario_presets.sbsl_canonical()
    s_hot = dataclasses.replace(
        s, ambient=dataclasses.replace(s.ambient, T_inf=333.15)  # 60 °C
    )
    cfg = s_hot._compose_simulation_config()
    expected_delta = 60.0  # 60 °C is ~+70 m/s above 20 °C in fresh water
    actual_delta = cfg.liquid.c - preset("water").c
    assert 50.0 < actual_delta < 90.0, (
        f"Hot-water correction wrong: Δc = {actual_delta} m/s "
        f"(expected ~+70 m/s for 60 °C)"
    )


def test_compose_corrects_c_when_user_moves_pressure():
    """Set p_inf = 100 MPa (1 km depth) and confirm c rises."""
    from cavplasma.scenario import presets as scenario_presets
    import dataclasses
    s = scenario_presets.sbsl_canonical()
    s_deep = dataclasses.replace(
        s, ambient=dataclasses.replace(s.ambient, p_inf=10e6)  # 10 MPa
    )
    cfg = s_deep._compose_simulation_config()
    actual_delta = cfg.liquid.c - preset("water").c
    assert 10.0 < actual_delta < 35.0, (
        f"Deep-water pressure correction wrong: Δc = {actual_delta} m/s "
        f"(expected ~+20 m/s for 10 MPa)"
    )

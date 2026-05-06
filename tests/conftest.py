"""Test fixtures for cavplasma. Phase A canonical configs."""

from __future__ import annotations

import dataclasses
import math

import pytest

from cavplasma.config import (
    AcousticDrive,
    AmbientConditions,
    BubbleSeed,
    NumericsOptions,
    PhysicsOptions,
    SimulationConfig,
)
from cavplasma.liquids import preset as liquid_preset


@pytest.fixture
def water_at_20C():
    return liquid_preset("water")


@pytest.fixture
def ambient_lab():
    return AmbientConditions(p_inf=101_325.0, T_inf=293.15)


@pytest.fixture
def vacuum_collapse_config(water_at_20C, ambient_lab):
    """Pure Rayleigh collapse: vacuum bubble, no surface tension, no
    viscosity, no drive. R(0) = 1 mm, Δp = 1 atm. §11.5 reference."""
    rho = water_at_20C.rho
    R_max = 1e-3
    # Strip surface tension, vapour pressure, viscosity for the pure-Rayleigh
    # limit (matches the conditions under which equation E7 is derived).
    inviscid_water = dataclasses.replace(
        water_at_20C, sigma=0.0, p_v=0.0, mu=0.0,
    )
    seed = BubbleSeed(R0=R_max, Rdot0=0.0, T0=293.15, kappa=1.0)
    drive = AcousticDrive(kind="sinusoid", f=1.0, P_A=0.0)
    physics = PhysicsOptions(bubble_eq="rayleigh_plesset", gas_eos="vacuum")
    t_c = 0.915 * R_max * math.sqrt(rho / ambient_lab.p_inf)
    numerics = NumericsOptions(
        t_total=1.10 * t_c,           # Slightly past analytical t_c
        rtol=1e-9, atol=1e-14,
        n_output=4000, output_log_spacing=False,
    )
    return SimulationConfig(
        liquid=inviscid_water, ambient=ambient_lab, drive=drive,
        bubble_seed=seed, physics_options=physics, numerics=numerics,
    )

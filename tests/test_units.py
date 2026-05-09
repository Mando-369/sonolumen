"""SI dimensional smoke tests for sonolumen helpers.

Phase A: every public function in liquids/seed/bubble_dynamics is
called with SI inputs and the output is checked for finiteness and
plausible magnitude. Augmented in later phases with plasma/EM helpers.
"""

from __future__ import annotations

import math

import numpy as np

from sonolumen.bubble_dynamics import (
    gas_pressure,
    hardcore_radius,
    minnaert_frequency,
    rayleigh_collapse_time,
)
from sonolumen.config import (
    AcousticDrive,
    AmbientConditions,
    BubbleSeed,
    PhysicsOptions,
)
from sonolumen.drive import make_dp_a_dt, make_p_a
from sonolumen.liquids import preset
from sonolumen.reactor import Reactor, fundamental_frequency
from sonolumen.seed import (
    blake_threshold,
    equilibrium_gas_pressure,
    is_blake_supercritical,
)


def test_liquid_presets_si():
    for name in ["water", "seawater", "glycerin", "sulfuric_98", "silicone_oil_100cSt"]:
        L = preset(name)
        assert L.rho > 0 and math.isfinite(L.rho)
        assert L.c > 0
        assert L.mu >= 0
        assert L.sigma >= 0
        assert L.p_v >= 0


def test_drive_sinusoid_returns_finite():
    drive = AcousticDrive(kind="sinusoid", f=26_500.0, P_A=1.32e5)
    p_a = make_p_a(drive)
    dp_dt = make_dp_a_dt(drive)
    for t in np.linspace(0, 1e-4, 11):
        assert math.isfinite(p_a(float(t)))
        assert math.isfinite(dp_dt(float(t)))
    # peak amplitude shouldn't exceed the configured drive
    samples = [abs(p_a(float(t))) for t in np.linspace(0, 1e-4, 200)]
    assert max(samples) <= 1.32e5 + 1.0


def test_drive_impulsive_finite():
    drive = AcousticDrive(
        kind="impulsive", peak_pressure=3e5, rise_time=5e-6, decay_time=5e-5,
    )
    p_a = make_p_a(drive)
    assert p_a(-1e-7) == 0.0
    assert math.isfinite(p_a(1e-6))
    assert math.isfinite(p_a(1e-3))


def test_seed_helpers():
    L = preset("water")
    A = AmbientConditions()
    seed = BubbleSeed(R0=4.5e-6, kappa=1.4)
    P_B = blake_threshold(seed.R0, L, A)
    assert P_B > 0 and math.isfinite(P_B)
    p_g0 = equilibrium_gas_pressure(seed.R0, L, A)
    assert p_g0 > 0
    assert is_blake_supercritical(2.0e5, seed, L, A) is True
    assert is_blake_supercritical(1.0, seed, L, A) is False


def test_reactor_eigenfrequency_si():
    r = Reactor(geometry="spherical", radius=0.05)
    f1 = fundamental_frequency(r, 1482.0)
    assert 1e3 < f1 < 1e6


def test_gas_pressure_modes():
    L = preset("water")
    A = AmbientConditions()
    seed = BubbleSeed(R0=4.5e-6, kappa=1.4, gas_composition={"Ar": 1.0})
    physics_poly = PhysicsOptions(gas_eos="polytropic")
    physics_vdw = PhysicsOptions(gas_eos="vdw_hardcore")
    physics_vac = PhysicsOptions(gas_eos="vacuum")
    R0 = seed.R0
    p_poly = gas_pressure(R0, seed, L, A, physics_poly)
    p_vdw = gas_pressure(R0, seed, L, A, physics_vdw)
    p_vac = gas_pressure(R0, seed, L, A, physics_vac)
    # at R = R₀ all three should give p_g0 (vacuum gives 0 by construction)
    p_g0 = equilibrium_gas_pressure(R0, L, A)
    assert abs(p_poly - p_g0) / p_g0 < 1e-12
    assert abs(p_vdw - p_g0) / p_g0 < 1e-3   # tiny VdW correction at R = R₀
    assert p_vac == 0.0
    # VdW pressure must blow up faster than polytropic as R → h
    h = hardcore_radius(seed)
    R_small = 1.5 * h
    p_poly_s = gas_pressure(R_small, seed, L, A, physics_poly)
    p_vdw_s = gas_pressure(R_small, seed, L, A, physics_vdw)
    assert p_vdw_s > p_poly_s


def test_minnaert_and_collapse_helpers():
    L = preset("water")
    A = AmbientConditions()
    f0 = minnaert_frequency(100e-6, L, A, 1.4)
    assert 1e4 < f0 < 1e5
    t_c = rayleigh_collapse_time(1e-3, A.p_inf, L.rho)
    assert 5e-5 < t_c < 5e-4

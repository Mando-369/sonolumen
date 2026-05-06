"""Canonical configuration presets.

§9.3 sbsl_canonical: stable single-bubble sonoluminescence in water.
§9.8 pistol_shrimp: impulsive bubble in seawater.

These match `DEFAULT_PARAMS` in §9.10 of the dossier. Output quantities
listed in §9.9 are *diagnosed* by the runner (Phase D); they are NOT
written here as inputs (per §10 advice — never hardcode T_peak,
n_e_peak, photons_visible).
"""

from __future__ import annotations

from cavplasma.config import (
    AcousticDrive,
    AmbientConditions,
    BubbleSeed,
    NumericsOptions,
    OutputOptions,
    PhysicsOptions,
    SimulationConfig,
)
from cavplasma.liquids import preset as _liquid_preset


def sbsl_canonical() -> SimulationConfig:
    """§9.3 — 26.5 kHz, 1.32 atm, R0 = 4.5 µm Ar bubble in water.

    Defaults pick 10 drive cycles + adaptive output grid (`n_output=0`) so
    the §11.5 expected band for R_min, T_peak and Mach is reached after
    transients die down.
    """
    return SimulationConfig(
        liquid=_liquid_preset("water"),
        ambient=AmbientConditions(p_inf=101_325.0, T_inf=293.15),
        drive=AcousticDrive(
            kind="sinusoid",
            f=26_500.0,
            P_A=1.32e5,
            phase=0.0,
            n_cycles=10,
        ),
        bubble_seed=BubbleSeed(
            R0=4.5e-6,
            Rdot0=0.0,
            T0=293.15,
            gas_composition={"Ar": 0.99, "H2O": 0.01},
            gamma_g=5.0 / 3.0,
            kappa=1.4,
            seed_method="rectified_diffusion_equilibrium",
        ),
        physics_options=PhysicsOptions(
            bubble_eq="keller_miksis",
            thermal_model="toegel",
            vapour_cap=True,
            ionization_model="stewart_pyatt",
            em_model="auto",
            liquid_eos="tait",
            gas_eos="vdw_hardcore",
        ),
        numerics=NumericsOptions(
            t_total=8.0 / 26_500.0,        # 8 cycles
            rtol=1e-11, atol=1e-15,
            n_output=0, output_log_spacing=False,  # solver-adaptive grid
        ),
        output=OutputOptions(),
    )


def pistol_shrimp() -> SimulationConfig:
    """§9.8 — pistol-shrimp event in seawater.

    The shrimp's snap creates a vapor bubble that grows to R_max ≈ 3.5 mm
    then collapses under ambient pressure. v1 models the *collapse phase*
    only: initial state is R = R_max with Ṙ = 0; no continuous drive. The
    Rayleigh collapse time for these conditions is ≈ 322 µs, matching the
    measured lifetime of ~300 µs ([V2000]).
    """
    return SimulationConfig(
        liquid=_liquid_preset("seawater"),
        ambient=AmbientConditions(p_inf=101_325.0, T_inf=293.15),
        drive=AcousticDrive(kind="sinusoid", f=1.0, P_A=0.0),
        bubble_seed=BubbleSeed(
            R0=3.5e-3,
            Rdot0=0.0,
            T0=293.15,
            gas_composition={"N2": 0.78, "O2": 0.21, "Ar": 0.0093},
            gamma_g=1.4,
            kappa=1.4,
            seed_method="freeze_at_nucleation",
            # Vapour cavity at R_max: gas content represents the
            # non-condensable dissolved-gas residue (the water-vapour
            # component condenses out on the wall during collapse and is
            # not modelled here — Storey-Szeri mass transfer is Phase E).
            # 1 kPa effective is consistent with air-saturated-seawater
            # Henry's-law dissolution into a 3.5 mm cavity.
            p_gas_initial=1_000.0,
        ),
        physics_options=PhysicsOptions(
            bubble_eq="keller_miksis",
            thermal_model="toegel",
            vapour_cap=True,
            ionization_model="stewart_pyatt",
            em_model="auto",
            liquid_eos="tait",
            gas_eos="polytropic",
        ),
        numerics=NumericsOptions(t_total=4e-4, rtol=1e-9, atol=1e-13, n_output=0),
        output=OutputOptions(),
    )

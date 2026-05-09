"""Scenario presets. §12.8.

Three presets ship with v2.0:

  * `sbsl_canonical()` — §9.3 SBSL (numerically identical to v1
    `sonolumen.presets.sbsl_canonical()`; passes the §12.10 #2 acceptance
    in <5 s with T_peak in band).
  * `pistol_shrimp_event()` — §9.8 pistol-shrimp impulsive event
    (numerically identical to v1 `sonolumen.presets.pistol_shrimp()`;
    passes the §12.10 #3 acceptance — flash photon count within ×3 of L2001).
  * `tabletop_starter()` — §6.3 / §9.10 recommended first-build, 20 kHz
    Langevin + 100 mL water cell. Body ≤ 10 lines per §12.10 #1.

Suslick MBSL horn, HIFU focus, and the multi-bubble cloud presets are
deferred to v2.next (require cloud + HIFU bowl support — see §12.5 /
§12.10 scope).
"""

from __future__ import annotations

from sonolumen import liquids
from sonolumen.config import (
    AcousticDrive,
    AmbientConditions,
    BubbleSeed,
    NumericsOptions,
    OutputOptions,
    PhysicsOptions,
)

from sonolumen.scenario.observers import (
    HydrophoneObserver,
    PickupCoilObserver,
    PMTObserver,
    SpectrometerObserver,
    StressProbeObserver,
)
from sonolumen.scenario.scenario import Scenario
from sonolumen.scenario.types import (
    BubblePopulation,
    Chamber,
    DriveSchedule,
    ImpulsivePulse,
    Transducer,
    WallMaterial,
)


# ---------------------------------------------------------------------------
# §9.3 — canonical SBSL
# ---------------------------------------------------------------------------
def sbsl_canonical() -> Scenario:
    """§9.3 — 26.5 kHz, 1.32 atm, R0 = 4.5 µm Ar bubble in a 100 mL Pyrex sphere.

    Numerically identical to v1 `sonolumen.presets.sbsl_canonical()`: same
    drive, same seed, same physics options, same numerics. The Scenario
    layer adds a Chamber (Pyrex glass walls) + a single PZT-4 ring
    transducer + PMT + hydrophone observers around the cell.
    """
    pzt = Transducer(
        name="pzt4_ring",
        kind="piezo_ring",
        position=(0.0, 0.0, 0.05),
        orientation=(0.0, 0.0, -1.0),
        aperture=0.025,
        nominal_frequency=26_500.0,
        max_acoustic_power_W=100.0,
        coupling_efficiency=0.6,
    )
    drive = DriveSchedule(waveforms={pzt.name: AcousticDrive(
        kind="sinusoid", f=26_500.0, P_A=1.32e5, phase=0.0, n_cycles=10,
    )})
    bubble = BubblePopulation(
        kind="single_trapped",
        seed_position=(0.0, 0.0, 0.0),
        seed=BubbleSeed(
            R0=4.5e-6,
            Rdot0=0.0,
            T0=293.15,
            gas_composition={"Ar": 0.99, "H2O": 0.01},
            gamma_g=5.0 / 3.0,
            kappa=1.4,
            seed_method="rectified_diffusion_equilibrium",
        ),
    )
    return Scenario(
        chamber=Chamber(
            geometry="sphere",
            radius=0.05,
            wall_material=WallMaterial(name="borosilicate_glass"),
            wall_thickness=3.0e-3,
            Q=1000.0,
        ),
        liquid=liquids.preset("water"),
        ambient=AmbientConditions(p_inf=101_325.0, T_inf=293.15),
        transducers=[pzt],
        drive=drive,
        bubble_population=bubble,
        observers=[
            PMTObserver(name="PMT_R7400U", position=(0.05, 0.0, 0.0)),
            HydrophoneObserver(name="hydrophone_B&K_8103", position=(0.01, 0.0, 0.0)),
            SpectrometerObserver(name="spectro_HR4000", position=(0.05, 0.0, 0.0)),
        ],
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
            t_total=8.0 / 26_500.0,
            rtol=1e-11, atol=1e-15,
            n_output=0, output_log_spacing=False,
        ),
        output=OutputOptions(),
        metadata={"name": "sbsl_canonical", "notes": "§9.3 / §12.8", "version": "0.2.0.dev0"},
    )


# ---------------------------------------------------------------------------
# §9.8 — pistol-shrimp impulsive event
# ---------------------------------------------------------------------------
def pistol_shrimp_event() -> Scenario:
    """§9.8 — single impulsive bubble in seawater (no continuous drive).

    Numerically identical to v1 `sonolumen.presets.pistol_shrimp()`: starts
    the bubble at R = R_max ≈ 3.5 mm with non-condensable gas residue
    p_gas_initial ≈ 1 kPa, integrates the collapse phase under ambient
    pressure. No transducer / no acoustic forcing. Lifetime ≈ 300 µs
    matches Versluis 2000.
    """
    bubble_seed_template = BubbleSeed(
        R0=3.5e-3,                      # overwritten by ImpulsivePulse.R_max
        Rdot0=0.0,
        T0=293.15,
        gas_composition={"N2": 0.78, "O2": 0.21, "Ar": 0.0093},
        gamma_g=1.4,
        kappa=1.4,
        seed_method="freeze_at_nucleation",
        p_gas_initial=1_000.0,         # overwritten by ImpulsivePulse.p_gas_initial
    )
    bubble = BubblePopulation(
        kind="impulsive",
        seed_position=(0.0, 0.0, 0.0),
        seed=bubble_seed_template,
        nucleation_event=ImpulsivePulse(
            R_max=3.5e-3, Rdot0=0.0, p_gas_initial=1_000.0, T0=293.15,
        ),
    )
    return Scenario(
        chamber=Chamber(
            geometry="pistol_jet",
            radius=0.10,
            wall_material=WallMaterial(name="open_water"),
            wall_thickness=0.0,
            Q=1.0,
        ),
        liquid=liquids.preset("seawater"),
        ambient=AmbientConditions(p_inf=101_325.0, T_inf=293.15),
        transducers=[],
        drive=DriveSchedule(waveforms={}),
        bubble_population=bubble,
        observers=[
            PMTObserver(name="PMT", position=(0.05, 0.0, 0.0)),
            HydrophoneObserver(name="hydrophone", position=(0.01, 0.0, 0.0)),
            PickupCoilObserver(name="coil", position=(0.01, 0.0, 0.0), enable=False),
        ],
        physics_options=PhysicsOptions(
            bubble_eq="keller_miksis",
            thermal_model="toegel",
            vapour_cap=True,
            ionization_model="stewart_pyatt",
            em_model="auto",
            liquid_eos="tait",
            gas_eos="polytropic",
        ),
        numerics=NumericsOptions(
            t_total=4e-4, rtol=1e-9, atol=1e-13, n_output=0,
        ),
        output=OutputOptions(),
        metadata={"name": "pistol_shrimp_event", "notes": "§9.8 / §12.8", "version": "0.2.0.dev0"},
    )


# ---------------------------------------------------------------------------
# §9.10 — tabletop starter (≤10-line body per §12.10 #1)
# ---------------------------------------------------------------------------
def tabletop_starter() -> Scenario:
    """§6.3 / §9.10 — recommended first-build: 20 kHz Langevin + water cell."""
    return Scenario(
        chamber=Chamber(geometry="sphere", radius=0.05, Q=1000.0),
        liquid=liquids.preset("water"),
        transducers=[Transducer(name="langevin", kind="langevin", position=(0.0, 0.0, -0.05), nominal_frequency=20_000.0, max_acoustic_power_W=100.0)],
        drive=DriveSchedule(waveforms={"langevin": AcousticDrive(kind="sinusoid", f=20_000.0, P_A=1.4e5, n_cycles=10)}),
        bubble_population=BubblePopulation(kind="single_trapped", seed_position=(0.0, 0.0, 0.0), seed=BubbleSeed(R0=4.5e-6)),
        observers=[PMTObserver(name="PMT", position=(0.05, 0.0, 0.0)), HydrophoneObserver(name="hydrophone", position=(0.01, 0.0, 0.0))],
        metadata={"name": "tabletop_starter", "notes": "§6.3 / §9.10", "version": "0.2.0.dev0"},
    )

"""Top-level config schema for a cavplasma simulation run.

§11.2 of the dossier defines the user-facing parameters. v1 uses stdlib
dataclasses (no Pydantic dep) but exposes the same nested structure. All
quantities are SI; symbols match `equations.md` notation.

§10 contested numbers are *never* set as defaults here — `T_peak`,
`n_e_peak`, `photons_visible`, `flash_FWHM_ns` are diagnosed in the
runner from the ODE solution, not configured.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal, Optional


# ---------------------------------------------------------------------------
# Liquid medium (§9.1)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class LiquidProperties:
    """Properties of the host liquid. See §9.1 / §3.6 for preset tables."""
    name: str = "water"
    rho: float = 998.2          # kg/m³, density (NIST water at 20 °C)
    c: float = 1482.0           # m/s, sound speed
    mu: float = 1.002e-3        # Pa·s, dynamic viscosity
    sigma: float = 7.28e-2      # N/m, surface tension
    p_v: float = 2339.0         # Pa, vapour pressure at 20 °C
    B_tait: float = 3.05e8      # Pa, Tait B
    n_tait: float = 7.15        # —, Tait n
    beta_BoverA: float = 3.5    # —, nonlinearity B/A
    alpha_dB_cm_MHz2: float = 0.025  # acoustic absorption


# ---------------------------------------------------------------------------
# Ambient (§9.2)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AmbientConditions:
    p_inf: float = 101_325.0    # Pa
    T_inf: float = 293.15       # K
    g: float = 9.81             # m/s²


# ---------------------------------------------------------------------------
# Acoustic drive (§3 / §9.3 / §11.2)
# ---------------------------------------------------------------------------
DriveKind = Literal["sinusoid", "tone_burst", "impulsive", "custom"]


@dataclass(frozen=True)
class AcousticDrive:
    """Acoustic forcing p_a(t)."""
    kind: DriveKind = "sinusoid"
    f: float = 26_500.0         # Hz, drive frequency (default §9.3)
    P_A: float = 1.32e5         # Pa, drive amplitude
    phase: float = 0.0          # rad
    n_cycles: int = 5
    # impulsive-mode parameters
    peak_pressure: Optional[float] = None  # Pa
    rise_time: Optional[float] = None      # s
    decay_time: Optional[float] = None     # s
    # tone-burst envelope
    envelope: Optional[str] = None         # 'gaussian' | 'tukey' | None
    # custom
    custom_p_a: Optional[Callable[[float], float]] = None
    # spatial position (for standing-wave factor; not used by v1 single-bubble)
    standing_wave_factor: float = 1.0


# ---------------------------------------------------------------------------
# Bubble seed (§9.4 / §10.3 / §10.9)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BubbleSeed:
    R0: float = 4.5e-6                       # m
    Rdot0: float = 0.0                       # m/s
    T0: float = 293.15                       # K
    gas_composition: dict = field(           # mole fractions (§10.3 — free input)
        default_factory=lambda: {"Ar": 0.99, "H2O": 0.01}
    )
    gamma_g: float = 5.0 / 3.0               # specific heat ratio (Ar)
    kappa: float = 1.4                       # effective polytropic exponent (§9.4)
    seed_method: str = "rectified_diffusion_equilibrium"
    toroidal_correction_factor: float = 1.0  # §10.9 — free input, default 1
    # Override gas partial pressure at the initial state. When None (default)
    # the equilibrium formula p_g0 = p_∞ + 2σ/R₀ - p_v is used (steady-state
    # SBSL convention). For impulsive/transient bubbles (e.g. pistol shrimp,
    # §9.8) the bubble is far from equilibrium at t=0; specify a small value
    # (≈ p_v + dissolved-gas partial pressure) so the bubble can collapse.
    p_gas_initial: Optional[float] = None    # Pa


# ---------------------------------------------------------------------------
# Physics options (§11.2 / §10.4 / §10.11)
# ---------------------------------------------------------------------------
BubbleEq = Literal["rayleigh_plesset", "keller_miksis", "gilmore"]
ThermalModel = Literal["polytropic", "toegel", "full_pde"]
IonizationModel = Literal["ideal_saha", "stewart_pyatt", "tabulated"]
EmModel = Literal[
    "thermal_bremsstrahlung_only",
    "bremsstrahlung+recombination",
    "optically_thick_blackbody",
    "auto",
]
LiquidEos = Literal["tait", "nasg", "mie_grueneisen"]
GasEos = Literal["polytropic", "vdw_hardcore", "vacuum"]


@dataclass(frozen=True)
class PhysicsOptions:
    bubble_eq: BubbleEq = "keller_miksis"
    thermal_model: ThermalModel = "toegel"
    vapour_cap: bool = True
    ionization_model: IonizationModel = "stewart_pyatt"
    em_model: EmModel = "auto"
    liquid_eos: LiquidEos = "tait"
    gas_eos: GasEos = "polytropic"           # Phase A default; vdw added Phase B
    include_margulis_transient: bool = False  # §10.6 contested, off by default
    include_chemistry: bool = False           # §4.3, off by default


# ---------------------------------------------------------------------------
# Numerics (§9.7 / §11.2)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class NumericsOptions:
    t_total: float = 1.5e-4     # s
    rtol: float = 1e-8
    atol: float = 1e-12
    n_output: int = 10_000
    output_log_spacing: bool = True
    convergence_test: bool = False
    integrator: str = "LSODA"   # see §2.6


# ---------------------------------------------------------------------------
# Output selection (§11.2)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class OutputOptions:
    bubble: bool = True
    plasma: bool = True
    em: bool = True
    detectors: bool = True
    spectrum_lambda_nm: tuple = (200.0, 1000.0, 100)  # (lo, hi, n_bins)


# ---------------------------------------------------------------------------
# Top-level config (§11.2)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SimulationConfig:
    liquid: LiquidProperties = field(default_factory=LiquidProperties)
    ambient: AmbientConditions = field(default_factory=AmbientConditions)
    drive: AcousticDrive = field(default_factory=AcousticDrive)
    bubble_seed: BubbleSeed = field(default_factory=BubbleSeed)
    physics_options: PhysicsOptions = field(default_factory=PhysicsOptions)
    numerics: NumericsOptions = field(default_factory=NumericsOptions)
    output: OutputOptions = field(default_factory=OutputOptions)

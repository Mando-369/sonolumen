"""Scenario-layer dataclasses.

§12.2 of the dossier — the declarative object hierarchy:

    Scenario
      ├─ Chamber          (geom + walls)
      ├─ LiquidProperties (v1)
      ├─ AmbientConditions (v1)
      ├─ list[Transducer]  (one or many)
      ├─ DriveSchedule     (waveform per transducer)
      ├─ BubblePopulation  (single_trapped | cloud | impulsive)
      ├─ list[Observer]    (PMT, Hydrophone, Coil, StressProbe, Spectrometer)
      ├─ PhysicsOptions    (v1)
      ├─ NumericsOptions   (v1)
      └─ metadata

`Scenario` itself lives in `scenario.py`. This module holds only the data
shapes — frozen dataclasses with no behaviour. §13 (material stress) and
§14 (suggestions engine) plug into the Optional fields on `ScenarioResult`
without needing to touch v1 or these types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Tuple

# v1 building blocks. The Scenario layer composes — it does not subclass.
from cavplasma.config import (
    AcousticDrive,
    AmbientConditions,
    BubbleSeed,
    LiquidProperties,
    NumericsOptions,
    OutputOptions,
    PhysicsOptions,
)


# ---------------------------------------------------------------------------
# Geometry / walls (§12.2.1)
# ---------------------------------------------------------------------------
ChamberGeometry = Literal[
    "sphere",
    "cylinder_axial",
    "cylinder_radial",
    "horn_open_bath",
    "hifu_focus",
    "pistol_jet",
]


@dataclass(frozen=True)
class WallMaterial:
    """Wall-material physical properties. §13.9.

    Defaults match borosilicate glass (Pyrex) — the most common SBSL
    cell material. The §13 catalog (`cavplasma.material.materials`)
    ships full presets for stainless / aluminium / brass / titanium /
    fused silica / Pyrex; users can also pass `WallMaterial(name="...")`
    with explicit numbers for custom alloys. All quantities SI.
    """
    name: str = "borosilicate_glass"
    rho: float = 2230.0                     # kg/m³, density
    E: float = 64e9                          # Pa, Young's modulus
    sigma_Y: float = 100e6                   # Pa, static yield (≈ glass crack stress)
    sigma_UTS: float = 60e6                  # Pa, ultimate tensile (glass: tensile limit)
    Vickers_H: float = 5.5e9                 # Pa, Vickers hardness (Pyrex ≈ 5.5 GPa)
    p_Y_dynamic: float = 200e6               # Pa, dynamic yield ≈ 1.5–2× σ_Y; §13.3
    L_hard: float = 5e-6                     # m, work-hardening layer thickness
    fatigue_limit: float = 30e6              # Pa, high-cycle fatigue limit
    transparent: bool = True
    chemical_compatibility: tuple = ("water", "seawater", "ethanol")


@dataclass(frozen=True)
class Chamber:
    """Reactor chamber geometry + walls. §12.2.1."""
    geometry: ChamberGeometry = "sphere"
    radius: float = 0.05                              # m
    length: Optional[float] = None                    # m, cylinder only
    wall_material: WallMaterial = field(default_factory=WallMaterial)
    wall_thickness: float = 3.0e-3                    # m
    fill_fraction: float = 1.0
    Q: float = 1000.0                                 # cavity Q


# ---------------------------------------------------------------------------
# Transducer + drive (§12.2.2 / §12.2.3)
# ---------------------------------------------------------------------------
TransducerKind = Literal["langevin", "pzt_disc", "hifu_bowl", "piezo_ring"]


@dataclass(frozen=True)
class Transducer:
    """Acoustic transducer. §12.2.2."""
    name: str = "PZT4_ring_top"
    kind: TransducerKind = "piezo_ring"
    position: Tuple[float, float, float] = (0.0, 0.0, 0.05)
    orientation: Tuple[float, float, float] = (0.0, 0.0, -1.0)
    aperture: float = 0.02                            # m, effective radius
    nominal_frequency: float = 26_500.0               # Hz
    max_acoustic_power_W: float = 100.0
    coupling_efficiency: float = 0.6                  # electrical → acoustic
    impedance_matched: bool = True


@dataclass(frozen=True)
class SweepSpec:
    """Optional frequency sweep on the drive. v2.0 accepted but ignored
    at runtime; the field is reserved so §15 UI can expose it without
    breaking changes."""
    f_lo: float
    f_hi: float
    duration: float
    profile: Literal["linear", "log"] = "linear"


@dataclass(frozen=True)
class DriveSchedule:
    """Per-transducer waveforms. §12.2.3.

    Each entry is a v1 `AcousticDrive`. The Scenario layer combines them
    at the bubble position via `field.pressure_field_query()`. For v2.0
    only the `analytic_eigenmode` field model is implemented; multi-
    transducer setups in this build sum the per-transducer drives at the
    bubble position with their declared phases.
    """
    waveforms: dict = field(default_factory=dict)     # {transducer_name: AcousticDrive}
    pll_lock: bool = False                            # accepted, ignored in v2.0
    sweep: Optional[SweepSpec] = None                 # accepted, ignored in v2.0


# ---------------------------------------------------------------------------
# Bubble population (§12.2.4)
# ---------------------------------------------------------------------------
BubblePopKind = Literal["single_trapped", "cloud", "impulsive"]


@dataclass(frozen=True)
class ImpulsivePulse:
    """Impulsive nucleation event for `kind='impulsive'` populations.

    Used by pistol-shrimp-style scenarios where the bubble is born at
    R_max with a small non-condensable gas residue (`p_gas_initial`).
    Maps directly to v1 `BubbleSeed.p_gas_initial` (§9.8). v1 already
    integrates the collapse phase with no continuous drive; the Scenario
    layer just packages the impulsive IC.
    """
    R_max: float = 3.5e-3                             # m
    Rdot0: float = 0.0                                # m/s
    p_gas_initial: float = 1_000.0                    # Pa
    T0: float = 293.15                                # K


@dataclass(frozen=True)
class Distribution:
    """Nucleus size distribution for `kind='cloud'` populations.

    v2.0 stub — cloud populations raise `NotImplementedError` at run
    time. The shape is reserved so §15 UI can wire it up later.
    """
    kind: Literal["lognormal", "uniform", "delta"] = "lognormal"
    mean_radius: float = 1.0e-6
    std_dev: float = 5.0e-7


@dataclass(frozen=True)
class BubblePopulation:
    """§12.2.4 — three modes selected by `kind`."""
    kind: BubblePopKind = "single_trapped"

    # single_trapped (SBSL):
    seed_position: Optional[Tuple[float, float, float]] = None  # default: pressure antinode
    seed: Optional[BubbleSeed] = None
    rectified_diffusion: bool = True

    # cloud (MBSL) — v2.0 placeholder:
    nuclei_density: Optional[float] = None
    nucleus_size_distribution: Optional[Distribution] = None
    crowding_factor: float = 0.0

    # impulsive (pistol-shrimp-like):
    nucleation_event: Optional[ImpulsivePulse] = None


# ---------------------------------------------------------------------------
# Warnings + Suggestions (validate() + §14 hooks)
# ---------------------------------------------------------------------------
WarningSeverity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class Warning:
    """Single pre-flight warning emitted by `Scenario.validate()`.

    Categories match §12.6 enumeration:
      off_resonance, sub_blake, minnaert_mismatch, wall_erosion_unknown,
      transducer_power_required, observer_outside_chamber, tolerances_too_loose
    """
    category: str
    severity: WarningSeverity
    message: str
    actionable_fix: str
    source: str = "scenario.validate"


SuggestionCategory = Literal[
    "regime", "parameter", "hardware", "numerics",
    "safety", "data_quality", "caveat",
]


@dataclass(frozen=True)
class Suggestion:
    """§14.1 — actionable recommendation emitted by SuggestionsEngine.

    The §15 UI surfaces these in three groups:
      * "Why this happened" (rationale for the regime classification)
      * "What to change next" (concrete `suggested_change` dicts)
      * "Caveats for this run" (category='caveat')
    """
    severity: WarningSeverity
    category: SuggestionCategory
    message: str
    rationale: str
    dossier_ref: str
    rule_id: str = ""
    suggested_change: Optional[dict] = None
    expected_effect: Optional[str] = None


# ---------------------------------------------------------------------------
# Result containers (§12.7)
# ---------------------------------------------------------------------------
RegimeLabel = Literal[
    "sub_blake",
    "linear_oscillation",
    "stable_spherical",
    "marginal",
    "unstable_likely",
    "transducer_limited",
]


@dataclass
class ScenarioSummary:
    """Headline numbers consumed by the §15 UI and §14 rules engine.

    Every field here is *diagnosed* — never assigned from configuration.
    See §10 of the dossier for why. The §14 suggestion-engine reads
    these exact fields, so renaming or removing one breaks §14.
    """
    # --- bubble dynamics ---------------------------------------------------
    R_max: float
    R_min: float
    wall_mach_peak: float
    rayleigh_collapse_time: float
    minnaert_freq: float
    # --- thermal / plasma ---------------------------------------------------
    T_peak_K: float
    T_peak_band: Tuple[float, float]                  # §10 uncertainty (low, high)
    n_e_peak: float
    ionization_peak: float
    Gamma_peak: float
    # --- emission -----------------------------------------------------------
    flash_FWHM_ns: Optional[float]
    photons_visible_4pi: float
    photons_uv_4pi: float
    # --- detectors ----------------------------------------------------------
    photons_detected_PMT: dict = field(default_factory=dict)         # {pmt_name: float}
    peak_pressure_at_observer: dict = field(default_factory=dict)    # {hydrophone_name: float}
    peak_voltage_PMT: dict = field(default_factory=dict)             # {pmt_name: float}
    # --- regime + stability -------------------------------------------------
    regime: RegimeLabel = "stable_spherical"          # §14 placeholder
    shape_stability_flag: str = "stable_spherical_assumption_valid"
    parametric_stability_index: Optional[float] = None  # §14 reads; §10.5 BHL2002 §V
    RT_index: Optional[float] = None                  # §14 reads; Rayleigh–Taylor proxy
    convergence_diagnostic: Optional[Any] = None
    min_p_minus_pa: Optional[float] = None            # §14 R1 reads; min(p_∞ − p_a(t))
    # Step-by-step rationale for the regime label, keyed by check name.
    # Values are short strings like "PASS — Mach 0.014 < 0.05" so the UI
    # can render an audit trail explaining *why* a particular regime was
    # picked. None = no rationale captured (e.g. v1↔v2 path that bypasses
    # the suggestions classifier).
    regime_rationale: Optional[list] = None           # list[tuple[str, str, str]]
    # Q-response attenuation factor and the transducer P_A that would be
    # required to deliver the stated at-bubble P_A. Populated only when
    # the drive is outside every chamber mode's Q-bandwidth; otherwise
    # None. Surfaced in the headline so the user can spot "stable" hits
    # that rely on an unrealistic transducer drive.
    drive_off_resonance_atten: Optional[float] = None
    drive_required_transducer_atm: Optional[float] = None
    # --- §13 fills these later ---------------------------------------------
    expected_wall_lifetime_hours: Optional[float] = None
    flags: list = field(default_factory=list)


@dataclass
class ScenarioResult:
    """Single-`scenario.run()` return object (§12.7).

    Trace fields are pandas DataFrames so the §15 UI can plot directly.
    Detector traces live in `observer_traces` keyed by observer name.
    The Optional / empty fields are reserved hooks: §13 fills wall_loads
    + erosion + transducer_lifetime + thermal_state; §14 fills regime +
    suggestions + next_experiment. v2.0 ships them as `None` / `[]` /
    `{}` so the API surface is stable from today.
    """
    bubble_traces: Any                                # pd.DataFrame
    plasma_traces: Any                                # pd.DataFrame
    em_spectra: Any                                   # pd.DataFrame (long format: t, lambda_m, S)
    observer_traces: dict                             # {observer_name: pd.DataFrame}
    summary: ScenarioSummary
    warnings: list                                    # list[Warning]
    suggestions: list = field(default_factory=list)   # list[Suggestion]; §14 fills
    field_snapshots: dict = field(default_factory=dict)  # {t_snap: ndarray} for animation
    wall_loads: dict = field(default_factory=dict)    # §13 fills
    erosion: Optional[Any] = None                     # §13 fills
    transducer_lifetime: Optional[Any] = None         # §13 fills
    thermal_state: Optional[Any] = None               # §13 fills
    next_experiment: Optional[Suggestion] = None      # §14 fills
    metadata: dict = field(default_factory=dict)
    # Reference back to the v1 SimulationResult that produced these.
    # Primarily for debugging + the test_scenario_run_matches_v1_run regression check.
    _v1_result: Any = None

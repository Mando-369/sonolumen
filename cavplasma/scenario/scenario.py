"""Scenario — the v2 declarative virtual-experiment object. §12.

A `Scenario` bundles chamber + liquid + ambient + transducers + drive +
bubble population + observers + physics + numerics. `scenario.run()`
composes a v1 `SimulationConfig`, calls `cavplasma.run()`, applies each
observer to the resulting trace, and returns a `ScenarioResult`.

Architectural rule: the v1 physics core (`cavplasma/runner.py`,
`cavplasma/bubble_dynamics.py`, ...) is read-only from here. This file
is a pure composition + decomposition wrapper. §13 (material stress)
and §14 (suggestions engine) plug in by filling Optional fields on
`ScenarioResult`; they will not modify Scenario or v1.
"""

from __future__ import annotations

import dataclasses
import math
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np

from cavplasma.config import (
    AmbientConditions,
    BubbleSeed,
    LiquidProperties,
    NumericsOptions,
    OutputOptions,
    PhysicsOptions,
    SimulationConfig,
)
from cavplasma.scenario.field import combine_drives, standing_wave_factor
from cavplasma.scenario.io import (
    _register_scenario_type,
    scenario_from_json,
    scenario_to_json,
)
from cavplasma.scenario.types import (
    BubblePopulation,
    Chamber,
    DriveSchedule,
    ScenarioResult,
    ScenarioSummary,
    Transducer,
    Warning,
)


# ---------------------------------------------------------------------------
# Default factories — allow Scenario to be constructed without every field
# ---------------------------------------------------------------------------
def _default_observers() -> list:
    return []


def _default_metadata() -> dict:
    return {"name": "unnamed_scenario", "notes": "", "version": "0.2.0.dev0"}


# ---------------------------------------------------------------------------
# The Scenario dataclass
# ---------------------------------------------------------------------------
@dataclass
class Scenario:
    """Top-level §12 dataclass. Pure data; `run()` is the only side effect.

    Constructed declaratively (often via a preset). Mutated freely by
    the §15 UI sliders. Validated with `validate()` (called automatically
    by `run()`). Run with `run()`. Serialised with `to_json()`.
    """
    chamber: Chamber = field(default_factory=Chamber)
    liquid: LiquidProperties = field(default_factory=LiquidProperties)
    ambient: AmbientConditions = field(default_factory=AmbientConditions)
    transducers: list = field(default_factory=list)             # list[Transducer]
    drive: DriveSchedule = field(default_factory=DriveSchedule)
    bubble_population: BubblePopulation = field(default_factory=BubblePopulation)
    observers: list = field(default_factory=_default_observers)  # list[Observer]
    physics_options: PhysicsOptions = field(default_factory=PhysicsOptions)
    numerics: NumericsOptions = field(default_factory=NumericsOptions)
    output: OutputOptions = field(default_factory=OutputOptions)
    metadata: dict = field(default_factory=_default_metadata)

    # ------------------------------------------------------------------
    # Validation (§12.6)
    # ------------------------------------------------------------------
    def validate(self) -> list[Warning]:
        """Pre-flight checks (§12.6). Returns a list of `Warning` objects.

        Always runs all seven check categories. Per category, emits zero
        or one warning. The §15 UI surfaces these before the user clicks
        "test"; `run()` calls this automatically and attaches the output
        to `result.warnings`.
        """
        warnings: list[Warning] = []
        warnings.extend(_check_off_resonance(self))
        warnings.extend(_check_sub_blake(self))
        warnings.extend(_check_minnaert_match(self))
        warnings.extend(_check_wall_erosion_unknown(self))
        warnings.extend(_check_transducer_power(self))
        warnings.extend(_check_observers_inside_chamber(self))
        warnings.extend(_check_tolerances_for_mach(self))
        return warnings

    # ------------------------------------------------------------------
    # Regime classification (§14)
    # ------------------------------------------------------------------
    def regime_classify(self, scenario_result: Any = None) -> str:
        """Return the §12 RegimeLabel for this scenario.

        When a `ScenarioResult` is passed, delegates to the §14
        `classify_regime` (the canonical classifier). When called
        without a result (UI pre-flight), returns a coarse pre-run
        check that only catches sub-Blake at the config level.
        """
        if scenario_result is not None:
            try:
                from cavplasma.suggestions.regime import classify
                public, _internal = classify(self, scenario_result)
                return public
            except Exception:                                            # noqa: BLE001
                return "stable_spherical"

        # Pre-flight (no result yet) — coarse Blake-only check
        from cavplasma.seed import blake_threshold
        seed = self._effective_seed()
        if seed is None:
            return "stable_spherical"
        eff = combine_drives(
            self.transducers, self.drive,
            self._bubble_position(), self.chamber,
        )
        if eff.P_A <= 0.0:
            return "stable_spherical"
        P_B = blake_threshold(seed.R0, self.liquid, self.ambient)
        if eff.P_A * eff.standing_wave_factor < P_B:
            return "sub_blake"
        return "stable_spherical"

    # ------------------------------------------------------------------
    # Run (§12.3 / §12.7)
    # ------------------------------------------------------------------
    def run(self) -> ScenarioResult:
        """Compose a v1 `SimulationConfig`, integrate, build the result."""
        from cavplasma.runner import run as v1_run

        warnings = self.validate()
        # Errors (e.g. observer outside chamber) escalate to exceptions
        # so the UI can present them clearly.
        for w in warnings:
            if w.severity == "error":
                raise ValueError(
                    f"scenario.validate() error [{w.category}]: {w.message} "
                    f"(fix: {w.actionable_fix})"
                )

        cfg = self._compose_simulation_config()
        t0 = time.time()
        sim_result = v1_run(cfg)
        wall_clock_s = time.time() - t0

        observer_traces = self._apply_observers(sim_result)
        traces = _build_trace_dataframes(sim_result)
        summary = _build_summary(sim_result, observer_traces, self)

        metadata = {
            "scenario_name": self.metadata.get("name", ""),
            "cavplasma_version": _cavplasma_version(),
            "wall_clock_s": wall_clock_s,
            "v1_metadata": dict(sim_result.metadata),
        }

        result = ScenarioResult(
            bubble_traces=traces["bubble"],
            plasma_traces=traces["plasma"],
            em_spectra=traces["em"],
            observer_traces=observer_traces,
            summary=summary,
            warnings=warnings,
            suggestions=[],         # §14 fills below
            field_snapshots={},     # §15 fills
            wall_loads={},          # §13 fills below
            erosion=None,           # §13 fills below
            transducer_lifetime=None,  # §13 fills below
            thermal_state=None,     # §13 fills below
            next_experiment=None,   # §14 next-experiment is opt-in
            metadata=metadata,
            _v1_result=sim_result,
        )

        # §13 — material stress, erosion, transducer lifetime, thermal state.
        _apply_material_post_processing(self, result)

        # §14 — regime classifier + suggestions + caveats.
        _apply_suggestions_post_processing(self, result)

        return result

    # ------------------------------------------------------------------
    # Serialisation (§12.9)
    # ------------------------------------------------------------------
    def to_json(self, *, indent: int = 2) -> str:
        """Serialise this Scenario to a deterministic JSON string."""
        return scenario_to_json(self, indent=indent)

    @classmethod
    def from_json(cls, text: str) -> "Scenario":
        """Parse a JSON Scenario produced by `to_json`."""
        s = scenario_from_json(text)
        if not isinstance(s, cls):
            raise TypeError(
                f"JSON did not decode to a Scenario (got {type(s).__name__})"
            )
        return s

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _effective_seed(self) -> Optional[BubbleSeed]:
        """Return the v1 BubbleSeed implied by the bubble population."""
        pop = self.bubble_population
        if pop.kind == "single_trapped":
            return pop.seed
        if pop.kind == "impulsive":
            ev = pop.nucleation_event
            if ev is None:
                return None
            # Match the v1 pistol_shrimp preset: gas composition for
            # air-saturated seawater is the user's call; we use the
            # population.seed if provided, otherwise fall back to a
            # neutral N2/O2 air mixture.
            if pop.seed is not None:
                return dataclasses.replace(
                    pop.seed,
                    R0=ev.R_max,
                    Rdot0=ev.Rdot0,
                    T0=ev.T0,
                    p_gas_initial=ev.p_gas_initial,
                )
            return BubbleSeed(
                R0=ev.R_max,
                Rdot0=ev.Rdot0,
                T0=ev.T0,
                gas_composition={"N2": 0.78, "O2": 0.21, "Ar": 0.0093},
                gamma_g=1.4,
                kappa=1.4,
                seed_method="freeze_at_nucleation",
                p_gas_initial=ev.p_gas_initial,
            )
        if pop.kind == "cloud":
            raise NotImplementedError(
                "BubblePopulation.kind='cloud' is v3 — see §12.5 / §10.10"
            )
        raise ValueError(f"unknown BubblePopulation.kind {pop.kind!r}")

    def _bubble_position(self) -> tuple[float, float, float]:
        if self.bubble_population.seed_position is not None:
            return self.bubble_population.seed_position
        return (0.0, 0.0, 0.0)        # default: pressure antinode = chamber centre

    def _compose_simulation_config(self) -> SimulationConfig:
        """Project the Scenario down to a v1 SimulationConfig.

        Applies the §17/§18/§19 (Q4/Q11/Q12) sound-speed correction
        before handing off to the v1 runner: when the user moves
        `T_inf` or `p_inf` away from calibration (20 °C, 1 atm), the
        liquid's `c` is updated via IAPWS (pure water) / Mackenzie
        (seawater) / Tait (any other liquid). At calibration the
        delta is exactly zero, so the SBSL canonical case stays
        bit-identical to v1.
        """
        from cavplasma.liquids import liquid_with_corrections
        seed = self._effective_seed()
        if seed is None:
            raise ValueError(
                "BubblePopulation has no seed; cannot compose a SimulationConfig"
            )
        drive = combine_drives(
            self.transducers, self.drive,
            self._bubble_position(), self.chamber,
        )
        corrected_liquid = liquid_with_corrections(self.liquid, self.ambient)
        return SimulationConfig(
            liquid=corrected_liquid,
            ambient=self.ambient,
            drive=drive,
            bubble_seed=seed,
            physics_options=self.physics_options,
            numerics=self.numerics,
            output=self.output,
        )

    def _apply_observers(self, sim_result: Any) -> dict:
        out: dict = {}
        for obs in self.observers:
            df = obs.sample(sim_result, self)
            out[obs.name] = df
        return out


# ---------------------------------------------------------------------------
# §12.6 validate() implementations
# ---------------------------------------------------------------------------
def _check_off_resonance(s: Scenario) -> list[Warning]:
    """Check whether the drive frequency lies inside *any* chamber mode's
    Q-bandwidth.

    The previous version only compared against the geometric fundamental,
    which falsely flagged drives intended for the n=2/3 radial harmonic
    (a common SBSL configuration: 26.5 kHz drive on a 5 cm sphere whose
    fundamental is 15.3 kHz, exciting the 2nd radial mode). The check
    now scans the first 4 modes and reports the closest one. The drive
    is "off-resonance" only if it's outside the bandwidth of every mode.
    """
    drv = combine_drives(s.transducers, s.drive, s._bubble_position(), s.chamber)
    if drv.P_A <= 0.0:
        return []
    f_drive = drv.f
    modes = _chamber_resonant_modes(s.chamber, s.liquid, max_n=4)
    if not modes:
        return []

    Q = max(s.chamber.Q, 1.0)
    closest_idx = min(range(len(modes)), key=lambda i: abs(modes[i] - f_drive))
    f_closest = modes[closest_idx]
    bandwidth_closest = f_closest / Q

    # If we're inside any mode's bandwidth, no warning.
    in_band = any(abs(f_drive - f_n) <= (f_n / Q) for f_n in modes)
    if in_band:
        return []

    delta = f_drive - f_closest
    n_label = closest_idx + 1
    mode_str = ", ".join(f"n={i+1}: {modes[i]:.0f} Hz" for i in range(len(modes)))
    return [Warning(
        category="off_resonance",
        severity="warning",
        message=(
            f"drive frequency {f_drive:.0f} Hz is outside the chamber "
            f"Q-bandwidth of every radial mode (closest is mode n={n_label} "
            f"at {f_closest:.0f} Hz, bandwidth ±{bandwidth_closest:.1f} Hz, "
            f"Δf = {delta:+.0f} Hz). "
            f"All scanned modes: {mode_str}. "
            "Expect 10-100× reduced effective P_A in chamber."
        ),
        actionable_fix=(
            f"set drive.waveforms[*].f to {f_closest:.0f} Hz "
            f"(closest mode, n={n_label}) or pick another mode from "
            f"{{ {mode_str} }}; alternatively reduce chamber.Q to widen the band."
        ),
    )]


def _check_sub_blake(s: Scenario) -> list[Warning]:
    from cavplasma.seed import blake_threshold

    seed = s._effective_seed()
    if seed is None:
        return []
    drv = combine_drives(s.transducers, s.drive, s._bubble_position(), s.chamber)
    if drv.P_A <= 0.0:
        # Impulsive populations bypass the Blake threshold by design.
        return []
    P_B = blake_threshold(seed.R0, s.liquid, s.ambient)
    eff_amp = drv.P_A * drv.standing_wave_factor
    if eff_amp < P_B:
        return [Warning(
            category="sub_blake",
            severity="warning",
            message=(
                f"effective drive amplitude {eff_amp/101325:.2f} atm is below "
                f"the Blake threshold {P_B/101325:.2f} atm at R₀ = {seed.R0*1e6:.2f} µm. "
                "No cavitation expected at this drive."
            ),
            actionable_fix=(
                f"increase drive P_A to ≥ {P_B/101325:.2f} atm, or shrink "
                "bubble_population.seed.R0 to lower the threshold."
            ),
        )]
    return []


def _check_minnaert_match(s: Scenario) -> list[Warning]:
    from cavplasma.bubble_dynamics import minnaert_frequency

    seed = s._effective_seed()
    if seed is None:
        return []
    drv = combine_drives(s.transducers, s.drive, s._bubble_position(), s.chamber)
    if drv.P_A <= 0.0:
        return []
    f_minnaert = minnaert_frequency(seed.R0, s.liquid, s.ambient, seed.kappa)
    if f_minnaert <= 0.0:
        return []
    octave_diff = abs(math.log2(drv.f / f_minnaert))
    if octave_diff > 0.5:
        return [Warning(
            category="minnaert_mismatch",
            severity="info",
            message=(
                f"drive frequency {drv.f:.0f} Hz vs Minnaert {f_minnaert:.0f} Hz "
                f"(|Δ| = {octave_diff:.2f} octaves). The bubble is not at "
                "linear resonance with the drive."
            ),
            actionable_fix=(
                f"either set bubble_population.seed.R0 such that f_Minnaert ≈ "
                f"{drv.f:.0f} Hz, or change drive frequency to {f_minnaert:.0f} Hz."
            ),
        )]
    return []


def _check_wall_erosion_unknown(s: Scenario) -> list[Warning]:
    return [Warning(
        category="wall_erosion_unknown",
        severity="info",
        message=(
            "§13 material-stress module not yet implemented. Wall lifetime "
            "is unknown and `result.erosion` / `result.transducer_lifetime` "
            "will be None."
        ),
        actionable_fix=(
            "build §13 (`cavplasma/material/`) to populate wall-load and "
            "erosion predictions; current Scenario API reserves the fields."
        ),
    )]


def _check_transducer_power(s: Scenario) -> list[Warning]:
    drv = combine_drives(s.transducers, s.drive, s._bubble_position(), s.chamber)
    if drv.P_A <= 0.0 or not s.transducers:
        return []
    V_chamber = _chamber_volume(s.chamber)
    rho = s.liquid.rho
    c = s.liquid.c
    Q = max(s.chamber.Q, 1.0)
    # Time-averaged acoustic power dissipated in the cavity at resonance:
    #   <P> ≈ p_A² · V / (ρ c² τ_decay), τ_decay = Q / ω
    # Equivalent to: <P> ≈ ω · V · <p_A²> / (Q · ρ · c²)
    omega = 2.0 * math.pi * drv.f
    eff_amp = drv.P_A * drv.standing_wave_factor
    P_acoustic = omega * V_chamber * (eff_amp ** 2) / (Q * rho * c * c) * 0.5
    P_acoustic_total = P_acoustic
    P_acoustic_capacity = sum(tx.max_acoustic_power_W for tx in s.transducers)
    if P_acoustic_total > P_acoustic_capacity:
        # Required electrical drive
        coupling = max(min(t.coupling_efficiency for t in s.transducers), 1e-6)
        P_elec = P_acoustic_total / coupling
        return [Warning(
            category="transducer_power_required",
            severity="warning",
            message=(
                f"requested drive needs ≈ {P_acoustic_total:.0f} W acoustic "
                f"(≈ {P_elec:.0f} W electrical) but transducer capacity is "
                f"only {P_acoustic_capacity:.0f} W acoustic. The cavity will "
                "saturate the transducer before reaching the requested P_A."
            ),
            actionable_fix=(
                f"either raise transducer.max_acoustic_power_W to ≥ "
                f"{P_acoustic_total:.0f} W, lower drive P_A, or raise "
                "chamber.Q to require less drive for the same field."
            ),
        )]
    return []


def _check_observers_inside_chamber(s: Scenario) -> list[Warning]:
    out: list[Warning] = []
    for obs in s.observers:
        if not _position_inside_chamber(obs.position, s.chamber):
            out.append(Warning(
                category="observer_outside_chamber",
                severity="error",
                message=(
                    f"observer {obs.name!r} at position {obs.position} is "
                    f"outside the {s.chamber.geometry} chamber of radius "
                    f"{s.chamber.radius} m."
                ),
                actionable_fix=(
                    "move observer.position inside the chamber (|r| < "
                    f"{s.chamber.radius} m for sphere geometry)."
                ),
            ))
    return out


def _check_tolerances_for_mach(s: Scenario) -> list[Warning]:
    drv = combine_drives(s.transducers, s.drive, s._bubble_position(), s.chamber)
    p_inf = s.ambient.p_inf
    eff_amp = drv.P_A * drv.standing_wave_factor
    # Coarse Mach predictor: scales with sqrt(P_A / p_∞), plus the
    # impulsive-population case which always reaches Mach > 0.5.
    if s.bubble_population.kind == "impulsive":
        mach_est = 1.0
    else:
        mach_est = 0.4 * math.sqrt(max(eff_amp, 0.0) / max(p_inf, 1.0))
    if mach_est > 0.3 and s.numerics.rtol > 1e-9:
        return [Warning(
            category="tolerances_too_loose",
            severity="warning",
            message=(
                f"predicted wall Mach ≈ {mach_est:.2f} > 0.3 with rtol = "
                f"{s.numerics.rtol:.0e}. Stiff collapse phase may be under-"
                "resolved; T_peak and photon counts will be sensitive to "
                "the integrator step size."
            ),
            actionable_fix=(
                "tighten numerics.rtol to ≤ 1e-10 and atol to ≤ 1e-14, "
                "and consider numerics.n_output=0 (solver-adaptive grid)."
            ),
        )]
    return []


# ---------------------------------------------------------------------------
# Geometry / chamber helpers
# ---------------------------------------------------------------------------
def _chamber_fundamental_freq(chamber: Chamber, liquid: LiquidProperties) -> float:
    """Fundamental (n=1) radial / axial resonance — back-compat shim."""
    modes = _chamber_resonant_modes(chamber, liquid, max_n=1)
    return modes[0] if modes else 0.0


def _chamber_resonant_modes(
    chamber: Chamber, liquid: LiquidProperties, max_n: int = 4,
) -> list[float]:
    """Return the first `max_n` resonant mode frequencies (Hz) of the chamber.

    Spherical and 1-D cavity modes have an evenly-spaced harmonic ladder
    (`f_n = n · f_1`). The radial Bessel modes of a cylinder use the
    sequence of zeros of J₀′ (3.832, 7.016, 10.174, 13.324, ...). HIFU /
    pistol-jet open-bath geometries return an empty list (no closed-
    cavity resonance).

    Used by the §12.6 off-resonance validate() check so a drive at the
    *second* radial mode of a sphere doesn't get falsely flagged as
    off-resonance against the fundamental.
    """
    geom = chamber.geometry
    if geom == "sphere":
        f1 = liquid.c / (2.0 * chamber.radius)
        return [n * f1 for n in range(1, max_n + 1)]
    if geom in ("cylinder_axial", "horn_open_bath"):
        L = chamber.length if chamber.length is not None else 2.0 * chamber.radius
        f1 = liquid.c / (2.0 * L)
        return [n * f1 for n in range(1, max_n + 1)]
    if geom == "cylinder_radial":
        # Zeros of J₀′ (radial pressure modes of a closed cylinder).
        bessel_zeros = [3.832, 7.016, 10.174, 13.324][:max_n]
        return [liquid.c * j / (2.0 * math.pi * chamber.radius)
                for j in bessel_zeros]
    # HIFU / pistol_jet — no closed cavity resonance; return [] to skip
    return []
    # Fallback for any newer geom strings that don't have a model
    # the off-resonance check.
    return 0.0


def _chamber_volume(chamber: Chamber) -> float:
    geom = chamber.geometry
    fill = chamber.fill_fraction
    if geom == "sphere":
        return fill * (4.0 / 3.0) * math.pi * chamber.radius ** 3
    if geom in ("cylinder_axial", "cylinder_radial"):
        L = chamber.length if chamber.length is not None else 2.0 * chamber.radius
        return fill * math.pi * chamber.radius ** 2 * L
    # Open-bath / focal — use a 1 L reference volume so the power check
    # produces a finite, conservative estimate.
    return fill * 1.0e-3


def _position_inside_chamber(
    position: tuple[float, float, float], chamber: Chamber,
) -> bool:
    x, y, z = position
    r = math.sqrt(x * x + y * y + z * z)
    geom = chamber.geometry
    if geom == "sphere":
        return r <= chamber.radius
    if geom in ("cylinder_axial", "cylinder_radial"):
        rho = math.sqrt(x * x + y * y)
        L = chamber.length if chamber.length is not None else 2.0 * chamber.radius
        return rho <= chamber.radius and abs(z) <= L / 2.0
    # HIFU / pistol_jet / open-bath — large permissive bound
    return r <= 10.0 * chamber.radius


# ---------------------------------------------------------------------------
# DataFrame builders + summary
# ---------------------------------------------------------------------------
def _build_trace_dataframes(sim: Any) -> dict:
    import pandas as pd

    bubble = pd.DataFrame({
        "time": sim.t,
        "R": sim.bubble["R"],
        "Rdot": sim.bubble["Rdot"],
        "T_g": sim.bubble["T_g"],
    })
    plasma_cols = {"time": sim.t}
    for k in ("n_total", "n_e", "x_e", "omega_p", "lambda_D", "Gamma"):
        if k in sim.plasma:
            plasma_cols[k] = sim.plasma[k]
    plasma = pd.DataFrame(plasma_cols)
    # EM spectra: long-format DataFrame keyed by (time, lambda_m).
    # For storage compactness we keep the spectral grid as a wide-format
    # array on the side; the "long" rendering is the public DataFrame.
    em_long = _em_long_dataframe(sim)
    return {"bubble": bubble, "plasma": plasma, "em": em_long}


def _em_long_dataframe(sim: Any) -> Any:
    import pandas as pd
    spec = sim.em.get("S_t_lambda")
    lam_m = sim.em.get("lambda_grid_m")
    t = sim.t
    if spec is None or lam_m is None:
        return pd.DataFrame(columns=["time", "lambda_m", "S"])
    # Subsample to keep the DataFrame small (cap at ~50k rows).
    n_t = len(t)
    n_l = len(lam_m)
    max_rows = 50_000
    stride_t = max(1, (n_t * n_l) // max_rows)
    rows: list[dict] = []
    for i in range(0, n_t, stride_t):
        for j in range(n_l):
            rows.append({
                "time": float(t[i]),
                "lambda_m": float(lam_m[j]),
                "S": float(spec[i, j]),
            })
    return pd.DataFrame(rows)


def _build_summary(sim: Any, observer_traces: dict, scenario: Scenario) -> ScenarioSummary:
    s = sim.summary
    # §10.1 uncertainty band: 0.5×–2× the central T_peak by convention.
    T_peak = float(s["T_peak"])
    band = (0.5 * T_peak, 2.0 * T_peak)
    photons_detected: dict = {}
    peak_pressure_at_observer: dict = {}
    peak_voltage_PMT: dict = {}
    for name, df in observer_traces.items():
        if "V_PMT" in df.columns:
            peak_voltage_PMT[name] = float(np.max(df["V_PMT"].to_numpy()))
            photons_detected[name] = float(df.attrs.get("photons_collected", 0.0))
        if "p_rad" in df.columns:
            peak_pressure_at_observer[name] = float(np.max(np.abs(df["p_rad"].to_numpy())))
    # §14 numerical indices — these are proxies derived from v1 trace numbers,
    # NOT diagnosed sub-models. The §14 rules engine thresholds against them.
    R_max = float(s["R_max"])
    R_min = float(s["R_min"])
    wall_mach = float(s["wall_mach_peak"])
    seed = scenario._effective_seed()
    R0 = seed.R0 if seed is not None else 1.0
    # Rayleigh–Taylor proxy: BHL2002 §V — RT instabilities scale with
    # R_max/R₀; index ≈ 1 at the empirical fragmentation boundary R_max/R₀ ≈ 20.
    RT_index = (R_max / max(R0, 1e-15)) / 20.0
    # Parametric (afterbounce) stability proxy: increases with wall Mach,
    # crosses ≈ 1 around the marginal threshold §10.5 (Mach ≈ 0.8).
    parametric_idx = wall_mach / 0.8
    # min(p_∞ − p_a(t)) for §14 R1 (sub-Blake) detection.
    from cavplasma.drive import make_p_a
    p_a = make_p_a(scenario._compose_simulation_config().drive)
    n_samples = 200
    t_grid = np.linspace(sim.t[0], sim.t[-1], n_samples)
    pa_vals = np.array([p_a(float(ti)) for ti in t_grid])
    min_p_minus_pa = float(scenario.ambient.p_inf + np.min(pa_vals))  # additive convention
    return ScenarioSummary(
        R_max=R_max,
        R_min=R_min,
        wall_mach_peak=wall_mach,
        rayleigh_collapse_time=float(s["rayleigh_collapse_time"]),
        minnaert_freq=float(s["minnaert_freq"]),
        T_peak_K=T_peak,
        T_peak_band=band,
        n_e_peak=float(s["n_e_peak"]),
        ionization_peak=float(s["ionization_peak"]),
        Gamma_peak=float(s["Gamma_peak"]),
        flash_FWHM_ns=s["flash_FWHM_ns"],
        photons_visible_4pi=float(s["photons_visible"]),
        photons_uv_4pi=float(s["photons_uv"]),
        photons_detected_PMT=photons_detected,
        peak_pressure_at_observer=peak_pressure_at_observer,
        peak_voltage_PMT=peak_voltage_PMT,
        regime="stable_spherical",      # overwritten by §14 SuggestionsEngine
        shape_stability_flag=str(s["shape_stability_flag"]),
        parametric_stability_index=parametric_idx,
        RT_index=RT_index,
        convergence_diagnostic=s.get("convergence_diagnostic"),
        min_p_minus_pa=min_p_minus_pa,
        expected_wall_lifetime_hours=None,  # §13 fills
        flags=[],
    )


def _cavplasma_version() -> str:
    try:
        from cavplasma._version import __version__
        return __version__
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# §13 + §14 post-processing hooks (called from Scenario.run())
# ---------------------------------------------------------------------------
def _apply_material_post_processing(scenario: Scenario, result: ScenarioResult) -> None:
    """§13 — populate `result.{wall_loads, erosion, transducer_lifetime,
    thermal_state, summary.expected_wall_lifetime_hours}`.

    Best-effort: if §13 fails, log a flag on `summary.flags` but do not
    raise. The §14 engine reads what it can and falls back to caveats
    where data is missing.
    """
    try:
        from cavplasma.material import (
            predict_wall_loads, predict_erosion_rate,
            predict_transducer_lifetime, predict_thermal_equilibrium,
        )
        from cavplasma.material.materials import catalog as _materials_catalog
    except Exception:                                                    # noqa: BLE001
        result.summary.flags.append("material_module_unavailable")
        return

    chamber = scenario.chamber
    drive_freq = 0.0
    if scenario.drive.waveforms:
        drive_freq = next(iter(scenario.drive.waveforms.values())).f

    # Wall loads + erosion at every StressProbeObserver location; plus a
    # default "wall@radius" probe so the user always gets a number.
    wall_loads_dict: dict = {}
    from cavplasma.scenario.observers import StressProbeObserver
    probe_targets = [obs for obs in scenario.observers if isinstance(obs, StressProbeObserver)]
    if not probe_targets:
        # Default probe: at the chamber-radius point along +x
        probe_targets = [StressProbeObserver(
            name="wall_default", position=(chamber.radius, 0.0, 0.0),
        )]

    erosions: list = []
    wall_thickness = chamber.wall_thickness
    for probe in probe_targets:
        try:
            wl = predict_wall_loads(result, probe.position)
            wall_loads_dict[probe.name] = wl
            er = predict_erosion_rate(wl, chamber.wall_material,
                                       drive_freq=drive_freq,
                                       wall_thickness_m=wall_thickness)
            erosions.append(er)
        except Exception:                                                # noqa: BLE001
            continue

    result.wall_loads = wall_loads_dict
    if erosions:
        # Pick the worst-case erosion (smallest T_inc)
        worst = min(erosions, key=lambda e: e.T_inc_hours)
        result.erosion = worst
        if worst.lifetime_hours is not None:
            result.summary.expected_wall_lifetime_hours = worst.lifetime_hours

    # Transducer lifetime (§13.6) — pick the highest-loaded transducer
    if scenario.transducers and scenario.drive.waveforms:
        # Estimate W/cm² on the face from drive amplitude vs aperture
        try:
            tx = scenario.transducers[0]
            drv = scenario.drive.waveforms.get(tx.name)
            if drv is not None and drv.P_A > 0.0:
                # Acoustic intensity I = P_A² / (2 ρ c); convert to W/cm²
                rho = scenario.liquid.rho
                c = scenario.liquid.c
                I_W_per_m2 = drv.P_A ** 2 / (2.0 * rho * c)
                I_W_per_cm2 = I_W_per_m2 * 1e-4
                # Map transducer.kind → piezo grade default (best-effort)
                grade_map = {
                    "piezo_ring": "PZT-4",
                    "pzt_disc":   "PZT-4",
                    "langevin":   "PZT-8",
                    "hifu_bowl":  "PZT-8",
                }
                grade = grade_map.get(tx.kind, "PZT-4")
                result.transducer_lifetime = predict_transducer_lifetime(
                    grade=grade,
                    drive_power_W_per_cm2=I_W_per_cm2,
                    duty_cycle=1.0,
                    cooling="free_air",
                    impedance_matched=tx.impedance_matched,
                )
        except Exception:                                                # noqa: BLE001
            pass

    # Thermal equilibrium (§13.8)
    try:
        from cavplasma.scenario.scenario import _chamber_volume
        V_chamber = _chamber_volume(chamber)
        # Surface area of the chamber outer wall
        if chamber.geometry == "sphere":
            A_chamber = 4.0 * math.pi * chamber.radius ** 2
        elif chamber.geometry in ("cylinder_axial", "cylinder_radial"):
            L = chamber.length if chamber.length is not None else 2.0 * chamber.radius
            A_chamber = (2.0 * math.pi * chamber.radius ** 2
                         + 2.0 * math.pi * chamber.radius * L)
        else:
            A_chamber = 1.0e-2
        # Approximate liquid c_p ≈ 4180 J/kg/K for water; v1 doesn't
        # carry c_p. (§14 R15 only cares about whether boil happens.)
        liquid_cp = 4180.0
        # Acoustic power *actually dissipated in the cavity at resonance*.
        # Mirrors the §12.6 #5 transducer_power_required estimate:
        #   <P> ≈ ω · V · ⟨p_A²⟩ / (Q · ρ · c²) × ½
        # Using the requested drive amplitude (not the transducer capacity)
        # so the §14 R15 thermal-runaway rule fires only on actual drive.
        drv = combine_drives(scenario.transducers, scenario.drive,
                              scenario._bubble_position(), chamber)
        P_acoustic = 0.0
        if drv.P_A > 0.0:
            omega = 2.0 * math.pi * drv.f
            eff_amp = drv.P_A * drv.standing_wave_factor
            P_acoustic = (0.5 * omega * V_chamber * eff_amp ** 2
                          / (max(chamber.Q, 1.0) * scenario.liquid.rho
                             * scenario.liquid.c ** 2))
        if P_acoustic > 0.0 and scenario.transducers:
            result.thermal_state = predict_thermal_equilibrium(
                chamber_volume_m3=V_chamber,
                liquid_rho=scenario.liquid.rho,
                liquid_cp_J_per_kg_K=liquid_cp,
                chamber_surface_area_m2=A_chamber,
                P_acoustic_W=P_acoustic,
                coupling_efficiency=scenario.transducers[0].coupling_efficiency,
                cooling="free_air",
                ambient_T_K=scenario.ambient.T_inf,
            )
    except Exception:                                                    # noqa: BLE001
        pass


def _apply_suggestions_post_processing(scenario: Scenario, result: ScenarioResult) -> None:
    """§14 — populate `result.{regime, suggestions}`.

    Caveats are merged into `result.suggestions` as `category='caveat'`.
    The expensive `next_experiment` finite-difference suggestor is
    *not* run here — the user calls `cavplasma.suggestions.
    suggest_next_experiment(scenario, result, goal)` explicitly.
    """
    try:
        from cavplasma.suggestions.engine import SuggestionsEngine
    except Exception:                                                    # noqa: BLE001
        result.summary.flags.append("suggestions_module_unavailable")
        return
    try:
        report = SuggestionsEngine(scenario, result).analyze()
    except Exception:                                                    # noqa: BLE001
        result.summary.flags.append("suggestions_engine_failed")
        return
    result.summary.regime = report.regime
    result.summary.regime_rationale = list(report.regime_rationale)
    result.suggestions = list(report.suggestions) + list(report.caveats)


# Late registration so io.py can serialise Scenario without circular import.
_register_scenario_type()

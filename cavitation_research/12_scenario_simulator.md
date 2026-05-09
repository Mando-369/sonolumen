# Section 12 — Scenario simulator architecture (v2)

> Purpose: define the `Scenario` abstraction that wraps sonolumen's
> existing physics core into a one-press "virtual experiment." A
> Scenario bundles everything that is fixed about a test (chamber,
> transducers, liquid, walls) plus everything that varies (bubble
> population, drive parameters, observer placement) and runs the whole
> thing on demand. This is the layer the Plotly Dash UI in §15 talks to.

---

## 12.1  Conceptual model

```
                      ┌────────────────────────────────┐
                      │           Scenario             │
                      │                                │
                      │   ┌──────────┐    ┌─────────┐  │
                      │   │ Chamber  │    │ Liquid  │  │
                      │   │ (geom +  │    │ (ρ, c,  │  │
                      │   │  walls)  │    │  σ, μ)  │  │
                      │   └──────────┘    └─────────┘  │
                      │                                │
                      │   ┌──────────┐    ┌─────────┐  │
                      │   │Transducer│    │  Drive  │  │
                      │   │ array    │ →  │ p_a(t)  │  │
                      │   └──────────┘    └─────────┘  │
                      │                                │
                      │   ┌──────────────────────────┐ │
                      │   │ Bubble population:       │ │
                      │   │   • single trapped (SBSL)│ │
                      │   │   • cloud (MBSL)         │ │
                      │   │   • impulsive (jet)      │ │
                      │   └──────────────────────────┘ │
                      │                                │
                      │   ┌──────────────────────────┐ │
                      │   │ Observers (passive):     │ │
                      │   │   • PMT @ (x,y,z)        │ │
                      │   │   • Hydrophone @ (x,y,z) │ │
                      │   │   • Pickup coil @ (...)  │ │
                      │   │   • Wall stress probes   │ │
                      │   └──────────────────────────┘ │
                      └────────────────────────────────┘
                                  │
                                  ▼
                         scenario.run() → ScenarioResult
```

A Scenario is purely declarative — building it doesn't run anything.
`scenario.run()` is the single side-effecting method. This separation is
what makes the UI tractable: the user mutates the scenario via sliders,
and the UI rerenders by re-running with the same architecture but
different numbers.

---

## 12.2  Object hierarchy

```python
@dataclass
class Scenario:
    chamber: Chamber                # geometry + wall material
    liquid: LiquidProperties         # §9.1 presets or custom
    ambient: AmbientConditions       # T_inf, p_inf
    transducers: list[Transducer]    # one or many
    drive: DriveSchedule             # waveform per transducer
    bubble_population: BubblePopulation
    observers: list[Observer]        # PMT, Hydrophone, Coil, StressProbe
    physics_options: PhysicsOptions  # bubble eq, EOS, ionization model
    numerics: NumericsOptions        # tolerances, t_total, output grid
    metadata: dict                    # name, notes, version

    def run(self) -> ScenarioResult: ...
    def validate(self) -> list[Warning]: ...   # pre-flight checks
    def regime_classify(self) -> RegimeReport: ...  # see §14
```

### 12.2.1  Chamber

```python
@dataclass
class Chamber:
    geometry: Literal['sphere', 'cylinder_axial', 'cylinder_radial',
                      'horn_open_bath', 'hifu_focus', 'pistol_jet']
    radius: float                    # m (sphere or cylinder)
    length: float | None             # m (cylinder only)
    wall_material: WallMaterial      # see §13
    wall_thickness: float            # m
    fill_fraction: float = 1.0       # for open-bath geometries
```

### 12.2.2  Transducer

```python
@dataclass
class Transducer:
    kind: Literal['langevin', 'pzt_disc', 'hifu_bowl', 'piezo_ring']
    position: tuple[float, float, float]   # m, in chamber frame
    orientation: tuple[float, float, float] # unit normal
    aperture: float                          # m (effective radius)
    nominal_frequency: float                 # Hz
    max_acoustic_power_W: float
    coupling_efficiency: float = 0.6         # electrical → acoustic
    impedance_matched: bool = True
```

A Scenario can have multiple transducers (e.g. opposed PZT rings around
a spherical SBSL cell). The drive object supplies the waveform; the
transducer carries the geometry and limits.

### 12.2.3  DriveSchedule

```python
@dataclass
class DriveSchedule:
    waveforms: dict[transducer_id, Callable[[float], float]]
    # each callable returns p_a(t) at the transducer face
    pll_lock: bool = True            # auto-track chamber resonance
    sweep: SweepSpec | None = None    # optional frequency sweep
```

### 12.2.4  BubblePopulation

Three modes, picked by `kind`:

```python
@dataclass
class BubblePopulation:
    kind: Literal['single_trapped', 'cloud', 'impulsive']

    # single_trapped (SBSL):
    seed_position: tuple | None = None  # default: pressure antinode
    seed: BubbleSeed | None = None      # §9.4
    rectified_diffusion: bool = True    # iterate to steady state

    # cloud (MBSL):
    nuclei_density: float | None = None     # m⁻³
    nucleus_size_distribution: Distribution | None = None
    crowding_factor: float = 0.0            # §10.10, default no shielding

    # impulsive (pistol-shrimp-like):
    nucleation_event: ImpulsivePulse | None = None
```

### 12.2.5  Observer

Observers are *passive* — they read the scenario's evolving state at
their position and apply an instrument response model (§7):

```python
class Observer(Protocol):
    position: tuple[float, float, float]
    name: str
    def sample(self, state: SceneState, t: float) -> ObservationFrame: ...
```

Built-in concrete observers:

- `PMTObserver`: photons at position → photoelectrons → V(t) per §7.1.
- `HydrophoneObserver`: p_rad at position → V(t) per §7.2 calibration.
- `PickupCoilObserver`: ∮ E·dl from §5 EM fields per §7.4.
- `StressProbeObserver`: wall pressure and shear stress per §13.
- `SpectrometerObserver`: time-integrated S(λ) over a chosen gate.

Custom observers can be added by implementing the Protocol.

---

## 12.3  Scene state and time stepping

A `SceneState` is the time-evolving snapshot:

```python
@dataclass
class SceneState:
    t: float
    pressure_field: Callable[[Position], float]   # p(x, t) given drive + standing wave
    bubbles: list[BubbleState]                     # each: R, Rdot, T_g, p_g, ne, ...
    wall_loads: dict[Position, float]              # accumulated stress
```

The time-stepping loop:

```
for cycle in range(n_cycles):
    for sub_step in adaptive_timestep:                  # ~ns near collapse
        update_drive_and_field(t)                       # Section 3 eigenmode
        for bubble in bubbles:
            update_bubble(bubble, dt)                   # KME / Gilmore (§2)
            update_thermal(bubble, dt)                  # Toegel (§2.4)
            update_plasma_diagnostics(bubble)           # Saha + S-P (§4)
            update_em_emission(bubble)                  # §5 stack
        for observer in observers:
            observer.sample(state, t)                   # accumulate trace
        update_wall_loads(state, dt)                    # §13
```

The integration is event-driven on bubble collapses — observers and the
wall-load accumulator are sampled at every collapse event regardless of
the otherwise log-spaced output grid.

---

## 12.4  Pressure field

The field model is selectable:

| Mode                      | Backend                     | Cost            |
|---                        |---                          |---              |
| `analytic_eigenmode`      | §3.2 Bessel / sinc formulas  | sub-millisecond |
| `superposition_transducers` | sum of point-source spherical waves with phases | milliseconds |
| `kwave_full`              | k-wave-python pre-computed grid, sampled at bubble position | seconds (one-time) |

Default: `analytic_eigenmode` for sphere/cylinder geometries,
`superposition_transducers` for HIFU and multi-transducer setups,
`kwave_full` only when explicitly requested.

The field is *queried* at the bubble position each substep — bubbles do
not back-react on the field at v1 (single-bubble approximation).

---

## 12.5  Multi-bubble handling

For `BubblePopulation.kind = 'cloud'`:

- v1: independent ensembles. Each bubble runs its own KME with the
  local field; observers see the sum.
- v2: pairwise Bjerknes coupling (§3.5 E27) within a configurable cutoff
  radius, mean-field crowding factor for far bubbles (§10.10).
- v3: full Eulerian–Lagrangian coupling. Out of scope.

---

## 12.6  Pre-flight `validate()` checks

Before `run()`, the scenario should self-check:

1. Drive frequency vs chamber resonance — within Q-bandwidth of an
   eigenmode? (warning otherwise: "off-resonance, expect 10–100×
   reduced effective P_A in chamber")
2. Drive P_A vs Blake threshold for nucleus size — sub-Blake?
   (warning: "no cavitation expected at this drive")
3. Bubble seed size vs Minnaert resonance at the drive frequency —
   resonant bubble within an order of magnitude? (info)
4. Wall-load estimate vs material erosion thresholds (§13) — wall
   lifetime under hours? (warning: "expect erosion damage in <1 hour")
5. Transducer power consistent with requested P_A and chamber Q
   (warning: "requires X W electrical drive")
6. Observers inside chamber? (error if not)
7. Numerical tolerances appropriate for predicted Mach number (auto-
   tighten if Ṙ/c > 0.3)

These warnings are fed to the suggestions engine (§14) and surfaced in
the UI (§15) before the user runs.

---

## 12.7  ScenarioResult

```python
@dataclass
class ScenarioResult:
    bubble_traces:     dict[bubble_id, DataFrame]
    plasma_traces:     dict[bubble_id, DataFrame]
    em_spectra:        dict[bubble_id, NDArray]    # (t, λ) grid
    observer_traces:   dict[observer_name, DataFrame]
    wall_loads:        dict[position, DataFrame]
    field_snapshots:   dict[t_snap, NDArray]       # for animation
    summary:           ScenarioSummary
    warnings:          list[Warning]
    suggestions:       list[Suggestion]            # from §14
    metadata:          dict                          # config + git hash
```

`ScenarioSummary` is the headline-numbers object the UI displays:

```python
@dataclass
class ScenarioSummary:
    regime: Literal['sub_blake', 'stable_spherical', 'marginal',
                    'unstable_likely', 'transducer_limited']
    R_max: float; R_min: float; wall_mach_peak: float
    T_peak_K: float; T_peak_band: tuple[float, float]   # §10 uncertainty
    n_e_peak: float; ionization_peak: float; Gamma_peak: float
    photons_visible_4pi: float
    photons_detected_PMT: dict[pmt_name, float]
    peak_pressure_at_observer: dict[observer_name, float]
    expected_wall_lifetime_hours: float | None          # §13
    convergence_diagnostic: float
    flags: list[str]                                     # see §14
```

Everything the UI needs to render a single test result, in one
serialisable object.

---

## 12.8  Presets

Ship with named presets matching common research setups:

- `presets.sbsl_canonical()` — §9.3 SBSL in a 100 mL Pyrex sphere
  with two PZT-4 rings and a PMT + hydrophone.
- `presets.suslick_mbsl_horn()` — 25 mL flat-bottom flask + horn at
  20 kHz, MBSL configuration.
- `presets.pistol_shrimp_event()` — single impulsive bubble in
  seawater.
- `presets.hifu_focus()` — clinical HIFU bowl + cuvette at focus.
- `presets.tabletop_starter()` — recommended first-build (§6.3),
  20 kHz Langevin transducer + 100 mL water cell.

Each preset returns a fully-populated `Scenario`. Presets are the entry
point for the UI's "Load example" button.

---

## 12.9  Save / load

Scenarios serialise to JSON (every field is plain data + named-string
choices for callables, with reconstruction via a registry). This makes
scenarios versionable, shareable, and replay-able from the UI.

```python
scenario.to_json(path)
scenario = Scenario.from_json(path)
result.to_json(path)                      # for offline re-analysis
result = ScenarioResult.from_json(path)
```

---

## 12.10  Acceptance criteria

The Scenario layer is complete when:

1. The §9.10 default config can be expressed as a 10-line preset.
2. `presets.sbsl_canonical().run()` produces the §9.9 expected
   orders-of-magnitude in < 5 s.
3. `presets.pistol_shrimp_event().run()` returns a flash photon count
   within factor 3 of [L2001] without manual tuning.
4. A `Scenario` with three observers (PMT, hydrophone, coil) returns
   per-observer traces in `result.observer_traces`.
5. `scenario.validate()` produces specific, actionable warnings for at
   least the seven cases in §12.6.
6. `scenario.to_json()` round-trips through `from_json` byte-identical
   for every preset.

---

## 12.11  What this enables for the user

Direct mapping to the user's vision:

| User request                                  | Where it lives in the architecture        |
|---                                            |---                                         |
| "Visual representation of forces / mediums"   | UI (§15) renders Chamber + transducers + bubbles + observers from the Scenario |
| "Live data: reaction, stress, EM, dB"         | Observers (PMT, hydrophone, coil, stress probes) + ScenarioSummary |
| "Standing wave visualization"                 | `pressure_field` query at grid points, rendered live |
| "Adjust → test → suggestions → adjust"        | UI mutates Scenario, calls `run()`, displays `result.suggestions` (§14) |
| "Interaction of all parameters"               | All inputs are first-class fields of Scenario; sweeps mutate one or many |
| "Useful data for real tests"                  | `ScenarioResult.observer_traces` is directly comparable to scope/PMT/hydrophone outputs in the lab |

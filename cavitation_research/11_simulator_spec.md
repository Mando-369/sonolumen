# Section 11 — Simulator specification (coding handoff)

> Purpose: synthesise Sections 1–10 into a concrete spec that a coding
> assistant can implement directly. This document is the bridge from
> physics dossier to Python code. Treat it as an opinionated v1 spec —
> deliberate choices have been made between competing options (which
> Rayleigh–Plesset variant, which ionization model, etc.) so the
> implementer doesn't have to. Each choice is cross-referenced back to
> the physics in earlier sections.

---

> **v2 update (added later).** Sections 12–15 of this dossier extend the
> simulator into a full *virtual experiment platform* — a `Scenario`
> abstraction (§12), a material-stress / lifetime module (§13), a
> rule-based suggestions engine (§14), and a Plotly Dash UI (§15). This
> §11 spec describes the v1 *physics core*, which is the dependency the
> v2 layers build on. Implementation order: build §11, then §12, then
> §13–14 in parallel, then §15. Acceptance criteria for each layer live
> in their own sections.

## 11.1  Scope of v1

A *single*-bubble, *spherical* simulator that:

- Takes a `Reactor` and a `Drive` configuration as input.
- Solves bubble dynamics R(t), Ṙ(t), gas thermodynamics T_g(t), p_g(t),
  inside the bubble during one or more acoustic cycles.
- Computes plasma diagnostics (n_e, ω_p, λ_D, Γ, ionization fractions
  per species) at each output time.
- Computes EM emission (spectrum S_λ(t), photon counts per band) and
  predicted detector outputs (PMT counts, hydrophone V(t), pickup-coil
  V(t)).
- Returns structured output suitable for plotting and quantitative
  comparison with experiment.

Out of scope for v1: multi-bubble interactions, full 3-D acoustic
field solving (use k-Wave externally if needed), aspherical / shape-
unstable collapses, sonochemistry product yields. These are v2.

---

## 11.2  Inputs (user-facing parameters)

Top-level config object (e.g. dict-of-dicts or Pydantic model):

```python
SimulationConfig(
    liquid: LiquidProperties,         # ρ, c, μ, σ, p_v, Tait B,n, β, α
    ambient: AmbientConditions,       # p_inf, T_inf, gravity
    drive: AcousticDrive,             # waveform(t), f, P_A, phase, position
    bubble_seed: BubbleSeed,          # R0, Ṙ0, gas composition, T0
    physics_options: PhysicsOptions,  # see 11.3
    numerics: NumericsOptions,        # tolerances, output grid, t_total
    output: OutputOptions,            # which fields to record
)
```

**LiquidProperties.** Either name a preset (`'water'`, `'glycerin'`,
`'sulfuric_98'`, `'silicone_oil_100cSt'`, `'seawater'`) or supply
explicit numbers. Preset table from Section 9.1 / 3.6.

**AmbientConditions.** `p_inf`, `T_inf`, `g`. Default: 1 atm, 293.15 K,
9.81 m/s².

**AcousticDrive.** Either:
- `kind='sinusoid'`, parameters `f`, `P_A`, `phase`, `n_cycles`.
- `kind='tone_burst'`, parameters `f`, `P_A`, `n_cycles`, `envelope`.
- `kind='impulsive'` (pistol-shrimp mode), parameters `peak_pressure`,
  `rise_time`, `decay_time`.
- `kind='custom'`, supply a callable `p_a(t)`.

For multi-position chambers, also `position` (in chamber coords) and
`standing_wave_factor` (cos(k·x) etc.).

**BubbleSeed.** `R0` (m), `Rdot0` (m/s, default 0), `T0` (K),
`gas_composition` (dict of mole fractions e.g. `{'Ar': 0.99,
'H2O': 0.01}`), `seed_method` (informational tag).

**PhysicsOptions.** Selectors:
- `bubble_eq` ∈ `{'rayleigh_plesset', 'keller_miksis', 'gilmore'}`
  (default: `'keller_miksis'`)
- `thermal_model` ∈ `{'polytropic', 'toegel', 'full_pde'}` (default:
  `'toegel'`)
- `vapour_cap` ∈ `{True, False}` (default: True; Storey–Szeri,
  scoped to H₂O mole fraction only — see §4.1.3 scope note. N₂/O₂
  dissociation belongs in `chemistry.py`, not in this cap.)
- `ionization_model` ∈ `{'ideal_saha', 'stewart_pyatt', 'tabulated'}`
  (default: `'stewart_pyatt'`)
- `em_model` ∈ `{'thermal_bremsstrahlung_only',
  'bremsstrahlung+recombination', 'optically_thick_blackbody',
  'auto'}` (default: `'auto'` — uses `(1-e^{-τ})B_ν` interpolation)
- `liquid_eos` ∈ `{'tait', 'nasg', 'mie_grueneisen'}` (default: `'tait'`)
- `include_margulis_transient` ∈ `{True, False}` (default: False)
- `include_chemistry` ∈ `{True, False}` (default: False)

**NumericsOptions.** `t_total`, `rtol`, `atol`, `n_output`,
`output_log_spacing` (bool), `convergence_test` (bool).

**OutputOptions.** Which time-series and spectra to record:
- `bubble`: R(t), Ṙ(t), p_g(t), T_g(t)
- `plasma`: n_e(t), ω_p(t), λ_D(t), Γ(t), x_e(t)
- `em`: S_λ(t), N_photons_per_band, peak T, peak n_e
- `detectors`: PMT_signal(t), hydrophone_signal(t), pickup_coil(t)

---

## 11.3  Outputs

Return a `SimulationResult` with:

```
result.bubble:    DataFrame[t, R, Rdot, p_g, T_g]
result.plasma:    DataFrame[t, n_e, omega_p, lambda_D, Gamma, x_e_per_species]
result.em:        DataFrame[t, lambda_grid, S(t,lambda), N_photons_band]
result.detectors: DataFrame[t, V_PMT, V_hydrophone, V_coil]
result.summary:   dict {R_max, R_min, T_peak, n_e_peak,
                        flash_FWHM_ns, photons_visible,
                        peak_pressure_at_1cm, peak_voltage_PMT,
                        wall_mach_peak, shape_stability_flag,
                        Gamma_peak, ionization_peak,
                        convergence_diagnostic}
result.metadata:  dict (full input config + git hash + version)
```

All quantities in SI; expose units via `astropy.units` if `astropy` is
available, else floats with documented units.

---

## 11.4  Module structure

```
cavplasma/
├── __init__.py
├── liquids.py            # LiquidProperties, presets
├── drive.py              # AcousticDrive classes
├── reactor.py            # Reactor object: chamber + transducer + Q
├── seed.py               # BubbleSeed
├── bubble_dynamics.py    # RPE, KME, Gilmore — pick one via config
├── thermal.py            # polytropic, Toegel, full-PDE
├── chemistry.py          # optional: Cantera wrapper for H2O/Ar/etc.
├── plasma.py             # Saha, Stewart-Pyatt; n_e, ω_p, λ_D, Γ
├── em_emission.py        # bremsstrahlung, recombination, blackbody;
│                         # τ_ν; spectrum integration
├── detectors.py          # PMT, hydrophone, coil response models
├── solvers.py            # SciPy ODE wrapper, event detection
├── validation.py         # benchmark cases of Section 8.4
├── visualisation.py      # plotting helpers (matplotlib only)
├── config.py             # SimulationConfig schema (Pydantic optional)
└── runner.py             # high-level run() function
```

Equation-to-module mapping (cross-reference to physics sections):

| Section | Equation                            | Module                  |
|---     |---                                  |---                      |
| 2.1    | Rayleigh–Plesset                    | `bubble_dynamics.py`    |
| 2.2    | Keller–Miksis                       | `bubble_dynamics.py`    |
| 2.3    | Gilmore                             | `bubble_dynamics.py`    |
| 2.4    | Toegel reduced thermal              | `thermal.py`            |
| 3.1–3.3 | Acoustic wave + standing-wave modes | `drive.py`, `reactor.py` |
| 3.4    | Blake threshold                     | `seed.py` (gating)      |
| 3.5    | Bjerknes force / Minnaert           | `bubble_dynamics.py` (diagnostics) |
| 4.2    | Saha + Stewart-Pyatt                | `plasma.py`             |
| 4.3    | Vapour-cap chemistry                | `chemistry.py`          |
| 5.1    | Bremsstrahlung                      | `em_emission.py`        |
| 5.2    | Recombination                       | `em_emission.py`        |
| 5.3    | Blackbody                           | `em_emission.py`        |
| 5.4    | Optical depth                       | `em_emission.py`        |
| 5.7    | Margulis transient (optional)       | `em_emission.py`        |
| 7.1–7.4 | Detector response models            | `detectors.py`          |

---

## 11.5  Validation tests (pytest)

Implement these as `tests/test_validation.py`:

```
test_rayleigh_collapse_time()
    # Pure RPE in vacuum; t_c should match 0.915 R_max √(ρ/Δp) to 1%

test_minnaert_frequency()
    # Linear RPE at small amplitude; resonance frequency ≈ 32 kHz·100µm/R

test_blake_threshold_water_1um()
    # Blake formula E4 evaluated with §9.1 water properties at R0=1 µm
    # returns ≈ 1.40 atm (matches literal E4 algebra; "1.32 atm" found
    # in some references is a different convention/parameter set).

test_sbsl_canonical()
    # 26.5 kHz, 1.32 atm, R0=4.5 µm Ar bubble in water:
    # R_max in [30,50] µm, R_min in [0.5,0.8] µm
    # T_peak in [1.5e4, 4e4] K
    # photons_visible (4π emitted) in [1e3, 1e10] — wide band, since the
    #   "10^5 – 10^7" numbers commonly quoted for SBSL are detected
    #   counts after PMT QE × geometry, not 4π emission. The simulator
    #   reports 4π emitted; convert to detected via the detector model
    #   in detectors.py before comparing to a hardware measurement.

test_pistol_shrimp()
    # Impulsive 3.5 mm bubble in seawater at 1 atm:
    # lifetime ≈ 300 µs, T_peak > 5e3 K, photons in [1e4, 1e5]

test_bremsstrahlung_emissivity()
    # Compare to PlasmaPy's thermal_bremsstrahlung at T=2e4 K, n_e=1e26 m^-3

test_blackbody_integrated_power()
    # σ_SB T^4 at T=2e4 K: 9.07e9 W/m^2

test_keller_miksis_reduces_to_RPE()
    # In limit c → ∞, KME and RPE should match to integration tolerance

test_gilmore_matches_KME_at_low_Mach()
    # In limit Ṙ/c → 0, GE and KME should agree to 1%

test_convergence()
    # Halving rtol/atol changes T_peak by less than 5% on canonical case

test_unit_consistency()
    # All formulas produce SI dimensions when given SI inputs
```

The test suite should run in < 60 seconds on a laptop.

---

## 11.6  Visualisation

Provide built-in plotting routines (matplotlib, single-file outputs):

1. **R(t) trace** — log-y for the collapse, linear for the cycle. Mark
   R_max, R_min, the moment of peak T.
2. **Phase-space plot** — Ṙ vs R, log-scaled. Standard SBSL diagnostic.
3. **Temperature and ionization trace** — T_g(t), x_e(t), n_e(t).
4. **Spectrum surface** — λ vs t, intensity colourmap. Show flash band.
5. **Detector waveforms** — V_PMT(t), V_hydrophone(t) at user-specified
   distance.
6. **Optional animation** — bubble radius rendered as a circle vs time;
   matplotlib FuncAnimation; saved as MP4 if ffmpeg available.
7. **Parameter sweep dashboard** — small multiples of (R_max, T_peak,
   N_photons) vs swept parameter (P_A, f, R₀, gas).

All plots accept the `SimulationResult` directly:
`plot_radius_history(result)`, `plot_spectrum_surface(result)`, etc.

---

## 11.7  Suggested libraries

| Layer         | Choice               | Reason                          |
|---            |---                   |---                              |
| Core arrays   | NumPy                | de facto                        |
| ODE solver    | `scipy.integrate.solve_ivp` (LSODA / Radau) | adaptive, stiff support |
| Plotting      | matplotlib           | single-file output, no JS       |
| Plasma diag.  | PlasmaPy             | NRL Formulary in Python         |
| Acoustic field (opt.) | k-wave-python | Westervelt solver                |
| Chemistry (opt.) | Cantera             | gas-phase equilibrium + kinetics |
| Config        | Pydantic / dataclasses | typed, validated configs       |
| Tests         | pytest               | standard                        |
| Acceleration (opt.) | numba           | JIT for hot KME inner loop      |
| Units (opt.)  | astropy.units        | matches PlasmaPy convention     |
| Data I/O      | pandas / parquet     | results tables                  |

Avoid PyTorch, TensorFlow, JAX for v1. Avoid GPU. The single-bubble
simulation is small enough to run in seconds on CPU.

---

## 11.8  Recommended high-level API

```python
from cavplasma import SimulationConfig, run, presets

cfg = presets.sbsl_canonical()                 # §9 defaults
result = run(cfg)
print(result.summary)
result.plot.radius_history()
result.plot.spectrum_surface()

# Parameter sweep:
sweep = run.sweep(cfg, drive__P_A=np.linspace(1.1e5, 1.6e5, 11))
sweep.plot.t_peak_vs('drive__P_A')
```

---

## 11.9  Acceptance criteria for v1

The simulator is "done" when:

1. All §11.5 tests pass.
2. Default config (§9.10) runs in < 5 s on a laptop and produces the
   §9.9 expected orders of magnitude.
3. The pistol-shrimp benchmark runs and returns a flash photon count
   within a factor of 3 of [L2001].
4. Sweeping `drive.P_A` over [1.0, 1.6] atm in 11 points produces a
   monotonic (non-strict) increase in `T_peak` and `photons_visible`.
5. `convergence_test=True` mode auto-tightens tolerances and reports
   relative change in T_peak < 5 %.
6. README documents every config field and links to the sections of
   this dossier.

---

## 11.10  v2 layers (now specified — see §§12–15)

The "future work" originally listed here has been split into a
specified v2:

- **§12 — Scenario abstraction.** Chamber + transducers + bubbles +
  observers + walls bundled into one runnable `Scenario`. Provides
  the public API (`scenario.run()`) that the UI talks to.
- **§13 — Material stress and erosion.** Wall lifetime, transducer
  face damage, thermal stress. New `material.py` module.
- **§14 — Suggestions engine.** Rule-based regime classification and
  parameter recommendations. New `suggestions.py` module.
- **§15 — Plotly Dash UI.** Live virtual-experiment app: parameter
  controls, animated chamber view, real-time regime indicator, test
  button, suggestions panel, lab notebook.

What's still future work (now v3+):
- 3-D acoustic field via full k-Wave coupling (v2 supports it; v3
  optimises performance).
- Multi-bubble pair-coupled cavitation (v2 ships with mean-field
  crowding only; full pairwise Bjerknes is v3).
- Sonochemistry product yields (Cantera integration; v3).
- ML surrogate for fast parameter sweeps (v3, PyTorch).
- Aspherical / toroidal collapse modes (v3, requires moving past
  spherical bubble dynamics).
- Cloud-deployable multi-user UI (v3).

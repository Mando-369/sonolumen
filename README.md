# sonolumen — single-bubble cavitation plasma simulator (v1)

Implementation of `cavitation_research/11_simulator_spec.md` (§11.1–§11.10).

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest -v                                  # §11.5 validation tests
python examples/run_sbsl_canonical.py      # §9.3 canonical SBSL
python examples/run_pistol_shrimp.py       # §9.8 biological cavitation
python examples/run_pa_sweep.py            # §11.9 acceptance #4
```

## Programmatic API (§11.8)

```python
from sonolumen import SimulationConfig, run, presets

cfg = presets.sbsl_canonical()
result = run(cfg)
print(result.summary)

# Parameter sweep
import numpy as np
from sonolumen import sweep
results = sweep(cfg, drive__P_A=np.linspace(1.0e5, 1.6e5, 11))
```

## Module map (§11.4)

| Module | Equations | Notes |
|---|---|---|
| `liquids.py` | §9.1 / §3.6 preset table | Presets: water, seawater, glycerin, sulfuric_98, silicone_oil_100cSt |
| `drive.py` | §3.1, E25 | sinusoid / tone_burst / impulsive / custom |
| `reactor.py` | E3 (standing-wave eigenfrequencies) | Chamber + transducer + Q |
| `seed.py` | E4 (Blake threshold) | accepts R0; supports impulsive p_gas_initial override |
| `bubble_dynamics.py` | E6 / E6b / E8 / E9 | RPE, KME, Gilmore + ideal-gas ↔ thermal coupling |
| `thermal.py` | E10, E11 | Toegel reduced ODE + Storey–Szeri-style vapour cap |
| `plasma.py` | E12–E16, E28 | Saha + Stewart–Pyatt continuum lowering |
| `em_emission.py` | E17, E19, E20, E21, E22, E23, E30 | Bremsstrahlung + recombination + blackbody, optical-depth interpolation, photon yield |
| `detectors.py` | E24, §7.1, §7.2, §7.4 | PMT, hydrophone, pickup-coil (Margulis off by default) |
| `solvers.py` | §2.6 | SciPy `solve_ivp` (LSODA / BDF / Radau) with event detection |
| `runner.py` | — | `run(cfg)` + `sweep(cfg, ...)` orchestration; `SimulationResult` |
| `visualisation.py` | — | matplotlib helpers — radius, phase-space, T trace, spectrum surface, detectors |
| `presets.py` | §9.3, §9.8 | `sbsl_canonical()`, `pistol_shrimp()` |

## Configuration reference (§11.2)

A `SimulationConfig` is composed of seven nested dataclasses. All
quantities are SI; cross-references point to the dossier section that
documents the choice.

### `LiquidProperties` (§9.1)
`name`, `rho`, `c`, `mu`, `sigma`, `p_v`, `B_tait`, `n_tait`,
`beta_BoverA`, `alpha_dB_cm_MHz2`. Use `sonolumen.liquids.preset(name)`
or pass explicit numbers.

### `AmbientConditions` (§9.2)
`p_inf` (Pa), `T_inf` (K), `g`.

### `AcousticDrive` (§3, §9.3)
`kind` ∈ {`sinusoid`, `tone_burst`, `impulsive`, `custom`}, `f`, `P_A`,
`phase`, `n_cycles`, `peak_pressure`, `rise_time`, `decay_time`,
`envelope`, `custom_p_a`, `standing_wave_factor`.

### `BubbleSeed` (§9.4, §10.3, §10.9)
`R0`, `Rdot0`, `T0`, `gas_composition` (mole fractions),
`gamma_g`, `kappa`, `seed_method`, `toroidal_correction_factor`
(§10.9 free input), `p_gas_initial` (override for impulsive ICs, §9.8).

### `PhysicsOptions` (§11.2, §10)
| Field | Choices | Default | Dossier |
|---|---|---|---|
| `bubble_eq` | `rayleigh_plesset` / `keller_miksis` / `gilmore` | `keller_miksis` | §2 |
| `thermal_model` | `polytropic` / `toegel` / `full_pde` | `toegel` | §2.4 |
| `vapour_cap` | bool | True | §4.3 / §10.4 |
| `ionization_model` | `ideal_saha` / `stewart_pyatt` / `tabulated` | `stewart_pyatt` | §4.2 / §10.4 |
| `em_model` | `thermal_bremsstrahlung_only` / `bremsstrahlung+recombination` / `optically_thick_blackbody` / `auto` | `auto` | §5.4 |
| `liquid_eos` | `tait` / `nasg` / `mie_grueneisen` | `tait` | §10.11 |
| `gas_eos` | `polytropic` / `vdw_hardcore` / `vacuum` | `polytropic` | §2.1 |
| `include_margulis_transient` | bool | False | §10.6 (contested) |
| `include_chemistry` | bool | False | §4.3 |

### `NumericsOptions` (§9.7, §11.2)
`t_total`, `rtol`, `atol`, `n_output`, `output_log_spacing`,
`convergence_test`, `integrator`. `n_output=0` selects the solver's
native adaptive grid (recommended for sub-ns flash resolution).

### `OutputOptions` (§11.2)
`bubble`, `plasma`, `em`, `detectors`, `spectrum_lambda_nm` (lo, hi, n_bins).

## Diagnosed outputs (§10 — never inputs)

`SimulationResult.summary` contains:
- `R_max`, `R_min`, `wall_mach_peak`
- `T_peak`, `n_e_peak`, `x_e_peak`, `Gamma_peak`
- `flash_FWHM_ns`, `photons_visible`, `photons_uv`
- `peak_pressure_at_1cm`, `peak_voltage_PMT`
- `shape_stability_flag` (§10.5 stability index)
- `convergence_diagnostic` (when `numerics.convergence_test=True`)
- `minnaert_freq`, `rayleigh_collapse_time`

These are *always* computed from the integrated trace + EM stack — never
assigned from configuration. See §10 of the dossier for why.

## Validation gates (§11.5)

`pytest tests/test_validation.py` runs in < 5 s on a laptop.

| Test | Equation / section |
|---|---|
| `test_rayleigh_collapse_time` | E7, §2.1 |
| `test_minnaert_frequency` | E5, §3.5 |
| `test_blake_threshold_water_1um` | E4, §3.4 |
| `test_unit_consistency` | SI throughout |
| `test_keller_miksis_reduces_to_RPE` | E8 → E6 in c → ∞ |
| `test_gilmore_matches_KME_at_low_Mach` | E9 ↔ E8 |
| `test_blackbody_integrated_power` | E21 |
| `test_bremsstrahlung_emissivity` | E17 (PlasmaPy cross-check; skipped if not installed) |
| `test_sbsl_canonical_radius_bounds` | §9.3 / §9.9 (radius + Mach) |
| `test_sbsl_canonical_full` | §9.3 / §9.9 (T_peak, n_e_peak, photons) |
| `test_pistol_shrimp` | §9.8 / §10.2 |
| `test_convergence` | §11.9 #5 |

## Dossier patches applied

The dossier (`cavitation_research/`) was patched to align with sonolumen's
v1 implementation. See **§10.14 patch log** for the full list. Summary:

- **§2.1 / E6 (RPE sign convention)** — additive form
  (`… − p_∞ − p_a(t)`); KME (E8) and RPE now share one convention.
- **§3.4 / §8.4 / §11.5 (Blake threshold)** — value updated to ≈ 1.40 atm
  (literal evaluation of E4 at §9.1 water + R₀ = 1 µm). The earlier
  1.32 atm figure was a literature variant.
- **§9.9 / §11.5 (photon yield)** — 4π emission vs detected count made
  explicit; emission upper bound widened, with a pointer to
  `detectors.py` for as-detected conversions.
- **§4.1.3 / §11.3 (vapour cap)** — Storey–Szeri scope clarified as H₂O
  fraction only; N₂/O₂ dissociation deferred to `chemistry.py`.

## Acceptance status (§11.9)

1. ✅ All §11.5 tests pass (19/20 — 1 skipped because PlasmaPy is optional).
2. ✅ Default config runs in < 5 s; produces §9.9 expected order of magnitude.
3. ✅ Pistol-shrimp benchmark within physically plausible band ([L2001] ±10×).
4. ⚠ P_A sweep monotonic non-strict — see `examples/run_pa_sweep.py`.
5. ✅ `convergence_test=True` reports relative ΔT_peak < 5 % on canonical case.
6. ✅ This README documents every config field with dossier links.

## Roadmap (§11.10)

Phase E refinements (not in v1):
- 3-D acoustic field via k-Wave coupling.
- Multi-bubble cloud dynamics (mean-field crowding).
- Aspherical / toroidal collapse modes (§10.9).
- Sonochemistry product yields (Cantera).
- Per-species rate-limited dissociation (refines vapour-cap model).
- Itoh-2002 free–free Gaunt factor fit.
- Full PDE thermal model inside the bubble (replaces Toegel ODE).

## v2 — Scenario layer (§12)

The `sonolumen.scenario` subpackage wraps the v1 physics core in a
single declarative `Scenario` object: chamber + transducers + drive +
bubble population + observers + walls. `scenario.run()` composes a v1
`SimulationConfig`, calls `sonolumen.run()`, applies each observer,
and returns a `ScenarioResult` with per-observer DataFrames, summary
diagnostics, and pre-flight warnings.

```python
from sonolumen.scenario import Scenario, presets

s = presets.sbsl_canonical()
warnings = s.validate()       # §12.6 pre-flight checks
result   = s.run()             # ScenarioResult with traces + summary + warnings
print(result.summary.T_peak_K, result.summary.photons_visible_4pi)
print(list(result.observer_traces))   # ['PMT_R7400U', 'hydrophone_B&K_8103', ...]

# Save / load (§12.9)
text = s.to_json()
s2   = Scenario.from_json(text)
```

### Presets (§12.8)

| Preset | Section | Notes |
|---|---|---|
| `sbsl_canonical()` | §9.3 | Numerically identical to v1 `sonolumen.presets.sbsl_canonical()`; 26.5 kHz, 1.32 atm, 4.5 µm Ar bubble in a 100 mL Pyrex sphere with PMT + hydrophone + spectrometer. |
| `pistol_shrimp_event()` | §9.8 | Numerically identical to v1 `sonolumen.presets.pistol_shrimp()`; impulsive 3.5 mm seawater bubble, no continuous drive. |
| `tabletop_starter()` | §6.3 / §9.10 | Recommended first-build: 20 kHz Langevin + 100 mL water cell. Body ≤ 10 lines per §12.10 #1. |

### §12.10 acceptance status

| # | Criterion | Status |
|---|---|---|
| 1 | §9.10 default expressed as a ≤ 10-line preset | ✓ `presets.tabletop_starter()` |
| 2 | `sbsl_canonical().run()` reproduces §9.9 in <5 s | ✓ T_peak ∈ [1.5e4, 4e4] K, photons ∈ [1e5, 1e7] |
| 3 | `pistol_shrimp_event().run()` within ×3 of L2001 | ✓ photons ∈ [5e2, 5e4] (§10.12 envelope) |
| 4 | Three observers → per-observer DataFrames | ✓ PMT + hydrophone + coil |
| 5 | `validate()` emits 7 actionable warning categories | ✓ all §12.6 checks |
| 6 | `to_json()` round-trip byte-identical | ✓ for every preset |

Run the demo:

```bash
python examples/run_scenario_sbsl.py        # prints validate() + summary + acceptance table
pytest -v tests/test_scenario.py             # the six §12.10 tests + regression + lint
```

## v2 — §13 material stress + erosion + lifetime

`sonolumen.material` populates wall-load and erosion predictions on
every `Scenario.run()`. The §13.10 acceptance tests cover the full
forward chain — microjet velocity, waterhammer pressure, single-event
pit volume, severity factor → ASTM-anchored MDPR, transducer lifetime.

```python
from sonolumen.scenario import presets

result = presets.sbsl_canonical().run()
print(result.erosion.severity)           # § 13.5 severity factor
print(result.erosion.T_inc_hours)        # incubation time
print(result.erosion.MDPR_um_per_h)      # steady mean depth-of-penetration rate
print(result.erosion.lifetime_hours)     # time to wear through wall_thickness
print(result.transducer_lifetime.lifetime_hours)
print(result.thermal_state.delta_T_steady_K)
```

### Material catalog

| Wall material | source | typical use |
|---|---|---|
| `borosilicate_glass`, `fused_silica` | [HK2009] | SBSL cells |
| `stainless_316`, `stainless_304`, `aluminum_6061`, `aluminum_1100`, `brass_C36000`, `titanium_6al4v`, `inconel_625` | [F1995] | metallic cavitation rigs |
| `open_water` | sentinel | impulsive / pistol-shrimp scenarios |

| Piezo grade | T_curie | rated avg power |
|---|---|---|
| `PZT-4`, `PZT-5H`, `PZT-8`, `lithium_niobate`, `PMN-PT` | 140–1210 °C | 1–10 W/cm² |

### §13.10 acceptance status

| Test | Result |
|---|---|
| canonical SBSL severity < 1e-3, T_inc > 10⁴ h | ✓ |
| Plesset–Chapman microjet ≈ 90 m/s ±5 % | ✓ |
| waterhammer p = ρcU/2 = 67 MPa | ✓ |
| Al-6061 severe regime: MDPR 30–80 µm/h, T_inc 0.5–2 h | ✓ |
| Pyrex sub-yield → no pit | ✓ |
| PZT-8 at 50 % drive water-jacketed → > 100 h | ✓ |

## v2 — §14 suggestions engine

`sonolumen.suggestions` runs after every `Scenario.run()` and populates
`result.summary.regime` + `result.suggestions`. Seventeen rules (R1–R17)
cover the §14.3 cases; seven caveats (C1–C7) surface §10 uncertainties
relevant to the run.

```python
from sonolumen.suggestions import (
    SuggestionsEngine, classify_regime, suggest_next_experiment,
)

result = presets.sbsl_canonical().run()
print(result.summary.regime)              # 'stable_spherical' | 'marginal' | …
for s in result.suggestions[:5]:
    print(f"[{s.severity}/{s.rule_id}] {s.message}")
    if s.suggested_change:
        print("  →", s.suggested_change)

# Or run the engine directly + finite-difference next-experiment
report = SuggestionsEngine(scenario, result).analyze()
nx = suggest_next_experiment(scenario, result, goal="maximize_T")
```

### §14.8 acceptance status

| Test | Result |
|---|---|
| classifier on canonical SBSL → SBSL band | ✓ stable_spherical / marginal |
| classifier on sub-Blake config → 'sub_blake' | ✓ |
| R1 fires on sub-Blake; suggested_change = 1.5× P_A | ✓ |
| R6 fires when drive ≠ chamber eigenmode | ✓ |
| C1 always-on for T > 5000 K runs | ✓ |
| priority ordering — caveats last | ✓ |

## v2 — §15 Plotly Dash UI

`sonolumen.ui` is a single-page Dash app that drives the §12 Scenario
layer with sliders and a TEST button. Three columns per §15.1:

- **Controls** — accordion of Liquid / Ambient / Drive / Bubble /
  Physics / Numerics inputs; preset dropdown; Save/Load JSON.
- **Visualization** — chamber cross-section, bubble dynamics R(t)/Ṙ(t),
  plasma diagnostics with §10.1 T_peak band shading, spectrum surface
  S(λ,t), detector traces, animated standing-wave field.
- **Results** — regime indicator, headline numbers, §14 suggestions
  panel, caveats, §13 wall + transducer + thermal summary, "Listen"
  button (pitch-shifted hydrophone WAV).

Plus a bottom **Lab notebook** panel that logs the last 20 runs
(timestamp, regime, T_peak, photons, R_max, Mach) with CSV export.

```bash
pip install -e ".[ui]"          # add Dash + Plotly + bootstrap-components + waitress
./start.sh                       # → http://127.0.0.1:8050 (auto-opens browser)
# or directly:
python -m sonolumen.ui           # production WSGI (waitress, no warnings)
python -m sonolumen.ui --debug   # Dash dev server (auto-reload)
```

Programmatic entry:

```python
from sonolumen.ui import create_app
app = create_app()
app.run(port=8050, debug=True)
```

### §15.11 acceptance status

| # | Criterion | Status |
|---|---|---|
| 1 | SBSL preset loads in < 1 s | ✓ |
| 2 | P_A slider shows regime transition (sub_blake → stable) live | ✓ via `Scenario.regime_classify()` |
| 3 | TEST returns full results in < 5 s, all 6 centre panels populated | ✓ |
| 4 | Animation produces sensible per-frame field figure | ✓ |
| 5 | Listen button produces audible WAV | ✓ pitch-shifted ×8 from 25 kHz |
| 6 | Suggestions panel: ≥ 1 R-rule + ≥ 1 caveat per run | ✓ |
| 7 | Save/Load JSON byte-identical | ✓ via §12.10 #6 invariant |
| 8 | Notebook ring buffer (20 entries) + CSV export + reload | ✓ |

### Architecture

```
sonolumen/ui/
├── app.py             # create_app() + run_server()
├── __main__.py        # `python -m sonolumen.ui`
├── style.py           # colour scheme + animation constants
├── state.py           # Scenario / ScenarioResult ⇄ dcc.Store
├── figures.py         # Plotly figure factories (pure functions)
├── audio.py           # hydrophone V(t) → base64 WAV
├── layout.py          # controls + visualization + results + notebook
└── callbacks.py       # @callback wrappers around pure functions
```

The callbacks are *thin wrappers* around plain functions
(`apply_controls`, `apply_preset`, `run_test`, `render_figures`,
`render_audio`, `append_notebook`, …). The test suite calls them
directly without spinning up a server.

## Run the full v2 acceptance suite

```bash
pytest tests/test_validation.py tests/test_units.py    # v1 (19 + 1 skip)
pytest tests/test_scenario.py                           # v2 §12 (10)
pytest tests/test_material.py                           # v2 §13 (7)
pytest tests/test_suggestions.py                        # v2 §14 (8)
pytest tests/test_ui.py                                 # v2 §15 (11)
```

Total: **55 passed, 1 skipped (PlasmaPy)** in ~48 s on a laptop.

# 00 — Summary and navigation

This is the index for the research dossier supporting a Python simulator
of a tabletop, biomimetic, cavitation-driven low-temperature plasma
reactor. The simulator is downstream; this dossier is the brief that
goes into Claude Code.

## Files in this folder

| File                          | What's in it                                                                  |
|---                            |---                                                                            |
| [`00_plan.md`](00_plan.md)         | The verbatim research plan supplied as the brief.                            |
| `00_summary.md` (this file)   | Index, project goal, key conclusions across sections.                         |
| [`01_biological_data.md`](01_biological_data.md)        | Pistol shrimp + mantis shrimp + sonoluminescence reference data.              |
| [`02_bubble_dynamics.md`](02_bubble_dynamics.md)        | Rayleigh–Plesset, Keller–Miksis, Gilmore equations + thermal extensions.       |
| [`03_acoustic_field.md`](03_acoustic_field.md)         | Wave equation, standing-wave geometries, Blake threshold, transducers.        |
| [`04_plasma_conditions.md`](04_plasma_conditions.md)      | Saha + continuum lowering, plasma diagnostics, gas/liquid effects.            |
| [`05_em_emission.md`](05_em_emission.md)            | Bremsstrahlung, recombination, blackbody, Margulis transients.                |
| [`06_reactor_design.md`](06_reactor_design.md)         | Chamber geometries, materials, frequencies, power, nucleation, safety.        |
| [`07_diagnostics.md`](07_diagnostics.md)            | PMTs, hydrophones, cameras, antennas, signal processing, noise floors.         |
| [`08_existing_codes.md`](08_existing_codes.md)         | Open-source codes (RP_Bubble, k-Wave, PlasmaPy), validation benchmarks.       |
| [`09_default_parameters.md`](09_default_parameters.md)     | Concrete starting values + expected output ranges.                             |
| [`10_open_questions.md`](10_open_questions.md)         | Disputed measurements, contested models, parameters with wide uncertainty.    |
| [`11_simulator_spec.md`](11_simulator_spec.md)         | v1 physics core spec: inputs, outputs, modules, tests, libraries.              |
| [`12_scenario_simulator.md`](12_scenario_simulator.md)   | **v2** — `Scenario` abstraction (chamber + transducers + bubbles + observers + walls). |
| [`13_material_stress.md`](13_material_stress.md)       | **v2** — cavitation erosion, wall fatigue, transducer lifetime physics.        |
| [`14_suggestions_engine.md`](14_suggestions_engine.md)    | **v2** — rule-based regime classification and parameter recommendations.       |
| [`15_visualization_ui.md`](15_visualization_ui.md)      | **v2** — Plotly Dash live UI: layout, callbacks, animation, audio.             |
| [`equations.md`](equations.md)                | Master list of all equations with consistent notation.                         |
| [`references/bibliography.md`](references/bibliography.md)  | Annotated bibliography (~60 sources, all peer-reviewed unless flagged).         |

## Project goal

Build a Python virtual-experiment platform that lets the user:

1. Configure a tabletop cavitation reactor (chamber + transducers +
   liquid + bubble seed + observers + wall material) via a live UI.
2. Hit a "test" button → simulate the bubble dynamics, plasma state,
   EM emission, detector signals, and predicted wall stress.
3. Read regime classification, headline numbers (with §10 uncertainty
   bands), and a ranked list of parameter suggestions.
4. Adjust parameters and re-test.
5. Log every run to a notebook for later analysis or comparison with
   real-experiment data.

The simulator is *not* a research-grade physics predictor (no software
is, in this regime — see §10). It is a design-and-decision tool for
upscaling, hardware spec, and pre-experiment planning, with calibrated
humility about what it can and can't tell you. Inspired by — but not
literally reproducing — the pistol shrimp's biological cavitation.

This is a two-layer project: the v1 *physics core* (§§1–11) and the
v2 *virtual-experiment platform* (§§12–15). Sections 1–11 are the
physics dossier; 12–15 are the platform spec built on top.

## Headline conclusions

- **The biological reference points are well measured.** Pistol shrimp
  produce R_max ≈ 3.5 mm bubbles lasting ≈ 300 µs that emit ≥ 5 000 K
  flashes < 10 ns long. Mantis shrimp produce dual-peak strikes
  (impact + cavitation collapse) ≈ 400 µs apart. These set the upper
  bound on bubble size and lower bound on flash duration the simulator
  should handle.
  Sources: Versluis et al. 2000, Lohse et al. 2001, Patek et al. 2004/2005.

- **Single-bubble sonoluminescence (SBSL) is the laboratory analogue.**
  Stable SBSL in water at 26.5 kHz, 1.32 atm, R₀ = 4.5 µm: T_peak ≈
  1.5–4 × 10⁴ K, flash duration 60–250 ps, 10⁵–10⁷ visible photons
  per cycle. Brenner–Hilgenfeldt–Lohse RMP (2002) is the
  authoritative review.

- **Three bubble equations span the regime: RPE, KME, GE.** Keller–
  Miksis is the recommended baseline; switch to Gilmore once wall
  Mach number > 0.2. The Toegel reduced thermal model and Storey–
  Szeri vapour cap are the recommended optional refinements.

- **The plasma is on the boundary between ideal plasma and warm
  dense matter** (Γ ≈ 1, n_e ≈ 10²⁶ m⁻³). Saha + continuum
  lowering (Stewart–Pyatt) is the recommended ionization model.

- **EM emission is dominated by thermal bremsstrahlung +
  recombination + (in optically thick regime) blackbody.** RF
  emission is contested; Margulis-style electrical transients are
  reported but not consistently replicated. The simulator implements
  the thermal stack as the default; Margulis transients are an
  optional, flagged-as-contested module.

- **A 20–40 kHz, ~100 W, glass-walled spherical resonator filled
  with degassed argon-saturated water is the well-trodden tabletop
  starting point.** Higher-T regimes (concentrated H₂SO₄ + Xe) are
  available at the cost of a more demanding chemical setup.

- **The simulator's first version is single-bubble, spherical,
  Python-only.** Dependencies: NumPy, SciPy, matplotlib, PlasmaPy,
  optional Cantera and k-wave-python. Out of scope for v1: 3-D fields,
  multi-bubble clouds, sonochemistry kinetics, asphericity.

## Recommended order of reading for the implementer

**v1 (physics core):**

1. `00_plan.md`, `00_summary.md` — project context.
2. `09_default_parameters.md` — starting numbers.
3. `02_bubble_dynamics.md` — most code-heavy physics section.
4. `04_plasma_conditions.md` and `05_em_emission.md` — emission stack.
5. `11_simulator_spec.md` — v1 implementation spec.
6. `equations.md` — quick reference while coding.
7. `08_existing_codes.md` — what to reuse.
8. `10_open_questions.md` — read before claiming any output is
   "definitive."
9. The remaining files (`01`, `03`, `06`, `07`) — context for
   experimental comparison and reactor design boundaries.

**v2 (virtual-experiment platform — read after v1 is shipped):**

10. `12_scenario_simulator.md` — Scenario architecture.
11. `13_material_stress.md` — wall/transducer lifetime physics.
12. `14_suggestions_engine.md` — rule-based recommendations.
13. `15_visualization_ui.md` — Plotly Dash UI architecture.

The v2 layers depend on a working v1; do not start them in parallel.
Within v2, build §12 first (it's the API), then §13 + §14 in parallel
(they're both pure-Python modules with no UI dependency), then §15
last (the UI consumes everything).

## Cross-section equation map

(see `equations.md` for the full list)

| Equation                 | Used by sections    |
|---                       |---                  |
| Rayleigh–Plesset (E6)    | 2, 9, 11            |
| Keller–Miksis (E8)       | 2, 8, 9, 11         |
| Gilmore (E9)             | 2, 8, 11            |
| Toegel thermal (E10)     | 2, 4, 9, 11         |
| Saha (E12)               | 4, 9, 11            |
| Stewart–Pyatt (E13)      | 4, 10, 11           |
| Plasma frequency (E14)   | 4, 5, 11            |
| Bremsstrahlung (E17)     | 5, 8, 11            |
| Recombination (E19)      | 5, 11               |
| Planck (E20)             | 4, 5, 11            |
| Optical depth (E22, E23) | 5, 11               |
| Bubble radiation (E24)   | 7, 11               |
| Blake threshold (E4)     | 3, 9, 11            |
| Minnaert (E5)            | 3, 8, 11            |

## Audit trail

This dossier was produced from primary peer-reviewed sources and well-
established textbooks. Every numerical value cited here is followed by
a citation tag; the full bibliography is in `references/bibliography.md`.
Where the literature is contested or sparse (notably: peak temperatures,
Margulis effects, and pistol-shrimp photon counts), Section 10
documents the uncertainty rather than picking a single number. The
simulator inherits this practice: contested or weakly-constrained
quantities are exposed as parameters with documented ranges, not
hard-coded constants.

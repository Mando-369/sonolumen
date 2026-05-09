# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Project renamed from `cavplasma` to `sonolumen` — package, repository,
  preset filenames, and documentation all updated. Imports change from
  `from cavplasma import ...` to `from sonolumen import ...`.

### Added
- `LICENSE` (MIT), `CONTRIBUTING.md`, and `.github/` templates +
  GitHub Actions test workflow.

## [0.1.0] — 2026-05-08

First public release. Implements `cavitation_research/11_simulator_spec.md`
end-to-end and adds a Dash-based interactive UI on top.

### Core simulator (v1)
- Bubble dynamics: Rayleigh–Plesset, Keller–Miksis, Gilmore (E6 / E6b / E8 / E9).
- Thermal model: Toegel reduced ODE with Storey–Szeri-style vapour cap (E10, E11).
- Plasma: Saha + Stewart–Pyatt continuum lowering (E12–E16, E28).
- EM emission: bremsstrahlung + recombination + blackbody, optical-depth
  interpolation, photon yield (E17, E19–E23, E30).
- Detectors: PMT, hydrophone, pickup-coil (E24, §7.1, §7.2, §7.4).
- Solvers: SciPy `solve_ivp` (LSODA / BDF / Radau) with event detection (§2.6).
- Liquid presets with T/S/p sound-speed correction: water, seawater,
  glycerin, sulfuric_98, silicone_oil_100cSt.
- Acoustic drives: sinusoid, tone-burst, impulsive, custom waveform.
- 55-test validation suite reproducing canonical SBSL and pistol-shrimp cases.

### Scenario layer (v2)
- Composable `Scenario` orchestration with field, observers, and chamber
  geometry on top of v1 (`cavitation_research/12_scenario_simulator.md`).
- 24 ready-to-load preset scenarios under `presets/` covering SBSL,
  pistol-shrimp, HIFU sonochemistry, Suslick H₂SO₄/Ar, cold-water and
  air-saturated SBSL, glycerin viscous demo, and more.

### Material stress + suggestions (§13–§14)
- Wall pressure capability and erosion limits for chamber materials
  (Pyrex, stainless 316, Inconel, …).
- Regime classifier with rationale chips and live notebook history.
- Inverse design: target outcome → recommended parameters.
- Auto-adapt with preview-then-commit coupling between `drive_f`, `R₀`, `P_A`.

### UI (§15)
- Dash UI with bidirectionally synced sliders + numeric inputs for every knob.
- Live regime chip, animated progress bar, Q-attenuation surfacing, wall
  pressure capability panel, chamber accordion, dossier-id labels on every
  slider.
- One-click preset load, preset name display, scenario JSON save/load.

### Documentation
- 27 markdown documents in `cavitation_research/` covering physics
  derivations, equation lists, sound-speed corrections, pressure regimes,
  open questions, and the simulator spec.
- `PARAMETERS.md` — single-file reference for every UI knob, with
  cross-references to the dossier.

[Unreleased]: https://github.com/Mando-369/sonolumen/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Mando-369/sonolumen/releases/tag/v0.1.0

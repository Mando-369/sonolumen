# Research Plan — Cavitation-Driven Low-Temperature Plasma Reactor

This file is the verbatim plan supplied by the user. It is the master brief.
The remaining files in `cavitation_research/` are the section-by-section
deliverables that fulfil this brief.

---

## Goal

Collect technical data, equations, and reference parameters needed to build a
Python simulation of a tabletop cavitation-based plasma reactor, inspired by
the pistol shrimp's biological mechanism. The output is a structured research
dossier that a coding assistant can use to write simulation code.

## Background context

- Inspiration is biological cavitation (pistol shrimp, mantis shrimp) producing
  brief plasma conditions through acoustic bubble collapse.
- Target: low-temperature plasma regime (thousands of K, not fusion temperatures).
- Goal is a tabletop laboratory device, not industrial fusion.
- End deliverable will be a Python simulator predicting plasma conditions and
  EM signatures from given acoustic driving parameters.

## Sections

1. Biological cavitation reference data
2. Bubble dynamics equations
3. Acoustic field generation
4. Plasma conditions during collapse
5. Electromagnetic emission
6. Reactor design parameters
7. Detection and diagnostic methods
8. Existing simulations and codes
9. Default parameter ranges for initial simulation
10. Open questions and uncertainties
11. Simulator specification (coding handoff)

Plus cross-cutting deliverables:
- `00_summary.md` — overview and navigation
- `equations.md` — master list of all equations with consistent notation
- `references/bibliography.md` — full bibliography of cited sources

## Style rules (apply to every section)

- Consistent variable notation across all files (see `equations.md`).
- Citations for every claim or equation.
- Distinguish well-established physics from contested results.
- Provide both equations and example numerical values.
- Equations in LaTeX, transcribable into Python without ambiguity.
- Prefer peer-reviewed sources; preprints/technical reports are noted as such.
- Where there is no single "right" answer (e.g. which Rayleigh–Plesset
  variant to use), present multiple options with tradeoffs rather than
  picking one.
- Length: thorough but not exhaustive. "Enough information to write a
  working simulator," not a complete literature review. For topics with
  hundreds of papers, find the 3–5 most-cited or most-relevant.

## Deliverable folder layout

```
cavitation_research/
├── 00_plan.md              ← this file
├── 00_summary.md           ← overview and navigation
├── 01_biological_data.md
├── 02_bubble_dynamics.md
├── 03_acoustic_field.md
├── 04_plasma_conditions.md
├── 05_em_emission.md
├── 06_reactor_design.md
├── 07_diagnostics.md
├── 08_existing_codes.md
├── 09_default_parameters.md
├── 10_open_questions.md
├── 11_simulator_spec.md
├── equations.md
└── references/
    └── bibliography.md
```

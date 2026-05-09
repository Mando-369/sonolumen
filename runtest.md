# How to run a test — step by step

This is the workflow walk-through for the sonolumen UI: launch → set up
a test → read the data → save it → recall it → repeat. Plus a few
gotchas the dossier (`cavitation_research/`) doesn't cover but that
matter when you're at the keyboard.

---

## 0. First-time install

One-off:

```bash
cd sonolumen
python3 -m venv .venv
.venv/bin/pip install -e '.[ui]'
```

That installs sonolumen in editable mode plus the UI extras (Dash,
Plotly, dash-bootstrap-components, waitress).

---

## 1. Launch the UI

```bash
./start.sh
```

You should see only:

```
  sonolumen UI
  http://127.0.0.1:8050
  Ctrl-C to stop
```

The browser auto-opens once waitress is actually serving (the script
polls the URL before opening — no "site can't be reached" race). Stop
with **Ctrl-C** in the terminal.

Useful flags:

| Flag | Effect |
|---|---|
| `./start.sh --debug` | Dash dev server (auto-reload, verbose tracebacks) |
| `./start.sh --port 9000` | run on a different port |
| `./start.sh --no-browser` | don't auto-open — just print the URL |
| `./start.sh --help` | show usage |

---

## 2. Load a preset (the canonical starting point)

In the **Controls** column on the left, pick one from the *"Load preset"*
dropdown:

| Preset | What it is |
|---|---|
| `sbsl_canonical` | §9.3 SBSL — 26.5 kHz, 1.32 atm, 4.5 µm Ar bubble in a 100 mL Pyrex sphere. The textbook starting point. |
| `pistol_shrimp_event` | §9.8 pistol shrimp — 3.5 mm bubble in seawater, no continuous drive. Impulsive collapse. |
| `tabletop_starter` | §6.3 / §9.10 tabletop first-build — 20 kHz Langevin + water cell. |

Selecting a preset overwrites every control with that preset's values.
The accordion sections fill in: liquid, ambient, drive, bubble,
physics, numerics.

---

## 3. Adjust parameters

Open any accordion and tweak:

- **Liquid** — preset dropdown (water, seawater, glycerin, 98 % H₂SO₄,
  silicone oil 100 cSt).
- **Ambient** — T_∞, p_∞.
- **Drive** — frequency (log slider, 1 kHz – 5 MHz), amplitude
  P_A (atm), number of cycles to integrate.
- **Bubble** — R₀ (log slider, 0.1 µm – 10 mm), gas mole fractions
  (Ar / H₂O / air).
- **Physics** — bubble equation (KME / RPE / Gilmore), thermal model
  (Toegel / polytropic), ionization model (Stewart-Pyatt / ideal Saha).
- **Numerics** — rtol log slider, convergence-test toggle.

While you slide, the regime indicator on the right updates instantly
(no full run yet). When the indicator says **sub_blake** in grey,
you've dropped below the Blake threshold — bubble won't cavitate.
Push P_A back up.

---

## 4. Run the test

Click the big **TEST ▶** button at the bottom of the controls.

- Takes 1–5 s for SBSL canonical, similar for tabletop, ~0.3 s for
  pistol shrimp.
- The status line under the button reads `ran in X.XX s` on success.
- All six centre-column figures repopulate.
- The right-column results panel rebuilds: regime, headline numbers,
  suggestions, caveats, material summary.
- A new row appears at the bottom in the **Lab notebook** with
  timestamp + regime + T_peak + photons + R_max + Mach.

If the run fails (e.g. observer placed outside the chamber → §12.6 #6
escalates to `error`), the status line shows the reason. Fix the
problem and click TEST again.

---

## 5. Read the data

### Right column — at-a-glance

- **Regime card** (top, coloured) — the §14.2 classification:
  - `stable_spherical` (green) — SBSL band, you're in business.
  - `marginal` (amber) — Mach > 0.3; collapse is shape-stability
    marginal. Common for SBSL canonical because v1 hits Mach ≈ 0.59.
  - `unstable_likely` (red) — parametric / RT index > 1; expect
    fragmentation.
  - `sub_blake` (grey) — drive doesn't exceed Blake threshold; no
    cavitation.
  - `transducer_limited` (red) — requested drive exceeds the
    transducer's max acoustic power.

- **Headline numbers** — `R_max`, `R_min`, wall Mach, `T_peak` (with
  §10.1 ±factor 2 band shown in parentheses), `n_e_peak`, `Γ_peak`,
  `photons (4π)`, `photons @ PMT_R7400U`, wall lifetime, flash FWHM.

- **Suggestions** — top entries are §14 R-rules: actionable parameter
  changes with a `[Apply]`-style suggested-change dict. Each one cites
  the dossier section that motivates it.

- **Caveats** — §10 uncertainties relevant to *this* run. Always-on:
  C1 (T_peak factor 2-3 spread). Conditional: C2 (pistol shrimp
  weakly-constrained), C4 (toroidal not modelled), C7 (Tait limits
  past Mach 0.5), etc.

- **Wall + transducer + thermal** — §13 outputs:
  - severity factor S, T_inc, MDPR
  - transducer grade + lifetime hours + steady-state T
  - liquid ΔT and time constant; flag if it'll boil.

- **Listen 🔊** — pitch-shifts the hydrophone trace down 8× (25 kHz →
  3 kHz audible). Click after the first run; an audio control appears.
  Lets you *hear* the collapse cadence.

### Centre column — figures

Six stacked plots, top to bottom:

1. **Chamber cross-section** — chamber outline, transducer positions
   (blue squares), bubble (yellow disk, R₀-scaled), observers (red
   diamonds). Static layout.
2. **Bubble dynamics** — R(t) (left axis, blue) + Ṙ(t) (right axis,
   red). Linear-time, µs.
3. **Plasma diagnostics** — T_g(t) (purple, log scale) + n_e(t) (green,
   log) + x_e(t) (orange dashed). Shaded band shows §10.1 T_peak
   uncertainty.
4. **Spectrum surface** — log₁₀ S(λ, t) heatmap, wavelength on y, time
   on x.
5. **Detector traces** — V_PMT, hydrophone V, pickup-coil V — one line
   per observer.
6. **Standing-wave field** — chamber pressure field heatmap at one
   frame. Hit ▶ Play below the figure to animate one acoustic cycle
   at 30 fps.

### Lab notebook (bottom)

Every TEST run auto-logs a row with timestamp, wall-clock duration,
regime, T_peak, photons, R_max, Mach. The buffer keeps the most recent
**20 runs**.

- **Export CSV** — downloads the buffer for your real lab notebook.
- **Clear** — empties the buffer (won't undo prior CSV exports).

---

## 6. Save the test as a preset

The UI doesn't write Python preset files (those live in
`sonolumen/scenario/presets.py` and ship with the package). Instead it
saves your *current Scenario* as a JSON file you can recall later.

1. Configure the controls until you have the test you want.
2. Click **Save JSON** in the lower-left of the controls.
3. Your browser downloads `sonolumen_scenario.json`. **Rename it
   immediately** to something memorable, e.g.
   `xenon_argon_30kHz_3atm.json`, and put it in a folder you'll find
   again.

The JSON is byte-identical-round-trippable (§12.10 #6) — so loading
the same file back always reconstructs the exact same Scenario.

> **Note** — `.gitignore` excludes `sonolumen_scenario.json` and
> `*.local.json` so you don't accidentally commit your saved tests.
> If you want to version-control a saved preset, rename it to
> something like `presets/my_xenon_test.json` and add it explicitly.

---

## 7. Recall a preset

1. Click **Load JSON** in the lower-left of the controls.
2. Pick the JSON file you saved earlier in the file picker.
3. The controls repopulate from the file.
4. Click **TEST ▶** to re-run.

The Load button validates the JSON first; if it's malformed (or from
an incompatible sonolumen version), nothing changes and an error is
silently swallowed. Open the developer console in your browser to see
the parse error.

---

## 8. Compare two runs

The lab notebook is the simplest way:

1. Run scenario A → row 1 logs.
2. Edit one parameter (e.g. drop drive frequency by 10 %).
3. Run scenario B → row 2 logs.
4. Click **Export CSV** to dump both rows for offline analysis.

For a tighter loop without leaving the UI: keep the right-column
**suggestions** and **headline numbers** open; tweak one slider at a
time and re-run. The §14 engine highlights the parameter most worth
sweeping next under the *Next experiment* heuristic (called from
Python; not yet wired into the UI button — see *Things on the roadmap*
below).

---

## 9. Programmatic / scripted use (no UI)

For sweeps and batch jobs the UI is the wrong tool. Use the Python
API directly:

```python
from sonolumen.scenario import presets

s = presets.sbsl_canonical()
result = s.run()
print(result.summary.T_peak_K, result.summary.photons_visible_4pi)
print(result.summary.regime)
for sg in result.suggestions[:5]:
    print(sg.severity, sg.rule_id, sg.message)
```

Sweep over P_A:

```python
import dataclasses, numpy as np
from sonolumen.scenario import presets

base = presets.sbsl_canonical()
for P in np.linspace(1.0e5, 1.6e5, 11):
    new_drive = {n: dataclasses.replace(d, P_A=P)
                 for n, d in base.drive.waveforms.items()}
    s = dataclasses.replace(base,
        drive=dataclasses.replace(base.drive, waveforms=new_drive))
    r = s.run()
    print(f"{P/101325:.2f} atm → T_peak {r.summary.T_peak_K:.0f} K")
```

`§14`'s next-experiment finite-difference suggestor (CLI-only at v2):

```python
from sonolumen.suggestions import suggest_next_experiment

s = presets.sbsl_canonical()
r = s.run()
nx = suggest_next_experiment(s, r, goal="maximize_T")
print(nx.message, nx.suggested_change)
```

`§13` direct calls (catalog lookups, microjet velocity, transducer
lifetime) — see `sonolumen/material/__init__.py` for the API.

---

## 10. Common gotchas

| Symptom | Likely cause | Fix |
|---|---|---|
| Browser shows "site can't be reached" | start.sh exited before `python` ran (already-fixed `set -u` array bug) or you opened the URL too early. | Reload the page once. If still broken, check the terminal for tracebacks. |
| Off-resonance warning fires for `sbsl_canonical` | The 26.5 kHz drive sits at a higher chamber mode of a 0.05 m sphere (fundamental ≈ 14.8 kHz). Correct physics — SBSL drives a higher harmonic. | Ignore. §14 R6 is informative, not a bug. |
| Regime is `marginal` not `stable_spherical` for SBSL | v1 SBSL hits Mach ≈ 0.59 (above the §14.2 textbook 0.3 threshold). | Expected. The regime label is the §14 strict classification; the SBSL band as the literature describes it spans both. |
| Slider snaps to round numbers; can't pick exactly 1.32 atm | Slider step size is 0.05. | Type the exact value into the suggested-change dict in the suggestions panel, or edit + re-load the saved JSON. |
| "Listen" button has no effect | Click TEST first. The audio is built from the result's hydrophone trace, which only exists after a run. | Run, then click Listen. |
| `pytest` fails on PlasmaPy import | PlasmaPy is an optional cross-check (only `test_bremsstrahlung_emissivity` uses it). | Either `pip install plasmapy` or accept the 1 skipped test. |
| Save JSON downloads but Load JSON does nothing | Most common: you tried to load a JSON saved from a *different* sonolumen version. | Re-save a fresh scenario from the current build. |
| Test runs forever | Convergence-test toggle is on plus a stiff scenario. | Untoggle convergence test for normal use; it doubles the run cost. |

---

## 11. Where the dossier lives

Every R-rule and caveat in the suggestions panel cites a dossier
section (e.g. *§4.6*, *§10.1*). Those refer to files in
`cavitation_research/`:

| Section | File |
|---|---|
| Bubble dynamics | `02_bubble_dynamics.md` |
| Acoustic field | `03_acoustic_field.md` |
| Plasma | `04_plasma_conditions.md` |
| EM emission | `05_em_emission.md` |
| Reactor design | `06_reactor_design.md` |
| Diagnostics | `07_diagnostics.md` |
| Default parameters | `09_default_parameters.md` |
| Open questions / contested numbers | `10_open_questions.md` |
| Equations master list | `equations.md` |
| §12 / §13 / §14 / §15 specs | `12_*.md`, `13_*.md`, `14_*.md`, `15_*.md` |

When a suggestion looks weird, open the cited file. The §14 engine
never makes anything up — every recommendation is anchored.

---

## 12. Things on the roadmap (not yet shipped)

- **Save as preset (in-app)** — currently you save *scenarios* as
  JSON. To register one as a Python preset (so it shows in the
  dropdown alongside `sbsl_canonical`), copy your JSON into
  `sonolumen/scenario/presets.py` as a new `def my_preset() -> Scenario`
  function. Future v2.next will add an in-UI "promote to preset"
  button that writes to a user-owned `presets_user.py`.
- **Next-experiment button** — `suggest_next_experiment(...)` exists
  in Python but isn't wired into the UI. Run two perturbation
  simulations to find the most informative axis for your stated
  goal (`maximize_T`, `maximize_n_e`, `maximize_photons`).
- **3-D field views** — the standing-wave field is 2-D for now;
  three orthogonal cross-sections + true 3-D Plotly Surface are §15.4.1
  follow-up work.
- **Multi-bubble cloud regime** — `BubblePopulation.kind='cloud'`
  raises `NotImplementedError`. Bjerknes coupling and crowding
  factors are §12.5 / §10.10 / v3 territory.

---

## 13. Reset, abort, escape hatches

- **Stop a hung run** — Ctrl-C in the terminal kills the server.
  Re-run `./start.sh`.
- **Reset all controls** — pick `sbsl_canonical` from the preset
  dropdown again; that overwrites every slider.
- **Reset notebook** — click **Clear** at the bottom.
- **Wipe everything** — `rm -rf .venv .pytest_cache sonolumen.egg-info`
  then re-install per step 0. Won't touch your saved scenario JSON
  files unless you put them in those folders.

# Section 15 — Visualization & UI architecture (v2, Plotly Dash)

> Purpose: define the user-facing application — what's on the screen,
> how the panels connect to the §12 Scenario object, how live updates
> work, and how the test/adjust/repeat loop is wired. Tech choice:
> **Plotly Dash** (browser-based, Python-only, real-time-callback,
> shareable via URL). Decided in the v2 scoping conversation.

---

## 15.1  High-level layout

Single-page app, three columns:

```
┌──────────────────┬──────────────────────────┬──────────────────┐
│  CONTROLS        │  VIRTUAL EXPERIMENT      │  RESULTS &       │
│  (left, 25%)     │  (center, 50%)           │  SUGGESTIONS     │
│                  │                           │  (right, 25%)    │
│  ┌────────────┐  │  ┌────────────────────┐  │  ┌────────────┐  │
│  │ Liquid     │  │  │  Chamber view      │  │  │ Regime     │  │
│  │ Ambient    │  │  │  (2-D cross-       │  │  │ summary    │  │
│  │ Drive      │  │  │   section, live)   │  │  │            │  │
│  │ Bubble     │  │  └────────────────────┘  │  ├────────────┤  │
│  │ Physics    │  │  ┌────────────────────┐  │  │ Suggestions│  │
│  │ Numerics   │  │  │  Bubble dynamics   │  │  │ (top 5)    │  │
│  └────────────┘  │  │  R(t), Ṙ(t)        │  │  ├────────────┤  │
│                  │  └────────────────────┘  │  │ Caveats    │  │
│  ┌────────────┐  │  ┌────────────────────┐  │  ├────────────┤  │
│  │ TEST  ▶    │  │  │  Plasma diagnostics│  │  │ Headline   │  │
│  └────────────┘  │  │  T(t), n_e(t)      │  │  │ numbers    │  │
│                  │  └────────────────────┘  │  └────────────┘  │
│  ┌────────────┐  │  ┌────────────────────┐  │                  │
│  │ Preset ▼   │  │  │  Spectrum surface  │  │  ┌────────────┐  │
│  │ Save / Load│  │  │  (λ × t heatmap)   │  │  │ Wall stress│  │
│  │ Export     │  │  └────────────────────┘  │  │ heatmap    │  │
│  └────────────┘  │  ┌────────────────────┐  │  └────────────┘  │
│                  │  │  Detector traces   │  │                  │
│                  │  │  (PMT, hyd., coil) │  │  ┌────────────┐  │
│                  │  └────────────────────┘  │  │ "Listen" 🔊│  │
│                  │  ┌────────────────────┐  │  │ to event   │  │
│                  │  │  Standing wave field│ │  └────────────┘  │
│                  │  │  (live animation)   │ │                  │
│                  │  └────────────────────┘  │  ┌────────────┐  │
│                  │                           │  │ Next       │  │
│                  │                           │  │ experiment │  │
│                  │                           │  │ suggestion │  │
│                  │                           │  └────────────┘  │
└──────────────────┴──────────────────────────┴──────────────────┘
```

Bottom of page: a parameter-sweep "lab notebook" panel that records
each test run (timestamp, parameter delta, regime, headline numbers).

---

## 15.2  Page state model

Three pieces of state live in `dcc.Store` components:

- `scenario_store`: serialised current `Scenario` (JSON, edited by
  every control input).
- `result_store`: most recent `ScenarioResult` (JSON, updated only
  when the TEST button fires).
- `notebook_store`: list of past (scenario_diff, result_summary,
  notes) entries.

Every panel either *reads* from one of these stores (display) or
*writes* to one (controls + TEST button).

---

## 15.3  Controls column (left)

Grouped accordions, one per Scenario sub-object:

### Liquid
Dropdown `liquid.name` (preset names), or "Custom" → numeric inputs
for ρ, c, μ, σ, p_v, B, n_tait, β. Live re-validation against §9.1
table.

### Ambient
Sliders: T_inf (273–323 K), p_inf (50–200 kPa).

### Drive
- Waveform: dropdown {sinusoid, tone_burst, impulsive, custom}
- f: slider (1 kHz – 5 MHz, log scale, with a "snap to chamber
  resonance" button — wires to §3.2 eigenmode)
- P_A: slider (0.1 – 10 atm)
- duty cycle: slider (1% – 100% for tone_burst)
- Number of cycles: numeric input

### Bubble
Mode radio: {single trapped, cloud, impulsive}. Conditional inputs
per mode:
- single trapped: R₀ slider, gas composition (Ar / Xe / He / air mix
  pie chart)
- cloud: nuclei density, size distribution preset
- impulsive: peak pressure, rise time, decay time

### Physics options
Dropdowns matching §11.3 (`bubble_eq`, `thermal_model`, `ionization`,
`em_model`, `liquid_eos`, plus `vapour_cap`, `include_margulis`,
`include_chemistry` toggles). Tooltip on each option points to the
relevant dossier section.

### Numerics
- Tolerances (rtol, atol) — sliders with sensible defaults
- t_total — slider in cycles
- "Convergence test" toggle (auto-tightens, reports stability)

### TEST button
Big, central, only enabled when `scenario.validate()` returns no
errors. Clicking fires `scenario.run()` → updates `result_store`.
Disabled state shows the reason in a tooltip.

### Preset / Save / Load / Export
- Preset dropdown loads §12.8 presets.
- Save → POST scenario_store to a Dash file-download.
- Load → upload JSON → replace scenario_store.
- Export → ScenarioResult as JSON / CSV bundle.

---

## 15.4  Centre column — visualizations

### 15.4.1  Chamber cross-section view

Plotly `go.Scatter` (2-D) of the chamber boundary, transducer
positions (with active phase indicators), bubble locations (animated
size = current R(t)), observer positions (icons), and an overlaid
heat-map of the standing-wave pressure field at the current frame.

Live animation via `dcc.Interval`: 30 fps, advances `t` through the
last simulated cycle. Pause/play controls.

For 3-D chambers: a toggle to flip between three orthogonal cross-
sections; a true 3-D `Plotly Surface` view is available but slower.

### 15.4.2  Bubble dynamics traces

Two stacked subplots: R(t) on top (linear), Ṙ(t) on bottom (linear)
with log-scaled time near collapse. Markers for events: nucleation
(green), maximum radius (yellow), collapse (red), peak T (purple).

Phase-space inset: Ṙ vs R, log-log, with the trajectory animated
along the path. Standard SBSL diagnostic — instantly recognisable.

### 15.4.3  Plasma diagnostics traces

T_g(t) and n_e(t) on twin-axis plot; ionization fraction on a second
panel. Shaded band on T_g indicates the §10.1 uncertainty range
([T × 0.5, T × 1.5]) — the user *sees* the band, not just a line.

### 15.4.4  Spectrum surface

Heatmap of S(λ, t) — wavelength on y-axis (200–1000 nm), time on
x-axis (zoomed to flash window), intensity colour-coded log scale.
Optional overlay: blackbody curve at peak T_g, line emission at
expected atomic transitions (Ar I, OH band, Na D, etc., from NIST
ASD).

### 15.4.5  Detector traces

One subplot per observer:
- PMT: predicted photoelectron counts vs t (integer histogram during
  flash, then dropping to dark-count Poisson tail).
- Hydrophone: V(t) bandpass-filtered to the calibration band of the
  selected hydrophone model.
- Coil: V(t) from §5 EM module (only meaningful if Margulis or EDL
  modules enabled).

Each panel shows a "noise floor" shaded band per §7.7 so the user
sees whether the predicted signal is detectable.

### 15.4.6  Standing-wave field animation

Full chamber pressure field p(x, y, t) over one acoustic cycle, via
`Plotly.Heatmap` updated by `Interval`. Colour: blue (rarefaction)
to red (compression). Bubble locations overlaid as moving dots.

This is what "visualize the forces" looks like for the user.

---

## 15.5  Right column — results & suggestions

### Regime summary card
Big text label of the §14.2 regime classification, with a coloured
status indicator (green / amber / red). One-line "what this means"
caption. Click → expands to show the rule that fired and the dossier
section.

### Suggestions list
Top 5 from §14, sorted by priority. Each:

```
[severity icon]  message
                 ↳ rationale (collapsed by default)
                 ↳ [Apply] button (writes to scenario_store, doesn't auto-run)
                 ↳ Expected effect: T_peak +30%
                 ↳ §X.Y reference (link, opens dossier file in new tab)
```

### Caveats list
§14.4 caveats relevant to this run, collapsed by default. Title:
"What this run *can't* tell you."

### Headline numbers card

```
T_peak     :  2.3 × 10⁴ K   (band: 1.2–3.5 × 10⁴ K)
n_e_peak   :  3 × 10²⁶ /m³
Γ peak     :  0.8           (warm dense matter)
Photons (4π emitted)  :  4 × 10⁷
Photons (PMT detected):  2 × 10⁴   (after QE × geom)
Wall lifetime :  > 10 000 h  (no concern)
```

Each row clickable → drills into a focused subplot.

### Wall stress heatmap
Mini-overlay on a chamber outline showing predicted MDPR per wall
location. Hot-spots flagged.

### Listen button
Plays the synthesised hydrophone signal at audible frequency. The
real signal is at 25 kHz (above hearing); pitch-shift down by 8×
to bring it into 3 kHz audible range, time-stretched to match. Uses
Web Audio API via Dash extension (or a precomputed WAV download).

### Next experiment suggestion
The §14.6 "what to change next" output. One-click "apply this
parameter" button.

---

## 15.6  Bottom panel — "lab notebook"

Persistent log of all runs in this session:

| # | timestamp | what changed | regime | T_peak | photons | notes |

Click a row → restores that scenario into the controls. Compare two
rows side-by-side (subplots).

Export as CSV / JSON / Markdown table for the user's actual lab
notebook.

---

## 15.7  Performance and responsiveness

The pure physics core takes 1–10 s for a typical run; this is too long
for "live slider" updates. The UI uses two response modes:

1. **Live preview (free)**: as the user moves sliders, recompute
   *only* the regime classification and the validate() output — both
   sub-millisecond. Show the current regime indicator and any
   blocking warnings *without* running the simulator.
2. **Full run (TEST button)**: actually invoke `scenario.run()`,
   spinner during compute, full update on completion.

Optional **fast mode**: a coarse-tolerance preview run with rtol=1e-6
that finishes in ~200 ms, used for "scrubbing" parameters when the
user holds shift. Marked clearly as preview; not used for headline
numbers.

---

## 15.8  Animation strategy

For the chamber view + standing-wave field + bubble dynamics:

- After a run completes, server stores the field snapshots and
  bubble traces in `result_store` (JSON-serialised dense arrays).
- `dcc.Interval` ticks at 30 Hz; an Interval-callback reads the
  current `t_anim`, looks up the corresponding frame from
  `result_store`, and updates each animated `Plotly.Figure` via
  `Patch` (avoids full re-render — much faster than naive `figure=`
  reassignment).
- Animations pause when the page is idle (visibility API).

For chamber views with > 100 frames, use the Plotly built-in
animation slider (works out of the box for Scatter/Heatmap).

---

## 15.9  Component layout (Dash code shape)

```python
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(controls_panel(),  width=3),
        dbc.Col(visualization_panel(), width=6),
        dbc.Col(results_panel(),   width=3),
    ], className='g-1'),
    dbc.Row([
        dbc.Col(notebook_panel(), width=12),
    ]),
    dcc.Store(id='scenario_store'),
    dcc.Store(id='result_store'),
    dcc.Store(id='notebook_store', storage_type='session'),
    dcc.Interval(id='animation_tick', interval=33, disabled=True),
])
```

Callback graph (read top→bottom):

```
[any control input]   →   scenario_store  (write)
                      →   regime_indicator + validate_warnings (read scenario_store, recompute fast)
[TEST button click]   →   result_store    (write, invokes scenario.run)
result_store          →   visualization panel (read, render plots)
                      →   suggestions panel (read, run §14 engine)
                      →   notebook_store (append)
                      →   animation_tick disabled=False  (start animation)
```

---

## 15.10  Module structure for the UI

```
sonolumen/ui/
├── __init__.py
├── app.py                # Dash app entry point
├── layout/
│   ├── controls.py       # left column components
│   ├── visualization.py  # center column figures
│   ├── results.py        # right column cards
│   └── notebook.py       # bottom panel
├── callbacks/
│   ├── scenario_state.py # control inputs → scenario_store
│   ├── run.py            # TEST button → result_store
│   ├── render.py         # result_store → figures
│   ├── suggestions.py    # result_store → suggestions panel
│   └── animation.py      # animation tick → patch figures
├── audio.py              # hydrophone → audible WAV
├── style.py              # colour scheme, layout constants
└── presets.py            # §12.8 presets, exposed in UI dropdown
```

Entry point:

```bash
python -m sonolumen.ui            # → http://localhost:8050
```

---

## 15.11  Acceptance criteria for the UI

The UI is complete when:

1. The §12.8 SBSL preset loads in < 1 s, no errors.
2. Sliding `drive.P_A` from 0.5 to 1.5 atm shows the regime indicator
   transition `sub_blake → linear → stable_spherical` in real time
   (no full runs).
3. Clicking TEST on the SBSL preset returns full results in < 5 s,
   all six centre-column panels populated.
4. The chamber animation plays smoothly at 30 fps for at least one
   acoustic cycle.
5. The "listen" button produces audible output that matches the
   collapse pulse cadence visually displayed on the hydrophone trace.
6. The suggestions panel shows at least one R-rule and at least one
   caveat for every run.
7. Saving and loading a scenario JSON round-trips byte-identical.
8. The notebook panel correctly logs the last 20 runs and allows
   restoring any of them.

---

## 15.12  Out of scope for v2

- Multi-user collaboration (single-user Dash app for now).
- Cloud deployment (run locally; future deploy via Heroku-class).
- Mobile/tablet layout.
- Authentication (intended for personal lab use).
- Export to PDF / formal reports (CSV/JSON/MD only at v2).

---

## 15.13  Hand-off note for Claude Code

When implementing:
- Build the Scenario layer (§12) first and verify with CLI scripts
  against §12.10 acceptance criteria.
- Add `material.py` (§13) and `suggestions.py` (§14) before any UI
  work — they're the ones the UI calls.
- Build the UI bottom-up: `controls.py` first (it's just inputs),
  then `run.py` (the TEST callback), then visualisation, then
  suggestions, then animation, then audio.
- Don't attempt the standing-wave field animation until the rest is
  working — it's the most expensive piece and easy to get wrong.
- The Listen feature is a *nice-to-have*; ship UI without it first.

# Parameter reference

Every parameter exposed in the cavplasma UI, what it does in the
model, how it interacts with the other parameters, and meaningful
values to try.

Organised by the accordion section in the controls panel.

For deeper physics and modelling notes, see `cavitation_research/`
(the research dossier — §16–§20 cover sound speed, water anomalies,
P_A interpretation, etc.).

---

## 1. Chamber

The vessel that holds the liquid. Determines where the acoustic
energy lives, what walls the bubble can shock, and what static
pressure the chamber can hold.

### `chamber_geometry`

What kind of cavity the bubble lives in.

| Option | Where energy lives | Use case |
|---|---|---|
| **Closed sphere** | Standing wave fills the chamber, antinode at centre. Real eigenmode `j₀(kr)`. Chamber Q multiplies the drive at resonance. | SBSL, pistol-shrimp-in-a-flask |
| **Cylinder axial** | Standing wave along the long axis (`cos(πz/L)`). | Suslick MBSL horns, tube reactors |
| **Cylinder radial** | Bessel mode `J₀(2.405 r/R)` — pressure pile-up on the axis. | Some sonochemistry rigs |
| **HIFU focal spot** | Focused beam from a curved/array transducer. cavplasma model: bubble at focal antinode, full drive amplitude, no falloff modelled. | Lithotripsy, histotripsy, tumour ablation |
| **Open water / pistol-jet** | No cavity. Bubble lives in static `p_∞`. | Pistol shrimp itself, laser cavitation |
| **Horn / open bath** | Transducer horn dipped into a tank. Same plane-wave treatment as HIFU. | Lab-bench sonochemistry |

For pistol-shrimp-in-a-real-chamber: pick **Closed sphere**. The
shrimp is impulsive; the closed cavity gives you (1) optical access
(transparent walls), (2) a place to add a transducer drive that
amplifies through chamber Q.

### `chamber_radius` (cm)

Inner radius of the chamber. Slider 1–50 cm, step 0.5.

**Disabled** for HIFU / pistol-jet / open-bath geometries — those
don't model a cavity in the current code.

For closed cavities, the radius sets the eigenmodes:
- Sphere: `f_n = n · c / (2R)`
- Cylinder radial: `f = c · 2.405 / (2πR)` (first Bessel zero)

| Radius | Volume | Sphere fundamental f₁ in seawater (c=1530 m/s) |
|---|---|---|
| 3 cm | 0.11 L | 25.5 kHz |
| **5 cm** | **0.52 L** | **15.3 kHz** (classic SBSL flask) |
| 10 cm | 4.2 L | 7.65 kHz |
| 20 cm | 33 L | 3.83 kHz |

Smaller chamber → higher mode frequencies → higher peak wall pressure
during collapse (closer wall sees more shock).

### `wall_material`

The wall's catalog name. Maps to a fully-populated `WallMaterial`
via `cavplasma.material.materials.get(name)` — sets density,
Young's modulus, yield strength, dynamic yield, fatigue limit,
hardness, plus chemical compatibility info.

| Material | σ_Y (yield, MPa) | p_Y_dynamic (MPa) | fatigue_limit (MPa) | Notes |
|---|---|---|---|---|
| **borosilicate_glass** (Pyrex) | 100 | 200 | 30 | transparent, classic SBSL cell |
| **fused_silica** | 50 | 100 | 25 | transparent, UV-grade |
| stainless_316 | 290 | 580 | 290 | robust, opaque |
| stainless_304 | 215 | 430 | 215 | cheaper than 316 |
| aluminum_6061 | 276 | 552 | 95 | light, low fatigue |
| aluminum_1100 | 35 | 70 | 30 | very soft |
| brass_C36000 | 124 | 248 | 95 | machinable |
| **titanium_6al4v** | 880 | 1760 | 510 | strong, light, expensive |
| **inconel_625** | 414 | 828 | 380 | best for cyclic shocks |
| open_water | — | — | — | sentinel: no wall |

For pistol-shrimp impulsive collapse: peak wall pressures can hit
~100 MPa briefly. Pyrex's *dynamic* yield handles single shots
(~21 MPa for 5 cm sphere with 3 mm wall) — borderline. Inconel 625
or Ti-6Al-4V handle repeated shocks indefinitely.

### `chamber_Q`

Quality factor. Numeric input, default 1000. **Disabled** for
HIFU / pistol-jet / open-bath.

| Q | Behaviour |
|---|---|
| 10–50 | broad bandwidth, weak amplification — open chambers |
| 100 | typical glass cell with no transducer tuning |
| **1000** | textbook SBSL Pyrex sphere |
| 5000+ | high-Q resonator, very narrow bandwidth |

`Q` controls two things at once:
- **Amplification**: on-resonance, drive gets multiplied by ~Q
- **Bandwidth**: half-power band is `f / Q`. At Q=1000, f=30 kHz, bandwidth = ±30 Hz — drive must be in this window or it gets attenuated.

### Derived: wall pressure capability

The right-column "Wall pressure capability" card shows four ratings
computed from the wall material + geometry:

- `static_yield_MPa = (2/3)·σ_Y·(1−(a/b)³)` — DC pressure first yield
- `static_collapse_MPa = 2·σ_Y·ln(b/a)` — DC plastic collapse
- `dynamic_yield_MPa = (2/3)·p_Y_dynamic·(1−(a/b)³)` — single-shock yield
- `fatigue_MPa = (2/3)·fatigue_limit·(1−(a/b)³)` — cyclic limit

Where `a` is inner radius, `b = a + wall_thickness`. Compare
peak wall pressure (from §13 stress probe observer) to:
- **dynamic_yield** for impulsive single-shot events (pistol shrimp)
- **fatigue_MPa** for SBSL continuous operation

---

## 2. Liquid

The medium the bubble lives in. Sets every bulk-fluid scalar in the
simulator.

### `liquid_dropdown`

Five entries in the catalog (`cavplasma.liquids.preset(name)`):

| Liquid | ρ (kg/m³) | c (m/s) | μ (Pa·s) | σ (N/m) | p_v (Pa) |
|---|---|---|---|---|---|
| **water** | 998 | 1482 | 1.0×10⁻³ | 0.073 | 2,339 |
| **seawater** | 1025 | 1530 | 1.1×10⁻³ | 0.075 | 2,300 |
| **glycerin** | 1261 | 1904 | 1.4 | 0.063 | 0.13 |
| **sulfuric_98** | 1840 | 1430 | 0.024 | 0.055 | 1.0 |
| **silicone_oil_100cSt** | 965 | 980 | 0.097 | 0.021 | 1.0 |

What each property does:

- **ρ density** — sets collapse violence (Rayleigh time ∝ √ρ); denser liquid means longer but more inertial collapse.
- **c sound speed** — sets radiation damping during collapse; sets chamber eigenmodes (`f_n = n·c/(2R)`); the simulator uses a T/p-corrected `c` (dossier §17 Q4) so changing `T_∞` or `p_∞` updates it live in the right-column liquid card.
- **μ viscosity** — damps shape modes, helps spherical stability. Glycerin's 1400× higher viscosity makes bubbles ridiculously stable.
- **σ surface tension** — favours spherical small bubbles.
- **p_v vapor pressure** — the secret weapon for hot plasma. Water at p_v ≈ 2.3 kPa puts vapor inside the bubble that quenches T_peak via H₂O dissociation. **Glycerin and H₂SO₄ have near-zero vapor pressure → no quenching → 25–40 kK plasma.**
- **Tait (B, n)** — compressibility EOS parameters; mostly transparent to the user.
- **B/A nonlinearity** — wave-steepening parameter; relevant only at very high amplitude.
- **Absorption (dB/cm/MHz²)** — energy loss per cm per MHz²; high in glycerin and silicone oil.

Use-case picker:

| Goal | Liquid | Why |
|---|---|---|
| Pistol-shrimp realism | seawater | natural medium |
| Standard SBSL | water | most published data |
| Maximum T_peak (30–40 kK) | sulfuric_98 + Xe | Suslick recipe; CORROSIVE |
| Hot SBSL without acid | glycerin + Ar | low vapor → 25 kK |
| Shape-mode studies | silicone_oil_100cSt | low σ, high μ |

The right-column "Liquid properties" card shows every catalog field
plus the T/p-corrected sound speed and acoustic impedance Z = ρc,
with inline interpretive labels for vapor pressure (green/yellow/orange)
and viscosity (white/yellow/blue). A per-liquid info banner explains
each one.

---

## 3. Ambient

Bulk-liquid temperature and pressure, far from the bubble.

### `ambient_T` (K)

Slider 273–323 K (0 to 50 °C), step 1 K. Tooltip shows `{value} K`,
readout below shows `K ≡ °C`.

**Effects in the simulator:**
- Sets the bulk-liquid initial temperature.
- The corrected sound speed depends on T (IAPWS polynomial; non-monotonic, peaks at 74 °C — see §19).
- Vapor pressure rises with T in real water but the simulator uses a fixed catalog `p_v`.

**Meaningful values:**

| T_∞ | When |
|---|---|
| 273 K (0 °C) | cold cavitation; α flips sign so compression *cools* the liquid (anomaly, dossier §18) |
| 283 K (10 °C) | typical cold ocean |
| **293 K (20 °C)** | **SBSL canonical** |
| 303 K (30 °C) | warm tropics |
| 323 K (50 °C) | sonochemistry hot bath |

### `ambient_p` (log₁₀ kPa)

Slider 1.5 to 5.0, step 0.025. The slider value is `log₁₀(p_∞ in kPa)` — covers vacuum to Mariana Trench. Readout below shows the actual pressure in human units plus the seawater-depth equivalent.

**Sliderval ↔ pressure:**

| Sliderval | p_∞ | Depth (seawater) |
|---|---|---|
| 1.5 | 32 kPa | — (high altitude / partial vacuum) |
| **2.0** | **100 kPa** | **surface (1 atm)** |
| 2.5 | 316 kPa | 21 m |
| 3.0 | 1 MPa | 89 m |
| 3.5 | 3.2 MPa | 311 m |
| 4.0 | 10 MPa | 984 m |
| 4.5 | 32 MPa | 3,148 m |
| 5.0 | 100 MPa | 9,935 m (Challenger Deep) |

**Effects:**
- Sets the static pressure pushing on the bubble during collapse — `Δp = p_∞ − p_v` is the driving pressure.
- Higher p_∞ → faster, more violent collapse, hotter T_peak.
- Affects the Blake threshold for cavitation onset.
- The Tait sound-speed correction adds ~13 % at 100 MPa vs 1 atm.

**Meaningful values for pattern hunting:**
- Surface (1 atm): textbook SBSL, T_peak ~ 20 kK
- 100 m depth: T_peak ~ 22 kK
- 1 km depth: T_peak ~ 36 kK
- 5 km depth: T_peak ~ 48 kK

(Pistol-shrimp scaling — see §16 in the dossier for sweep results.)

---

## 4. Drive

The acoustic forcing that shakes the bubble. Three sliders.

### `drive_f` — Drive frequency (Hz)

Slider 1,000 – 200,000 Hz, step 100. Tooltip and value are in Hz.
The slider value IS the frequency in Hz (no log conversion).

**Effects:**
- Determines how the drive couples into the chamber. Must be inside one of the chamber's mode bandwidths (`f_n / Q`) to avoid Q-attenuation. The R6 warning in the suggestions panel scans the first 4 modes and tells you the closest one.
- Sets the Minnaert ratio `f_drive / f_M` where `f_M ∝ 1/R₀`. SBSL operates at ratio ~0.03; at ratio ~1 the bubble enters linear oscillation (no inertial collapse).

**Meaningful values for a 5 cm sphere in water:**

| Frequency | What happens |
|---|---|
| 14.8 kHz | mode n=1 — too violent at moderate P_A |
| 26.5 kHz | SBSL canonical (technically off-mode by 4 kHz — historical) |
| **29.6 kHz** | **mode n=2 — actual on-resonance for SBSL** |
| 44.4 kHz | mode n=3 |
| **61.2 kHz** | **mode n=4 — gentlest mode, where the canonical sweep found `stable_spherical`** |
| 1 MHz | only meaningful with HIFU geometry |

### `drive_pa` — Drive amplitude (atm)

Slider 0.1 – 10 atm, step 0.05.

**Interpretation (dossier §20):** `P_A` is the *at-bubble* pressure
amplitude — what the bubble actually feels. The simulator assumes
your transducer can deliver this regardless of the chamber's
Q-response. The R6 warning shows what transducer output that would
require if you're off-resonance.

**Effects:**
- Below Blake threshold (~1 atm for typical SBSL R₀): no cavitation.
- Above threshold: bubble grows to R_max ≈ 22 · (P_A/p_∞ − 1) · R₀ + R₀.
- Beyond ~1.5–1.8 atm at canonical conditions: shape modes grow, bubble fragments before collapse.

**Meaningful values:**

| P_A | What happens |
|---|---|
| < 0.8 atm | sub-Blake, no cavitation |
| 1.0 atm | weak inertial collapse |
| **1.32 atm** | SBSL canonical, R_max/R₀ ≈ 8, T_peak ≈ 20 kK |
| **1.5 atm** | Suslick H₂SO₄+Xe, R_max/R₀ ≈ 12, T_peak ≈ 30 kK |
| 1.8 atm + | shape instability, bubble fragments |
| 5 atm + | only with HIFU; closed sphere can't deliver this |

### `drive_cycles` — Cycles to integrate

Slider 1–20, step 1.

**Effects:**
- Sets integration window: `n_cycles / drive_f`. At 8 cycles, 26.5 kHz: 302 µs.
- Bubble takes 2–3 cycles to settle into steady-state oscillation; then repeats.

**Meaningful values:**

| Cycles | Use case |
|---|---|
| 1–3 | impulsive event (pistol shrimp); transient only |
| **8** | SBSL canonical — captures transient + 5 steady cycles |
| 10–15 | clean steady-state, rebound dynamics fully resolved |
| > 20 | usually wasted CPU |

### How the drive knobs interact with everything else

| If you change... | ...this changes too |
|---|---|
| `drive_f` | which chamber mode you're near; Q-attenuation factor; Minnaert ratio with current R₀ |
| `drive_pa` | Blake threshold crossed yes/no; R_max/R₀; shape stability; required transducer P_A (off-resonance) |
| `drive_cycles` | integration time only |

Parameter coupling cheat-sheet:
- Move `drive_f` → check the R6 warning shows you're still on a mode.
- Move `drive_pa` → check the live status chip stays green (SBSL band).
- Move `R₀` → consider also moving `drive_f` to keep the Minnaert ratio sensible (auto-adapt panel proposes this).

---

## 5. Bubble

The bubble itself — its size, what's inside, where it sits, what
kind of event you're studying.

### `bubble_R0` (µm)

The bubble's equilibrium radius (size at rest, balanced against
ambient pressure + surface tension). Slider stores log₁₀(µm),
range 0.1 µm to 10 mm; paired input box shows actual µm.

**What R₀ sets:**
- **Minnaert (natural) frequency**: `f_M = (1/(2π·R₀))·√(3γ·p_∞/ρ)`. f_M ∝ 1/R₀ — bigger bubble → lower natural frequency.
- **Blake threshold**: bigger R₀ → easier to cavitate. A 50 µm bubble cavitates at ~0.5 atm; a 1 µm bubble needs ~3 atm.
- **R_max growth**: at fixed P_A/p_∞ ratio, the absolute R_max scales with R₀.
- **Laplace pressure**: `2σ/R₀` — smaller bubble, more surface tension squeezing inward.

**Meaningful values:**

| R₀ | Use case |
|---|---|
| 1–3 µm | Suslick H₂SO₄+Xe regime — small bubble, less vapor in-fill, hotter |
| **4.5 µm** | **SBSL canonical** |
| 10–50 µm | sonochemistry; bubbles in detergent water |
| 100–500 µm | medical microbubble contrast agents |
| 0.5–3 mm | impulsive cavitation (laser, spark, **pistol shrimp**) |

### Gas composition: `gas_ar`, `gas_h2o`, `gas_air`

Three numeric inputs giving the bubble's gas mole fractions.

| Component | γ (adiabatic index) | Effect on T_peak |
|---|---|---|
| **Ar** (argon) | 5/3 = 1.667 | highest — monatomic, no internal modes |
| **H₂O** (water vapor) | ~1.33 | endothermic dissociation at ~5000 K quenches T_peak ~2× |
| **Air** (N₂/O₂) | 1.40 | reactive at high T, quenches relative to Ar |

How `gas_air` decomposes in `apply_controls`:
- N₂ = 0.78 × gas_air
- O₂ = 0.21 × gas_air
- Ar = gas_ar + 0.0093 × gas_air (atmospheric Ar component added)

**Common mixes:**

| `gas_ar` | `gas_h2o` | `gas_air` | Result |
|---|---|---|---|
| 0.99 | 0.01 | 0 | **SBSL canonical** — pure Ar with vapor equilibrium |
| 0 | 0 | 1.0 | air-saturated water (real-world starting condition) |
| 0.95 | 0.05 | 0 | Ar with extra water vapor — slightly hotter than SBSL |
| 0 | 0 | 0 | (falls back to whatever the preset's seed has) |

**Argon rectification** (real-world physics not in the model):
in air-saturated water, after ~10⁴ acoustic cycles the bubble
selectively expels reactive N₂/O₂ and concentrates Ar to ~99 %.
That's why air-seeded SBSL ends up looking like Ar SBSL after
~10 seconds of operation. The **C3 caveat** in the suggestions
panel reminds you of this when a run covers many cycles.

### `seed_position` (currently JSON-only)

`(x, y, z)` coordinates of the bubble centre in metres. Default
`(0, 0, 0)` = chamber centre. **Not in the UI** — set via JSON
or preset.

**Effects:**
- For closed sphere: bubble at centre = pressure antinode = full P_A. Off-centre, sees `P_A · sinc(π·r/R)`.
- Wall stress depends on bubble-to-wall distance. Closer = harder hit.

For pistol-shrimp impulsive events, position barely affects the
bubble dynamics directly (ambient pressure is uniform), but it
shifts where the wall stress is measured.

### Hidden seed parameters (not in UI)

These live on the `BubbleSeed` dataclass and are set by presets:

| Param | Default | What it does |
|---|---|---|
| `Rdot0` | 0 m/s | initial wall velocity at t=0 |
| `T0` | 293.15 K | initial gas temperature inside bubble |
| `gamma_g` | 5/3 (Ar) or 1.4 (air) | adiabatic index |
| `kappa` | 1.4 | polytropic index for the polytropic thermal model only |
| `seed_method` | `"rectified_diffusion_equilibrium"` / `"freeze_at_nucleation"` | how the initial state is computed at t=0 |
| `p_gas_initial` | 1 kPa (pistol shrimp) | initial gas pressure inside bubble for impulsive events; lower → more violent collapse |
| `toroidal_correction_factor` | 1.0 | shape-correction multiplier |

For pistol-shrimp realism, `p_gas_initial` is the most important
hidden parameter — it sets how much non-condensable gas remains
in the bubble at R_max. Standard 1 kPa gives Versluis 2000
collapse violence.

### `BubblePopulation.kind` (preset-controlled)

| Kind | What it is | Used by |
|---|---|---|
| `single_trapped` | one bubble in continuous acoustic drive | SBSL, tabletop_starter |
| `impulsive` | one-shot event with R_max + p_gas_initial set explicitly | pistol_shrimp_event |
| `cloud` | v3 — raises `NotImplementedError` | reserved for future |

### Derived: bubble properties card (right column)

The right-column "Bubble properties" card shows the derived
quantities from R₀ + gas + liquid + ambient + drive, updated live:

- R₀ in µm
- Gas mix string
- γ_g with annotation (monatomic / diatomic / polyatomic)
- Minnaert frequency f_M in kHz
- Drive frequency f and the **drive/Minnaert ratio**
- Laplace surface tension pressure (= 2σ/R₀)
- Blake threshold in atm

Plus two coloured banners:
- **Regime indicator** (info): "inertial collapse regime — SBSL works here" / "near-resonance — bubble oscillates linearly" / etc.
- **Blake margin** (green/grey): "above Blake — drive 1.32 atm vs threshold 0.96 atm (margin +37%)" or "sub-Blake — drive 0.40 atm < threshold 0.96 atm".

---

## 6. Physics *(to be documented)*

Currently exposes:
- `phys_bubble_eq` — Keller–Miksis / Rayleigh–Plesset / Gilmore
- `phys_thermal` — Toegel / polytropic
- `phys_ionization` — Stewart–Pyatt / ideal Saha

(Not yet expanded.)

---

## 7. Numerics *(to be documented)*

Currently exposes:
- `num_rtol` — log10 of relative tolerance for the ODE solver
- `num_conv` — toggle for the §11.5 convergence test

(Not yet expanded.)

---

## 8. Auto-design *(to be documented)*

Inverse-design panel. Target T_peak + filters → heuristic or grid-
refined scenario. Plus auto-adapt toggle that proposes coupled
slider values via Minnaert ratio.

(Walk-through TBD.)

---

## Cross-cutting concepts

These show up across multiple panels.

### Blake threshold

The drive amplitude needed to overcome surface tension and trigger
inertial cavitation. For a bubble of radius R₀ in a liquid with
surface tension σ at ambient pressure p_∞:

```
P_B ≈ p_∞ + (4·σ / (3·R₀)) · √(2·σ / (3·R₀·p_∞))
```

For canonical SBSL (R₀ = 4.5 µm, water, 1 atm): P_B ≈ 1.0 atm.

The live status chip flags `sub-Blake` when `P_A < P_B`.

### Minnaert frequency

The bubble's natural radial-oscillation frequency. For a
gamma-polytropic gas in a liquid of density ρ:

```
f_M = (1 / (2π·R₀)) · √(3·γ·p_∞ / ρ)
```

For canonical SBSL: f_M ≈ 850 kHz at R₀ = 4.5 µm in water.

The drive/Minnaert ratio determines regime:
- ratio « 1 → inertial collapse (SBSL works)
- ratio ~ 1 → linear resonance, no collapse
- ratio » 1 → drive is too fast, bubble can't follow

### Q-bandwidth attenuation

Off-resonance drive is attenuated by the chamber Q:

```
attenuation = √(1 + (2Q · Δf / f_mode)²)
```

For a 5 cm sphere with Q=1000 driven 5 kHz off the n=2 mode:
`atten = √(1 + (2·1000·5000/30000)²) ≈ 333×`. Means your transducer
needs to output 333× the at-bubble `P_A` you specified.

The R6 suggestion shows the required transducer P_A and flags
`> 50 atm` as "exceeds practical piezo capacity".

### Sound speed correction

The simulator uses `corrected_sound_speed_for(liquid, ambient)` that
applies T- and p-dependence on top of the catalog c:

- Pure water: IAPWS-95 polynomial in T (peaks at 74 °C, dossier §19)
- Seawater: Mackenzie 1981 in (T, S, depth)
- All liquids: Tait pressure correction `c² = c_0² + (n−1)·H`

Delta-from-calibration scheme: at 20 °C / 1 atm the correction is
exactly zero, so SBSL canonical stays bit-identical to v1. Off-corner
the corrected `c` shows up in the right-column liquid card.

---

## Where to look up which parameter does what

| You see this in the UI | Maps to |
|---|---|
| Wall pressure capability (right column) | `wall_pressure_capability(scenario)` in `cavplasma/ui/callbacks.py` |
| Liquid properties (right column) | `render_liquid_properties_card(scenario)` |
| Live status chip | `_classify_live` |
| Auto-adapt proposal | `_adapt_partner_slider` + Minnaert ratio |
| R6 off-resonance warning | `_check_off_resonance` in `cavplasma/scenario/scenario.py` |
| Regime card "why this regime?" | `classify_with_rationale` in `cavplasma/suggestions/regime.py` |

For physics-deep references (Newton-Laplace, Mackenzie, Clausius-
Clapeyron, etc.), see the research dossier in `cavitation_research/`:

- §16 — pressure regimes from waterjets to black holes
- §17 — sound speed in compressed water
- §18 — pressure-temperature-salinity coupling
- §19 — sound speed temperature dependence (74 °C peak)
- §20 — what `P_A` means

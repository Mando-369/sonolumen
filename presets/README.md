# Preset library

Ready-to-load JSON scenarios. Open the UI (`./start.sh`), click
**Load JSON**, and pick one of these. Or look at any one in this
folder as a template for your own scenarios — the JSON format is
documented in `sonolumen/scenario/io.py` (§12.9 of the dossier).

The status line under the Save / Load buttons will show the
loaded file name + `scenario.name` from the metadata.

## Series 1 — Pistol shrimp in a real chamber

These four take the open-water `pistol_shrimp_event` preset and
put the impulsive bubble inside a closed sphere with various wall
materials. Bubble dynamics are identical (same impulsive collapse,
T_peak ≈ 8200 K, ~6×10⁹ photons); the **wall stress observer** is
the active diagnostic.

| File | Wall | Wall thickness | Why |
|---|---|---|---|
| `00010_shrimp_in_pyrex_5cm.json` | borosilicate Pyrex | 3 mm | transparent; check fatigue margin |
| `00011_shrimp_in_stainless316_5cm.json` | SS-316 | 5 mm | robust + cheap; opaque |
| `00012_shrimp_in_inconel_5cm.json` | Inconel 625 | 5 mm | best fatigue limit; long-life |

Compare the **Wall pressure capability** card: Pyrex's 3.2 MPa
fatigue limit vs Inconel's 70 MPa. A single shrimp shot is fine
in any of them; cyclic operation only Inconel survives indefinitely.

## Series 2 — Pistol shrimp at depth

| File | p_∞ | Equivalent depth | T_peak |
|---|---|---|---|
| `00010_shrimp_in_pyrex_5cm.json` | 101 kPa | surface | 8.2 kK |
| `00013_shrimp_at_1km_depth.json` | 10 MPa | ~1 km seawater | **36 kK** |

The depth preset shows the depth coupling we documented in dossier §16:
deeper water → stiffer collapse → ~4× hotter T_peak with the same
impulsive bubble.

## Series 3 — Pistol shrimp + acoustic boost

| File | Drive | Result |
|---|---|---|
| `00014_shrimp_with_30khz_boost.json` | 30.6 kHz / 1 atm at chamber mode n=2 | regime = `linear_oscillation` |

Tests whether a continuous on-mode acoustic drive amplifies the
impulsive collapse via chamber Q. Result: at 1 atm, the boost is
too weak compared to the impulsive event — bubble stays in linear
regime, T_peak barely changes. Useful as a baseline; try cranking
up the drive to see when the boost wins.

## Series 4 — Hot SBSL recipes

| File | Liquid | Wall | Gas | R₀ | Drive | Regime | T_peak | Photons |
|---|---|---|---|---|---|---|---|---|
| `00015_suslick_h2so4_ar_sbsl.json` | 98 % H₂SO₄ | Pyrex | Ar | 4.5 µm | 28.6 kHz / 1.5 atm | stable_spherical | 16 kK | 2.0e6 |
| `00023_stable.json` | 98 % H₂SO₄ | **Ti-6Al-4V** | Ar | **8 µm** | 28.6 kHz / 1.5 atm | **stable_spherical** | **15 kK** | **7.0e6** |
| `00016_glycerin_viscous_demo.json` | pure glycerin | Pyrex | Ar | 4.5 µm | 38 kHz / 3 atm | linear_oscillation | 296 K | — |

**`00023_stable.json` is a cleaner Suslick variant** — same liquid
(H₂SO₄) and drive frequency (28.6 kHz mode n=2) as 00015, but with
R₀ bumped from 4.5 µm → 8 µm and the chamber wall switched to
Ti-6Al-4V (better fatigue resistance for hot SBSL). Drive/Minnaert
ratio = 0.090 — textbook SBSL inertial regime. ~3.5× more photons
than 00015 due to the larger R₀.

The Suslick presets use concentrated sulfuric acid (low vapor
pressure → no quenching). T_peak comes in at 15–16 kK rather than
the literature 30 kK because we're using mode n=2 not the actual
transducer-coupled chamber mode; tune drive_f and try.

The glycerin preset is intentionally a *demonstration* of the
viscous-dominated regime — pure glycerin (μ=1.4 Pa·s, ~1400×
water) is too viscous for SBSL to ignite at typical bubble sizes.
Real glycerin-SBSL experiments (Holsteyns 2007) use 5 % glycerin
in water, not pure glycerin.

## Series 5 — SBSL drive-amplitude threshold

Three presets at fixed chamber + R₀, only `drive_pa` varies:

| File | P_A | Regime | T_peak |
|---|---|---|---|
| `00019_sbsl_pa_weak_100.json` | 1.00 atm | sub_blake | 385 K |
| `00020_sbsl_pa_canonical_132.json` | 1.32 atm | marginal | 30 kK |
| `00021_sbsl_pa_violent_150.json` | 1.50 atm | marginal | 55 kK |

Load these in order, click TEST on each, and the **regime history
strip** in the lab notebook will show the cavitation threshold
crossover: grey (sub-Blake) → amber (marginal). Useful for
calibrating where the band edges live in your chamber + liquid.

## Series 6 — Other comparison points

| File | What it tests |
|---|---|
| `00017_air_saturated_water_sbsl.json` | starting state before argon rectification (78 % N₂, 21 % O₂); pre-rectification |
| `00018_cold_water_sbsl_1C.json` | T_∞ = 1 °C — anomalous α<0 compression cooling regime (dossier §18) |
| `00022_hifu_sonochem_1mhz_10atm.json` | HIFU focal-spot cavitation (1 MHz / 10 atm / R₀=2 µm); regime = `transducer_limited` |

## Earlier presets (kept for reference)

| File | Origin |
|---|---|
| `sonolumen_scenario_00001.json` | user's first "stable" hit (later flagged as off-resonance trap; produced `linear_oscillation`) |
| `sonolumen_scenario_00002-stable.json` | user's 10 kHz / 2 atm config (stable_spherical in model, but requires 1400 atm transducer per §20) |
| `sonolumen_scenario_00002_stable_sbsl_n4.json` | grid-searched real SBSL hit at chamber mode n=4 (61.2 kHz, 2 atm) — works in a real chamber |
| `sonolumen_scenario-stable_spherical Stable single-bubble dynamics-SBSL band.json` | user's earliest exploration |

## How to add your own preset

1. Configure the UI to your liking (every panel)
2. Click **Save JSON** — downloads `sonolumen_scenario.json`
3. Rename it descriptively and drop it in this folder
4. Add a row to this README with what it tests

Or, build it in Python with `dataclasses.replace` on a base preset,
then call `scenario.to_json()` and write the result. See the
`build_presets.py`-style commits in git history for examples
(commits `cb54faa`, `3be5448`, etc.).

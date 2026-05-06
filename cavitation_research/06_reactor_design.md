# Section 6 — Reactor design parameters

> Purpose: practical engineering data for a tabletop biomimetic cavitation
> reactor. The simulator's domain is bubble + plasma physics, but the
> reactor design constrains *what regime is reachable* — chamber dimensions
> set the available eigenfrequencies (Section 3), liquid choice sets the
> peak T (Section 4), nucleation method sets the bubble seed parameters
> (Sections 2 and 9). This section is a checklist of design choices the
> simulator's "Reactor" object should expose.

---

## 6.1  Chamber geometries used in the literature

| Geometry            | Typical dimensions  | Frequency band   | Use case                    | References |
|---                  |---                  |---               |---                          |---         |
| Spherical resonator | 5–10 cm radius      | 14–30 kHz        | Single-bubble sonoluminescence (SBSL) | [BHL2002, Z2003] |
| Cylindrical resonator (axial) | 5–20 cm L | 5–25 kHz | SBSL, large standing-wave volume | [BHL2002] |
| Open-bath horn      | 100 mL – 5 L bath, horn 13–25 mm dia | 20 kHz typical | Multibubble cavitation (MBSL), sonochemistry | [SD2008, KCL2014] |
| HIFU bowl + cuvette | 5–10 cm radius bowl, focal cuvette ~1 cm³ | 0.5–2 MHz | Single-bubble or microbubble cloud at MHz | [HIFU2020] |
| Microfluidic cell   | 100 µm – 1 mm channel | 100 kHz – 5 MHz  | Single-bubble in chip, controlled environment | [B2010] |
| Pistol-shrimp mimic | 10–50 mL, jet-driven | impulsive, no f  | Reproduce shrimp jet event   | [PS2024] |

The two most relevant for the biomimetic plasma reactor are:

- **Spherical resonator + air or argon-saturated water**: classical SBSL
  setup; reaches T ≈ 10⁴–4×10⁴ K. This is the "physics-target" geometry.
- **Open-bath horn or HIFU + degassed liquid**: MBSL geometry; produces
  many simultaneous flashes, easier to detect cumulatively. T ≈ 5 000–
  15 000 K, but more events per second.

The pistol-shrimp-mimic geometry (collapsing high-speed jet rather than
acoustic standing wave) is the truest analogue but is engineering-harder
and less reproducible. See [PS2024] for one published example.

---

## 6.2  Materials

Walls:
- **Borosilicate glass** (Pyrex, Schott Duran): standard for SBSL cells.
  Transparent UV→IR (down to ~300 nm). Acoustic impedance Z ≈ 1.3 × 10⁷
  rayl — large mismatch with water makes it acoustically rigid (good
  reflection for resonance).
- **Quartz / fused silica**: needed for UV diagnostics below 200 nm.
- **Stainless 316**: rugged, opaque, used for industrial sonoreactors.
  Z ≈ 4.6 × 10⁷ rayl.

Transducers:
- **PZT-4 / PZT-8** disc, ring, or bowl transducers. Typical d₃₃ ≈ 290–330
  pC/N, k_p ≈ 0.55 (planar coupling factor). [APC, M2018]
- For cylindrical SBSL cells the transducers are usually two opposing
  PZT rings bonded to the sidewall driven in radial mode.
- For HIFU, single-piece spherical-cap PZT or 1.5-D phased arrays.

Coupling layers (HIFU): degassed water reservoir + thin Mylar window;
acoustic gel for in-air coupling (rare for cavitation work).

---

## 6.3  Operating frequencies (recommended bands)

| Band         | What it does                          | Typical hardware           |
|---           |---                                    |---                         |
| 20–25 kHz    | Easy to reach > 1 MPa P_A; vigorous cavitation; loud (audible) | Langevin transducer, 50 W–1 kW |
| 30–40 kHz    | SBSL sweet spot; quieter; matches Minnaert resonance for ~50–100 µm bubbles | Glass-walled spherical cell + side PZTs |
| 100–500 kHz  | Smaller bubbles, higher collapse Mach numbers; more chemistry/yield per event | PZT discs, 10–100 W |
| 1–3 MHz (HIFU) | Highly localized cavitation at focus; medical imaging integration | HIFU bowl or array |

For a **first-build biomimetic reactor** the recommended starting band
is **20–40 kHz** because (a) standard SBSL physics is well characterised
in this band, (b) inexpensive Langevin transducers can deliver the
required > 1.2 atm acoustic pressure into water, and (c) a clear,
vacuum-degassed glass cell is cheap.

---

## 6.4  Power and electrical requirements

Minimum electrical power for cavitation in water at 20 kHz, ~100 mL cell:
- 30–100 W RMS to overcome chamber losses and reach P_A ≈ 1.2 atm in a
  Q ≈ 200 cell [BHL2002].
- A 1-kW industrial sonochemistry horn delivers ~600–800 W of acoustic
  power into a 1-L bath.

Driving electronics chain:
1. RF function generator (e.g. 20 kHz square or sine, sweepable).
2. 100–1000 W class-D amplifier matched to transducer impedance.
3. Tuning network (LC matching) — necessary because piezo impedance is
   capacitive at frequency.
4. Closed-loop frequency lock (PLL) to track the chamber resonance as the
   liquid degasses (the speed of sound shifts with dissolved-gas content
   and temperature).

The simulator should treat the electronics as a black box but expose
"effective" parameters: P_A as a function of (V_drive, η_transducer,
Q_chamber, frequency offset from resonance).

---

## 6.5  Cooling and thermal management

Acoustic energy ultimately becomes heat in the liquid. At 100 W net into
100 mL water, ΔT_water ≈ 0.24 K/s. The cell must be either:
- Liquid-cooled jacket (water at constant T_c).
- Periodic operation (run, cool, run).

Temperature affects: vapour pressure (sets cavitation threshold and peak
T_min), gas solubility (Henry's law, sets dissolved-gas concentration),
sound speed (sets resonance frequency). A drift of 5 K can shift the
resonance by ~0.05 % and detune a Q = 500 cell out of band.

Recommended: PID-controlled water jacket, T = 20.0 ± 0.1 °C.

---

## 6.6  Bubble nucleation and seeding

In SBSL the bubble is *introduced once* and trapped by the standing-wave
field. Methods:
- **Hot wire spark**: a thin Ni–Cr or Pt wire briefly heated to vapourise
  a small volume. Most common technique [BHL2002, Z2003].
- **Laser-pulse-induced**: focused ns laser produces a vapour bubble at
  the focus.
- **Syringe injection**: large bubbles ejected, trapped bubble shrinks via
  rectified diffusion to steady-state radius.
- **Electrolysis**: a small DC current splits water at electrodes and
  produces H₂ + O₂ bubbles.

In MBSL (cavitation cloud) nucleation is *spontaneous* on impurities and
dissolved-gas pockets; the cell does not need a seed. Background "natural"
cavitation nuclei in tap water are ~10⁴–10⁶ /cm³ at sizes 1–10 µm.

For the simulator, expose:
- `seed_method`: {'hot_wire', 'laser', 'syringe', 'spontaneous'}.
- `R0_seed` (equilibrium bubble radius)
- `n_nuclei` (volume density of nuclei, for MBSL)
- `gas_composition` (mole fractions in seed)

---

## 6.7  Liquid choices

Recommendations from §3.6 + §4.5:

| Use case                      | Liquid                  | Saturating gas        | Rationale |
|---                            |---                      |---                    |---        |
| Baseline biomimetic reactor   | Distilled water         | Air, 20 % saturation  | Cheap, well-characterised |
| Brightest aqueous SBSL        | Distilled, degassed water | Argon, 20 % sat.    | Removes N₂/O₂ chemistry |
| Highest plasma T              | 85–95 % H₂SO₄          | Xenon, 20 % sat.      | Dense, low p_v, low chemistry [FS2005] |
| Lowest threshold (didactic)   | Glycerin                | Air                   | Forgiving but damped     |

Liquid *purity* matters. Trace surfactants, DOC, and ionic contamination
all suppress cavitation. SBSL-grade water typically has resistivity > 18
MΩ·cm and is freshly degassed.

---

## 6.8  Existing tabletop devices (with published specifications)

- **Stony Brook SBSL apparatus** (Putterman group). 100 mL spherical
  Pyrex flask, 25 kHz, two PZT-4 cylindrical transducers driven by a
  100 W amplifier. Single Ar-bubble at center. [Z2003, BHL2002]
- **Suslick group MBSL apparatus**. 25 mL flat-bottom flask + horn,
  20 kHz, 50–100 W net acoustic. Spectrometric measurements of conc.
  H₂SO₄ + Xe SBSL. [FS2005, SD2008]
- **HIFU clinical device** (ExAblate, MR-guided focused ultrasound).
  256-element 1.5 MHz array, 90 MPa peak focal shocks. [HIFU2020]
- **Pistol-shrimp-inspired generator** (PSC-2024). Solenoid-driven
  rotating claw immersed in water, captures cavitation cycle. [PS2024]
- **Industrial sonotrode** (Hielscher UIP1000hd, Sonics VC-1500). Up to
  1.5 kW at 20 kHz, used in chemical processing.

---

## 6.9  Safety considerations

- **Acoustic exposure**: a 200 W horn at 20 kHz radiates ~120 dB at 1 m
  in air. Ear protection required; subharmonic content in audible band.
- **Optical**: SBSL emits UV; full-cell containment and UV-blocking
  enclosure for prolonged work.
- **Electrical**: 1 kV-class drive on transducers; cell electrically
  isolated; fault-current interlock on power supply.
- **Pressurised liquid**: degassing under vacuum produces a partially
  evacuated cell; implosion risk if cell wall is thin glass — use
  thick-walled Pyrex (≥ 3 mm) or quartz, and pressure-rated fittings.
- **Hot wire**: brief high current pulse; place on transient relay; allow
  cooldown.
- **Chemical**: H₂SO₄ runs require fume hood, PPE, and corrosion-resistant
  fittings (PTFE, glass only).

---

## 6.10  What the simulator's `Reactor` object should expose

```python
Reactor(
    geometry=...,            # 'sphere' | 'cylinder' | 'horn' | 'hifu_focus'
    chamber_radius=...,      # m
    chamber_length=...,      # m (cylinders only)
    wall_material='pyrex',   # affects Q via boundary impedance
    liquid='water',          # 'water' | 'glycerin' | 'sulfuric' | ...
    temperature=293.15,      # K
    dissolved_gas='argon',   # 'air' | 'argon' | 'xenon' | 'helium'
    saturation_fraction=0.2, # x of equilibrium dissolved-gas content
    transducer_power_W=100,  # net acoustic power
    drive_frequency_Hz=25e3,
    chamber_Q=300,           # quality factor (loaded)
    seed_method='hot_wire',
    R0_seed=4.5e-6,          # m
    n_nuclei=0,              # m^-3 (MBSL only)
)
```

This is the bridge from the physical reactor to the bubble + field
modules of Sections 2 and 3.

---

## Citation tags used in this section

- [APC] APC International, *Piezoelectric Ceramics — Principles and Applications*.
- [BHL2002] Brenner, Hilgenfeldt, Lohse, *Rev. Mod. Phys.* 74, 425 (2002).
- [Z2003] Ziegler (Stony Brook), single-bubble sonoluminescence apparatus notes (2003).
- [SD2008] Suslick, Flannigan, *Annu. Rev. Phys. Chem.* 59, 659 (2008).
- [KCL2014] Kanthale et al., *Ultrason. Sonochem.* 21, 1069 (2014).
- [HIFU2020] Izadifar et al., *J. Clin. Med.* 9, 460 (2020).
- [B2010] Bremond, Versluis et al., microfluidic single-bubble experiments.
- [FS2005] Flannigan, Suslick, *Nature* 434, 52 (2005).
- [M2018] Morgan Advanced Materials, *Piezo Materials Datasheet*.
- [PS2024] Lee et al., *Acoust. Soc. Korea* (2024) — pistol-shrimp-inspired cavitation generator.

# Section 1 — Biological cavitation reference data

> Purpose: provide measured values from the biological cavitation literature
> that bracket the regime a tabletop reactor should target. The pistol shrimp
> and the smasher mantis shrimp are the two existing biological systems that
> demonstrably generate cavitation strong enough to produce a brief plasma
> phase. Their parameters are useful as upper-bound bio-references for the
> reactor design (chamber pressure scale, bubble size, collapse time, photon
> yield).

All numerical values are reproduced from peer-reviewed primary sources. Each
fact is followed by an inline citation tag like `[V2000]`; the full
references are in `references/bibliography.md`.

---

## 1.1  Pistol (snapping) shrimp — *Alpheus heterochaelis* and *Synalpheus*

### Claw closure mechanics

| Quantity                       | Value                          | Source     |
|---                             |---                             |---         |
| Snapper plunger tip velocity   | up to ≈ 30 m s⁻¹ in water     | [V2000]    |
| Estimated jet velocity         | ≈ 25 m s⁻¹                     | [V2000]    |
| Closing duration               | ≈ 600 µs                       | [V2000]    |
| Reynolds number of jet         | Re ≈ 4 × 10⁴                   | [V2000]    |
| Bernoulli pressure drop in jet | ΔP ≈ ½ ρ U² ≈ 3 × 10⁵ Pa       | [V2000]    |

The jet velocity exceeds the cavitation onset condition (Bernoulli pressure
drop > saturation vapour pressure of water, ≈ 2.34 kPa at 20 °C), so the
core of the jet vapourises and forms a cavitation bubble. The acoustic
"snap" originates at bubble *collapse*, not at claw closure; this was
established in [V2000] by simultaneous high-speed imaging and hydrophone
recording.

### Cavitation bubble dynamics

| Quantity                                     | Value                               | Source     |
|---                                           |---                                  |---         |
| Maximum bubble radius (single-snap)          | ≈ 3.5 mm                            | [V2000]    |
| Lifetime of bubble (formation → final collapse) | ≈ 300 µs                          | [V2000]    |
| Time of first collapse after closure         | ≈ 700 µs                            | [V2000]    |
| Geometry                                     | Initially toroidal, then spheroidal | [HBN2017]  |
| Bubble dynamics model                        | Rayleigh–Plesset–like, fits R(t)    | [V2000]    |

[V2000] explicitly fit a Rayleigh–Plesset-type equation (see Section 2) to
the measured R(t) and obtained quantitative agreement, both for the bubble
radius history and the radiated acoustic pulse.

### Hydroacoustic emission

| Quantity                                       | Value                                 | Source       |
|---                                             |---                                    |---           |
| Peak-to-peak source level (zero-to-peak SL)    | 183–190 dB re 1 µPa @ 1 m              | [AB1998]     |
| Peak source level (Schmitz/Lohse measurement)  | up to 218 dB re 1 µPa @ 1 m peak       | [V2000, L2001] |
| Acoustic pressure at 4 cm                      | ≈ 80 kPa peak (≈ 218 dB re 1 µPa local) | [V2000]    |
| Frequency content                              | broadband, 2 kHz – ≥ 200 kHz           | [AB1998]     |
| Pulse duration (acoustic)                      | a few hundred µs total, with a sub-µs sharp shock at collapse | [V2000] |

### Optical emission ("shrimpoluminescence")

| Quantity                              | Value                         | Source     |
|---                                    |---                            |---         |
| Flash duration                        | < 10 ns                       | [L2001]    |
| Photons per flash (visible)           | ≈ 5 × 10⁴                     | [L2001]    |
| Inferred peak interior temperature    | ≥ 5 000 K (lower bound)       | [L2001]    |
| Spectrum                              | broadband, consistent with hot blackbody, no line structure resolved | [L2001] |
| Light yield ratio vs. driven SBSL     | 10⁻¹ – 10⁻² of single-bubble sonoluminescence | [L2001] |

The 5 000 K lower bound is conservative; it comes from the requirement that
the observed photon yield in the visible band correspond to a thermal
source. The actual interior temperature is plausibly higher but cannot be
constrained from the photon count alone.

### Energy budget (single snap)

A back-of-envelope energy balance, traceable to [V2000]:

- Kinetic energy of jet:  E_jet ≈ ½ ρ V_jet U² where V_jet ≈ 1 mm³ and
  U ≈ 25 m s⁻¹  →  E_jet ~ 3 × 10⁻⁴ J.
- Potential energy stored in maximum bubble: E_bubble ≈ (4π/3) R_max³ × P∞
  with R_max ≈ 3.5 mm and P∞ ≈ 10⁵ Pa  →  E_bubble ~ 2 × 10⁻² J.
- The energy that ends up in the optical flash (~5×10⁴ photons × ~3 eV) is
  ~ 2 × 10⁻¹⁴ J — i.e. a vanishingly small fraction. Almost all the
  collapse energy goes into the radiated shock and re-expansion.

These rough values are useful for setting the reactor energy scale: a
single biologically relevant cavitation event releases ~10⁻²–10⁻¹ J.

---

## 1.2  Smasher mantis shrimp — *Odontodactylus scyllarus*

The mantis shrimp produces cavitation in a different geometry (an
appendage striking a surface rather than a closing claw + jet), so its
numbers are a useful comparison rather than a direct analogue.

| Quantity                                              | Value                                | Source     |
|---                                                    |---                                   |---         |
| Strike speed (dactyl tip in water)                    | 12–23 m s⁻¹                           | [PCB2005]  |
| Peak acceleration                                     | ≈ 1.04 × 10⁵ m s⁻² (≈ 10 400 g)      | [PCB2005]  |
| Strike duration                                       | < 800 µs end-to-end                   | [PCB2005]  |
| Spring mechanism                                      | Saddle-shaped exoskeletal element     | [PKC2004]  |
| Peak limb impact force                                | 400–1 501 N                          | [PCB2005]  |
| Peak cavitation collapse force                        | up to 504 N                          | [PCB2005]  |
| Time between impact peak and cavitation peak          | 390–480 µs                           | [PCB2005]  |
| Visible cavitation                                    | yes; toroidal sheets at the dactyl   | [PKC2004, PCB2005] |
| Strike energy (per strike, dactyl KE)                 | 100–300 mJ                           | [PCB2005, derived from F·d and v² scaling] |
| Energy fraction returned via cavitation               | up to ~30 % of total impact energy   | [PCB2005]   |

The "dual force peak" is mechanically important: the first peak is the
solid–solid impact, the second is the cavitation-bubble collapse. The
delay (~400 µs) is comparable to a Rayleigh collapse time for bubbles of
~1 mm scale at ambient pressure — see Section 2 for the Rayleigh collapse
formula.

No direct optical-flash measurement on smasher mantis shrimp has been
published as of this dossier, so plasma conditions there are inferred
only by analogy with [V2000, L2001].

---

## 1.3  Sonoluminescence (the laboratory analogue)

Sonoluminescence — light emission from acoustically driven cavitation in
a degassed liquid — is the laboratory phenomenon that bridges the
biological observation and the engineered reactor target. Two regimes are
well characterised:

### Single-bubble sonoluminescence (SBSL)

A single trapped bubble driven by a standing acoustic field at ~20–40 kHz
emits a periodic, sub-nanosecond flash of light each acoustic cycle.

| Quantity                                  | Value                                 | Source     |
|---                                        |---                                    |---         |
| Flash duration (room-T, water, air seed)  | 60–250 ps (Gaussian)                   | [GGKL1997] |
| Spectrum                                  | broadband, peaks in UV; no line structure in pure noble-gas-saturated water | [BHL2002] |
| Inferred peak interior temperature        | 10⁴ – ≈ 4 × 10⁴ K                     | [BHL2002, FBSP2005] |
| Photons per flash (visible band)          | 10⁵ – 10⁷                              | [BHL2002] |
| Forcing pressure amplitude                | 1.2–1.5 atm at fundamental             | [BHL2002] |
| Driving frequency                         | 20–40 kHz typical                      | [BHL2002] |
| Ambient bubble radius R₀                  | 4–5 µm typical                        | [BHL2002] |
| Maximum radius during cycle               | 30–60 µm typical                      | [BHL2002] |

### Multi-bubble sonoluminescence (MBSL)

When a strong acoustic field drives cavitation throughout a liquid
volume, many bubbles emit incoherently. MBSL spectra are different from
SBSL: in MBSL the flashes are longer (ns), often show *line emission*
from atomic and molecular species (OH, Na, etc.), and inferred
temperatures are typically 4 000 – 15 000 K [SD2008, FBSP2005].

This regime is the closest published analogue for what a tabletop
biomimetic reactor will most easily produce — cavitation clouds rather
than single trapped bubbles.

---

## 1.4  Implications for a biomimetic reactor

The biological numbers above set the following design targets, which feed
forward into Sections 6 and 9:

1. **Length scale of a single cavitation event.** A bubble of R_max ≈
   1–4 mm collapsing under ~10⁵ Pa ambient pressure is biologically
   sufficient to produce > 5 000 K interior conditions and a
   sub-10-ns optical flash. A tabletop reactor that can drive bubbles
   of similar maximum radius at ambient pressure is in the right ballpark.

2. **Time scales the simulator must resolve.**
   - Acoustic driving: 10⁻⁵ – 10⁻⁴ s (10–100 kHz)
   - Bubble life cycle: 10⁻⁴ s
   - Final collapse: 10⁻⁹ – 10⁻⁷ s
   - Optical flash: 10⁻¹⁰ – 10⁻⁸ s
   These six orders of magnitude in time set the requirement for an
   adaptive integrator (see Section 2).

3. **Energy per event.** ~10⁻² J of acoustic energy is sufficient.
   For a reactor running at, e.g., 25 kHz with ~50 % bubble engagement,
   this implies ~250 W average acoustic power per active region —
   well within tabletop transducer capability (Section 3).

4. **Optical photon budget for diagnostics.** ~10⁴–10⁷ photons per
   collapse, into 4π sr, sub-10-ns burst → easily detectable by a
   single PMT with O(10⁻⁹ s) gate (Section 7).

---

## Citation tags used in this section

- [V2000] Versluis, Schmitz, von der Heydt, Lohse, *Science* 289, 2114 (2000).
- [L2001] Lohse, Schmitz, Versluis, *Nature* 413, 477 (2001).
- [HBN2017] Hess, Brücker, Hegner, Balmert, Bleckmann, *Sci. Rep.* 7, 1 (2017) — toroidal cavitation.
- [AB1998] Au, Banner, *J. Acoust. Soc. Am.* 103, 41 (1998) — snapping shrimp source levels.
- [PKC2004] Patek, Korff, Caldwell, *Nature* 428, 819 (2004).
- [PCB2005] Patek, Caldwell, *J. Exp. Biol.* 208, 3655 (2005).
- [GGKL1997] Gompf, Günther, Nick, Pecha, Eisenmenger, *Phys. Rev. Lett.* 79, 1405 (1997).
- [BHL2002] Brenner, Hilgenfeldt, Lohse, *Rev. Mod. Phys.* 74, 425 (2002).
- [FBSP2005] Flannigan, Suslick, *Nature* 434, 52 (2005) — line emission, plasma temp.
- [SD2008] Suslick, Flannigan, *Annu. Rev. Phys. Chem.* 59, 659 (2008).

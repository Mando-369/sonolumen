# Section 3 — Acoustic field generation

> Purpose: cover how a tabletop reactor produces the time-varying pressure
> field p_a(x, t) that drives the bubble dynamics of Section 2. The
> simulator's "field" module needs (a) a model for the spatial pressure
> profile, (b) a model for the source (transducer + chamber resonance),
> and (c) a cavitation-onset criterion to decide whether and where bubbles
> are seeded.

---

## 3.1  Acoustic wave equation in a liquid

Linear, lossless wave equation in a quiescent liquid:

$$
\nabla^2 p - \frac{1}{c_L^2}\frac{\partial^2 p}{\partial t^2} = 0
$$

Plane-wave solution: `p(x,t) = P_A · cos(ω t − k·x)` with `k = ω/c_L`,
acoustic intensity `I = P_A² / (2 ρ_L c_L)` (W/m²), specific acoustic
impedance `Z = ρ_L c_L` (≈ 1.48 × 10⁶ kg m⁻² s⁻¹ for water at 20 °C —
the "rayl" unit) [K2000, BR1994].

For finite amplitude (P_A ≳ 0.1 MPa) the linear equation breaks down;
nonlinear propagation is governed by the **Westervelt equation** [W1963]:

$$
\nabla^2 p - \frac{1}{c_L^2}\frac{\partial^2 p}{\partial t^2}
+ \frac{\delta}{c_L^4}\frac{\partial^3 p}{\partial t^3}
+ \frac{\beta}{\rho_L c_L^4}\frac{\partial^2 p^2}{\partial t^2} = 0
$$

with `β = 1 + B/2A` the nonlinearity parameter (β ≈ 3.5 for water at 20 °C)
and `δ` the diffusivity of sound. Westervelt is the standard model for
focused-ultrasound (HIFU) propagation; widely implemented in **k-Wave**
[TC2010] (Section 8). For the first-pass simulator, the linear equation
suffices unless the chamber is operated in a strongly focused regime.

**Acoustic attenuation in water (linear regime):**
`α = 0.025 dB/(cm·MHz²)` [BR1994] — i.e. 0.025 f²(MHz²) dB/cm. Negligible
for tabletop chambers at f ≲ 1 MHz.

---

## 3.2  Standing waves in bounded geometries

For a closed chamber (fluid bounded by rigid walls) the eigenmodes are
solutions of the Helmholtz equation `(∇² + k²) p = 0` with appropriate
boundary conditions.

### Spherical (radial) standing wave

Inside a sphere of radius `a` with rigid walls, radial pressure is

$$
p_n(r,t) \;=\; P_n \, \frac{\sin(k_n r)}{k_n r} \cos(\omega_n t)
$$

with the eigenvalues `k_n a = n π` (rigid termination at r = a treated as
pressure node) for `n = 1, 2, …`. The fundamental angular frequency is

$$
\omega_1 \;=\; \frac{\pi c_L}{a}, \qquad f_1 = \frac{c_L}{2a}
$$

(For water in a 5 cm sphere: f₁ ≈ 14.8 kHz.) Pressure-antinode at center
`r = 0` — the natural location for a single trapped bubble (SBSL geometry).

### Cylindrical standing wave (axial)

Closed-ended cylinder of length `L`:

$$
p_n(z,t) \;=\; P_n \cos(k_n z) \cos(\omega_n t), \quad k_n L = n \pi,
\quad f_n = \frac{n c_L}{2 L}
$$

(For water in a 10 cm long cylinder: f₁ ≈ 7.4 kHz.)

### Cylindrical standing wave (radial)

In a long cylinder of radius `a` with rigid walls, the radial mode is
`J_0(k_n r)` with `J_0'(k_n a) = 0` (rigid wall = velocity node). The
lowest non-trivial root gives `k_1 a ≈ 3.832` so

$$
f_1 \;=\; \frac{c_L \cdot 3.832}{2 \pi a}
$$

(For water in a 5 cm-radius cylinder: f₁ ≈ 18.1 kHz.)

In practice the chamber Q (quality factor) is set by liquid losses and
wall losses; for a clean glass-walled water cell at 20–40 kHz, Q ≈ 200–500
[CSF2002]. The driving electronics must therefore be matched to ±0.1 % of
the chamber resonance.

---

## 3.3  Piezoelectric transducers

Standard tabletop sources for cavitation cells:

| Type                        | Frequency band   | Acoustic power | Pressure at face |
|---                          |---               |---             |---               |
| Langevin (sandwich)         | 20–100 kHz       | 50–1500 W      | up to ~1 MPa     |
| PZT disc (thickness mode)   | 100 kHz–2 MHz    | 1–100 W        | 0.1–1 MPa        |
| HIFU concave bowl           | 0.5–5 MHz        | 1–500 W (focal) | 1–100 MPa focal |
| HIFU phased array (256-el)  | 1–3 MHz          | 100–2000 W     | 50–100 MPa shocks at focus [TBM2013] |

Transducer coupling efficiency η ≈ 0.5–0.8 typically. Design data and
material parameters (density, c_L of PZT, kₚ, kₜ) are tabulated in
[CC1992, ATILA].

The pressure at a point in the chamber is the sum of the directly radiated
field and the reflections; in resonant operation the standing-wave
amplification factor over the unfocused free-field amplitude can be 5–50×
in a high-Q cell.

For clinical HIFU systems [HIFU2020]: focal pressures 30 MPa compression /
10 MPa rarefaction are routine; with shock formation, > 90 MPa positive
peaks are reported. These numbers bracket the achievable upper end for a
tabletop reactor.

---

## 3.4  Cavitation onset — Blake threshold

For a *quasi-static* tensile pressure the threshold for unstable growth of
a gas-filled nucleus of equilibrium radius R₀ is the Blake threshold
[B1949, AP1989]:

$$
P_B \;=\; p_\infty - p_v + \frac{4\sigma}{3 R_0}\sqrt{\frac{2\sigma}{3 R_0 (p_\infty - p_v + 2\sigma/R_0)}}
$$

The critical (unstable) radius at threshold is

$$
R_c \;=\; R_0 \sqrt{\frac{3 R_0 (p_\infty - p_v + 2\sigma/R_0)}{2\sigma}}
$$

For water at 20 °C with R₀ = 1 µm and §9.1 properties, a literal evaluation
of E4 gives P_B ≈ 1.40 atm (acoustic amplitude required for the
rarefaction phase to reach the threshold tensile pressure ≈ −0.40 atm).
Values in the 1.3–1.5 atm range appear in the literature depending on
which σ, p_v, and small-correction terms are used; the simulator should
use whatever its E4 implementation produces and validate that, not a
quoted number. Larger nuclei → lower threshold; nuclei R₀ ≳ 10 µm have
P_B ≈ 1 atm. Vacuum-degassed water with no nuclei can sustain tensile
stresses of order 100 MPa before homogeneous nucleation [HK1980].

For *time-varying* pressure (the realistic case) the dynamic Blake
threshold lies above the quasi-static one because viscosity and inertia
delay growth; numerical Rayleigh–Plesset integration gives the true
threshold for a given f, P_A. See Apfel & Holland 1991 [AH1991] for the
*mechanical index* MI = P⁻ / √f (MHz) used as a rule of thumb in clinical
ultrasound (MI = 0.7 conventionally taken as the cavitation onset for
diagnostic ultrasound).

---

## 3.5  Acoustic radiation force on bubbles (primary Bjerknes force)

A bubble in a standing acoustic field experiences a time-averaged force

$$
\mathbf{F}_B \;=\; -\langle V(t) \nabla p_a(\mathbf{x},t)\rangle
$$

where V(t) is the instantaneous bubble volume. For small linear
oscillations this becomes

$$
\mathbf{F}_B \;=\; -\frac{2\pi R_0^3 P_A^2}{\rho_L (\omega_0^2 - \omega^2)} \cdot \nabla \cos^2(k z)
$$

with ω₀ the linear (Minnaert) bubble resonance frequency:

$$
\boxed{\;
\omega_0 \;=\; \frac{1}{R_0}\sqrt{\frac{3 \kappa (p_\infty + 2\sigma/R_0) - 2\sigma/R_0}{\rho_L}}
\;}
$$

For air bubbles in water at 1 atm, the simple form is `f₀ R₀ ≈ 3.26 m/s`,
i.e. a 100-µm bubble resonates at ~32 kHz.

Bubbles smaller than resonance (ω < ω₀) accumulate at *pressure antinodes*
(this is how SBSL traps a bubble at the chamber center). Bubbles larger
than resonance accumulate at pressure *nodes*. The cross-over is one of
the most important pieces of physics for cavitation-cell design: the
operating frequency must be matched to the desired bubble size.

The secondary Bjerknes force (bubble–bubble) is

$$
F_{12} = -\frac{4\pi R_1^2 R_2^2 \rho_L \omega^2}{r_{12}^2}\langle \dot{R}_1 \dot{R}_2 \rangle
$$

attractive when bubbles oscillate in phase (typical at ω < ω₀,₁,₂),
repulsive otherwise [LMA1998]. This is what produces the bubble
"streamers" seen in strongly driven cavitation cells.

---

## 3.6  Cavitation thresholds in different liquids (water at 20 °C reference)

Surface tension and vapour pressure matter most:

| Liquid              | σ (N/m)  | p_v at 20 °C (kPa) | μ (mPa·s) | ρ (kg/m³) | c (m/s) |
|---                  |---       |---                 |---        |---        |---      |
| Water               | 0.0728   | 2.34               | 1.002     | 998       | 1482    |
| Glycerin            | 0.0631   | 0.00002            | 1410      | 1261      | 1923    |
| Ethanol             | 0.0223   | 5.95               | 1.20      | 789       | 1162    |
| Sulfuric acid (98%) | 0.0541   | 0.00006            | 24.0      | 1830      | 1490    |
| Silicone oil 100 cSt| 0.020    | < 0.001            | 100       | 968       | 980     |

Sources: [LK1986, BR1994, NIST]. Glycerin and silicone oil have very low
vapour pressures and so support much higher tensile stresses without
cavitating; sulfuric acid is famous for SBSL because of its high
density × sound speed product (acoustic impedance) and very low vapour
pressure, giving the brightest reported SBSL flashes [FS2005].

---

## 3.7  Power densities required

Empirical thresholds for vigorous (visible-flash) acoustic cavitation in
water at 20 °C [SD2008, KCL2014]:

| Frequency  | Threshold I (W/cm²) | Threshold P_A (MPa) |
|---         |---                  |---                  |
| 20 kHz     | 0.3 – 1             | 0.1 – 0.2           |
| 100 kHz    | 5 – 15              | 0.4 – 0.7           |
| 1 MHz      | 50 – 300            | 1.2 – 3             |
| 3 MHz (HIFU)| 1000 – 3000         | 5 – 9               |

Higher frequency requires higher pressure to nucleate bubbles, but the
collapse is correspondingly more violent because the bubbles are smaller
and the acoustic period is shorter.

For the tabletop reactor, **20–60 kHz with P_A ≈ 1.5–2 atm in water**
is a well-trodden operating point that produces SBSL or strong MBSL
[BHL2002, SD2008]. This is the recommended baseline (see Section 9).

---

## 3.8  Equations for the simulator's "field" module

For the v1 simulator, the field is parametrized at the bubble location by
a scalar driving pressure:

$$
p_a(t) \;=\; P_A \, g(t) \cos(\omega t + \phi)
$$

where `g(t)` is a slow envelope (e.g. continuous wave, tone burst,
chirp). For a 1D standing-wave geometry the bubble position `x` is a
parameter and `P_A → P_A cos(k x)`.

For v2 the field can be solved on a grid using k-Wave (Section 8) and
sampled at the bubble location.

Cavitation seeding rule (Blake-based) for the simulator:

```
if min_t [p_∞ − p_a(t)] < P_B(R₀_seed):
    spawn bubble at this location with R(0) = R₀_seed
```

This is the practical bridge between Sections 2 and 3.

---

## Citation tags used in this section

- [B1949] Blake, *Tech. Mem. 12, Acoustics Research Lab, Harvard* (1949).
- [W1963] Westervelt, *J. Acoust. Soc. Am.* 35, 535 (1963).
- [HK1980] Herbert, Caupin, *J. Phys. Cond. Mat.* 17, S3597 (2005).
- [LK1986] Lide (ed.), *CRC Handbook of Chemistry and Physics*, multiple editions.
- [AP1989] Apfel, *J. Acoust. Soc. Am.* 86, 2032 (1989).
- [AH1991] Apfel, Holland, *Ultrasound Med. Biol.* 17, 179 (1991) — mechanical index.
- [CC1992] Cady, *Piezoelectricity* (Dover 1992).
- [BR1994] Brennen, *Cavitation and Bubble Dynamics*, Oxford UP (1995).
- [LMA1998] Lauterborn, Kurz, Mettin, Ohl, *Adv. Chem. Phys.* 110, 295 (1999).
- [K2000] Kinsler et al., *Fundamentals of Acoustics*, 4th ed., Wiley (2000).
- [BHL2002] Brenner, Hilgenfeldt, Lohse, *Rev. Mod. Phys.* 74, 425 (2002).
- [CSF2002] Crum et al., review of acoustic cavitation cells.
- [FS2005] Flannigan, Suslick, *Nature* 434, 52 (2005) — sulfuric-acid SBSL.
- [SD2008] Suslick, Flannigan, *Annu. Rev. Phys. Chem.* 59, 659 (2008).
- [TC2010] Treeby, Cox, *J. Biomed. Opt.* 15, 021314 (2010) — k-Wave.
- [TBM2013] Khokhlova et al., *J. Acoust. Soc. Am.* 134, 1593 (2013) — boiling histotripsy.
- [KCL2014] Kanthale et al., *Ultrason. Sonochem.* 21, 1069 (2014).
- [HIFU2020] Izadifar, Izadifar, Chapman, Babyn, *J. Clin. Med.* 9, 460 (2020) — HIFU review.
- [NIST] NIST Webbook, https://webbook.nist.gov.

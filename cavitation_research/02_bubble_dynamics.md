# Section 2 — Bubble dynamics equations

> Purpose: provide the canonical ODEs that govern the radius–time history
> R(t) of a spherical (or near-spherical) cavitation bubble in a liquid
> driven by an acoustic field. These ODEs are the core of the simulator's
> "bubble" module. All three equations below reduce to one another in
> appropriate limits; the choice depends on how strongly the bubble's wall
> Mach number Ṙ/c approaches unity and how much radiation damping matters.

Notation used throughout this dossier:

| Symbol     | Meaning                                                    | Units (SI)   |
|---         |---                                                         |---           |
| R          | bubble radius                                              | m            |
| Ṙ, R̈      | dR/dt, d²R/dt²                                              | m/s, m/s²    |
| ρ_L        | liquid density (≈ 998 kg/m³ for water at 20 °C)            | kg/m³        |
| c, c_L     | speed of sound in liquid (≈ 1482 m/s in water at 20 °C)    | m/s          |
| μ_L        | liquid dynamic viscosity (≈ 1.002 × 10⁻³ Pa·s, water 20 °C) | Pa·s         |
| σ          | liquid–gas surface tension (≈ 0.0728 N/m, water 20 °C)     | N/m          |
| p_∞        | ambient (hydrostatic) pressure far from bubble             | Pa           |
| p_a(t)     | acoustic driving pressure (added to p_∞)                   | Pa           |
| p_v        | saturation vapour pressure of liquid (≈ 2.34 kPa, water 20 °C) | Pa       |
| p_g        | gas partial pressure inside bubble                         | Pa           |
| p_L(R)     | liquid pressure just outside the bubble wall               | Pa           |
| R₀         | equilibrium bubble radius (no driving)                     | m            |
| κ (γ)      | polytropic exponent of gas inside bubble (1 ≤ κ ≤ γ_gas)   | —            |
| ω          | angular driving frequency = 2π f                           | rad/s        |
| P_A        | acoustic pressure amplitude                                | Pa           |

---

## 2.1  Rayleigh–Plesset equation (RPE)

Standard incompressible-liquid form, attributed to Plesset 1949 (see [P1949,
P1977]) building on Rayleigh 1917 [R1917]:

$$
\rho_L \left( R\ddot{R} + \tfrac{3}{2}\dot{R}^2 \right)
\;=\; p_L(R,t) - p_\infty(t)
$$

with the bubble-wall boundary condition (Newton's 3rd law on the gas/liquid
interface):

$$
p_L(R,t) \;=\; p_g(R,t) + p_v - \frac{2\sigma}{R} - \frac{4\mu_L \dot{R}}{R}
$$

and `p_∞(t) = p_∞ + p_a(t)` (additive sign convention: positive `p_a`
adds pressure to the far field; rarefaction phases of the drive
correspond to `p_a < 0`). Putting these together gives the most commonly
used "engineering" form:

$$
\boxed{\;
\rho_L \left( R\ddot{R} + \tfrac{3}{2}\dot{R}^2 \right)
\;=\; p_g(R,t) + p_v - \frac{2\sigma}{R} - \frac{4\mu_L \dot{R}}{R} - p_\infty - p_a(t)
\;}
$$

> **Sign convention note.** The literature uses both `+ p_a(t)`
> (rarefaction convention, where `p_a > 0` denotes a tensile drive) and
> `− p_a(t)` (additive convention, where `p_a > 0` denotes a
> compressive drive). The dossier and simulator standardise on the
> *additive* convention so that the c → ∞ limit of E8 (Keller–Miksis)
> reduces cleanly to E6 with no sign flip on `p_a`. If you adopt the
> rarefaction convention instead, swap the sign of `p_a` *consistently*
> in E6, E8, E9, and the drive module — never partially.

For an isothermal/polytropic gas:

$$
p_g(R,t) \;=\; p_{g,0} \left(\frac{R_0}{R}\right)^{3\kappa}, \quad
p_{g,0} = p_\infty + \frac{2\sigma}{R_0} - p_v
$$

**Van der Waals hard-core correction (recommended for SBSL).** The
ideal-gas form above breaks down at the densities reached in violent
collapses (R/R₀ ≲ 0.1). The standard SBSL practice [LBP1993, BHL2002]
is to replace it with a hard-core polytropic form that prevents
unphysical compression below the molecular packing limit:

$$
p_g(R,t) \;=\; \left(p_\infty + \frac{2\sigma}{R_0} - p_v\right)
\left(\frac{R_0^3 - h^3}{R^3 - h^3}\right)^{\kappa}
$$

with `h` the hard-core (excluded-volume) radius. For monatomic gases
the standard values are `h = R_0 / 8.54` for argon, `R_0 / 8.86` for
xenon, `R_0 / 8.5` (approx.) for helium [LBP1993]. This single change
prevents R from going below ~h during the collapse and substantially
improves agreement with measured R(t) traces.

Choices of κ:
- κ = 1 (isothermal) — slow, low-amplitude oscillations, e.g. R₀ ~ 100 µm at <1 kHz.
- κ = γ_gas ≈ 1.4 (adiabatic) — strong, fast collapses (the relevant limit
  for sonoluminescence and biomimetic regimes).
- "Effective polytropic" κ between 1 and γ — required to match mid-range
  data; see Prosperetti 1991 [P1991] for a systematic derivation.

**Pure Rayleigh collapse** (no gas, no surface tension, no viscosity, p_a=0):

$$
t_c \;=\; 0.915\, R_{\max}\sqrt{\rho_L / \Delta p}
\quad\text{with } \Delta p = p_\infty
$$

For R_max = 1 mm, Δp = 1 atm, t_c ≈ 90 µs. This is the "Rayleigh collapse
time" benchmark; the simulator should reproduce it in the corresponding
limit (validation test in Section 11).

---

## 2.2  Keller–Miksis equation (KME)

Compressible-liquid extension valid up to wall Mach number Ṙ/c ~ 0.3
[KM1980, BHL2002]:

$$
\boxed{\;
\left(1 - \frac{\dot R}{c}\right) R \ddot R
+ \frac{3}{2}\dot R^2 \left(1 - \frac{\dot R}{3c}\right)
= \left(1 + \frac{\dot R}{c}\right)\frac{p_L - p_\infty - p_a(t + R/c)}{\rho_L}
+ \frac{R}{\rho_L c}\frac{d}{dt}\!\bigl[p_L - p_\infty - p_a(t + R/c)\bigr]
\;}
$$

with `p_L(R,t)` given by the same wall boundary condition as in §2.1.
The retarded time `t + R/c` in the driving term encodes acoustic radiation
into the far field — this is the dominant energy-loss channel during the
final collapse and rebound.

In the limit c → ∞ (incompressible liquid) the KME reduces to the RPE.

This is the recommended baseline equation for any simulator that aims at
sonoluminescence-like collapses, because the radiation-damping term is
essential for stable computation through and past the rebound.

---

## 2.3  Gilmore equation (GE)

Higher-order compressible model, derived from the Kirkwood–Bethe hypothesis
[G1952]:

$$
\boxed{\;
\left(1-\frac{\dot R}{C}\right) R \ddot R
+ \frac{3}{2}\dot R^2 \left(1-\frac{\dot R}{3C}\right)
= \left(1+\frac{\dot R}{C}\right) H
+ \frac{R}{C}\left(1-\frac{\dot R}{C}\right)\dot H
\;}
$$

where:

- `H` is the *enthalpy difference* between the liquid at the wall pressure
  p_L(R,t) and at the far-field pressure p_∞(t):
  $$
  H \;=\; \int_{p_\infty(t)}^{p_L(R,t)} \frac{dp}{\rho_L(p)}
  $$
- `C` is the local speed of sound in the liquid at the wall:
  $$
  C(p_L) \;=\; \sqrt{c_0^2 + (n-1)H}
  $$
  using a Tait equation of state for water:
  $$
  \frac{p + B}{p_\infty + B} \;=\; \left(\frac{\rho_L}{\rho_{L,0}}\right)^n
  $$
  with B ≈ 3.05 × 10⁸ Pa and n ≈ 7.15 for water (Tait fit, [BR1994]).
  c₀ is the unperturbed sound speed.

GE is valid up to Ṙ/C of order unity and is preferred over KME for the
*final* collapse phase of strongly driven bubbles where the wall Mach
number transiently exceeds ~0.3 (typical of sonoluminescence collapses).
For most of the cycle, GE and KME agree to within a few percent
[BHL2002, DBA2020].

The Gilmore–NASG variant [DBA2020] replaces the Tait EOS with the
Noble–Abel–Stiffened-Gas EOS to fix the temperature inconsistency Tait
exhibits at extreme densities; recommended if the simulator computes
gas-phase thermodynamics consistently with liquid thermodynamics.

---

## 2.4  Thermal effects and mass transfer

The above three equations all close the gas pressure with a single
polytropic relation `p_g = p_{g,0}(R₀/R)^{3κ}`. Real cavitation collapses
deviate from this in two ways:

### 2.4.1  Heat conduction in the gas

A rigorous treatment solves the energy equation inside the bubble. A widely
used reduced model is the *spatially-uniform-pressure* assumption with a
single thermal-diffusion length, due to Prosperetti [P1991]; in that
framework the gas pressure obeys

$$
\dot p_g \;=\; -\frac{3}{R}\bigl[\gamma_g p_g \dot R - (\gamma_g - 1) k_g \,\partial T/\partial r |_R \bigr]
$$

with `k_g` the gas thermal conductivity. Numerical implementation of the
full PDE inside the bubble is given in [SHL1995, KP1996]; see also the
"Toegel reduced model" [TGGL2000] which collapses the inside-bubble PDE to
a single ODE for the gas temperature.

### 2.4.2  Water-vapour evaporation/condensation

For violent collapses the bubble can be > 90 % water vapour. Storey &
Szeri [SS2000] showed that water-vapour mass transfer caps the peak
temperature reached at collapse — vapour molecules undergo dissociation
(an endothermic sink) at ~5 000 K and limit further heating. A simulator
that ignores vapour will *overestimate* peak T by a factor of 2–5 at large
P_A.

A practical first-cut model is to add a vapour-diffusion equation with
diffusion length `L_d ≈ √(D_v R / |Ṙ|)` where D_v is the binary diffusion
coefficient of water vapour in the host gas (D_v ≈ 2.4 × 10⁻⁵ m²/s for
H₂O in air at 300 K).

For the first-pass simulator the recommendation is: **adopt KME with a
polytropic gas equation as the baseline; add a Toegel-style reduced
thermal model and a Storey–Szeri vapour cap as optional refinements.**

---

## 2.5  Initial and boundary conditions

Standard initial conditions for an SBSL-style simulation:

- R(0) = R₀ (equilibrium radius, set by gas content via Henry's law)
- Ṙ(0) = 0
- p_g(0) = p_∞ + 2σ/R₀ − p_v
- T_g(0) = T_∞ (typically 293–300 K)

For a "shock-injected" cavitation event (closer to the pistol-shrimp case),
the initial condition is instead a high-pressure pulse driving the liquid:

- Ṙ(0) determined by jet kinetic energy delivered to the bubble
- p_g(0) = p_v (vapour bubble, formed by tensile rupture)
- One must specify the bubble's *origin time* relative to the acoustic
  forcing — i.e. the nucleation time inside the cycle.

---

## 2.6  Numerical integration

These ODEs are stiff: the time scale during the rebound shrinks by 5–6
orders of magnitude relative to the driving period. Recommended:

- Adaptive Runge–Kutta with embedded error control (e.g. SciPy's
  `LSODA` for stiff/non-stiff switching, `Radau` for fully implicit
  stiff systems, or `BDF` — also implicit, slightly faster than Radau
  on smoother problems); avoid fixed-step RK4.
- State variables: y = (R, Ṙ, p_g, T_g) (latter two only if thermal
  module is on). The KME/GE expressions for R̈ are explicit in Ṙ and
  R, so the system is a first-order ODE in y.
- Use log-spacing in time for output; the rebound emits photons over
  ~0.1 ns while the cycle is 25 µs, so linear time-stepping wastes
  output points.
- Recommended tolerances: rtol = 1e-8, atol = 1e-12. Tighter is needed
  for Mach-1 collapses; looser for gentle (linear) oscillations.
- The simulator should support a **maximum-radius detection event** (zero
  crossing of Ṙ) and a **collapse-event detection** (R̈ > 0 after R minimum)
  so that diagnostic outputs are emitted at physically meaningful instants.

---

## 2.7  Validated parameter ranges (water, 20 °C, 1 atm ambient)

| Driving regime              | R₀ (µm) | P_A (atm) | f (kHz) | Valid model     |
|---                          |---      |---        |---      |---              |
| Linear oscillation          | 1–500   | < 0.1     | any     | RPE, linear     |
| Stable SBSL                 | 4–6     | 1.2–1.5   | 20–40   | KME             |
| Violent SBSL / shape-unstable | 4–6   | > 1.5     | 20–40   | GE + thermal    |
| Pistol-shrimp-like (jet-induced) | ~10³ at peak | n/a (impulsive) | n/a | KME or GE, with shock IC |
| Multi-bubble cloud          | 1–100 (broadband) | 1–10 | 20–500 | KME per bubble + interaction term [MK1996] |

For multi-bubble interactions (cloud cavitation) the single-bubble RP/KM/G
equations gain a coupling term involving the pressure radiated by all
other bubbles. The standard derivation is in Mettin et al. 1996 [MK1996].

---

## 2.8  Recommended choices for the tabletop reactor simulator

1. **Single-bubble baseline:** Keller–Miksis with polytropic gas. ~1 µs
   driving period resolved, sub-ps integrator step at peak collapse.
2. **Strong-collapse mode:** Switch to Gilmore once Ṙ/c > 0.2.
3. **Thermal mode:** Toegel reduced model for T_g(t).
4. **Vapour cap:** Storey–Szeri vapour-mole-fraction limit on peak T.
5. **Bubble cloud (extension):** ensemble of KME ODEs with pairwise
   acoustic coupling; out-of-scope for v1, planned for v2.

These choices are referenced again in Sections 9 (defaults) and 11
(simulator spec).

---

## Citation tags used in this section

- [R1917] Rayleigh, *Phil. Mag.* 34, 94 (1917).
- [P1949] Plesset, *J. Appl. Mech.* 16, 277 (1949).
- [P1977] Plesset, Prosperetti, *Annu. Rev. Fluid Mech.* 9, 145 (1977).
- [P1991] Prosperetti, *J. Fluid Mech.* 222, 587 (1991).
- [KM1980] Keller, Miksis, *J. Acoust. Soc. Am.* 68, 628 (1980).
- [G1952] Gilmore, Cal Tech Hydrodynamics Lab Rep. 26-4 (1952).
- [BR1994] Brennen, *Cavitation and Bubble Dynamics*, Oxford UP (1995).
- [BHL2002] Brenner, Hilgenfeldt, Lohse, *Rev. Mod. Phys.* 74, 425 (2002).
- [SHL1995] Hilgenfeldt, Grossmann, Lohse, *Phys. Fluids* 11, 1318 (1999).
- [KP1996] Kamath, Prosperetti, *J. Acoust. Soc. Am.* 94, 248 (1993).
- [TGGL2000] Toegel, Gompf, Pecha, Lohse, *Phys. Rev. Lett.* 85, 3165 (2000).
- [SS2000] Storey, Szeri, *Proc. R. Soc. A* 456, 1685 (2000).
- [MK1996] Mettin, Akhatov, Parlitz, Ohl, Lauterborn, *Phys. Rev. E* 56, 2924 (1997).
- [DBA2020] Denner, Schenke, *Ultrason. Sonochem.* 70, 105307 (2020) — Gilmore–NASG.
- [LBP1993] Löfstedt, Barber, Putterman, *Phys. Fluids A* 5, 2911 (1993) — VdW hard-core gas EOS for SBSL.

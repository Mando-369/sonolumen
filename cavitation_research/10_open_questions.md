# Section 10 — Open questions and uncertainties

> Purpose: catalogue the places where the literature is still debated or
> the data are sparse. The simulator should treat the corresponding model
> components as *parameterised* (with documented uncertainty ranges)
> rather than baked-in deterministic predictions.

Each item below names the question, summarises the disagreement, points to
the relevant primary sources, and gives concrete advice for the simulator.

---

## 10.1  Peak temperature inside an SBSL bubble

**Disagreement.** Different methods give different answers.
- Spectral fits to optically thick blackbody: T = 1.5–4 × 10⁴ K
  [BHL2002, HBL1999].
- Line-emission-based plasma diagnostics (concentrated H₂SO₄ + Ar):
  T = 1.5 × 10⁴ K [FBSP2005].
- Ab initio molecular-dynamics simulations: T = 1.5–3 × 10⁴ K, with
  significant model dependence on the gas EOS [SBM2016].
- Hydrocode + plasma EOS: T can exceed 10⁵ K under some parameter
  choices, but these have been criticised as artefacts of the cold-EOS
  assumption [BHL2002].

**Why it matters.** The peak T sets the spectrum, the ionization
fraction, and any putative chemistry/sonochemistry yields. A factor of
3 uncertainty propagates to a factor of ~80 in radiated visible photon
count (Stefan–Boltzmann ∝ T⁴) and a factor of ~10 in ionization (Saha).

**Simulator advice.** Expose `T_peak` as a *diagnosed* output, not a
fixed input. Run with multiple EOS / chemistry choices and compute the
spread; report a band rather than a point estimate.

---

## 10.2  Pistol-shrimp bubble plasma temperature

**Disagreement.** Lohse, Schmitz, Versluis [L2001] place a lower bound
of 5 000 K, but acknowledge the actual interior could be anywhere from
5 000 K to ~20 000 K. No spectroscopic measurement has been reported
since.

**Why it matters.** This is the central biological data point that
motivates the whole project. If the actual T is 5 000 K the reactor
target is "modest plasma"; if it is 20 000 K the target is "real
plasma".

**Simulator advice.** When running the §9.8 pistol-shrimp benchmark,
report T_peak across the full plausible range and flag this case as
"weakly constrained by experiment".

---

## 10.3  Gas content of the bubble

**Disagreement.** In SBSL the steady-state bubble is widely cited as
"~99 % argon" through rectified diffusion, but the time required to
reach this asymptote and the residual N₂/O₂ chemistry are unsettled
[BHL2002 Sec. III; AKD2002]. Pistol-shrimp bubbles are *transient*
(no rectified diffusion has time to operate) and start with whatever
composition the seawater provides — N₂/O₂/Ar in air-equilibrium.

**Simulator advice.** Treat the gas composition as a free parameter,
not a derived one. Provide a "rectified diffusion" iterator for SBSL
mode and a "freeze-at-nucleation" mode for impulsive events.

---

## 10.4  Validity of Saha ionization at warm-dense-matter densities

**Disagreement.** Continuum-lowering corrections (Stewart–Pyatt,
Ecker-Kröll, Inglis–Teller) give different ionization fractions at
the same (T, n) [SP1966, BAILEY2015]. Discrepancies up to factor ~3 in
n_e at peak.

**Simulator advice.** Implement *at least two* models (ideal Saha and
Stewart–Pyatt) and expose the choice as a parameter; document the
spread.

---

## 10.5  Bubble shape stability at collapse

**Disagreement.** Idealised models assume spherical symmetry. Real
collapses develop Rayleigh–Taylor and parametric (RP-instability)
modes [BHL2002 Sec. V]. For "violent" collapses (P_A ≳ 1.5 atm in
water at 25 kHz) the bubble can fragment, suppressing flash brightness.
For *aspherical* impulsive cases (pistol shrimp), the initial bubble is
*toroidal* [HBN2017] — never spherical.

**Why it matters.** Asymmetric collapses radiate less coherently,
fragment, and sometimes produce stronger jets/shocks. Spherical
simulators systematically *over-estimate* peak T for aspherical events.

**Simulator advice.** v1 stays spherical, but emit a *shape stability
index* (the parametric-stability and RT thresholds from [BHL2002]) so
the user knows when the spherical assumption breaks.

---

## 10.6  Margulis "electrical" theory

**Disagreement.** Margulis claims [M2000] that bubble fragmentation
produces measurable electrical transients (tens of mV, 100 ns–µs) on
nearby electrodes, distinct from the hot-spot mechanism. The
mainstream community treats these signals as either electronics
artefacts or secondary effects of charged-bubble migration. The
disagreement extends to whether sonochemistry is driven primarily by
heat or by transient electric fields.

**Simulator advice.** Implement Margulis-style transients as an
*optional* parametric model with documented "weak literature support"
flags. Do not include in the default output.

---

## 10.7  Cavitation fusion / sonofusion claims

**Disagreement.** Taleyarkhan et al. [T2002] reported D-D fusion in
deuterated acetone driven by neutron-seeded cavitation; subsequent
attempts to replicate were largely unsuccessful [N2009] and the
original results were retracted/contested. Mainstream consensus: no
robust evidence of cavitation-driven fusion at any tabletop
parameter set.

**Simulator advice.** Do not include any fusion-yield prediction in
default outputs. If a user requests it, return clearly-labelled output
based on Saha/Maxwellian-tail with explicit warnings about the
literature controversy.

---

## 10.8  Numerical artefacts in collapse modeling

**Disagreement.** Even within a fixed equation set (e.g. KME), different
integrators, tolerances, and EOS choices produce different R_min,
T_peak, and rebound dynamics. [BHL2002] discusses this; [DBA2020] argues
that NASG fixes some of the temperature anomalies introduced by Tait.

**Simulator advice.** Always run a convergence test (rtol, atol, time
step). Output the convergence diagnostic with each result.

---

## 10.9  Toroidal vs. spherical biological cavitation

**Disagreement.** Versluis et al. [V2000] modelled the snapping-shrimp
bubble as effectively spherical for R(t); Hess et al. [HBN2017] showed
the bubble is initially a torus that collapses to multiple sites. Both
models reproduce the *acoustic* signature reasonably; the *plasma*
implications (multi-site collapse, weaker peak conditions) of the
toroidal picture have not been fully worked out.

**Simulator advice.** Document the spherical assumption clearly. For
biomimetic-mode runs, allow the user to specify a "toroidal correction
factor" (effective R_max scaling) and propagate the uncertainty to
outputs.

---

## 10.10  Bubble–bubble interaction at MBSL densities

**Disagreement.** Mean-field models (Mettin et al. [MK1996]) approximate
the cloud average; full pair-coupled or microbubble-cloud DNS shows
that bubble-bubble shielding can suppress the peak conditions of
individual bubbles relative to the SBSL ideal [LMA1998]. There is no
universally agreed-on closure model.

**Simulator advice.** v1 does single-bubble. v2 should expose a
"crowding factor" parameter f_c such that effective P_A is multiplied
by (1 − f_c · n_b · V_b) with n_b the local bubble density.

---

## 10.11  Liquid EOS at extreme compressions

**Disagreement.** The Tait equation, used in classical Gilmore-derived
codes, becomes inaccurate for water above ~10 GPa. NASG and Mie–
Grüneisen-type equations have been proposed [DBA2020]. The choice
affects the wall-pressure history during the rebound phase.

**Simulator advice.** Allow EOS to be selected from `{Tait, NASG,
Mie–Grueneisen}`; document the choice in output metadata.

---

## 10.12  Quantitative photon yield for shrimpoluminescence

**Disagreement.** [L2001] reports ~5 × 10⁴ photons but the geometric
collection efficiency was estimated, not directly calibrated.
Replicated photon-count measurements have not been published.

**Simulator advice.** When comparing the simulator to biological data,
treat the quoted photon yield as known to ~factor of 3.

---

## 10.13  Pulse-width measurements at extreme conditions

**Disagreement.** SBSL pulses are 60–250 ps in water with air [GGKL1997];
shorter (~30 ps) and longer (~ns) values have been reported in different
liquids and gases [BHL2002, FBSP2005]. The mechanism for the variation
is debated.

**Simulator advice.** Output pulse FWHM as a diagnostic and document the
expected band.

---

## 10.14  Patch log — dossier inconsistencies surfaced during implementation

The following items were caught while building cavplasma v1 against this
dossier and have been patched in place. Recorded here so future readers
know what changed and why.

- **Blake threshold value.** §3.4, §8.4, §11.5 originally quoted
  P_B ≈ 1.32 atm for R₀ = 1 µm in water. A literal evaluation of E4
  with §9.1 properties gives 1.40 atm. Patched: dossier now uses 1.40
  atm and notes that 1.32 atm in some references reflects different
  σ/p_v assumptions or is conflated with the canonical SBSL drive
  amplitude.
- **RPE/KME sign convention.** E6 originally used the rarefaction
  convention (+p_a), E8 the additive convention (−p_a). Patched:
  both standardised on the additive convention. Sign-convention note
  added to §2.1 and equations.md.
- **Photon yield convention.** §9.9's [10⁵, 10⁷] band was the SBSL
  literature's *detected* count; cavplasma reports 4π emitted photons.
  Patched: §9.9 now distinguishes the two and the §11.5 test uses a
  wider [10³, 10¹⁰] band on emitted photons.
- **Vapour-cap species scope.** §4.3's table covered N₂/O₂/H₂O
  dissociation, which a literal implementation of the Storey–Szeri
  cap would treat uniformly. Storey–Szeri is for H₂O only. Patched:
  §4.1.3 scope note added; cap is H₂O-fraction-only by default.

## Summary table

| # | Topic                                | Status                       | Simulator handling     |
|---|---                                   |---                           |---                     |
| 1 | SBSL T_peak                          | Factor-of-3 uncertainty      | Multi-model band       |
| 2 | Shrimpoluminescence T                | Lower bound only             | Flag uncertainty       |
| 3 | Gas content                          | Mode-dependent               | Free parameter         |
| 4 | Saha vs WDM ionization               | Multiple competing models    | Selectable model       |
| 5 | Shape stability                      | Spherical idealisation       | Stability index output |
| 6 | Margulis electrical theory           | Contested                    | Optional, flagged      |
| 7 | Sonofusion                           | Not reproduced               | Disabled by default    |
| 8 | Numerical convergence                | Real and significant         | Auto convergence test  |
| 9 | Toroidal cavitation                  | Spherical may overestimate   | Correction factor      |
| 10 | MBSL bubble–bubble                  | No closure consensus         | v2 only                |
| 11 | Liquid EOS                          | Tait inaccurate at high p    | Selectable             |
| 12 | Pistol-shrimp photon count          | ±factor 3                    | Document               |
| 13 | Flash duration in non-air systems   | Mechanism unclear           | Output as diagnostic   |

---

## Citation tags used in this section

- [BHL2002] Brenner, Hilgenfeldt, Lohse, *Rev. Mod. Phys.* 74, 425 (2002).
- [HBL1999] Hilgenfeldt, Grossmann, Lohse, *Phys. Fluids* 11, 1318 (1999).
- [FBSP2005] Flannigan, Suslick, *Nature* 434, 52 (2005).
- [SBM2016] Bataller, Putterman, *Sci. Rep.* 6, 20623 (2016).
- [SP1966] Stewart, Pyatt, *Astrophys. J.* 144, 1203 (1966).
- [BAILEY2015] Bailey et al., *Nature* 517, 56 (2015) — continuum-lowering controversy.
- [AKD2002] Akhatov et al., *Phys. Fluids* 14, 3727 (2002).
- [HBN2017] Hess et al., *Sci. Rep.* 7, 1 (2017).
- [HF2002] Margulis, *High Energy Chem.* 38, 135 (2004).
- [M2000] Margulis, *High Energy Chem.* 38, 135 (2004).
- [T2002] Taleyarkhan et al., *Science* 295, 1868 (2002) — sonofusion claim.
- [N2009] Naranjo, *Phys. Rev. Lett.* 96, 134301 (2006) — replication failure.
- [DBA2020] Denner, Schenke, *Ultrason. Sonochem.* 70, 105307 (2020).
- [LMA1998] Lauterborn et al., *Adv. Chem. Phys.* 110, 295 (1999).
- [MK1996] Mettin et al., *Phys. Rev. E* 56, 2924 (1997).
- [V2000] Versluis et al., *Science* 289, 2114 (2000).
- [L2001] Lohse et al., *Nature* 413, 477 (2001).
- [GGKL1997] Gompf et al., *Phys. Rev. Lett.* 79, 1405 (1997).

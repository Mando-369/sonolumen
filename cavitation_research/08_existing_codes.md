# Section 8 — Existing simulations and codes

> Purpose: enumerate the open-source software the simulator can reuse,
> and the published methodologies / benchmarks against which the simulator's
> outputs should be validated.

---

## 8.1  Open-source bubble-dynamics codes

### RP_Bubble (Python)
- Repository: https://github.com/stromatolith/RP_Bubble
- Language: Python (NumPy + SciPy)
- Scope: Rayleigh–Plesset only, with optional viscous and radiation
  damping terms; no gas thermodynamics, no plasma module.
- Strengths: minimal, readable, ~200 lines. Useful as a starting point
  and a sanity-check reference.
- Limitations: no Keller–Miksis or Gilmore; no thermal model; no plasma.

### OptimUS (Python)
- Repository: https://github.com/optimuslib/optimus
- Language: Python (BEM++ wrapper)
- Scope: 3-D acoustic wave propagation (boundary-element method),
  including focused ultrasound. Not bubble-resolved.
- Use: for the *acoustic field* module if the chamber has complex
  geometry; pairs naturally with RP/KME bubble integration.

### Bubble-collapse Caltech (Colonius group)
- Code: `BubbleCollapse` (Fortran/C++; not pip-installable).
- Reference: Johnsen, Colonius *et al.* (multiple JFM/JCP papers).
- Scope: full Navier–Stokes for compressible liquid + bubble interaction,
  shock formation. Beyond v1 scope but useful for spot-checking.

### Sonoluminescence MD code (Ruuth, Putterman)
- arXiv: physics/0104062 (Lehmann, Ruuth, Putterman 2001).
- Scope: molecular-dynamics inside a collapsing bubble. Heavy.

### Recommendation for v1 simulator
**Re-implement Keller–Miksis + Gilmore from scratch in Python,
referencing RP_Bubble's structure for I/O and validation.** None of the
existing tools combine bubble + plasma + EM out of the box.

---

## 8.2  Acoustic-field codes

### k-Wave / k-wave-python
- Website: http://www.k-wave.org/ ; PyPI: `k-wave-python`
- Method: k-space pseudospectral solver for the generalised Westervelt
  equation; supports nonlinear propagation and absorbing media.
- Scope: heterogeneous 3-D ultrasound fields including HIFU; widely
  validated.
- Reference: Treeby, Cox, *J. Biomed. Opt.* 15, 021314 (2010).
- **Recommended** for the simulator's optional 3-D field module: drive
  it externally, sample p(x_b, t) at the bubble location, feed into
  KME/Gilmore.

### mSOUND
- Open-source MATLAB/Python implementation of Westervelt-type
  propagation in heterogeneous media. Reference: Gu, Jing, *J. Acoust.
  Soc. Am.* 144 (2018).
- Lighter weight than k-Wave; useful for cylindrical/spherical resonator
  geometries where the eigenmode approach (Section 3) is cleaner than a
  full-grid solver.

### COMSOL Multiphysics — Pressure Acoustics
- Commercial. Often used in published cavitation-cell modelling for
  finding modes and Q. Not open source; mention here for completeness
  only.

---

## 8.3  Plasma-physics codes

### PlasmaPy
- Repository: https://github.com/PlasmaPy/PlasmaPy
- PyPI: `plasmapy`
- Capabilities relevant to this project:
  - `plasmapy.formulary`: plasma frequency, Debye length, coupling
    parameter, Coulomb logarithm, ionization (Saha), thermal speeds.
  - `plasmapy.formulary.thermal_bremsstrahlung`: spectral emissivity
    for Maxwellian plasmas — this is exactly the §5.1 formula
    pre-implemented.
  - Distribution functions: Maxwellian, Kappa.
  - Particle data and ionization energies (NIST-backed).
- **Strongly recommended** as the dependency for plasma diagnostics in
  the simulator's "plasma" module.
- Limitations: PlasmaPy is fluid/diagnostic-formulary-oriented; it does
  not solve hydrodynamics or EOS.

### Cantera (chemistry)
- Repository: https://github.com/Cantera/cantera
- Capability: thermochemistry of gas mixtures (including H₂/O₂/H₂O/Ar
  systems). Useful for the §4.3 chemistry/dissociation effects.
- Recommended *optional* dependency.

### NIST ASD / atomic line databases
- https://physics.nist.gov/PhysRefData/ASD
- For line-emission predictions (Section 5). Not Python-native; can be
  scraped or accessed via `astroquery.nist`.

---

## 8.4  Published validation benchmarks

For the simulator's test suite (Section 11):

1. **Rayleigh collapse time.** Pure vapour bubble collapsing in
   incompressible water, Δp = 1 atm, R_max = 1 mm, σ = 0, μ = 0:
   t_c = 0.915 R_max √(ρ_L/Δp) ≈ 91 µs. (Section 2.1 derivation).

2. **Stable SBSL bubble** (water, air, 26.5 kHz, 1.32 atm, R₀ = 4.5 µm):
   R_max ≈ 35 µm, R_min ≈ 0.5 µm, period 37.7 µs. Reference: Hilgenfeldt,
   Lohse, Brenner [HBL1999, BHL2002]. Used as Figure 1 standard SBSL
   case in the literature.

3. **Pistol-shrimp event.** R_max ≈ 3.5 mm, lifetime ≈ 300 µs at 1 atm
   ambient, no acoustic drive — cavitation produced by impulsive jet.
   Reference: Versluis et al. 2000 [V2000]. Used as the upper-radius,
   lower-frequency limiting case.

4. **Bremsstrahlung emissivity.** PlasmaPy's
   `thermal_bremsstrahlung_emissivity()` for T = 2 × 10⁴ K, n_e = n_i =
   10²⁶ m⁻³. The simulator's independent implementation should match
   to within 5 %.

5. **Blackbody integrated power.** σ_SB T⁴ = 9.07 × 10⁹ W/m² at
   T = 2 × 10⁴ K. A 1-µm-radius source for 100 ps emits 1.14 × 10⁻⁹ J
   ≈ 2 × 10⁹ visible photons; the simulator's photon-count output
   should reproduce this when set to optically thick.

6. **Minnaert frequency.** ω₀ R₀ = √(3κ p_∞ / ρ_L) ≈ 20.46 m/s for
   air bubbles in water (κ = 1.4, p_∞ = 1 atm) — standard textbook value.

7. **Blake threshold.** For R₀ = 1 µm with §9.1 water properties, a
   literal evaluation of E4 gives P_B ≈ 1.40 atm (acoustic amplitude).
   Use this as the test target rather than the loosely quoted "1.32
   atm" found in some references — simulator's E4 output should match
   E4 algebra to numerical precision. Section 3.4 explains the
   convention.

---

## 8.5  Available datasets

- **Putterman/Stony Brook SBSL data.** R(t) traces, optical-flash
  spectra, and acoustic-emission waveforms reported in [BHL2002] are
  reproduced as figures; quantitative tabulated data is available on
  request from the original authors.
- **Suslick group MBSL spectra.** Aqueous H₂SO₄ + Xe spectra in
  [FBSP2005, FS2005]; supplementary materials contain digital data.
- **k-Wave benchmark suite.** `kwave.examples` includes water-tank
  HIFU geometries used as cross-check for any implementation of
  Westervelt-type equations.

These can be used as cross-validation sets for the simulator's
forward predictions: same {f, P_A, R₀, gas, liquid} → reproduce R(t),
T_peak, photon count.

---

## 8.6  Suggested Python dependency set for v1

| Package        | Use                                          |
|---             |---                                           |
| `numpy`        | arrays, linear algebra                       |
| `scipy`        | ODE integration (LSODA/Radau), interpolation, FFT |
| `matplotlib`   | plotting                                     |
| `astropy.units`| unit handling (PlasmaPy uses this; reuse for consistency) |
| `plasmapy`     | plasma diagnostics, bremsstrahlung formulary |
| `cantera`     *(opt.)* | gas-phase chemistry equilibrium       |
| `k-wave-python` *(opt.)* | 3-D acoustic field             |
| `numba`       *(opt.)* | JIT for hot inner ODE loops           |
| `pandas`      *(opt.)* | parameter sweeps and result tables   |
| `pytest`       | the validation tests above              |

Avoid PyTorch unless adopting differentiable-physics or surrogate-model
workflows in v2. NumPy + SciPy + PlasmaPy is sufficient for the
deterministic single-bubble simulator.

---

## Citation tags used in this section

- [V2000] Versluis et al., *Science* 289, 2114 (2000).
- [HBL1999] Hilgenfeldt, Grossmann, Lohse, *Phys. Fluids* 11, 1318 (1999).
- [BHL2002] Brenner, Hilgenfeldt, Lohse, *Rev. Mod. Phys.* 74, 425 (2002).
- [FBSP2005] Flannigan, Suslick, *Nature* 434, 52 (2005).
- [FS2005] Flannigan, Suslick, *Phys. Rev. Lett.* 95, 044301 (2005).
- [TC2010] Treeby, Cox, *J. Biomed. Opt.* 15, 021314 (2010) — k-Wave.
- [PlasmaPy] PlasmaPy Community, https://docs.plasmapy.org.
- [Stromatolith2018] Stokmaier, RP_Bubble GitHub repo.

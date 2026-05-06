# Section 4 — Plasma conditions during collapse

> Purpose: provide the equations and reference data the simulator needs to
> compute, from a given collapse trajectory R(t), the gas-interior plasma
> state — temperature T, number density n, electron density n_e, plasma
> frequency ω_p, Debye length λ_D, and the optical/UV emission spectrum.
> The simulator's "plasma" module is downstream of the "bubble" module
> (Section 2) and upstream of the "EM" module (Section 5).

---

## 4.1  Gas state during compression

### 4.1.1  Adiabatic compression baseline

For a pure noble gas with constant γ, frozen in mass (no vapour, no
chemistry):

$$
T(R) = T_0 \left(\frac{R_0}{R}\right)^{3(\gamma - 1)}, \quad
p_g(R) = p_{g,0}\left(\frac{R_0}{R}\right)^{3 \gamma}
$$

For γ = 5/3 (monatomic, e.g. argon), a compression ratio R_max/R_min = 10
gives T_min/T_0 ≈ 100 and p_min/p_0 ≈ 1000. This is the "naive" upper
bound; thermal conduction, water vapour, and ionization all reduce the
peak T below this.

### 4.1.2  Number density at minimum radius

Counting argument: if N moles of gas are trapped at R_max with pressure
p_∞, the number density at R_min is

$$
n(R_{\min}) = \frac{p_\infty}{k_B T_0}\left(\frac{R_{\max}}{R_{\min}}\right)^3
$$

For R_max/R_min = 10 and p_∞ = 1 atm, n ≈ 2.7 × 10²⁸ m⁻³ (≈ liquid-like
density). This is consistent with [BHL2002, FBSP2005] which place the
collapsed-bubble core in the *warm dense matter* regime.

> **Scope of the Storey–Szeri vapour cap.** Storey & Szeri's analysis
> [SS2000, S2003] is specifically for *water* vapour endothermic
> dissociation. Applying the same energy-cap mechanism to N₂ and O₂
> dissociation (a literal reading of the Section 4.3 ΔH table) is *not*
> what the original paper did and over-suppresses peak temperatures —
> by ~3× in pistol-shrimp-style cases where the bubble is air-filled
> rather than dominated by water vapour. The simulator's `vapour_cap`
> option should be scoped to the H₂O mole fraction only; N₂/O₂
> chemistry, if modelled at all, belongs in a separate `chemistry`
> module via Cantera (see Section 11). Default behaviour: cap applies
> to `x_{H_2O}` only, with a documented note when `x_{H_2O} < 0.1`
> (cap effectively inactive for biological/transient cases that nucleate
> from air-saturated water).

### 4.1.3  Adiabatic + heat-loss reduced model (Toegel)

The Toegel reduced model [TGGL2000] provides a single ODE for the gas
temperature inside the bubble with a single thermal-diffusion length:

$$
\frac{4}{3}\pi R^3 \,c_v \,\dot{T}_g
\;=\; -p_g \cdot 4\pi R^2 \dot{R} \;-\; 4\pi R^2 \, q_{\rm cond}
\;+\; Q_{\rm chem}
$$

with `q_cond ≈ k_g (T_g − T_wall) / l_th` and the diffusion length

$$
l_{\rm th} = \min\!\left(\sqrt{\frac{R \chi_g}{|\dot R|}},\; R/\pi\right)
$$

where χ_g = k_g / (ρ_g c_v) is the gas thermal diffusivity. `Q_chem` is
the energy source/sink from chemistry inside the bubble (see §4.3).

This is the recommended "thermal" module for v1: 1 ODE coupled to the
KME of Section 2.

---

## 4.2  Plasma diagnostics (closed-form formulas)

Once T_g and n are known, the simulator computes:

### Saha ionization (single-stage)

$$
\frac{n_e n_i}{n_a} = \frac{2 g_i}{g_a}\left(\frac{m_e k_B T}{2\pi \hbar^2}\right)^{3/2} e^{-E_i / k_B T}
$$

with E_i the first ionization energy (Ar: 15.76 eV, Xe: 12.13 eV,
H₂O→H₂O⁺: 12.62 eV). For T = 10⁴ K and n = 10²⁸ m⁻³ this gives a
fractional ionization x_e ≈ 10⁻³–10⁻²; for T ≈ 1.5 × 10⁴ K, x_e ≈ 0.1–0.2,
consistent with [SBM2016].

**Caveat:** at densities n ≳ 10²⁷ m⁻³ pressure ionization (continuum
lowering) raises the effective ionization beyond Saha's prediction; the
gas inside the collapsed bubble is in the warm-dense-matter regime
[SBM2016, BHL2002]. For better accuracy use the **Stewart–Pyatt
continuum-lowering correction** [SP1966] or a non-ideal Saha [E1995]:

$$
E_i^{\rm eff} = E_i - \Delta E_{\rm cont}, \quad
\Delta E_{\rm cont} \approx \frac{e^2}{4\pi\epsilon_0 \lambda_D}
$$

For the simulator, expose ionization-model choice as a parameter:
`{'ideal_saha', 'stewart_pyatt', 'tabulated'}`.

### Plasma frequency

$$
\omega_p = \sqrt{\frac{n_e e^2}{\epsilon_0 m_e}}, \qquad
f_p[\rm Hz] \approx 8.98 \sqrt{n_e[{\rm m}^{-3}]}
$$

For n_e = 10²⁶ m⁻³ (1 % ionization at 10²⁸ m⁻³ neutral density),
f_p ≈ 90 THz — UV/IR boundary. The plasma is *optically thick* to
radiation below ω_p.

### Debye length

$$
\lambda_D = \sqrt{\frac{\epsilon_0 k_B T_e}{n_e e^2}}
$$

For T_e = 10⁴ K and n_e = 10²⁶ m⁻³: λ_D ≈ 7 × 10⁻¹¹ m (about an Angstrom).
Bubble radius at minimum (~10⁻⁶ m) ≫ λ_D → quasi-neutral plasma is well
defined inside the collapsed core.

### Plasma coupling parameter

$$
\Gamma = \frac{e^2 / (4\pi \epsilon_0 a_{\rm WS})}{k_B T_e}, \quad
a_{\rm WS} = \left(\frac{3}{4\pi n_e}\right)^{1/3}
$$

For SBSL at peak: Γ ≈ 1, on the boundary between weakly and strongly
coupled [SBM2016]. The simulator should report Γ as a diagnostic; ideal
plasma equations (Saha, ideal-gas EOS) are accurate only for Γ ≪ 1.

### Mean free path (electron–ion)

$$
\lambda_{ei} \approx \frac{(4\pi \epsilon_0)^2 (k_B T_e)^2}{n_e e^4 \ln \Lambda}
$$

with ln Λ ≈ 5–10 for these conditions [GR1995]. For T_e = 10⁴ K,
n_e = 10²⁶ m⁻³: λ_ei ≈ 10⁻¹¹ m. Again ≪ R_min → fluid description of the
plasma core is valid.

---

## 4.3  Water-vapour chemistry

For aqueous SBSL the bubble interior is dominated by H₂O vapour at
collapse. Endothermic dissociation steps cap the peak T:

| Reaction                       | ΔH (kJ/mol) | Equilibrium T (k_B T = ΔH / N_A) |
|---                             |---          |---                               |
| H₂O ↔ H + OH                   | +499        | ~6 000 K                         |
| H₂O ↔ 2H + O                   | +926        | ~11 000 K                        |
| O₂ ↔ 2O                        | +498        | ~6 000 K                         |
| N₂ ↔ 2N                        | +945        | ~11 400 K                        |

Source: [NIST, S2003]. Peak temperatures plateau in the 5 000–10 000 K
range for aqueous SBSL precisely because incoming compressional energy
goes into breaking these bonds [SS2000]. This is the *primary reason*
biomimetic reactors operating in water cap at thousands of K rather than
reaching SBSL-with-noble-gas temperatures.

Practical implication: to reach higher T (e.g. 20 000–30 000 K), the
simulator should support a mode where the bubble contents are pure noble
gas (degassed, argon-saturated water + degassed bath) — see §4.5 below.

---

## 4.4  Optical flash properties (output of the plasma module)

### Spectrum

The standard model [HBL2002, BHL2002] is *thermal bremsstrahlung* +
*continuum recombination* + (in air-/water-saturated cases) *line
emission*. Energy per unit frequency from the bubble interior:

$$
\frac{dE}{d\nu \, dt} \;=\; 4\pi R^2 \cdot \pi B_\nu(T) (1 - e^{-\tau_\nu})
$$

where $B_\nu(T)$ is the Planck function and τ_ν the optical depth (see
Section 5). For high optical depth (degassed water + Ar), the spectrum is
nearly black-body at T ≈ 15 000–40 000 K [BHL2002].

### Flash duration

In the optically thick limit the flash duration ≈ time the bubble interior
is hotter than ~10 000 K. This is set by the bubble dynamics:

$$
\tau_{\rm flash} \approx \frac{|R - R_{\min}|}{|\dot R|}\bigg|_{T = 10^4 \text{K}}
$$

Empirically ~50–250 ps for SBSL in water [GGKL1997], ~10⁰ – 10¹ ns for
MBSL [FBSP2005]. Pistol-shrimp shrimpoluminescence: < 10 ns [L2001].

### Photon yield (visible)

$$
N_{\rm ph}^{\rm vis} \;=\; \int dt \int_{400\text{ nm}}^{700\text{ nm}}
\frac{dE/dt\, d\lambda}{h c / \lambda}
$$

Typical SBSL: 10⁵–10⁷ photons/flash; aqueous H₂SO₄ + Xe: up to 10⁸
[FS2005]. Pistol shrimp: ~5×10⁴ [L2001].

---

## 4.5  Effect of dissolved-gas species

Empirical scaling from [BHL2002, SD2008, FS2005]:

| Dissolved gas / liquid system        | Peak T inferred  | Notes                    |
|---                                   |---               |---                       |
| Air-saturated water                  | 5 000 – 10 000 K | "Standard" SBSL          |
| Argon-saturated, degassed water       | 15 000 – 25 000 K | Brightest aqueous SBSL  |
| Xenon-saturated, degassed water       | 20 000 – 30 000 K | Brightest aqueous SBSL  |
| Argon, conc. H₂SO₄                   | 30 000 – 40 000 K | Brightest reported [FS2005] |
| Helium-saturated water               | 7 000 – 12 000 K  | Smaller bubbles, smaller flash |

Mechanism (rectified diffusion): in air-saturated water under steady
acoustic forcing, N₂ and O₂ slowly diffuse out of the bubble through
chemistry (forming HNO₃, etc.), leaving an Ar-rich residue [BHL2002].
The bubble equilibrium content in steady SBSL is therefore ~99 % Ar even
when the saturating gas is air at low concentration.

For the simulator, the dissolved-gas content sets:
- Initial bubble composition (mole fractions x_Ar, x_H2O, x_N2, x_O2)
- Effective γ_g and c_v(T) of the gas mixture
- Allowed ionization channels and chemistry

---

## 4.6  Differences in non-aqueous liquids

Sulfuric acid, glycerin, silicone oil: lower vapour pressure → less
water-vapour-induced cooling → higher achievable T. From [FS2005,
SD2008]:

| Liquid                           | T_peak inferred   | Notes |
|---                               |---                | --- |
| Water                            | 5 000 – 25 000 K   | Reference |
| 85 % H₂SO₄                       | 8 000 – 15 000 K   | [FBSP2005] |
| 95 % H₂SO₄ + Xe                  | 30 000 – 40 000 K  | [FS2005] |
| Glycerin                         | 5 000 – 9 000 K    | Higher viscosity damps oscillation |
| Silicone oil                      | 5 000 – 10 000 K  | Higher viscosity damps oscillation |

Liquid choice is therefore one of the *primary* design knobs for the
reactor: switching from water to H₂SO₄ + Xe at fixed acoustic drive
multiplies the peak T by 2–4×.

---

## 4.7  Simulator outputs from the plasma module

For each bubble at each output time, the plasma module should compute:

- T_g (gas temperature, K)
- n (total number density, m⁻³)
- n_e (electron density, m⁻³)
- x_e (ionization fraction)
- ω_p, λ_D, Γ (plasma diagnostics)
- Mole fractions of each species (Ar, H₂O, OH, H, O, e⁻, …)
- B_ν(T) integrated over visible / UV bands
- Flash energy per band, peak T, peak n_e
- A "validity" flag: Γ < 1 (ideal plasma) vs Γ ≳ 1 (WDM)

---

## Citation tags used in this section

- [BHL2002] Brenner, Hilgenfeldt, Lohse, *Rev. Mod. Phys.* 74, 425 (2002).
- [TGGL2000] Toegel, Gompf, Pecha, Lohse, *Phys. Rev. Lett.* 85, 3165 (2000).
- [SS2000] Storey, Szeri, *Proc. R. Soc. A* 456, 1685 (2000).
- [HBL2002] Hilgenfeldt, Grossmann, Lohse, *Phys. Fluids* 11, 1318 (1999).
- [GGKL1997] Gompf, Günther, Nick, Pecha, Eisenmenger, *Phys. Rev. Lett.* 79, 1405 (1997).
- [L2001] Lohse, Schmitz, Versluis, *Nature* 413, 477 (2001).
- [FBSP2005] Flannigan, Suslick, *Nature* 434, 52 (2005).
- [FS2005] Flannigan, Suslick, *Phys. Rev. Lett.* 95, 044301 (2005); *Nat. Phys.* 6, 598 (2010).
- [SBM2016] Bataller, Putterman, *Sci. Rep.* 6, 20623 (2016) — first-principles Ar ionization in SL.
- [SP1966] Stewart, Pyatt, *Astrophys. J.* 144, 1203 (1966).
- [E1995] Ebeling, Förster, Fortov, *Thermophysical Properties of Hot Dense Plasmas*, Teubner (1995).
- [GR1995] Gibbon, *Short Pulse Laser Interactions with Matter*, ICP (2005).
- [S2003] Storey, Szeri, *Proc. R. Soc. A* 459, 2143 (2003).
- [NIST] NIST Webbook, https://webbook.nist.gov.
- [SD2008] Suslick, Flannigan, *Annu. Rev. Phys. Chem.* 59, 659 (2008).

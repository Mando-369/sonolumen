# Section 5 — Electromagnetic emission

> Purpose: provide the equations for the EM signatures the simulator must
> predict — the optical flash spectrum, the broadband bremsstrahlung
> continuum, the thermal blackbody envelope, and any RF / voltage
> transients that diagnostic instruments will see. The simulator's "EM"
> module takes (T_g, n_e, ω_p, R(t)) from Section 4 and returns time- and
> frequency-resolved emission.

---

## 5.1  Thermal bremsstrahlung (free–free)

For a Maxwellian plasma at temperature T with electron density n_e and ion
density n_i (charge Z), the spectral volume emissivity is [B1966, RL1979]:

$$
\boxed{\;
j_\nu = \frac{1}{4\pi}\, \frac{32\pi^2 e^6}{3 m_e c^3 (4\pi\epsilon_0)^3}
\sqrt{\frac{2}{3 \pi m_e k_B T}}\, n_e n_i Z^2 \, \bar g_{\rm ff}(\nu, T)\, e^{-h\nu/k_B T}
\;}
$$

(units: W m⁻³ Hz⁻¹ sr⁻¹). The Gaunt factor `ḡ_ff(ν, T)` is O(1) and
captured by Karzas–Latter tables [KL1961] or the analytic fit of Itoh et
al. [I2002] (≤ 1 % over astrophysics-relevant range).

Frequency-integrated cooling rate (W/m³):

$$
\Lambda_{\rm ff} = \frac{32 \pi}{3}\sqrt{\frac{2 \pi k_B T}{3 m_e}}
\frac{Z^2 e^6}{m_e c^3 (4\pi\epsilon_0)^3 \hbar} \, n_e n_i \, \bar g_{\rm ff}^{\rm tot}
\approx 1.4 \times 10^{-40} \, T^{1/2}\, n_e n_i Z^2 \;\; ({\rm SI: \, W/m^3, } T{\rm \,in\,K, } n {\rm \,in\,m^{-3}})
$$

For SBSL conditions (T ≈ 2×10⁴ K, n_e ≈ 10²⁶ m⁻³, n_i ≈ 10²⁶ m⁻³, Z = 1)
this is Λ_ff ≈ 2 × 10²⁰ W/m³. Multiplied by a 1-µm-radius bubble volume
(4 × 10⁻¹⁸ m³) and a 100-ps duration: ~10⁻⁸ J ≈ 10⁵ eV ≈ 4×10⁴ visible
photons. Order-of-magnitude consistent with measured SBSL yields
[BHL2002].

For low-temperature SBSL plasmas the bremsstrahlung is *optically thick*
(see §5.4) — the Λ_ff above is the *unattenuated* emissivity; the actual
escaping flux is set by the photosphere temperature.

---

## 5.2  Recombination radiation (free–bound)

When a free electron recombines into a bound state n of an ion of charge
Z, a photon of energy `hν = ½ m_e v² + Z² Ry / n²` is emitted. The
emission coefficient at h ν > Z² Ry / n² is [RL1979]:

$$
j_\nu^{\rm fb} = \frac{1}{4\pi}\, \frac{32\pi^2 e^6 Z^4 \, {\rm Ry}}{3 m_e c^3 (4\pi\epsilon_0)^3 (k_B T)^{3/2}}
\sqrt{\frac{2}{3 \pi m_e k_B T}}
\, n_e n_i \sum_{n_{\min}}^{\infty} \frac{g_n}{n^3} e^{-(h\nu - Z^2 {\rm Ry}/n^2)/k_B T}
$$

with Ry = 13.6 eV the Rydberg energy. The recombination edges (UV "jumps"
in the spectrum at hν = Z²Ry/n²) are diagnostic; for Z = 1 hydrogen-like
ions the Lyman jump at 13.6 eV (91.2 nm) and Balmer jump at 3.4 eV
(364 nm) bracket the UV continuum.

Total recombination cooling rate (similar form to bremsstrahlung):

$$
\Lambda_{\rm fb} \approx 4 \times 10^{-39} T^{-1/2}\, n_e n_i Z^4 \quad ({\rm SI})
$$

At T ≈ 2 × 10⁴ K, recombination is comparable to bremsstrahlung; below
~10⁴ K it dominates [RL1979].

---

## 5.3  Thermal blackbody envelope

If the plasma is optically thick at frequency ν, it radiates as a
blackbody at the local electron temperature T_e:

$$
B_\nu(T) \;=\; \frac{2 h \nu^3 / c^2}{e^{h\nu/k_B T} - 1}
\quad ({\rm W \, m^{-2} \, Hz^{-1} \, sr^{-1}})
$$

Integrated power flux from a sphere of radius R:

$$
P_{\rm BB}(T,R) = 4\pi R^2 \cdot \sigma_{\rm SB} T^4
$$

with σ_SB = 5.67 × 10⁻⁸ W m⁻² K⁻⁴. For T = 2 × 10⁴ K, R = 1 µm:
P_BB ≈ 1.1 × 10⁵ W ≈ 1 GW/m² — but only for the duration the plasma is
hot, ~100 ps, giving total radiated energy ~10⁻⁸ J. Again consistent
with SBSL data.

The empirical SBSL spectrum is fit *better* by a blackbody than by an
optically thin bremsstrahlung [HBL1999, BHL2002], indicating optical
depth τ_ν ≳ 1 over much of the visible/UV range during the flash.

---

## 5.4  Optical depth

Free–free absorption coefficient (the inverse process to bremsstrahlung
emission, by Kirchhoff's law in LTE):

$$
\kappa_\nu^{\rm ff} \;=\; \frac{j_\nu^{\rm ff}}{B_\nu(T)}
\;\approx\; \frac{4 e^6}{3 m_e h c (4\pi\epsilon_0)^3}\sqrt{\frac{2 \pi}{3 m_e k_B T}}
\, \frac{n_e n_i Z^2 \bar g_{\rm ff}}{\nu^3} (1 - e^{-h\nu/k_B T})
$$

Optical depth across a bubble of radius R: `τ_ν = κ_ν · R`. For SBSL
conditions, τ_ν ≳ 1 in the visible — confirming the blackbody picture.
For shrimpoluminescence (T inferred ≈ 5 000 K, smaller n_e), τ_ν ≪ 1
and the spectrum should be optically thin → bremsstrahlung-dominated
[L2001, BHL2002].

The simulator should compute τ_ν explicitly and switch between optically
thin (sum of j_ff and j_fb) and optically thick (B_ν(T)(1-e^-τ)) regimes.

---

## 5.5  Plasma oscillation emission

A plasma at frequency ω_p radiates inefficiently in vacuum because
plasma waves are longitudinal. However, *transition radiation* and
*nonlinear mode coupling* produce some EM emission near ω_p [B1966]. For
the bubble plasma, ω_p ≈ 10¹⁴–10¹⁵ rad/s (UV/IR boundary) — coincident
with the broadband emission window, so a separate narrow plasma-emission
peak is generally not observed [BHL2002].

A simpler observable: when ω_emitted < ω_p the radiation cannot escape
the plasma. So the *cutoff* in the spectrum at low frequencies is at
ω_p. For n_e = 10²⁶ m⁻³, this cutoff is at λ ≈ 3 µm (mid-IR) — well
below the visible band where most measurements are made.

---

## 5.6  RF emission and electrical signatures

There are two distinct claims in the literature:

### 5.6.1  Margulis "electrical" theory

Margulis [M1995, M2000] argues that bubble-fragmentation events deposit
uncompensated surface charges in the liquid, producing measurable
voltage transients on nearby electrodes (~mV to tens of mV) and broadband
RF emission. This is a *non-thermal* mechanism distinct from the
hot-spot model.

A more concrete physical picture for the same family of effects is the
**electric double layer (EDL) disruption** mechanism: a stable bubble
in water has a charged interfacial layer (Stern + diffuse layer, surface
potential typically −20 to −60 mV depending on pH and ionic strength
[GB2008]). Rapid bubble-wall acceleration during collapse and rebound
disrupts this layer, producing a transient dipole that radiates a
sub-µs pulse. Predicted voltage at a 1 cm electrode for a 1 mm² bubble
surface, ζ ≈ −40 mV, collapse time ~1 µs is in the µV–mV range —
consistent with reported Margulis-style measurements but also with what
careful electronics could mistake for noise. This sharpens the
parametric Margulis model: the free parameter Q_b is the integrated
disrupted EDL charge, of order ζ · A_bubble · C_dl ≈ 10⁻¹²–10⁻¹⁰ C.

### 5.6.2  Hot-spot RF emission

In the standard hot-spot picture the plasma radiates broadband EM down to
its plasma frequency. For SBSL, ω_p is very high (UV) and direct RF
emission from the plasma is undetectable. RF signatures observed near
cavitation cells therefore are usually attributed to:

- Switching transients in the driving electronics
- Charge separation on bubble walls (the Margulis effect)
- Rectified-diffusion-driven streaming and triboelectric effects

For the simulator, the recommendation is:
- Implement the thermal-emission stack (§§5.1–5.4) as the primary EM
  output module. This is the well-established physics.
- Provide an *optional* "Margulis" module that emits a parametric
  voltage pulse `V(t) ∝ Q_b / (4πε₀ r)` with `Q_b` an empirical
  parameter (typical value 10⁻¹²–10⁻¹⁰ C per fragmentation event,
  duration ~10⁻⁷ s [M2000]). Mark this as contested (see Section 10).

---

## 5.7  Published RF / voltage measurements

Measurement              | Reported value                          | Source
---                      |---                                       |---
Voltage transient on nearby Pt electrode (kHz cavitation in water) | 1–50 mV peak, 100 ns–1 µs duration | [M2000, MM1995]
RF spectrum near 20 kHz cell | broadband 100 kHz – 10 MHz, dB above background ~30 dB | [M2000]
Pickup-coil dB/dt signal at 30 kHz cell (integrated 1 cm³ volume) | ~100 nV·s, single-collapse | reported value [LH2002], modest replication
Far-field RF (10 cm from cell, > 1 MHz) | not robustly detected above noise | [BHL2002]

All three regimes are at the level where careful shielding, common-mode
rejection, and differential pickup are required to distinguish bubble
signals from electronics. The simulator should output predicted V(t)
for a virtual electrode located at user-specified position; cross-check
against measured noise floors of Section 7.

---

## 5.8  Spectrum that the simulator should emit

For each output time t and each bubble:

```
S_ν(t) = ε(t) · [ j_ff_ν(T(t), n_e(t)) + j_fb_ν(T(t), n_e(t)) ]
```

where `ε(t) = (1 − exp(−τ_ν · 2R(t)))` is the escape factor that
smoothly interpolates between the optically thin and thick limits.

Time-integrated visible photon yield:

$$
N_{\rm vis} = \int dt \int_{\nu_{\rm red}}^{\nu_{\rm blue}} \frac{4\pi V_b(t) S_\nu(t)}{h\nu} d\nu
$$

Validation target: SBSL → 10⁵–10⁷ photons; pistol-shrimp event →
~5×10⁴ photons.

---

## Citation tags used in this section

- [B1966] Bekefi, *Radiation Processes in Plasmas*, Wiley (1966).
- [KL1961] Karzas, Latter, *Astrophys. J. Suppl.* 6, 167 (1961).
- [RL1979] Rybicki, Lightman, *Radiative Processes in Astrophysics*, Wiley (1979).
- [I2002] Itoh, Sakamoto, Kusano, Nozawa, Kohyama, *Astrophys. J. Suppl.* 128, 125 (2000).
- [HBL1999] Hilgenfeldt, Grossmann, Lohse, *Phys. Fluids* 11, 1318 (1999).
- [BHL2002] Brenner, Hilgenfeldt, Lohse, *Rev. Mod. Phys.* 74, 425 (2002).
- [M1995] Margulis, *Ultrasonics* 30, 152 (1992) and *Ultrason. Sonochem.* 1, S87 (1994).
- [M2000] Margulis, *High Energy Chem.* 38, 135 (2004).
- [MM1995] Margulis, *J. Acoust. Soc. Am.* (review of cavitation electrification).
- [LH2002] cavitation pickup-coil reports — note: limited replication; flag in Section 10.
- [L2001] Lohse, Schmitz, Versluis, *Nature* 413, 477 (2001).
- [GB2008] Graciaa, Creux, Lachaise (review of bubble surface charge in water), *Adv. Colloid Interface Sci.* (2008).

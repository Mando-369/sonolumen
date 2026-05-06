# Master equation list — consistent notation

> Purpose: a single reference page where every equation used in the
> simulator is collected, with consistent symbols, units, and pointers
> back to the section where it is derived or applied.

## Notation key

Common symbols used everywhere in this dossier:

| Symbol     | Meaning                                          | Units (SI)    |
|---         |---                                               |---            |
| t          | time                                             | s             |
| ω          | angular frequency = 2π f                         | rad/s         |
| f          | frequency                                        | Hz            |
| R(t), Ṙ, R̈| bubble radius and time derivatives               | m, m/s, m/s²  |
| R₀         | equilibrium bubble radius                        | m             |
| R_max      | maximum bubble radius during a cycle             | m             |
| R_min      | minimum bubble radius during a cycle             | m             |
| ρ_L        | liquid density                                   | kg/m³         |
| c, c_L     | speed of sound in liquid                         | m/s           |
| μ_L        | liquid dynamic viscosity                         | Pa·s          |
| σ          | liquid–gas surface tension                       | N/m           |
| p_∞        | hydrostatic / ambient pressure                   | Pa            |
| p_a(t)     | acoustic driving pressure                        | Pa            |
| P_A        | acoustic pressure amplitude                      | Pa            |
| p_v        | saturation vapour pressure                       | Pa            |
| p_g(R)     | gas partial pressure inside bubble               | Pa            |
| p_L(R)     | liquid pressure at bubble wall                   | Pa            |
| κ          | polytropic exponent inside bubble                | —             |
| γ_g        | gas specific-heat ratio                          | —             |
| T_g, T_e   | gas temperature, electron temperature            | K             |
| n          | total number density inside bubble               | m⁻³           |
| n_e, n_i   | electron, ion number density                     | m⁻³           |
| Z          | ion charge state                                 | —             |
| ε₀         | vacuum permittivity                              | F/m           |
| e          | electron charge                                  | C             |
| m_e        | electron mass                                    | kg            |
| k_B        | Boltzmann constant                               | J/K           |
| ℏ          | reduced Planck constant                          | J·s           |
| h          | Planck constant                                  | J·s           |
| ν, λ       | photon frequency, wavelength                     | Hz, m         |
| B_ν(T)     | Planck function                                  | W m⁻² Hz⁻¹ sr⁻¹|
| σ_SB       | Stefan–Boltzmann constant                        | W m⁻² K⁻⁴      |
| Z_acoustic | specific acoustic impedance ρ_L c_L              | rayl          |
| ḡ_ff       | free–free Gaunt factor                           | —             |
| Ry         | Rydberg energy 13.605693 eV                      | J             |
| ω_p        | plasma frequency                                 | rad/s         |
| λ_D        | Debye length                                     | m             |
| Γ          | plasma coupling parameter                        | —             |

---

## E1. Linear acoustic wave equation (Section 3.1)

$$
\nabla^2 p - \frac{1}{c_L^2}\frac{\partial^2 p}{\partial t^2} = 0
$$

## E2. Westervelt nonlinear wave equation (Section 3.1)

$$
\nabla^2 p - \frac{1}{c_L^2}\frac{\partial^2 p}{\partial t^2}
+ \frac{\delta}{c_L^4}\frac{\partial^3 p}{\partial t^3}
+ \frac{\beta}{\rho_L c_L^4}\frac{\partial^2 p^2}{\partial t^2} = 0
$$

## E3. Standing wave eigenfrequencies (Section 3.2)

Spherical resonator (radius `a`, rigid walls, fundamental):
`f₁ = c_L / (2 a)`.

Cylindrical resonator (length `L`, axial fundamental): `f₁ = c_L / (2L)`.

Cylindrical resonator (radius `a`, lowest radial mode, J₀′(k a) = 0):
`f₁ = c_L · 3.832 / (2 π a)`.

## E4. Blake threshold (Section 3.4)

$$
P_B = p_\infty - p_v + \frac{4\sigma}{3 R_0}\sqrt{\frac{2\sigma}{3 R_0 (p_\infty - p_v + 2\sigma/R_0)}}
$$

## E5. Minnaert resonance (Section 3.5)

$$
\omega_0 = \frac{1}{R_0}\sqrt{\frac{3 \kappa (p_\infty + 2\sigma/R_0) - 2\sigma/R_0}{\rho_L}}
$$

## E6. Rayleigh–Plesset equation (Section 2.1)

$$
\rho_L \left( R \ddot R + \tfrac{3}{2}\dot R^2 \right)
= p_g(R,t) + p_v - \frac{2\sigma}{R} - \frac{4 \mu_L \dot R}{R} - p_\infty - p_a(t)
$$

with `p_g(R) = p_{g,0} (R_0/R)^{3κ}` and `p_{g,0} = p_∞ + 2σ/R_0 − p_v`.
Sign convention: additive (positive `p_a` is compressive drive). See the
"Sign convention note" in §2.1 — applies identically to E8 and E9.

### E6b. Van der Waals hard-core gas EOS (Section 2.1, recommended for SBSL)

$$
p_g(R) = \left(p_\infty + \frac{2\sigma}{R_0} - p_v\right)
\left(\frac{R_0^3 - h^3}{R^3 - h^3}\right)^{\kappa}
$$

with hard-core radius `h = R_0 / 8.54` (Ar), `R_0 / 8.86` (Xe).

## E7. Pure Rayleigh collapse time (Section 2.1)

$$
t_c = 0.915\, R_{\max}\sqrt{\rho_L / \Delta p}
$$

## E8. Keller–Miksis equation (Section 2.2)

$$
\left(1 - \frac{\dot R}{c}\right) R \ddot R
+ \frac{3}{2}\dot R^2 \left(1 - \frac{\dot R}{3 c}\right)
= \left(1 + \frac{\dot R}{c}\right)\frac{p_L - p_\infty - p_a(t + R/c)}{\rho_L}
+ \frac{R}{\rho_L c}\frac{d}{dt}\!\bigl[p_L - p_\infty - p_a(t + R/c)\bigr]
$$

## E9. Gilmore equation (Section 2.3)

$$
\left(1 - \frac{\dot R}{C}\right) R \ddot R
+ \frac{3}{2}\dot R^2 \left(1 - \frac{\dot R}{3 C}\right)
= \left(1 + \frac{\dot R}{C}\right) H
+ \frac{R}{C}\left(1 - \frac{\dot R}{C}\right)\dot H
$$

with enthalpy difference

$$
H = \int_{p_\infty}^{p_L} \frac{dp}{\rho_L(p)}, \qquad
C(p_L) = \sqrt{c_0^2 + (n-1) H}
$$

and Tait EOS for the liquid:

$$
\frac{p + B}{p_\infty + B} = \left(\frac{\rho_L}{\rho_{L,0}}\right)^n
$$

(B ≈ 3.05×10⁸ Pa, n ≈ 7.15 for water [BR1994].)

## E10. Toegel reduced thermal model (Section 2.4)

$$
\frac{4}{3}\pi R^3 c_v \dot{T}_g
= -p_g \cdot 4\pi R^2 \dot R - 4\pi R^2 \,k_g \frac{T_g - T_{\rm wall}}{l_{\rm th}}
+ Q_{\rm chem}
$$

with

$$
l_{\rm th} = \min\!\left(\sqrt{\frac{R \chi_g}{|\dot R|}}, \; R/\pi\right)
$$

## E11. Adiabatic compression law (Section 4.1)

$$
T(R) = T_0 (R_0/R)^{3(\gamma-1)}, \qquad
p_g(R) = p_{g,0} (R_0/R)^{3\gamma}
$$

## E12. Saha ionization (Section 4.2)

$$
\frac{n_e n_i}{n_a} = \frac{2 g_i}{g_a}\left(\frac{m_e k_B T}{2\pi \hbar^2}\right)^{3/2} e^{-E_i / k_B T}
$$

## E13. Stewart–Pyatt continuum lowering (Section 4.2)

$$
E_i^{\rm eff} = E_i - \Delta E_{\rm cont}, \quad
\Delta E_{\rm cont} \approx \frac{e^2}{4\pi \epsilon_0 \lambda_D}
$$

## E14. Plasma frequency (Section 4.2)

$$
\omega_p = \sqrt{\frac{n_e e^2}{\epsilon_0 m_e}}, \qquad
f_p[{\rm Hz}] \approx 8.98 \sqrt{n_e[{\rm m}^{-3}]}
$$

## E15. Debye length (Section 4.2)

$$
\lambda_D = \sqrt{\frac{\epsilon_0 k_B T_e}{n_e e^2}}
$$

## E16. Plasma coupling parameter (Section 4.2)

$$
\Gamma = \frac{e^2 / (4\pi \epsilon_0 a_{\rm WS})}{k_B T_e}, \quad
a_{\rm WS} = \left(\frac{3}{4\pi n_e}\right)^{1/3}
$$

## E17. Thermal bremsstrahlung emissivity (Section 5.1)

$$
j_\nu = \frac{1}{4\pi}\, \frac{32\pi^2 e^6}{3 m_e c^3 (4\pi\epsilon_0)^3}
\sqrt{\frac{2}{3 \pi m_e k_B T}}\, n_e n_i Z^2 \bar g_{\rm ff}(\nu, T) \, e^{-h\nu/k_B T}
$$

## E18. Bremsstrahlung total cooling (Section 5.1)

$$
\Lambda_{\rm ff} \approx 1.4 \times 10^{-40}\, T^{1/2}\, n_e n_i Z^2 \quad (\text{SI: W/m}^3)
$$

## E19. Recombination emissivity (Section 5.2)

$$
j_\nu^{\rm fb} = \frac{1}{4\pi}\, \frac{32\pi^2 e^6 Z^4 {\rm Ry}}{3 m_e c^3 (4\pi\epsilon_0)^3 (k_B T)^{3/2}}
\sqrt{\frac{2}{3 \pi m_e k_B T}}
\, n_e n_i \sum_{n_{\min}}^{\infty} \frac{g_n}{n^3} e^{-(h\nu - Z^2 {\rm Ry}/n^2)/k_B T}
$$

## E20. Planck function (Section 5.3)

$$
B_\nu(T) = \frac{2 h \nu^3 / c^2}{e^{h\nu/k_B T} - 1}
$$

## E21. Stefan–Boltzmann (Section 5.3)

$$
P_{\rm BB}(T,R) = 4\pi R^2 \sigma_{\rm SB} T^4
$$

## E22. Free–free absorption (Section 5.4)

$$
\kappa_\nu^{\rm ff}
\approx \frac{4 e^6}{3 m_e h c (4\pi\epsilon_0)^3}\sqrt{\frac{2 \pi}{3 m_e k_B T}}
\, \frac{n_e n_i Z^2 \bar g_{\rm ff}}{\nu^3} (1 - e^{-h\nu/k_B T})
$$

## E23. Optically thin → thick interpolation (Section 5.4)

$$
S_\nu^{\rm escape}(t) = \bigl(1 - e^{-\tau_\nu(t)}\bigr) B_\nu(T(t))
\quad\text{with}\quad \tau_\nu(t) = \kappa_\nu(t) \cdot R(t)
$$

## E24. Far-field acoustic emission from bubble (Section 7.2)

$$
p_{\rm rad}(r,t) = \frac{\rho_L}{4\pi r}\,\ddot V_b\!\left(t - \frac{r}{c}\right)
$$

## E25. Acoustic intensity, plane wave (Section 3.1)

$$
I = \frac{P_A^2}{2 \rho_L c_L}
$$

## E26. Primary Bjerknes force (Section 3.5)

$$
\mathbf{F}_B = -\langle V(t) \nabla p_a(\mathbf{x},t) \rangle
$$

## E27. Secondary Bjerknes force (Section 3.5)

$$
F_{12} = -\frac{4\pi R_1^2 R_2^2 \rho_L \omega^2}{r_{12}^2}\langle \dot R_1 \dot R_2 \rangle
$$

## E28. Mean free path (electron–ion) (Section 4.2)

$$
\lambda_{ei} \approx \frac{(4\pi\epsilon_0)^2 (k_B T_e)^2}{n_e e^4 \ln \Lambda}
$$

## E29. Margulis transient (optional, parametric, Section 5.6)

$$
V(t) = \frac{Q_b}{4\pi \epsilon_0 r}\, \chi(t)
$$

with `χ(t)` a parametric pulse shape and `Q_b` a free parameter
(empirical: 10⁻¹²–10⁻¹⁰ C; flagged contested in Section 10).

## E30. Photon yield (visible) (Section 5.8)

$$
N_{\rm vis} = \int dt \int_{\nu_{\rm red}}^{\nu_{\rm blue}}
\frac{4 \pi V_b(t) S_\nu^{\rm escape}(t)}{h \nu}\, d\nu
$$

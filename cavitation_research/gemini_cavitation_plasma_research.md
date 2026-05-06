
# Research Dossier: Cavitation-Driven Plasma Reactor

This document serves as the technical specification for a Python-based simulator designed to model a tabletop laboratory device inspired by biological cavitation[cite: 2].

## SECTION 1: BIOLOGICAL CAVITATION REFERENCE DATA
Biological mechanisms provide the proof-of-concept for localized plasma generation through acoustic energy[cite: 2].

*   **Pistol Shrimp (*Alpheus heterochaelis*):**
    *   **Claw Closure Speed:** 20–25 m/s.
    *   **Water Jet Velocity:** Up to 30 m/s.
    *   **Acoustic Pressure:** Source levels reach 190–210 dB re 1 µPa.
    *   **Bubble Lifecycle:** Bubbles grow to 3–5 mm before collapsing over 300–400 µs.
    *   **Peak Temperature:** Estimates reach 4,000–5,000 K[cite: 2].
    *   **Optical Signature:** Sonoluminescence flashes are <10 ns in duration.
*   **Mantis Shrimp (*Odontodactylus scyllarus*):**
    *   **Strike Speed:** 14–23 m/s.
    *   **Strike Force:** Peak mechanical forces up to 1,500 N[cite: 2].
    *   **Energy:** Strike energy is 100–300 mJ, with significant energy recovery from cavitation collapse.

---

## SECTION 2: BUBBLE DYNAMICS EQUATIONS
The simulator must model the radial evolution $R(t)$ of a microbubble under acoustic forcing.

### **The Keller-Miksis Equation**
This is the standard model for Single-Bubble Sonoluminescence (SBSL) as it accounts for liquid compressibility and acoustic radiation[cite: 2]:

$$\left(1 - \frac{\dot{R}}{c_L}\right)R\ddot{R} + \frac{3}{2}\left(1 - \frac{\dot{R}}{3c_L}\right)\dot{R}^2 = \frac{1}{\rho_L} \left(1 + \frac{\dot{R}}{c_L}\right) \left(P_L - P_\infty(t)\right) + \frac{R}{\rho_L c_L}\frac{d P_L}{dt}$$

*   **Internal Pressure ($P_L$):** $P_L = P_g - \frac{2\sigma}{R} - \frac{4\mu\dot{R}}{R}$
*   **Van der Waals Correction:** $P_g(R) = (P_0 + \frac{2\sigma}{R_0}) (\frac{R_0^3 - h^3}{R^3 - h^3})^\gamma$
    *   Where $h$ is the hard-core radius ($\approx R_0/8.54$ for Argon).
*   **Numerical Considerations:** Use stiff solvers (BDF or Radau) with absolute tolerances $\leq 10^{-12}$ to capture the nanosecond collapse phase.

---

## SECTION 3: ACOUSTIC FIELD GENERATION
To trap and drive the bubble, a standing wave must be established in a resonant chamber.

*   **Spherical Resonance:** Fundamental frequency $f_1 = \frac{c_L}{2 R_{flask}}$[cite: 2].
*   **Blake Threshold:** The minimum pressure amplitude $P_B$ to trigger transient cavitation[cite: 2]:
    $$P_B = P_0 + \frac{8\sigma}{9} \sqrt{\frac{2\sigma}{3 R_0^3 (P_0 + \frac{2\sigma}{R_0})}}$$
*   **Bjerknes Forces:** Primary radiation forces must counteract buoyancy to keep the bubble at the pressure antinode (the center).

---

## SECTION 4: PLASMA CONDITIONS
The collapse creates a briefly ionized core[cite: 2].

*   **Ionization:** Modeled via the **Saha Equation**[cite: 2]:
    $$\frac{x^2}{1-x} = \frac{1}{n} \left(\frac{2\pi m_e k_B T}{h^2}\right)^{3/2} e^{-E_i / k_B T}$$
*   **Peak Density:** Exceeds $10^{22}$ atoms/cm³[cite: 2].
*   **Noble Gas Effect:** Argon (Ar) or Xenon (Xe) are preferred as they lack molecular dissociation pathways that quench thermal energy[cite: 2].

---

## SECTION 5: ELECTROMAGNETIC EMISSION
The output signature is primarily optical and potentially RF-based[cite: 2].

*   **Spectral Mechanism:** Modeled as thermal **Bremsstrahlung** and Blackbody radiation[cite: 2].
*   **Blackbody Formula:** $I(\lambda, T) = \frac{2 h c^2}{\lambda^5} \frac{1}{e^{hc/\lambda k_B T} - 1}$
*   **RF Transients:** Rapid displacement of the liquid-gas interface can induce microvolt-scale transients in nearby electrodes due to the disruption of the electric double layer.

---

## SECTION 6 & 7: REACTOR DESIGN & DIAGNOSTICS
*   **Chamber:** 100 mL borosilicate spherical flask with PZT-8 transducers bonded at the equator[cite: 2].
*   **Control:** Phase-Locked Loop (PLL) to track the resonant frequency as the temperature changes[cite: 2].
*   **Detection:** Photomultiplier tubes (PMTs) for timing and needle hydrophones for shockwave measurements[cite: 2].

---

## SECTION 9: DEFAULT PARAMETERS FOR INITIAL SIMULATION
These values provide a validated baseline for the coding assistant[cite: 2].

| Parameter | Value |
| :--- | :--- |
| **Ambient Pressure ($P_0$)** | $101,325$ Pa |
| **Liquid Density ($\rho_L$)** | $998$ kg/m³ (Water) |
| **Surface Tension ($\sigma$)** | $0.072$ N/m |
| **Dynamic Viscosity ($\mu$)** | $0.001$ Pa·s |
| **Equilibrium Radius ($R_0$)** | $4.5$ µm |
| **Driving Frequency ($f$)** | $26.5$ kHz |
| **Acoustic Amplitude ($P_A$)** | $1.35$ atm |

---

## SECTION 11: SIMULATOR SPECIFICATION (HANDOFF)
The Python code should be modularized to facilitate iterative testing[cite: 2].

1.  **`config.py`**: Defines physical constants and material properties[cite: 2].
2.  **`dynamics.py`**: Implements the Keller-Miksis derivative for `scipy.integrate.solve_ivp`[cite: 2].
3.  **`plasma.py`**: Calculates ionization fraction, Debye length, and radiation power based on $T_{max}$[cite: 2].
4.  **`viz.py`**: Generates $R(t)$ plots, phase diagrams ($\dot{R}$ vs $R$), and spectral power distribution[cite: 2].

**Validation Test:** Ensure the code predicts $R_{max} \approx 40$ µm and $T_{max} > 10,000$ K for the default parameters above[cite: 2].

---

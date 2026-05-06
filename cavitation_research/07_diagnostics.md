# Section 7 — Detection and diagnostic methods

> Purpose: list the standard instruments used to characterise cavitation
> events. The simulator's role is twofold: (a) compute predicted detector
> outputs (PMT counts, hydrophone V(t), pickup-coil V(t)) given the
> physics of Sections 4–5, and (b) provide noise-floor / sensitivity
> models so the user can assess whether a given setup will detect a
> simulated event.

For each instrument category below: principle, typical commercial part(s),
key parameters, noise floor, sample published use in cavitation work.

---

## 7.1  Photomultiplier tube (PMT) — optical flash

**Principle.** Photocathode + secondary-emission dynode chain. Sub-ns
single-photon timing, gain 10⁵–10⁷.

**Reference parts:**

| Part                       | QE peak    | Rise time | Transit-time spread | Use case |
|---                         |---         |---        |---                  |---       |
| Hamamatsu R7400U           | 24 % @ 420 nm | 0.78 ns | 0.27 ns FWHM       | SBSL flash counting [BHL2002] |
| Hamamatsu R9880U-20        | 35 % @ 400 nm | 0.57 ns | 0.27 ns FWHM       | Higher-QE replacement |
| Hamamatsu H10721 module    | 25 % @ 400 nm | 0.57 ns | 0.30 ns FWHM       | Compact +HV+amp built-in |
| Hamamatsu R6094 (UV)       | 20 % @ 220 nm | 1.8 ns  | 1.5 ns FWHM        | UV bremsstrahlung detection |

**What the simulator should output.** Predicted photon-arrival time
distribution given the bubble flash model (Section 4) folded with the
PMT impulse response:

```
n_pe(t) = Conv[ N_ph(t) · QE(λ) , h_PMT(t) ]
V_PMT(t) = G · e · n_pe(t) / R_load · h_amp(t)
```

with QE(λ) and impulse response h(t) tabulated in datasheets.

**Sensitivity / noise.** Dark count rate at room T, R7400U: 100–500 cps.
Single-photon pulse height ≈ 5 mV into 50 Ω at G = 10⁶. SBSL flash
(10⁵ photons, 4π sr, geometric collection efficiency 1–10 %): ~10³–10⁴
photoelectrons → easily detectable above SPE.

**Typical setup.** PMT in light-tight enclosure aligned with SBSL cell
optical port, 50 Ω TIA → 1 GHz LeCroy/Tektronix scope or constant-fraction
discriminator + TDC.

---

## 7.2  Hydrophones — acoustic signature

**Principle.** Piezo membrane or PVDF film responds to local pressure.
Calibrated voltage-per-Pa across a known bandwidth.

**Reference parts:**

| Part                       | Bandwidth         | Sensitivity | Tip diameter |
|---                         |---                |---          |---           |
| ONDA HNR-0500              | 1–20 MHz          | 0.4 mV/MPa  | 500 µm       |
| ONDA HGL-0200              | 0.25–40 MHz       | 50 nV/Pa    | 200 µm       |
| Reson TC4034               | 1 Hz – 600 kHz    | 215 µV/Pa   | spherical 25 mm |
| Brüel & Kjær 8104          | 0.1 Hz – 120 kHz  | 50 µV/Pa    | 25 mm        |
| Fibre-optic (e.g. FOPH 2000) | 1 kHz – 100 MHz | 10⁻¹ V/MPa  | 100 µm       |

**What the simulator should output.** Predicted V(t) at the hydrophone
position from the bubble's far-field acoustic emission:

$$
p_{\rm rad}(r,t) = \frac{\rho_L}{4\pi r}\left[\ddot{V}_b(t-r/c) + \text{higher orders}\right]
$$

where V_b is the bubble volume. Fold with the hydrophone calibration
curve M(f) [V/Pa], output `V(t) = IFFT[M(f) · P_rad(f)]`.

**Sensitivity / noise.** Self-noise of HNR-0500 at 5 MHz ≈ 2 nV/√Hz.
SBSL collapse pressure pulse: ~50 kPa peak at 1 cm distance, sub-µs
duration, ~10 mV into hydrophone — well above noise.

**Use in cavitation work.** [V2000] used a Brüel & Kjær hydrophone
30 cm from snapping shrimp; [BHL2002] cite Reson and ONDA models for
SBSL acoustic emission measurements.

---

## 7.3  High-speed cameras — bubble dynamics R(t)

**Reference parts:**

| Camera                       | Frame rate (max) | Resolution at frame rate | Notes |
|---                           |---               |---                       |---     |
| Photron FASTCAM SA-X2        | 12 800 fps full HD | 1024 × 1024 @ 12.8 kfps  | 20 µs/frame typical |
| Phantom v2640                | 6 600 fps full HD | 2048 × 1952 @ 6.6 kfps  | Long record time |
| Shimadzu HPV-X2              | 10 Mfps          | 400 × 250 @ 10 Mfps     | 256 frames total — used for SBSL collapse [Z2003] |
| Specialised Imaging Kirana   | 5 Mfps           | 924 × 768 @ 5 Mfps      | Same niche |
| Streak cameras (Hamamatsu C10910) | sub-ps temporal | 1 spatial line          | Shrimpoluminescence / sonoluminescence flash duration [GGKL1997] |

For the *bubble lifetime* (~300 µs for pistol-shrimp; ~25 µs for SBSL
cycle): 100 kfps suffices.

For the *collapse* (~1 ns – 1 µs): 10 Mfps minimum or, for sub-ns flash
itself, a streak camera (gated PMT or ICCD).

**What the simulator should output.** Synthetic R(t) overlaid on a
synthetic pixel intensity model: spherical bubble with refractive-index
contrast, projected onto camera plane with the camera's pixel size and
frame rate.

---

## 7.4  RF antennas and pickup coils — EM emission

**Antennas.**
- For ω_p-related emission (UHF / sub-mm): nothing standard. Plasma is
  inside an opaque liquid; even if the bubble emitted at ω_p, the water
  would absorb above ~10 GHz.
- For RF noise from electronics + Margulis effect (kHz–10 MHz): broadband
  loop antenna or a near-field probe (e.g. Beehive Electronics 100C
  E-field probes, 100 kHz–100 MHz, capacitive coupling).

**Pickup coils.**
- Hand-wound multi-turn coil (e.g. 100 turns × 1 cm radius) read into a
  high-impedance pre-amp (e.g. Stanford SR560, 100 nV/√Hz @ 10 kHz).
- Output ∝ -dΦ/dt, integrated → magnetic flux. For a 1 µT pulse over
  1 µs in a 1 cm³ active volume: 100 µV signal — borderline detectable.
- For Margulis-style charge-fluctuation measurements: capacitive plates
  near (not in) the cavitation cell + FET preamp.

**FET-based charge amplifiers.** For pC-class signals from any
single-event electrical transient. Reference: Cremat CR-Z110-R5
charge-sensitive preamp, 5 V/pC, ~1 keV electronic noise (silicon-Si
equivalent).

**What the simulator should output.** Predicted V(t) at antenna /
coil from the EM module of Section 5; user-specified position and
geometry; convolve with antenna transfer function (free parameter at
v1; tabulated at v2).

---

## 7.5  Optical spectrometers — flash spectrum

**Reference parts:**
- Ocean Optics HR4000 / QE65 Pro: 200–1100 nm, ~1 nm resolution, USB.
  Not gated — accumulates over many flashes.
- Princeton Instruments PI-Max ICCD: gated, ns time resolution, 200–900 nm,
  used for time-resolved SBSL spectroscopy [FBSP2005].
- Andor Mechelle ME5000 echelle: high-resolution, used for line-emission
  identification.

For the simulator: emit S_λ(t) on a user-specified grid (100 wavelength
bins from 200–1000 nm, 100 time bins from 0 to 10 × τ_collapse).

---

## 7.6  Signal processing approaches

- **Pulse-shape analysis** for PMT: integrate over a 50–500 ns gate to
  separate single-bubble pulses from afterglow / dark counts.
- **Trigger schemes**: one PMT channel can act as the trigger; a second
  delayed channel + TDC measures inter-event timing.
- **Synchronous averaging** for periodic SBSL: phase-lock to the
  acoustic drive; integrate hundreds–thousands of flashes for SNR.
- **High-pass filtering** for cavitation-noise discrimination: SBSL
  collapse pulse is ~MHz-band; low-frequency drive is at 25 kHz; a
  single-pole 1 MHz HPF removes the drive signal in hydrophones.
- **Coincidence**: PMT + hydrophone simultaneously triggered → SL pulse
  is at collapse, drive ringdown is not. Used to reject noise.

---

## 7.7  Noise floors and detection limits (summary)

| Quantity                       | Predicted from physics | Typical noise floor of standard instrument |
|---                             |---                     |---                                          |
| Visible photons per flash       | 10⁴–10⁷               | < 1 photon per 10 ms (PMT dark)             |
| Acoustic pressure at 1 cm       | 10–100 kPa peak       | 0.1 Pa rms (Reson, 25 kHz B)                |
| Magnetic field, 1 cm pickup     | <~ 10⁻⁹ T predicted   | 10⁻¹⁰ T/√Hz (3 mm SQUID); coil-amp ~10⁻⁷    |
| Electric voltage, near-cell    | 1–50 mV (Margulis)    | µV with 1 GΩ FET preamp                      |
| RF, 100 MHz, 1 cm              | uncertain, < 1 µV     | 10 nV/√Hz                                   |

Conclusion: **optical flash, acoustic pulse, and sub-µs voltage
transients are easily detectable**; the magnetic and RF channels are
marginal and require shielded experiments to test claims in [M2000].

---

## Citation tags used in this section

- [Z2003] Ziegler (Stony Brook), single-bubble sonoluminescence apparatus notes (2003).
- [BHL2002] Brenner, Hilgenfeldt, Lohse, *Rev. Mod. Phys.* 74, 425 (2002).
- [GGKL1997] Gompf, Günther, Nick, Pecha, Eisenmenger, *Phys. Rev. Lett.* 79, 1405 (1997).
- [V2000] Versluis, Schmitz, von der Heydt, Lohse, *Science* 289, 2114 (2000).
- [FBSP2005] Flannigan, Suslick, *Nature* 434, 52 (2005).
- [M2000] Margulis, *High Energy Chem.* 38, 135 (2004).
- [HamamatsuPMT] Hamamatsu Photonics, *Photomultiplier Tubes — Basics and Applications*, 4th ed. (2017).
- [ONDA] Onda Corporation, hydrophone datasheets, www.ondacorp.com.
- [Photron] Photron, FASTCAM SA-X2 datasheet.
- [Shimadzu] Shimadzu, HPV-X2 datasheet.

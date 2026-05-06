# Section 9 — Default parameters for first simulation

> Purpose: provide a single, concrete, citation-backed parameter set that
> the coding assistant can adopt as defaults for v1. These numbers
> reproduce the standard "stable air-saturated SBSL" published case
> [BHL2002] and the standard "biological pistol-shrimp event" [V2000].
> Both are well-documented and produce predictable outputs that serve as
> sanity checks.

All values are SI unless noted. References resolve in
`references/bibliography.md`.

---

## 9.1  Liquid medium (water at 20 °C, default)

| Parameter           | Symbol    | Default value      | Source           |
|---                  |---        |---                 |---               |
| Density             | ρ_L       | 998.2 kg/m³        | NIST             |
| Sound speed         | c_L       | 1482 m/s           | NIST             |
| Dynamic viscosity   | μ_L       | 1.002 × 10⁻³ Pa·s   | NIST             |
| Surface tension     | σ         | 0.0728 N/m         | NIST             |
| Vapour pressure (20 °C) | p_v   | 2 339 Pa            | NIST             |
| Tait B              | B         | 3.05 × 10⁸ Pa       | [BR1994]         |
| Tait n              | n         | 7.15                | [BR1994]         |
| Nonlinearity B/A    | β         | 3.5                 | [BR1994]         |
| Acoustic absorption | α         | 0.025 dB/(cm·MHz²)  | [BR1994]         |

(Switch to `glycerin`, `silicone_oil_100cSt`, or `H2SO4_85` from
Section 3.6 / 4.6 tables as alternative defaults.)

## 9.2  Ambient

| Parameter         | Default            | Notes                       |
|---                |---                 |---                          |
| Temperature       | T_∞ = 293.15 K     | Lab ambient                 |
| Hydrostatic pressure | p_∞ = 101 325 Pa | 1 atm                       |
| Gravity           | g = 9.81 m/s²      | Default; only matters for buoyancy in long simulations |

## 9.3  Driving acoustic field — "stable SBSL" case

| Parameter            | Default        | Source              |
|---                   |---             |---                  |
| Drive frequency f    | 26.5 kHz       | [HBL1999, BHL2002]  |
| Drive period T       | 37.7 µs        | derived             |
| Acoustic pressure amplitude P_A | 1.32 × 10⁵ Pa (≈ 1.30 atm) | [HBL1999] |
| Drive waveform       | sine, single-frequency, continuous | [BHL2002] |
| Position             | pressure antinode (chamber center) | [BHL2002] |
| Drive duration (sim) | 5 cycles                       | enough for transient + flash |

This regime produces stable, repeatable single-bubble sonoluminescence:
T_peak ≈ 1.5–2.5 × 10⁴ K, ~10⁵–10⁶ visible photons per flash, period
matching the drive. Excellent v1 validation target.

## 9.4  Bubble seed

| Parameter            | Default        | Source              |
|---                   |---             |---                  |
| Equilibrium radius R₀ | 4.5 µm        | [HBL1999, BHL2002]  |
| Initial Ṙ            | 0              | quiescent IC         |
| Initial gas content  | 99 % Ar, 1 % H₂O vapour | [BHL2002] (rectified-diffusion equilibrium) |
| Initial T_g          | 293.15 K       | thermal equilibrium |
| Polytropic exponent (default) | κ = 1.4 (effective) | [TGGL2000] |
| Specific heat ratio of gas | γ_g = 5/3 (Ar) | NIST |

The simulator's `seed` block should accept either `R0` (from rectified
diffusion equilibrium) or `R_max` (a single-cycle event); the code can
back-solve the other.

## 9.5  Plasma module

| Parameter            | Default                | Notes                |
|---                   |---                     |---                   |
| Ionization model     | `'stewart_pyatt'` Saha + continuum lowering | Section 4.2 |
| Species              | Ar, H₂O, OH, H, O, e⁻  | NIST atomic energies |
| Heat conduction      | Toegel reduced model    | [TGGL2000]           |
| Vapour mass-transfer cap | enabled (Storey–Szeri) | [SS2000]            |
| EOS at high density  | ideal gas + virial corrections; NASG optional | Section 2.3 |

## 9.6  EM module

| Parameter            | Default                  | Notes                |
|---                   |---                       |---                   |
| Bremsstrahlung formula | Bekefi/PlasmaPy        | Section 5.1         |
| Recombination         | Karzas-Latter Gaunt     | Section 5.2         |
| Optical-depth treatment | smooth interpolation between thin and thick | Section 5.4 |
| Spectrometer band    | 200–1000 nm, 100 bins   |                     |
| Detector model       | ideal (no PMT response) for v1; load PMT-impulse for v2 | Section 7 |

## 9.7  Time and space resolution

| Parameter                        | Default        | Reasoning           |
|---                               |---             |---                  |
| Total simulation time            | 4 × T_drive ≈ 150 µs | ~4 cycles, captures multiple flashes |
| Time step (adaptive)             | rtol 1e-8, atol 1e-12 | Section 2.6      |
| Output time grid                 | 10 000 log-spaced points | dense near collapse |
| Spatial sampling (1-D field)    | 64 points per wavelength | k-Wave default |
| Wavelength bins (spectrum)       | 100 (200–1000 nm)      |                     |

## 9.8  Pistol-shrimp benchmark case (alternative default)

For users comparing to biological cavitation:

| Parameter                | Default value       | Source        |
|---                       |---                  |---            |
| Liquid                   | seawater (35 ‰)     | adjust ρ_L = 1025, c_L = 1530, σ = 0.075, μ = 0.00108; properties from [LK1986] |
| Ambient                  | 1 atm, 293 K        |               |
| Drive type               | impulsive jet (Bernoulli pulse) | [V2000]   |
| Effective P_A            | 3 × 10⁵ Pa          | [V2000]      |
| R_max                    | 3.5 mm              | [V2000]      |
| Bubble lifetime          | 300 µs              | [V2000]      |
| Initial gas content      | air-saturated seawater (≈ 78 % N₂, 21 % O₂, 0.93 % Ar) | NIST |
| Expected outputs         | T_peak ≈ 5 000 K, ~5 × 10⁴ photons | [L2001] |

This case is the *upper end* of bubble size and the *lower end* of
operating frequency the simulator should handle cleanly.

## 9.9  Expected output orders of magnitude (sanity ranges)

For the §9.3 "stable SBSL" defaults the simulator should produce, within
~30 %:

| Quantity                       | Expected order of magnitude                |
|---                             |---                                          |
| R_max                          | 30–50 µm                                    |
| R_min                          | 0.5–0.8 µm                                  |
| Wall Mach at collapse          | 0.5–1.5                                     |
| Peak gas T                     | 1.5 × 10⁴ – 4 × 10⁴ K                       |
| Peak n_e                       | 10²⁵ – 10²⁷ m⁻³                            |
| Peak ionization fraction       | 1 % – 30 %                                  |
| Plasma frequency at peak       | 10¹³ – 10¹⁵ rad/s                          |
| Debye length at peak           | 10⁻¹¹ – 10⁻¹⁰ m                            |
| Optical flash duration         | 30–250 ps                                   |
| Visible photons per flash, **4π emitted** | 10⁶ – 10⁹ (depends strongly on T_peak via T⁴; widely quoted "10⁵ – 10⁷" numbers in the SBSL literature are typically *detected* counts after PMT QE × geometric collection efficiency, ~10⁻³–10⁻¹ of emitted) |
| Acoustic pulse peak (1 cm away) | 10–100 kPa                                  |
| Acoustic pulse FWHM            | 10–100 ns                                   |

Outputs *outside* these bands should be flagged as "off the published
parameter envelope" by the simulator's validator.

## 9.10  Quick-start parameter dictionary

```python
DEFAULT_PARAMS = {
    'liquid': {
        'name': 'water',
        'rho': 998.2,           # kg/m^3
        'c': 1482.0,            # m/s
        'mu': 1.002e-3,         # Pa·s
        'sigma': 7.28e-2,       # N/m
        'p_v': 2339.0,          # Pa
        'B': 3.05e8, 'n_tait': 7.15,
        'beta': 3.5,
    },
    'ambient': {
        'p_inf': 101325.0,      # Pa
        'T_inf': 293.15,        # K
    },
    'drive': {
        'kind': 'sinusoid',
        'f_Hz': 26.5e3,
        'P_A': 1.32e5,          # Pa
        'phase': 0.0,
    },
    'bubble': {
        'R0': 4.5e-6,           # m
        'gas': {'Ar': 0.99, 'H2O': 0.01},
        'T0': 293.15,           # K
        'gamma_g': 1.667,
        'kappa': 1.4,
    },
    'physics': {
        'bubble_eq': 'keller_miksis',
        'thermal_model': 'toegel',
        'vapour_cap': True,
        'ionization': 'stewart_pyatt',
        'em_model': 'thermal_bremsstrahlung+recombination',
    },
    'numerics': {
        't_total': 1.5e-4,      # s
        'rtol': 1e-8, 'atol': 1e-12,
        'n_output': 10000,
        'spectrum_lambda_nm': (200, 1000, 100),
    },
}
```

This dict is the default v1 input. Sweeping parameters should mutate
copies of this baseline.

---

## Citation tags used in this section

- [BR1994] Brennen, *Cavitation and Bubble Dynamics*, Oxford UP (1995).
- [HBL1999] Hilgenfeldt, Grossmann, Lohse, *Phys. Fluids* 11, 1318 (1999).
- [BHL2002] Brenner, Hilgenfeldt, Lohse, *Rev. Mod. Phys.* 74, 425 (2002).
- [TGGL2000] Toegel et al., *Phys. Rev. Lett.* 85, 3165 (2000).
- [SS2000] Storey, Szeri, *Proc. R. Soc. A* 456, 1685 (2000).
- [V2000] Versluis et al., *Science* 289, 2114 (2000).
- [L2001] Lohse et al., *Nature* 413, 477 (2001).
- [LK1986] CRC Handbook of Chemistry and Physics.
- [NIST] NIST Webbook, https://webbook.nist.gov.

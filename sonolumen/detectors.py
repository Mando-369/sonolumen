"""Synthetic detector signals.

§7 of the dossier:
  §7.1  PMT (photomultiplier) — optical flash
  §7.2  Hydrophone — acoustic emission via far-field expansion
  §7.4  Pickup-coil and capacitive electrode — Margulis transient
        (parametric, off by default)

v1 detector models are deliberately simple — convolutions with full
impulse responses land in v2. Each function emits a SI voltage trace
suitable for direct comparison with an oscilloscope record.
"""

from __future__ import annotations

import math

import numpy as np

from sonolumen._constants import C_LIGHT, EPS0, H_PLANCK


# ---------------------------------------------------------------------------
# §7.1  PMT
# ---------------------------------------------------------------------------
def pmt_signal(
    t: np.ndarray,
    R: np.ndarray,
    spectrum_t_lambda: np.ndarray,
    lambda_grid_m: np.ndarray,
    distance: float = 0.05,           # 5 cm port standoff
    aperture_radius: float = 5e-3,    # 5 mm photocathode
    QE_peak: float = 0.25,            # Hamamatsu R7400U @ 420 nm
    gain: float = 1e6,
    R_load: float = 50.0,
) -> dict:
    """Predicted photoelectron rate and PMT voltage trace.

    The PMT sees a fraction of 4π emission given by the geometric solid
    angle of its photocathode. Convolution with the impulse response is
    a Phase E refinement; v1 returns the *idealised* output.

    Returns dict with keys:
      'photon_rate_at_PMT' (s⁻¹)
      'photoelectron_rate' (s⁻¹)
      'V_PMT' (V) — instantaneous output voltage assuming ideal preamp
      'photons_collected' — integrated total
    """
    nu = C_LIGHT / lambda_grid_m
    # Solid angle subtended by the PMT cathode at `distance`
    omega = math.pi * aperture_radius ** 2 / max(distance ** 2, 1e-12)

    # spectrum is W m⁻² Hz⁻¹ sr⁻¹ at the bubble surface; far-field flux is
    # 4π R² × S_ν / (distance²·4π) per sr — i.e. just S_ν × (R/distance)².
    # Photons/s/Hz/sr arriving at the detector area:
    #   ṅ_ν = S_ν / (h ν)
    # Total photons/s/Hz over the cathode area:
    #   integrated over cathode solid angle = S_ν / (h ν) × A_cathode × 4π R² / (4π distance²)
    # Simplification: emission is isotropic over 4π, photon flux at
    # detector ≈ N_emitted / (4π distance²) × A_cathode.

    # Per-frequency emission rate (photons/s/Hz) over 4π:
    nu_arr = nu[None, :]
    photon_em_rate_per_Hz = (4.0 * math.pi) ** 2 * (R ** 2)[:, None] * spectrum_t_lambda / (H_PLANCK * nu_arr)
    # Integrate over band wavelengths to get photons/s
    order = np.argsort(nu)
    photon_em_rate = np.trapezoid(photon_em_rate_per_Hz[:, order], x=nu[order], axis=1)

    geom_factor = math.pi * aperture_radius ** 2 / (4.0 * math.pi * distance ** 2)
    photon_rate_PMT = photon_em_rate * geom_factor

    # Apply quantum efficiency (constant peak QE here; wavelength-dependent
    # QE is a Phase E refinement)
    pe_rate = photon_rate_PMT * QE_peak
    # Voltage at preamp output: V = G × e × ṅ × R_load (single-electron pulse smoothed)
    e_charge = 1.602176634e-19
    V_PMT = gain * e_charge * pe_rate * R_load
    photons_collected = float(np.trapezoid(photon_rate_PMT, x=t))
    return {
        "photon_rate_at_PMT": photon_rate_PMT,
        "photoelectron_rate": pe_rate,
        "V_PMT": V_PMT,
        "photons_collected": photons_collected,
        "geom_factor": geom_factor,
        "QE": QE_peak,
        "gain": gain,
    }


# ---------------------------------------------------------------------------
# §7.2  Hydrophone — far-field acoustic emission (E24)
# ---------------------------------------------------------------------------
def hydrophone_signal(
    t: np.ndarray, R: np.ndarray, Rdot: np.ndarray,
    rho_L: float, c_L: float,
    distance: float = 0.01,
    sensitivity_V_per_Pa: float = 50e-6,
) -> dict:
    """Predicted V(t) at a hydrophone located at `distance` from the bubble.

    Far-field bubble radiation: p_rad(r, t) = ρ_L / (4π r) × V̈_b(t − r/c).
    V̈_b = 8π R Ṙ² + 4π R² R̈. R̈ is recovered via central differences of Ṙ.
    """
    if len(t) < 3:
        return {"p_rad": np.zeros_like(t), "V": np.zeros_like(t)}
    Rddot = np.gradient(Rdot, t)
    Vddot = 8.0 * math.pi * R * Rdot ** 2 + 4.0 * math.pi * R ** 2 * Rddot
    # Retarded time shift is small; for v1 ignore (simulation t is short).
    p_rad = rho_L / (4.0 * math.pi * distance) * Vddot
    V = p_rad * sensitivity_V_per_Pa
    return {"p_rad": p_rad, "V": V}


# ---------------------------------------------------------------------------
# §7.4  Pickup coil — Margulis-style parametric transient
# ---------------------------------------------------------------------------
def pickup_coil_signal(
    t: np.ndarray, R: np.ndarray, Rdot: np.ndarray,
    distance: float = 0.01,
    Q_b: float = 1e-11,
    pulse_duration_s: float = 1e-7,
    enable: bool = False,
) -> dict:
    """Optional parametric Margulis voltage pulse (E29). Off by default.

    Per §10.6, the underlying mechanism is contested. v1 emits a
    rectangular pulse triggered around the moment of R_min, with charge
    Q_b ∈ [10⁻¹², 10⁻¹⁰] C as a free parameter.
    """
    if not enable:
        return {"V": np.zeros_like(t)}
    i_min = int(np.argmin(R))
    t_min = float(t[i_min])
    V_peak = Q_b / (4.0 * math.pi * EPS0 * max(distance, 1e-6))
    V = np.where(np.abs(t - t_min) < 0.5 * pulse_duration_s, V_peak, 0.0)
    return {"V": V}

"""Electromagnetic emission from the bubble plasma.

§5 of the dossier. Implements:
  E17  thermal bremsstrahlung emissivity (free–free)
  E19  recombination emissivity (free–bound)
  E20  Planck function
  E21  Stefan–Boltzmann
  E22  free–free absorption coefficient
  E23  optically thin↔thick interpolation S_ν^escape = (1 − e^{−τ}) B_ν
  E30  visible photon yield

Units: SI throughout. Spectral emissivity j_ν is W m⁻³ Hz⁻¹ sr⁻¹.

§9.4 / §10.1 advice: the spectrum is emitted; T_peak / n_e_peak / photon
yield are *diagnosed* from the runner, never set as inputs.
"""

from __future__ import annotations

import math

import numpy as np

from cavplasma._constants import (
    C_LIGHT, E_CHARGE, EPS0, H_PLANCK, K_B, M_ELECTRON, RY_J, SIGMA_SB,
)


# Frequency-domain constants pre-computed for performance.
# j_ν^ff = C_BREMS × √(2 / (3π m_e k_B T)) × n_e n_i Z² ḡ_ff exp(-hν/kT)
# with the (1/(4π)) factor folded in (so the result is per steradian).
_C_BREMS = (
    32.0 * math.pi * math.pi * E_CHARGE ** 6
    / (3.0 * M_ELECTRON * C_LIGHT ** 3 * (4.0 * math.pi * EPS0) ** 3)
) / (4.0 * math.pi)

# Coefficient for the Λ_ff total cooling rate (E18). Comes out close to
# the often-quoted 1.4e-40 prefactor with Z² folded in by the caller.
_LAMBDA_FF_COEFF = 1.4e-40


def planck_function(nu: np.ndarray | float, T: float) -> np.ndarray | float:
    """B_ν(T) (W m⁻² Hz⁻¹ sr⁻¹). E20.

    Handles both Wien (x ≫ 1) and Rayleigh–Jeans (x ≪ 1) limits without
    intermediate overflow.
    """
    if T <= 0.0:
        return np.zeros_like(nu) if isinstance(nu, np.ndarray) else 0.0
    nu_arr = np.asarray(nu, dtype=float)
    x = H_PLANCK * nu_arr / (K_B * T)
    # Wien limit: B_ν → 2 h ν³ / c² × exp(-x) for x > 50 (saturates expm1)
    # Rayleigh-Jeans limit: B_ν → 2 ν² k_B T / c² for x < 1e-4
    val = np.zeros_like(nu_arr)
    rj = x < 1e-4
    wien = x > 50.0
    mid = ~rj & ~wien
    if np.any(mid):
        x_mid = x[mid] if isinstance(x, np.ndarray) else x
        val_mid = 2.0 * H_PLANCK * nu_arr[mid] ** 3 / (C_LIGHT ** 2 * np.expm1(x_mid))
        val[mid] = val_mid
    if np.any(rj):
        val[rj] = 2.0 * nu_arr[rj] ** 2 * K_B * T / (C_LIGHT ** 2)
    if np.any(wien):
        val[wien] = (2.0 * H_PLANCK * nu_arr[wien] ** 3 / C_LIGHT ** 2) * np.exp(-x[wien])
    if not isinstance(nu, np.ndarray):
        return float(val)
    return val


def stefan_boltzmann_power(T: float, R: float) -> float:
    """P_BB(T,R) = 4π R² σ_SB T⁴. E21."""
    return 4.0 * math.pi * R * R * SIGMA_SB * T ** 4


def gaunt_factor_ff(nu: float, T: float) -> float:
    """Free–free Gaunt factor ḡ_ff. v1 returns 1.0 (Itoh 2002 fit is a
    Phase E refinement, < 1 % effect over the SBSL band)."""
    return 1.0


def bremsstrahlung_emissivity(
    T: float, n_e: float, n_i: float, Z: float, nu: np.ndarray | float,
) -> np.ndarray | float:
    """j_ν^ff (W m⁻³ Hz⁻¹ sr⁻¹) for thermal bremsstrahlung. E17."""
    if T <= 0.0 or n_e <= 0.0 or n_i <= 0.0:
        return np.zeros_like(nu) if isinstance(nu, np.ndarray) else 0.0
    pref = _C_BREMS * math.sqrt(2.0 / (3.0 * math.pi * M_ELECTRON * K_B * T))
    nu_arr = np.asarray(nu, dtype=float)
    g_ff = 1.0
    x = H_PLANCK * nu_arr / (K_B * T)
    safe = np.where(x > 700.0, 700.0, x)
    expo = np.exp(-safe)
    expo = np.where(x > 700.0, 0.0, expo)
    val = pref * n_e * n_i * (Z * Z) * g_ff * expo
    if not isinstance(nu, np.ndarray):
        return float(val)
    return val


def bremsstrahlung_total_cooling(T: float, n_e: float, n_i: float, Z: float) -> float:
    """Λ_ff (W m⁻³). E18."""
    if T <= 0.0:
        return 0.0
    return _LAMBDA_FF_COEFF * math.sqrt(T) * n_e * n_i * (Z * Z)


def recombination_emissivity(
    T: float, n_e: float, n_i: float, Z: float, nu: np.ndarray | float,
    n_min: int = 1, n_max: int = 4,
) -> np.ndarray | float:
    """j_ν^fb (W m⁻³ Hz⁻¹ sr⁻¹). E19, summed over recombining levels n.

    The pre-factor is identical to bremsstrahlung up to the Z² Ry / (k_B T)
    enhancement and the level-dependent exponential.
    """
    if T <= 0.0 or n_e <= 0.0 or n_i <= 0.0:
        return np.zeros_like(nu) if isinstance(nu, np.ndarray) else 0.0
    nu_arr = np.asarray(nu, dtype=float)
    pref = _C_BREMS * math.sqrt(2.0 / (3.0 * math.pi * M_ELECTRON * K_B * T))
    boltz_factor = (Z * Z * RY_J) / (K_B * T)
    total = np.zeros_like(nu_arr)
    for n in range(n_min, n_max + 1):
        # Energy threshold for recombination into level n
        E_n = (Z * Z * RY_J) / (n * n)
        # Above threshold only; below, spectral emissivity → 0 in this term
        valid = nu_arr * H_PLANCK >= E_n
        x = (H_PLANCK * nu_arr - E_n) / (K_B * T)
        safe = np.where(x > 700.0, 700.0, x)
        expo = np.exp(-safe)
        expo = np.where(x > 700.0, 0.0, expo)
        gn = 1.0  # Gaunt factor for bound state n; v1 takes 1
        weight = gn / (n ** 3)
        total = total + weight * np.where(valid, expo, 0.0)
    val = pref * n_e * n_i * boltz_factor * total
    if not isinstance(nu, np.ndarray):
        return float(val)
    return val


def free_free_absorption(
    T: float, n_e: float, n_i: float, Z: float, nu: np.ndarray | float,
) -> np.ndarray | float:
    """κ_ν^ff (m⁻¹) by Kirchhoff: κ = j_ν / B_ν. E22."""
    if T <= 0.0 or n_e <= 0.0:
        return np.zeros_like(nu) if isinstance(nu, np.ndarray) else 0.0
    j = bremsstrahlung_emissivity(T, n_e, n_i, Z, nu)
    B = planck_function(nu, T)
    if isinstance(B, np.ndarray):
        kappa = np.where(B > 0.0, j / B, 0.0)
        return kappa
    return j / B if B > 0.0 else 0.0


def optical_depth(kappa: np.ndarray | float, R: float) -> np.ndarray | float:
    """τ_ν = κ_ν · R. E23."""
    return kappa * R


def escape_factor(tau: np.ndarray | float) -> np.ndarray | float:
    """(1 − e^{−τ}) — smoothly interpolates between thin and thick. E23."""
    if isinstance(tau, np.ndarray):
        # Use expm1 for accuracy at small tau
        return -np.expm1(-tau)
    return -math.expm1(-tau)


def escaping_specific_intensity(
    T: float, n_e: float, n_i: float, Z: float, R: float, nu: np.ndarray,
    em_model: str = "auto",
) -> np.ndarray:
    """S_ν^escape (W m⁻² Hz⁻¹ sr⁻¹). E23."""
    if em_model == "thermal_bremsstrahlung_only":
        return bremsstrahlung_emissivity(T, n_e, n_i, Z, nu) * R
    if em_model == "bremsstrahlung+recombination":
        j_ff = bremsstrahlung_emissivity(T, n_e, n_i, Z, nu)
        j_fb = recombination_emissivity(T, n_e, n_i, Z, nu)
        return (j_ff + j_fb) * R
    if em_model == "optically_thick_blackbody":
        B = planck_function(nu, T)
        return B
    # 'auto': smooth interpolation via τ_ν
    kappa = free_free_absorption(T, n_e, n_i, Z, nu)
    tau = optical_depth(kappa, R)
    B = planck_function(nu, T)
    return escape_factor(tau) * B


def emit_spectrum(
    T_arr: np.ndarray,
    n_e_arr: np.ndarray,
    n_i_arr: np.ndarray,
    Z: float,
    R_arr: np.ndarray,
    lambda_grid_m: np.ndarray,
    em_model: str = "auto",
) -> np.ndarray:
    """Compute S_ν^escape on (t, λ) grid. Returns shape (n_t, n_lambda)."""
    nu_grid = C_LIGHT / lambda_grid_m
    out = np.zeros((len(T_arr), len(lambda_grid_m)))
    for i in range(len(T_arr)):
        out[i] = escaping_specific_intensity(
            float(T_arr[i]), float(n_e_arr[i]), float(n_i_arr[i]),
            Z, float(R_arr[i]), nu_grid, em_model=em_model,
        )
    return out


def photon_yield(
    t_arr: np.ndarray, R_arr: np.ndarray,
    spectrum_t_lambda: np.ndarray, lambda_grid_m: np.ndarray,
    band_nm: tuple[float, float] = (400.0, 700.0),
) -> float:
    """Total photons emitted in the wavelength band over the integration
    interval. E30, with luminosity = 4π × A_bubble × S_ν.

    spectrum_t_lambda: shape (n_t, n_lambda), in W m⁻² Hz⁻¹ sr⁻¹.
    """
    band_m = (band_nm[0] * 1e-9, band_nm[1] * 1e-9)
    in_band = (lambda_grid_m >= band_m[0]) & (lambda_grid_m <= band_m[1])
    if not np.any(in_band):
        return 0.0
    sub_lam = lambda_grid_m[in_band]
    nu = C_LIGHT / sub_lam
    sub_S = spectrum_t_lambda[:, in_band]   # W/m²/Hz/sr

    # photon energy h ν, photon emission rate per unit area per Hz per sr:
    # n_dot_ν = S_ν / (h ν).   Total photons per second over 4π and over surface:
    #   N_dot(t) = ∫dν 4π S_ν · 4π R² / (h ν)
    coef = (4.0 * math.pi) ** 2
    photons_per_sec_per_Hz = sub_S / (H_PLANCK * nu[None, :])
    photon_rate = coef * (R_arr ** 2)[:, None] * photons_per_sec_per_Hz
    # Integrate over ν then over t. Use dν between successive λ bins.
    # Note ν decreases as λ increases; flip to ascending ν before trapz.
    order = np.argsort(nu)
    nu_sorted = nu[order]
    photon_rate_sorted = photon_rate[:, order]
    photons_per_sec = np.trapezoid(photon_rate_sorted, x=nu_sorted, axis=1)
    return float(np.trapezoid(photons_per_sec, x=t_arr))

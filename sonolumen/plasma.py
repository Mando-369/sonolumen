"""Plasma diagnostics: Saha (E12), Stewart–Pyatt (E13), and the
closed-form ω_p / λ_D / Γ / λ_ei (E14–E16, E28).

§4.2 of the dossier. Single-stage, single-species ionization is the v1
model; mixtures are handled by per-species independent Saha then summed
to give a total n_e (consistent only when species ionizations don't
strongly compete — fine for the 99 % Ar / 1 % H₂O canonical case).

§10.4 advice: ionization model is selectable, default 'stewart_pyatt'.
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np

from sonolumen._constants import (
    E_CHARGE, EPS0, EV_J, HBAR, K_B, M_ELECTRON,
)


# First-ionization energies (eV) and ionic-to-atomic statistical weight ratios.
# Sources: NIST atomic spectra database; values per §4.2 / §9.5.
_IONIZATION_DATA: dict[str, tuple[float, float]] = {
    # species: (E_i_eV, 2 g_i / g_a)
    "Ar":  (15.7596, 6.0),
    "Xe":  (12.1298, 6.0),
    "He":  (24.5874, 4.0),
    "Ne":  (21.5645, 6.0),
    "H":    (13.5984, 1.0),
    "H2O":  (12.6206, 2.0),     # H2O → H2O+ (approx degeneracy)
    "N2":   (15.5810, 2.0),
    "O2":   (12.0697, 4.0),
    "Air":  (15.0,    2.0),     # blended
    "OH":   (13.0,    2.0),
    "O":    (13.6181, 9.0),
}


IonizationModel = Literal["ideal_saha", "stewart_pyatt", "tabulated"]


def saha_constant(T: float, species: str) -> float:
    """K(T) = (2 g_i / g_a) (m_e k_B T / (2π ℏ²))^{3/2} exp(-E_i / k_B T)."""
    E_i_J, weight_ratio = _ionization(species)
    if T <= 0.0:
        return 0.0
    thermal_de_broglie_inv = (M_ELECTRON * K_B * T / (2.0 * math.pi * HBAR * HBAR)) ** 1.5
    return weight_ratio * thermal_de_broglie_inv * math.exp(-E_i_J / (K_B * T))


def saha_constant_with_lowering(T: float, species: str, delta_E_J: float) -> float:
    E_i_J, weight_ratio = _ionization(species)
    E_eff = max(0.0, E_i_J - delta_E_J)
    thermal_de_broglie_inv = (M_ELECTRON * K_B * T / (2.0 * math.pi * HBAR * HBAR)) ** 1.5
    return weight_ratio * thermal_de_broglie_inv * math.exp(-E_eff / (K_B * T))


def _ionization(species: str) -> tuple[float, float]:
    if species not in _IONIZATION_DATA:
        # Fall back to "Air" defaults; warn via printing nothing — the runner
        # is responsible for reporting unknown-species warnings.
        species = "Air"
    E_eV, weight_ratio = _IONIZATION_DATA[species]
    return E_eV * EV_J, weight_ratio


def saha_xe_single(K: float, n_total: float) -> float:
    """Solve x²/(1-x) = K/n_total for ionization fraction x ∈ [0, 1]."""
    if n_total <= 0.0:
        return 0.0
    a = K / n_total
    # x² + a x - a = 0 → x = (-a + √(a² + 4a)) / 2
    disc = a * a + 4.0 * a
    if disc < 0.0:
        return 0.0
    x = (-a + math.sqrt(disc)) / 2.0
    return max(0.0, min(1.0, x))


def stewart_pyatt_lowering(T: float, n_e: float) -> float:
    """ΔE_cont ≈ e² / (4π ε₀ λ_D), with λ_D from the Debye formula.

    A simplified Stewart–Pyatt closure; full SP includes ion sphere
    corrections that we elide for v1 per §10.4 advice.
    """
    if n_e <= 0.0 or T <= 0.0:
        return 0.0
    lam_D = debye_length(T, n_e)
    return E_CHARGE * E_CHARGE / (4.0 * math.pi * EPS0 * max(lam_D, 1e-15))


def solve_ionization(
    T: float, n_total: float,
    gas_composition: dict,
    model: IonizationModel = "stewart_pyatt",
    tol: float = 1e-5, max_iter: int = 50,
) -> dict:
    """Solve for n_e and per-species ionization fractions at (T, n_total).

    Returns a dict with keys 'n_e', 'x_e_total' (electrons per gas particle),
    and 'x_e_per_species' (mole-fraction-weighted contributions).
    """
    if T <= 0.0 or n_total <= 0.0:
        return {"n_e": 0.0, "x_e_total": 0.0, "x_e_per_species": {s: 0.0 for s in gas_composition}}

    total_mole = sum(gas_composition.values()) or 1.0
    species_fractions = {s: gas_composition[s] / total_mole for s in gas_composition}
    species_n = {s: species_fractions[s] * n_total for s in species_fractions}

    n_e = 0.0
    for _ in range(max_iter):
        if model == "ideal_saha":
            delta_E = 0.0
        elif model == "stewart_pyatt":
            delta_E = stewart_pyatt_lowering(T, max(n_e, 1.0))
        elif model == "tabulated":
            raise NotImplementedError(
                "ionization_model='tabulated' is Phase E (deferred). "
                "Use 'ideal_saha' or 'stewart_pyatt'."
            )
        else:
            raise ValueError(f"unknown ionization model {model!r}")

        new_xe_per_species = {}
        new_n_e = 0.0
        for species, n_s in species_n.items():
            K = saha_constant_with_lowering(T, species, delta_E)
            xe = saha_xe_single(K, n_s)
            new_xe_per_species[species] = xe
            new_n_e += xe * n_s

        if abs(new_n_e - n_e) <= tol * max(new_n_e, 1.0):
            n_e = new_n_e
            x_e_per_species = new_xe_per_species
            break
        n_e = new_n_e
        x_e_per_species = new_xe_per_species
    else:
        x_e_per_species = new_xe_per_species

    x_e_total = n_e / max(n_total, 1.0)
    return {"n_e": n_e, "x_e_total": x_e_total, "x_e_per_species": x_e_per_species}


# ---------------------------------------------------------------------------
# Closed-form plasma diagnostics
# ---------------------------------------------------------------------------
def plasma_frequency(n_e: float) -> float:
    """ω_p = √(n_e e² / (ε₀ m_e)). E14."""
    if n_e <= 0.0:
        return 0.0
    return math.sqrt(n_e * E_CHARGE * E_CHARGE / (EPS0 * M_ELECTRON))


def debye_length(T: float, n_e: float) -> float:
    """λ_D = √(ε₀ k_B T / (n_e e²)). E15."""
    if n_e <= 0.0 or T <= 0.0:
        return 1e10  # effectively infinite
    return math.sqrt(EPS0 * K_B * T / (n_e * E_CHARGE * E_CHARGE))


def coupling_parameter(T: float, n_e: float) -> float:
    """Γ = e²/(4π ε₀ a_WS) / (k_B T) with a_WS = (3/(4π n_e))^{1/3}. E16."""
    if n_e <= 0.0 or T <= 0.0:
        return 0.0
    a_WS = (3.0 / (4.0 * math.pi * n_e)) ** (1.0 / 3.0)
    return E_CHARGE * E_CHARGE / (4.0 * math.pi * EPS0 * a_WS) / (K_B * T)


def electron_ion_mfp(T: float, n_e: float, ln_Lambda: float = 8.0) -> float:
    """λ_ei ≈ (4π ε₀)² (k_B T)² / (n_e e⁴ ln Λ). E28."""
    if n_e <= 0.0 or T <= 0.0:
        return 1e10
    num = (4.0 * math.pi * EPS0) ** 2 * (K_B * T) ** 2
    den = n_e * E_CHARGE ** 4 * ln_Lambda
    return num / den


def plasma_diagnostics(T: float, n_e: float) -> dict:
    """Return ω_p, λ_D, Γ, λ_ei for a given (T, n_e)."""
    return {
        "omega_p": plasma_frequency(n_e),
        "lambda_D": debye_length(T, n_e),
        "Gamma": coupling_parameter(T, n_e),
        "lambda_ei": electron_ion_mfp(T, n_e),
    }


# ---------------------------------------------------------------------------
# Vectorised helpers — used by the runner over time-series traces
# ---------------------------------------------------------------------------
def saha_trace(
    T_arr: np.ndarray, n_total_arr: np.ndarray,
    gas_composition: dict,
    model: IonizationModel = "stewart_pyatt",
) -> dict:
    """Apply `solve_ionization` element-wise and return a stacked dict."""
    n_e = np.empty_like(T_arr, dtype=float)
    x_e = np.empty_like(T_arr, dtype=float)
    for i, (T, nt) in enumerate(zip(T_arr, n_total_arr, strict=True)):
        sol = solve_ionization(float(T), float(nt), gas_composition, model)
        n_e[i] = sol["n_e"]
        x_e[i] = sol["x_e_total"]
    return {"n_e": n_e, "x_e": x_e}

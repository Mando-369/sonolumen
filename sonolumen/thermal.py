"""Thermal modelling inside the bubble.

§2.4 / §4.1 of the dossier. Phase B implements:
  * `polytropic_temperature(R)`: closed-form T(R) = T0 (R0/R)^{3(κ-1)} (E11)
  * `toegel_T_dot`: Ṫ_g from the Toegel reduced model (E10) — heat
    conduction loss + p dV work
  * `vapour_cap`: cap T_g via Storey–Szeri-style endothermic sink (§2.4.2,
    §4.3); Phase B implementation is parametric — caps Ṫ_g once water
    vapour begins to dissociate (~5000 K).

Mass transfer of water vapour itself is deferred to Phase E; v1 vapour
cap is an effective-energy-sink approximation.
"""

from __future__ import annotations

import math
from typing import Callable

from sonolumen._constants import K_B
from sonolumen.config import (
    AmbientConditions,
    BubbleSeed,
    LiquidProperties,
    PhysicsOptions,
)


# Approximate gas thermal conductivities at 300 K, W/(m·K).
# Used as constants in v1; T-dependence (k ∝ T^0.7) is a Phase E refinement.
_GAS_K_300K = {
    "Ar": 0.0177, "Xe": 0.00565, "He": 0.1513, "Ne": 0.0491,
    "H2O": 0.0193, "N2": 0.0259, "O2": 0.0263, "Air": 0.0257,
    "H": 0.0177, "OH": 0.025, "H2": 0.180,
}


def _mixture_k(gas_composition: dict) -> float:
    """Mole-fraction-weighted thermal conductivity at ~300 K."""
    if not gas_composition:
        return _GAS_K_300K["Ar"]
    total = sum(gas_composition.values()) or 1.0
    return sum(
        (frac / total) * _GAS_K_300K.get(species, _GAS_K_300K["Ar"])
        for species, frac in gas_composition.items()
    )


def _mixture_chi(gas_composition: dict, p_g: float, T: float) -> float:
    """Thermal diffusivity χ = k/(ρ c_v). Reduced ideal-gas form."""
    k_g = _mixture_k(gas_composition)
    # Density of ideal gas: ρ = p × M / (R_g T). For mole-fraction-weighted
    # mean molar mass, use a crude default M ≈ 0.040 kg/mol (Ar).
    M = _mean_molar_mass(gas_composition)
    R_gas = 8.314462618
    if T <= 0.0 or p_g <= 0.0:
        return 1e-5  # safe small value
    rho = p_g * M / (R_gas * T)
    # Specific heat at constant volume per kg: c_v ≈ R_g/(M(γ-1)). Use γ=5/3
    # as a proxy at the integration step level (true γ is in BubbleSeed).
    gamma = 5.0 / 3.0
    c_v = R_gas / (M * (gamma - 1.0))
    return k_g / (rho * c_v)


_MOLAR_MASS = {  # kg/mol
    "Ar": 0.0399, "Xe": 0.1313, "He": 0.0040, "Ne": 0.0202,
    "H2O": 0.0180, "N2": 0.0280, "O2": 0.0320, "Air": 0.0289,
    "H": 0.001, "O": 0.016, "OH": 0.017, "H2": 0.002,
}


def _mean_molar_mass(gas_composition: dict) -> float:
    if not gas_composition:
        return 0.0399
    total = sum(gas_composition.values()) or 1.0
    return sum(
        (frac / total) * _MOLAR_MASS.get(species, 0.0399)
        for species, frac in gas_composition.items()
    )


# ---------------------------------------------------------------------------
# Polytropic (no extra ODE state)  —  E11
# ---------------------------------------------------------------------------
def polytropic_temperature(R: float, seed: BubbleSeed) -> float:
    """T(R) for a polytropic process. Equation E11."""
    return seed.T0 * (seed.R0 / R) ** (3.0 * (seed.kappa - 1.0))


# ---------------------------------------------------------------------------
# Toegel reduced thermal ODE  —  E10
# ---------------------------------------------------------------------------
def toegel_n_total(seed: BubbleSeed, ambient: AmbientConditions, liquid: LiquidProperties) -> float:
    """Total number of gas molecules in the bubble at t=0 (assumed conserved).

    Honours `seed.p_gas_initial` so impulsive/non-equilibrium ICs (vapor
    cavities) carry the right molecule count.
    """
    if seed.p_gas_initial is not None:
        p_g0 = float(seed.p_gas_initial)
    else:
        p_g0 = ambient.p_inf + 2.0 * liquid.sigma / seed.R0 - liquid.p_v
    V0 = (4.0 / 3.0) * math.pi * seed.R0 ** 3
    return p_g0 * V0 / (K_B * seed.T0)


def make_toegel_T_dot(
    seed: BubbleSeed,
    liquid: LiquidProperties,
    ambient: AmbientConditions,
    physics: PhysicsOptions,
) -> Callable[[float, float, float, float, float], float]:
    """Build T_g_dot(R, Rdot, T_g, p_g, t) per the Toegel reduced model (E10).

    Returns a closure suitable for embedding in a coupled (R, Ṙ, T_g) ODE.
    """
    N_total = toegel_n_total(seed, ambient, liquid)
    cv_total_div_N = K_B / (seed.gamma_g - 1.0)   # c_v_total = N × this
    k_g = _mixture_k(seed.gas_composition)
    T_wall = ambient.T_inf
    gas_comp = seed.gas_composition
    do_vap_cap = physics.vapour_cap

    # Storey–Szeri water-vapour cap: scope to H2O fraction only. O2/N2
    # dissociation is on the same temperature scale but kinetically slower
    # over a single ~µs collapse and is the dominant uncertainty in §10.4.
    # Phase E may add a per-species rate-limited model.
    total_mole = sum(gas_comp.values()) or 1.0
    f_dissociable = gas_comp.get("H2O", 0.0) / total_mole

    def Tdot(R: float, Rdot: float, T_g: float, p_g: float, t: float) -> float:
        # diffusion length (E10)
        chi_g = _mixture_chi(gas_comp, p_g, T_g)
        if abs(Rdot) > 0.0:
            l_diff = math.sqrt(R * chi_g / abs(Rdot))
        else:
            l_diff = R / math.pi
        l_th = min(l_diff, R / math.pi)

        # Toegel reduced thermal ODE: 4/3 π R³ c_v Ṫ = -p_g 4π R² Ṙ - 4π R² k_g (T - T_wall)/l_th
        # Divide both sides by N_total × c_v_div_N to extract Ṫ:
        denom = N_total * cv_total_div_N
        if denom <= 0.0:
            return 0.0
        pdv_term = -p_g * 4.0 * math.pi * R * R * Rdot
        cond_term = -4.0 * math.pi * R * R * k_g * (T_g - T_wall) / max(l_th, 1e-15)
        Q = pdv_term + cond_term

        # Vapour cap: §4.3 — endothermic dissociation between ~5 000–11 000 K
        # caps further heating by sinking energy. Modelled as a smooth
        # ramp on Ṫ_g for T > 5000 K, scaled by the mole fraction of
        # dissociable species (water, O2, N2). For a 99 % Ar bubble the
        # cap is small; for a vapour-dominated bubble it strongly damps.
        if do_vap_cap and T_g > 5000.0:
            base = 1.0 / (1.0 + ((T_g - 5000.0) / 2000.0) ** 2)
            cap_factor = 1.0 - f_dissociable * (1.0 - base)
            if Q > 0.0:
                Q *= cap_factor

        return Q / denom

    return Tdot

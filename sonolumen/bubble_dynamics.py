"""Bubble-radius ODEs.

Phase B: RPE, KME, Gilmore + diagnostic Toegel.
Phase C: thermal-coupled Toegel (state = R, Ṙ, T_g; gas pressure via
ideal gas with optional VdW vol correction; dp_L/dt picks up the
∂p_g/∂T · Ṫ term).

Equation references map to `cavitation_research/equations.md`:
    E5  Minnaert resonance
    E6  Rayleigh–Plesset
    E6b Van der Waals hard-core gas pressure
    E7  Pure Rayleigh collapse time
    E8  Keller–Miksis (compressible liquid, retarded drive)
    E9  Gilmore (Tait EOS for the liquid + Kirkwood–Bethe)
    E11 Adiabatic compression law
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

from sonolumen._constants import K_B
from sonolumen.config import (
    AcousticDrive,
    AmbientConditions,
    BubbleSeed,
    LiquidProperties,
    PhysicsOptions,
)


# ---------------------------------------------------------------------------
# Gas-phase EOS helpers (E6 / E6b, §2.1; ideal-gas variants for §2.4 / §4.1)
# ---------------------------------------------------------------------------
_VDW_HARDCORE_FACTORS = {
    "Ar": 8.54,
    "Xe": 8.86,
    "He": 8.5,
}


def _dominant_gas(gas_composition: dict) -> str:
    if not gas_composition:
        return "Ar"
    return max(gas_composition.items(), key=lambda kv: kv[1])[0]


def hardcore_radius(seed: BubbleSeed) -> float:
    """h such that p_g blows up as R → h. §2.1 / equation E6b."""
    species = _dominant_gas(seed.gas_composition)
    factor = _VDW_HARDCORE_FACTORS.get(species, 8.54)
    return seed.R0 / factor


def equilibrium_p_g0(
    seed: BubbleSeed, liquid: LiquidProperties, ambient: AmbientConditions
) -> float:
    """Initial gas partial pressure at R = R₀.

    Returns `seed.p_gas_initial` when set (impulsive/non-equilibrium IC,
    §9.8). Otherwise the SBSL static-equilibrium expression p_∞ + 2σ/R₀ − p_v.
    """
    if seed.p_gas_initial is not None:
        return float(seed.p_gas_initial)
    return ambient.p_inf + 2.0 * liquid.sigma / seed.R0 - liquid.p_v


def total_gas_molecules(
    seed: BubbleSeed, liquid: LiquidProperties, ambient: AmbientConditions
) -> float:
    """N_total at the seed state (assumed conserved). §2.4 / Toegel."""
    p_g0 = equilibrium_p_g0(seed, liquid, ambient)
    V0 = (4.0 / 3.0) * math.pi * seed.R0 ** 3
    return p_g0 * V0 / (K_B * seed.T0)


def gas_pressure(
    R: float,
    seed: BubbleSeed,
    liquid: LiquidProperties,
    ambient: AmbientConditions,
    physics: PhysicsOptions,
) -> float:
    """p_g(R) via the configured gas EOS (no temperature feedback). E6 / E6b."""
    if physics.gas_eos == "vacuum":
        return 0.0
    p_g0 = equilibrium_p_g0(seed, liquid, ambient)
    R0 = seed.R0
    kappa = seed.kappa
    if physics.gas_eos == "polytropic":
        return p_g0 * (R0 / R) ** (3.0 * kappa)
    if physics.gas_eos == "vdw_hardcore":
        h = hardcore_radius(seed)
        Rc = max(R, h * (1.0 + 1e-9))
        ratio = (R0 ** 3 - h ** 3) / (Rc ** 3 - h ** 3)
        return p_g0 * ratio ** kappa
    raise ValueError(f"unknown gas_eos {physics.gas_eos!r}")


def gas_pressure_dR(
    R: float, p_g: float, seed: BubbleSeed, physics: PhysicsOptions,
) -> float:
    """dp_g/dR for the polytropic/vdw EOS (no thermal coupling)."""
    if physics.gas_eos == "vacuum":
        return 0.0
    kappa = seed.kappa
    if physics.gas_eos == "polytropic":
        return -3.0 * kappa * p_g / R
    if physics.gas_eos == "vdw_hardcore":
        h = hardcore_radius(seed)
        Rc = max(R, h * (1.0 + 1e-9))
        return -3.0 * kappa * p_g * (Rc * Rc) / (Rc ** 3 - h ** 3)
    raise ValueError(f"unknown gas_eos {physics.gas_eos!r}")


def ideal_gas_pressure(
    R: float, T_g: float, N_total: float, seed: BubbleSeed, physics: PhysicsOptions,
) -> float:
    """p_g = N_total k_B T / V_eff(R), with VdW excluded volume if requested."""
    if physics.gas_eos == "vdw_hardcore":
        h = hardcore_radius(seed)
        V_eff = (4.0 / 3.0) * math.pi * (R ** 3 - h ** 3)
        if V_eff <= 0.0:
            V_eff = (4.0 / 3.0) * math.pi * (h * 1e-9) ** 3
    else:
        V_eff = (4.0 / 3.0) * math.pi * R ** 3
    return N_total * K_B * T_g / max(V_eff, 1e-40)


def ideal_gas_dp_dR(
    R: float, p_g: float, seed: BubbleSeed, physics: PhysicsOptions,
) -> float:
    """∂p_g/∂R at constant T for ideal gas (with optional VdW vol correction)."""
    if physics.gas_eos == "vdw_hardcore":
        h = hardcore_radius(seed)
        Rc = max(R, h * (1.0 + 1e-9))
        return -3.0 * p_g * (Rc * Rc) / (Rc ** 3 - h ** 3)
    return -3.0 * p_g / R


def ideal_gas_dp_dT(p_g: float, T_g: float) -> float:
    """∂p_g/∂T at constant R for ideal gas. = p_g / T."""
    return p_g / max(T_g, 1.0)


def wall_pressure(
    R: float,
    Rdot: float,
    p_g: float,
    liquid: LiquidProperties,
) -> float:
    """p_L(R, Ṙ) at the bubble wall. §2.1 wall boundary condition."""
    return p_g + liquid.p_v - 2.0 * liquid.sigma / R - 4.0 * liquid.mu * Rdot / R


# ---------------------------------------------------------------------------
# Tait EOS helpers — used by Gilmore (E9)
# ---------------------------------------------------------------------------
def tait_enthalpy(P_far: float, p_L: float, liquid: LiquidProperties, p_inf_ref: float) -> float:
    """H = ∫_{P_far}^{p_L} dp/ρ_L(p) for the Tait EOS, §2.3."""
    B = liquid.B_tait
    n = liquid.n_tait
    rho_0 = liquid.rho
    pre = (n / (n - 1.0)) / rho_0 * (p_inf_ref + B) ** (1.0 / n)
    return pre * ((p_L + B) ** ((n - 1.0) / n) - (P_far + B) ** ((n - 1.0) / n))


def tait_sound_speed(H: float, c0: float, liquid: LiquidProperties) -> float:
    """C(p_L) = √(c_0² + (n−1) H), §2.3."""
    n = liquid.n_tait
    val = c0 * c0 + (n - 1.0) * H
    if val <= 0.0:
        return c0
    return math.sqrt(val)


# ---------------------------------------------------------------------------
# Closed-form helpers
# ---------------------------------------------------------------------------
def rayleigh_collapse_time(R_max: float, delta_p: float, rho_L: float) -> float:
    """Pure Rayleigh collapse time (E7)."""
    return 0.915 * R_max * math.sqrt(rho_L / delta_p)


def minnaert_frequency(
    R0: float, liquid: LiquidProperties, ambient: AmbientConditions, kappa: float
) -> float:
    """Linear (Minnaert) bubble resonance, in Hz (E5)."""
    p_inf = ambient.p_inf
    sigma = liquid.sigma
    rho_L = liquid.rho
    inner = 3.0 * kappa * (p_inf + 2.0 * sigma / R0) - 2.0 * sigma / R0
    omega0 = math.sqrt(inner / rho_L) / R0
    return omega0 / (2.0 * math.pi)


# ---------------------------------------------------------------------------
# Bubble-equation right-hand sides
# ---------------------------------------------------------------------------
@dataclass
class BubbleStateSpec:
    names: tuple[str, ...]
    initial: tuple[float, ...]


def _build_rhs(
    eq: str,
    seed: BubbleSeed,
    liquid: LiquidProperties,
    ambient: AmbientConditions,
    physics: PhysicsOptions,
    drive: AcousticDrive,
):
    """Build the unified RHS f(t, y).

    State y is (R, Ṙ) when thermal_model is 'polytropic', or (R, Ṙ, T_g)
    when 'toegel'. The KME / Gilmore equations' dp_L/dt term picks up
    the (∂p_g/∂T)·Ṫ contribution when thermal coupling is active.
    """
    from sonolumen.drive import make_p_a, make_dp_a_dt
    from sonolumen.thermal import make_toegel_T_dot

    p_a = make_p_a(drive)
    dp_a_dt = make_dp_a_dt(drive)
    is_thermal = (physics.thermal_model == "toegel")

    rho_L = liquid.rho
    sigma = liquid.sigma
    mu_L = liquid.mu
    c0 = liquid.c
    p_inf = ambient.p_inf
    p_inf_ref = ambient.p_inf

    use_ideal_gas = is_thermal and (physics.gas_eos != "vacuum")

    if is_thermal:
        Tdot_fn = make_toegel_T_dot(seed, liquid, ambient, physics)
    else:
        Tdot_fn = None

    if use_ideal_gas:
        N_total = total_gas_molecules(seed, liquid, ambient)

        def get_pg(R: float, T_g: float) -> float:
            return ideal_gas_pressure(R, T_g, N_total, seed, physics)

        def get_dpg_dR(R: float, T_g: float, p_g: float) -> float:
            return ideal_gas_dp_dR(R, p_g, seed, physics)

        def get_dpg_dT(R: float, T_g: float, p_g: float) -> float:
            return ideal_gas_dp_dT(p_g, T_g)
    else:
        def get_pg(R: float, T_g: float) -> float:
            return gas_pressure(R, seed, liquid, ambient, physics)

        def get_dpg_dR(R: float, T_g: float, p_g: float) -> float:
            return gas_pressure_dR(R, p_g, seed, physics)

        def get_dpg_dT(R: float, T_g: float, p_g: float) -> float:
            return 0.0

    # Per-equation closure constructors. Each one returns a `f(t, y)` taking
    # y = (R, Ṙ, [T_g]) with len(y) ∈ {2, 3} matching is_thermal.
    if eq == "rayleigh_plesset":
        def f_rpe(t: float, y):
            R, Rdot = y[0], y[1]
            T_g = y[2] if is_thermal else seed.T0
            p_g = get_pg(R, T_g)
            p_L = wall_pressure(R, Rdot, p_g, liquid)
            Rddot = (p_L - p_inf - p_a(t)) / (rho_L * R) - 1.5 * Rdot * Rdot / R
            if is_thermal:
                dT = Tdot_fn(R, Rdot, T_g, p_g, t)
                return (Rdot, Rddot, dT)
            return (Rdot, Rddot)
        return f_rpe

    if eq == "keller_miksis":
        def f_kme(t: float, y):
            R, Rdot = y[0], y[1]
            T_g = y[2] if is_thermal else seed.T0
            p_g = get_pg(R, T_g)
            p_L = wall_pressure(R, Rdot, p_g, liquid)
            t_ret = t + R / c0
            p_a_t = p_a(t_ret)
            dp_a_t = (1.0 + Rdot / c0) * dp_a_dt(t_ret)
            X = p_L - p_inf - p_a_t

            dpg_dR = get_dpg_dR(R, T_g, p_g)
            if is_thermal:
                dT = Tdot_fn(R, Rdot, T_g, p_g, t)
                dpg_dT = get_dpg_dT(R, T_g, p_g)
                dpg_dt_partial = dpg_dR * Rdot + dpg_dT * dT
            else:
                dT = 0.0
                dpg_dt_partial = dpg_dR * Rdot

            # dp_L/dt = dp_g/dt(no R̈) + 2σ Ṙ/R² + 4μ Ṙ²/R² − (4μ/R) R̈
            Y = dpg_dt_partial + 2.0 * sigma / (R * R) * Rdot + 4.0 * mu_L * Rdot * Rdot / (R * R)
            denom = (1.0 - Rdot / c0) * R + 4.0 * mu_L / (rho_L * c0)
            num = ((1.0 + Rdot / c0) * X / rho_L
                   + (R / (rho_L * c0)) * (Y - dp_a_t)
                   - 1.5 * Rdot * Rdot * (1.0 - Rdot / (3.0 * c0)))
            Rddot = num / denom
            if is_thermal:
                return (Rdot, Rddot, dT)
            return (Rdot, Rddot)
        return f_kme

    if eq == "gilmore":
        def f_gil(t: float, y):
            R, Rdot = y[0], y[1]
            T_g = y[2] if is_thermal else seed.T0
            p_g = get_pg(R, T_g)
            p_L = wall_pressure(R, Rdot, p_g, liquid)
            t_ret = t + R / c0
            P_far = p_inf + p_a(t_ret)
            H = tait_enthalpy(P_far, p_L, liquid, p_inf_ref)
            C = tait_sound_speed(H, c0, liquid)

            B = liquid.B_tait
            n = liquid.n_tait
            rho_at_pL = rho_L * ((p_L + B) / (p_inf_ref + B)) ** (1.0 / n)
            rho_at_Pfar = rho_L * ((P_far + B) / (p_inf_ref + B)) ** (1.0 / n)
            dH_dpL = 1.0 / rho_at_pL
            dH_dPfar = -1.0 / rho_at_Pfar

            dpg_dR = get_dpg_dR(R, T_g, p_g)
            if is_thermal:
                dT = Tdot_fn(R, Rdot, T_g, p_g, t)
                dpg_dT = get_dpg_dT(R, T_g, p_g)
                dpg_dt_partial = dpg_dR * Rdot + dpg_dT * dT
            else:
                dT = 0.0
                dpg_dt_partial = dpg_dR * Rdot

            Y = dpg_dt_partial + 2.0 * sigma / (R * R) * Rdot + 4.0 * mu_L * Rdot * Rdot / (R * R)
            dPfar_dt = (1.0 + Rdot / c0) * dp_a_dt(t_ret)
            Hdot_no_Rddot = dH_dpL * Y + dH_dPfar * dPfar_dt
            coef_Rddot_in_Hdot = -dH_dpL * 4.0 * mu_L / R

            a = (1.0 - Rdot / C) * R - (R / C) * (1.0 - Rdot / C) * coef_Rddot_in_Hdot
            b = ((1.0 + Rdot / C) * H
                 + (R / C) * (1.0 - Rdot / C) * Hdot_no_Rddot
                 - 1.5 * Rdot * Rdot * (1.0 - Rdot / (3.0 * C)))
            Rddot = b / a
            if is_thermal:
                return (Rdot, Rddot, dT)
            return (Rdot, Rddot)
        return f_gil

    raise ValueError(f"unknown bubble_eq {eq!r}")


# ---------------------------------------------------------------------------
# Equation dispatcher (wraps state spec + RHS construction)
# ---------------------------------------------------------------------------
def select_equation(
    physics: PhysicsOptions,
    seed: BubbleSeed,
    liquid: LiquidProperties,
    ambient: AmbientConditions,
    drive: AcousticDrive,
):
    """Return (rhs, state_spec, info)."""
    if physics.thermal_model == "full_pde":
        raise NotImplementedError(
            "thermal_model='full_pde' is Phase E (deferred); use 'polytropic' or 'toegel'."
        )

    if physics.thermal_model not in ("polytropic", "toegel"):
        raise ValueError(f"unknown thermal_model {physics.thermal_model!r}")

    rhs = _build_rhs(physics.bubble_eq, seed, liquid, ambient, physics, drive)

    if physics.thermal_model == "toegel":
        spec = BubbleStateSpec(
            names=("R", "Rdot", "T_g"),
            initial=(seed.R0, seed.Rdot0, seed.T0),
        )
    else:
        spec = BubbleStateSpec(
            names=("R", "Rdot"),
            initial=(seed.R0, seed.Rdot0),
        )

    return rhs, spec, {"eq": physics.bubble_eq, "thermal": physics.thermal_model}


def temperature_from_trace(
    R: float, seed: BubbleSeed, physics: PhysicsOptions,
    coupled_T: float | None = None,
) -> float:
    """Return T_g for a given R, using the configured thermal model."""
    if physics.thermal_model == "toegel" and coupled_T is not None:
        return coupled_T
    return seed.T0 * (seed.R0 / R) ** (3.0 * (seed.kappa - 1.0))

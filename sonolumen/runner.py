"""High-level run() function and SimulationResult dataclass.

§11.3 / §11.8 of the dossier. The runner takes a SimulationConfig,
integrates the bubble + thermal ODEs, computes plasma diagnostics and
EM emission, and emits a structured SimulationResult.

§10 advice baked in: T_peak, n_e_peak, photons_visible, flash_FWHM_ns,
shape_stability_flag are all *diagnosed* fields populated from the
ODE/Saha/EM stack — never set as inputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from sonolumen._constants import C_LIGHT, K_B
from sonolumen.bubble_dynamics import (
    minnaert_frequency,
    rayleigh_collapse_time,
    total_gas_molecules,
)
from sonolumen.config import SimulationConfig
from sonolumen.em_emission import emit_spectrum, photon_yield
from sonolumen.plasma import plasma_diagnostics, saha_trace
from sonolumen.solvers import integrate_bubble


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------
@dataclass
class SimulationResult:
    """Structured output of a single sonolumen run.

    Per §11.3, all quantities are SI. The `summary` dict carries the
    diagnosed peak values that §10 explicitly says must be outputs and
    not inputs.
    """
    config: SimulationConfig
    t: np.ndarray
    bubble: dict             # R, Rdot, T_g (when toegel)
    plasma: dict             # n_total, n_e, x_e, omega_p, lambda_D, Gamma, lambda_ei
    em: dict                 # lambda_grid, S_t_lambda, photons_visible, photons_uv
    detectors: dict          # V_PMT, V_hydrophone, V_coil
    summary: dict
    metadata: dict = field(default_factory=dict)

    @property
    def R(self) -> np.ndarray:
        return self.bubble["R"]

    @property
    def T_g(self) -> np.ndarray:
        return self.bubble["T_g"]

    @property
    def n_e(self) -> np.ndarray:
        return self.plasma["n_e"]


# ---------------------------------------------------------------------------
# Top-level run()
# ---------------------------------------------------------------------------
def run(cfg: SimulationConfig) -> SimulationResult:
    """Execute a full sonolumen simulation and return a SimulationResult.

    Phase D-complete: bubble → thermal → plasma → EM → detectors → summary.
    """
    seed = cfg.bubble_seed
    liquid = cfg.liquid
    ambient = cfg.ambient
    drive = cfg.drive
    physics = cfg.physics_options
    numerics = cfg.numerics
    output = cfg.output

    # ---- bubble + thermal integration ------------------------------------
    trace = integrate_bubble(
        seed=seed, liquid=liquid, ambient=ambient,
        drive=drive, physics=physics, numerics=numerics,
    )
    R = trace.R
    Rdot = trace.Rdot
    if "T_g" in trace.state:
        T_g = trace.state["T_g"]
    else:
        # polytropic post-hoc T(R)
        T_g = seed.T0 * (seed.R0 / R) ** (3.0 * (seed.kappa - 1.0))

    bubble_block = {"R": R, "Rdot": Rdot, "T_g": T_g}

    # ---- plasma diagnostics ----------------------------------------------
    N_total = total_gas_molecules(seed, liquid, ambient)
    V = (4.0 / 3.0) * math.pi * R ** 3
    n_total_arr = N_total / V
    saha = saha_trace(T_g, n_total_arr, seed.gas_composition,
                       model=physics.ionization_model)
    n_e = saha["n_e"]
    x_e = saha["x_e"]

    omega_p_arr = np.array([plasma_diagnostics(float(T), float(ne))["omega_p"]
                             for T, ne in zip(T_g, n_e, strict=True)])
    lambda_D_arr = np.array([plasma_diagnostics(float(T), float(ne))["lambda_D"]
                              for T, ne in zip(T_g, n_e, strict=True)])
    Gamma_arr = np.array([plasma_diagnostics(float(T), float(ne))["Gamma"]
                           for T, ne in zip(T_g, n_e, strict=True)])

    plasma_block = {
        "n_total": n_total_arr,
        "n_e": n_e,
        "x_e": x_e,
        "omega_p": omega_p_arr,
        "lambda_D": lambda_D_arr,
        "Gamma": Gamma_arr,
    }

    # ---- EM emission ------------------------------------------------------
    lam_lo_nm, lam_hi_nm, n_bins = output.spectrum_lambda_nm
    lam_grid = np.linspace(lam_lo_nm * 1e-9, lam_hi_nm * 1e-9, int(n_bins))
    spec = emit_spectrum(T_g, n_e, n_e, 1.0, R, lam_grid,
                          em_model=physics.em_model)
    N_phot_vis = photon_yield(trace.t, R, spec, lam_grid, band_nm=(400, 700))
    N_phot_uv = photon_yield(trace.t, R, spec, lam_grid, band_nm=(200, 400))

    em_block = {
        "lambda_grid_m": lam_grid,
        "S_t_lambda": spec,
        "photons_visible": N_phot_vis,
        "photons_uv": N_phot_uv,
    }

    # ---- detectors --------------------------------------------------------
    detectors_block: dict = {}
    if output.detectors:
        from sonolumen.detectors import (
            hydrophone_signal, pickup_coil_signal, pmt_signal,
        )
        pmt = pmt_signal(trace.t, R, spec, lam_grid)
        hyd = hydrophone_signal(trace.t, R, Rdot, liquid.rho, liquid.c)
        coil = pickup_coil_signal(
            trace.t, R, Rdot, enable=physics.include_margulis_transient,
        )
        detectors_block = {
            "V_PMT": pmt["V_PMT"],
            "photoelectron_rate": pmt["photoelectron_rate"],
            "photons_collected": pmt["photons_collected"],
            "p_rad_hydrophone": hyd["p_rad"],
            "V_hydrophone": hyd["V"],
            "V_coil": coil["V"],
        }

    # ---- summary (per §11.3 / §10 advice — all *diagnosed*) ---------------
    R_max = float(R.max())
    R_min = float(R.min())
    T_peak = float(T_g.max())
    n_e_peak = float(n_e.max())
    Gamma_peak = float(Gamma_arr.max())
    x_e_peak = float(x_e.max())
    wall_mach_peak = float(np.abs(Rdot).max() / liquid.c)

    flash_FWHM = _flash_FWHM_ns(trace.t, R, T_g)
    shape_stability_flag = _shape_stability(R, Rdot, drive.f, liquid)

    convergence_diag = None
    if numerics.convergence_test:
        convergence_diag = _convergence_check(cfg)

    peak_pressure_at_1cm = float(np.abs(detectors_block.get(
        "p_rad_hydrophone", np.array([0.0]))).max()) if detectors_block else 0.0
    peak_voltage_PMT = float(detectors_block.get(
        "V_PMT", np.array([0.0])).max()) if detectors_block else 0.0

    summary = {
        "R_max": R_max,
        "R_min": R_min,
        "T_peak": T_peak,
        "n_e_peak": n_e_peak,
        "x_e_peak": x_e_peak,
        "Gamma_peak": Gamma_peak,
        "wall_mach_peak": wall_mach_peak,
        "flash_FWHM_ns": flash_FWHM,
        "photons_visible": N_phot_vis,
        "photons_uv": N_phot_uv,
        "peak_pressure_at_1cm": peak_pressure_at_1cm,
        "peak_voltage_PMT": peak_voltage_PMT,
        "shape_stability_flag": shape_stability_flag,
        "ionization_peak": x_e_peak,
        "convergence_diagnostic": convergence_diag,
        "minnaert_freq": minnaert_frequency(seed.R0, liquid, ambient, seed.kappa),
        "rayleigh_collapse_time": rayleigh_collapse_time(R_max, ambient.p_inf, liquid.rho),
    }

    metadata = {
        "version": "0.1.0.dev0",
        "physics": physics,
        "drive_kind": drive.kind,
        "thermal_model": physics.thermal_model,
        "ionization_model": physics.ionization_model,
        "em_model": physics.em_model,
    }

    return SimulationResult(
        config=cfg,
        t=trace.t,
        bubble=bubble_block,
        plasma=plasma_block,
        em=em_block,
        detectors=detectors_block,
        summary=summary,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Helper diagnostics
# ---------------------------------------------------------------------------
def _flash_FWHM_ns(
    t: np.ndarray, R: np.ndarray, T_g: np.ndarray,
) -> Optional[float]:
    """FWHM of the optical-flash power pulse, P_BB(t) = 4π R² σ T⁴.

    Uses the brightest single connected interval above the half-max so
    multi-flash traces report the central flash duration rather than the
    cycle separation. §5.3 / §11.5.
    """
    from sonolumen._constants import SIGMA_SB
    if len(t) < 3:
        return None
    P = 4.0 * np.pi * R ** 2 * SIGMA_SB * T_g ** 4
    Pmax = float(P.max())
    if Pmax <= 0.0:
        return None
    half = 0.5 * Pmax
    above = P >= half
    if not np.any(above):
        return None
    # Find the connected segment containing the global max
    i_peak = int(P.argmax())
    lo = i_peak
    while lo > 0 and above[lo - 1]:
        lo -= 1
    hi = i_peak
    while hi < len(P) - 1 and above[hi + 1]:
        hi += 1
    return float((t[hi] - t[lo]) * 1e9)


def _shape_stability(
    R: np.ndarray, Rdot: np.ndarray, f_drive: float, liquid,
) -> str:
    """RT + parametric instability indicator (§10.5)."""
    R_max = R.max()
    # BHL2002 §V — parametric instability threshold scales with R_max/R₀ ratio
    # and the wall Mach number. v1 returns a coarse classification.
    mach = np.abs(Rdot).max() / liquid.c
    if mach > 1.5 or R_max > 60e-6:
        return "unstable_likely"
    if mach > 0.8:
        return "marginal"
    return "stable_spherical_assumption_valid"


def _convergence_check(cfg: SimulationConfig) -> dict:
    """Re-run with halved tolerances and report ΔT_peak."""
    from dataclasses import replace
    tighter = replace(
        cfg.numerics,
        rtol=cfg.numerics.rtol * 0.1,
        atol=cfg.numerics.atol * 0.1,
        convergence_test=False,  # avoid recursion
    )
    cfg2 = replace(cfg, numerics=tighter)
    res2 = run(cfg2)
    T1 = run(replace(cfg, numerics=replace(cfg.numerics, convergence_test=False))).summary["T_peak"]
    T2 = res2.summary["T_peak"]
    rel = abs(T2 - T1) / max(T1, 1.0)
    return {"T_peak_baseline": T1, "T_peak_tightened": T2, "relative_change": rel}


# ---------------------------------------------------------------------------
# run.sweep — minimal parameter sweep
# ---------------------------------------------------------------------------
def sweep(cfg: SimulationConfig, **axes) -> list[SimulationResult]:
    """Execute `run()` across a 1-D parameter sweep.

    Example:
        run.sweep(cfg, drive__P_A=np.linspace(1.0e5, 1.6e5, 11))

    The double-underscore key syntax navigates nested dataclass fields.
    """
    if len(axes) != 1:
        raise NotImplementedError(
            "v1 sweep supports a single 1-D axis at a time"
        )
    key, values = next(iter(axes.items()))
    parts = key.split("__")
    results = []
    for v in values:
        cfg_v = _replace_nested(cfg, parts, float(v))
        results.append(run(cfg_v))
    return results


def _replace_nested(cfg, parts: list[str], value):
    from dataclasses import replace
    if len(parts) == 1:
        return replace(cfg, **{parts[0]: value})
    inner = getattr(cfg, parts[0])
    new_inner = _replace_nested(inner, parts[1:], value)
    return replace(cfg, **{parts[0]: new_inner})


# Attach `sweep` as an attribute of `run` so the §11.8 idiom works:
#     from sonolumen import run
#     run.sweep(cfg, drive__P_A=...)
run.sweep = sweep   # type: ignore[attr-defined]

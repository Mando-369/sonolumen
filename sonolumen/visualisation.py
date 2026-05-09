"""Built-in matplotlib plot helpers for SimulationResult.

§11.6 of the dossier. Each function takes a SimulationResult and returns
a Figure suitable for saving or display. No JS / interactive backends.
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np


def plot_radius_history(result, ax=None):
    """R(t) trace, log-y for the collapse, linear for the cycle."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7.0, 4.5))
    else:
        fig = ax.get_figure()
    t_us = result.t * 1e6
    R_um = result.R * 1e6
    ax.plot(t_us, R_um, color="black", lw=1)
    i_max = int(np.argmax(R_um))
    i_min = int(np.argmin(R_um))
    ax.axhline(R_um[i_max], ls=":", color="C0", alpha=0.5,
                label=f"R_max = {R_um[i_max]:.2f} µm")
    ax.axhline(R_um[i_min], ls=":", color="C3", alpha=0.5,
                label=f"R_min = {R_um[i_min]:.3f} µm")
    ax.set_xlabel("t (µs)")
    ax.set_ylabel("R (µm)")
    ax.set_yscale("log")
    ax.set_title("Bubble radius history")
    ax.legend(loc="best")
    fig.tight_layout()
    return fig


def plot_phase_space(result, ax=None):
    """Ṙ vs R phase plot (log-scaled R)."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(6.5, 5.0))
    else:
        fig = ax.get_figure()
    R_um = result.R * 1e6
    Rdot = result.bubble["Rdot"]
    c_L = result.config.liquid.c
    ax.plot(R_um, Rdot / c_L, color="black", lw=0.6)
    ax.set_xscale("log")
    ax.set_xlabel("R (µm)")
    ax.set_ylabel("Ṙ / c (Mach)")
    ax.set_title("Phase-space portrait")
    ax.axhline(0, color="grey", lw=0.5)
    fig.tight_layout()
    return fig


def plot_temperature_trace(result, ax=None):
    """T_g(t) and ionization fraction x_e(t) on twin axes."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7.0, 4.5))
    else:
        fig = ax.get_figure()
    t_us = result.t * 1e6
    ax.plot(t_us, result.T_g, color="C3", label="T_g (K)")
    ax.set_xlabel("t (µs)")
    ax.set_ylabel("T_g (K)", color="C3")
    ax.set_yscale("log")
    ax2 = ax.twinx()
    ax2.plot(t_us, result.plasma["x_e"], color="C0", label="x_e", lw=0.8)
    ax2.set_ylabel("ionisation x_e", color="C0")
    ax.set_title("Temperature & ionization")
    fig.tight_layout()
    return fig


def plot_spectrum_surface(result, ax=None):
    """Imshow of S_λ(t) over the full simulation."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7.0, 4.5))
    else:
        fig = ax.get_figure()
    lam = result.em["lambda_grid_m"] * 1e9
    S = result.em["S_t_lambda"]
    extent = [lam.min(), lam.max(), result.t.min() * 1e6, result.t.max() * 1e6]
    img = ax.imshow(S, aspect="auto", origin="lower", extent=extent, cmap="viridis")
    ax.set_xlabel("λ (nm)")
    ax.set_ylabel("t (µs)")
    ax.set_title("Specific intensity (W/m²/Hz/sr)")
    fig.colorbar(img, ax=ax)
    fig.tight_layout()
    return fig


def plot_detector_waveforms(result, ax=None):
    """V_PMT(t), V_hydrophone(t), V_coil(t) stacked."""
    fig, axes = plt.subplots(3, 1, figsize=(7.0, 6.5), sharex=True)
    t_us = result.t * 1e6
    if "V_PMT" in result.detectors:
        axes[0].plot(t_us, result.detectors["V_PMT"], color="C0")
        axes[0].set_ylabel("V_PMT (V)")
    if "V_hydrophone" in result.detectors:
        axes[1].plot(t_us, result.detectors["V_hydrophone"] * 1e3, color="C1")
        axes[1].set_ylabel("V_hyd (mV)")
    if "V_coil" in result.detectors:
        axes[2].plot(t_us, result.detectors["V_coil"] * 1e3, color="C3")
        axes[2].set_ylabel("V_coil (mV)")
    axes[-1].set_xlabel("t (µs)")
    fig.tight_layout()
    return fig


def plot_summary_dashboard(result):
    """4-panel dashboard: R(t), T_g(t)+x_e, spectrum surface, V_PMT(t)."""
    fig, axes = plt.subplots(2, 2, figsize=(12.0, 8.0))
    plot_radius_history(result, axes[0, 0])
    plot_temperature_trace(result, axes[0, 1])
    plot_spectrum_surface(result, axes[1, 0])
    if "V_PMT" in result.detectors:
        axes[1, 1].plot(result.t * 1e6, result.detectors["V_PMT"], color="C0")
        axes[1, 1].set_xlabel("t (µs)")
        axes[1, 1].set_ylabel("V_PMT (V)")
        axes[1, 1].set_title("PMT voltage")
    fig.tight_layout()
    return fig

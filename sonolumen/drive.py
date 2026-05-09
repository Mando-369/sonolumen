"""Acoustic forcing p_a(t) for the bubble. §3 / §11.2 of the dossier.

The KME / Gilmore equations evaluate the drive at retarded time t + R/c
(see §2.2, equation E8); we expose `p_a(t)` and `dp_a_dt(t)` so the
right-hand-side can both apply the field and its time derivative.
"""

from __future__ import annotations

import math
from typing import Callable

from sonolumen.config import AcousticDrive


def make_p_a(drive: AcousticDrive) -> Callable[[float], float]:
    """Return p_a(t): the acoustic pressure perturbation as a function of t."""
    if drive.kind == "sinusoid":
        omega = 2.0 * math.pi * drive.f
        amp = drive.P_A * drive.standing_wave_factor
        phase = drive.phase

        def p_a(t: float) -> float:
            return -amp * math.sin(omega * t + phase)
        # Convention: p_a is *additive* (total far-field pressure
        # = p_∞ + p_a). With this sign, p_a(T/4) = −P_A → total pressure
        # below ambient → rarefaction → bubble expansion. Bubble equations
        # in `bubble_dynamics.py` are written for this convention; KME and
        # RPE both use `... − p_a(t)` on the RHS.
        return p_a

    if drive.kind == "tone_burst":
        omega = 2.0 * math.pi * drive.f
        amp = drive.P_A * drive.standing_wave_factor
        T = drive.n_cycles / drive.f
        env_kind = drive.envelope or "tukey"

        def env(t: float) -> float:
            if t < 0.0 or t > T:
                return 0.0
            if env_kind == "gaussian":
                t0 = 0.5 * T
                sigma = 0.25 * T
                return math.exp(-((t - t0) ** 2) / (2.0 * sigma * sigma))
            # tukey-like cosine taper at ends, flat in middle
            taper = 0.1 * T
            if t < taper:
                return 0.5 - 0.5 * math.cos(math.pi * t / taper)
            if t > T - taper:
                return 0.5 - 0.5 * math.cos(math.pi * (T - t) / taper)
            return 1.0

        def p_a(t: float) -> float:
            return -amp * env(t) * math.sin(omega * t + drive.phase)
        return p_a

    if drive.kind == "impulsive":
        # §3 / §9.8: pistol-shrimp Bernoulli pulse. Single rarefaction +
        # exponential decay.
        peak = drive.peak_pressure if drive.peak_pressure is not None else drive.P_A
        rise = drive.rise_time if drive.rise_time is not None else 1e-6
        decay = drive.decay_time if drive.decay_time is not None else 5e-5

        def p_a(t: float) -> float:
            if t < 0.0:
                return 0.0
            if t < rise:
                # rising rarefaction
                return -peak * (t / rise)
            return -peak * math.exp(-(t - rise) / decay)
        return p_a

    if drive.kind == "custom":
        if drive.custom_p_a is None:
            raise ValueError("AcousticDrive.kind='custom' requires custom_p_a")
        return drive.custom_p_a

    raise ValueError(f"unknown AcousticDrive kind {drive.kind!r}")


def make_dp_a_dt(drive: AcousticDrive) -> Callable[[float], float]:
    """Return dp_a/dt(t). Used by the KME (E8) retarded-driver term."""
    if drive.kind == "sinusoid":
        omega = 2.0 * math.pi * drive.f
        amp = drive.P_A * drive.standing_wave_factor

        def dp_dt(t: float) -> float:
            return -amp * omega * math.cos(omega * t + drive.phase)
        return dp_dt

    # tone_burst / impulsive / custom: numerical derivative is fine;
    # KME convergence at the canonical tolerances is insensitive to the
    # exact derivative form for non-sinusoidal drives.
    p_a = make_p_a(drive)
    h = 1e-9

    def dp_dt(t: float) -> float:
        return (p_a(t + h) - p_a(t - h)) / (2.0 * h)
    return dp_dt

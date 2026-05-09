"""Pressure-field query at the bubble position. §12.4.

v2.0 implements only `analytic_eigenmode`:

  * Spherical chamber, fundamental radial mode → bubble at the centre sees
    the full standing-wave amplitude (factor 1.0). Off-centre bubbles see
    `sinc(k r)` with k = π / R_chamber (first radial node at the wall).
  * Cylindrical chamber, axial mode → factor `cos(π z / L)` along the axis.
  * Open-bath / HIFU / pistol_jet → factor 1.0 (treats the local field
    as plane wave, transducer-driven; the bubble sits at the focus).

Multi-transducer drives are combined at the bubble position by complex
superposition for sinusoids of the same frequency (in-phase coherent
ring-pair: amplitudes add; out-of-phase: cancel). For impulsive or
mixed-kind drives, v2.0 requires a single transducer; mixing kinds
raises `NotImplementedError` (deferred to v3 — see §12.5 / §10.10).
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from sonolumen.config import AcousticDrive

from sonolumen.scenario.types import (
    Chamber,
    DriveSchedule,
    Transducer,
)


# ---------------------------------------------------------------------------
# Spatial mode shape — analytic_eigenmode (§3.2 / §12.4)
# ---------------------------------------------------------------------------
def standing_wave_factor(
    chamber: Chamber, position: Tuple[float, float, float],
) -> float:
    """Spatial amplitude factor of the fundamental eigenmode at `position`.

    Returns a number in [0, 1]. For the canonical SBSL configuration the
    bubble is parked at the pressure antinode of a centred spherical
    cell → factor 1.0 (matches v1 default `standing_wave_factor=1.0`).
    """
    x, y, z = position
    r = math.sqrt(x * x + y * y + z * z)

    geom = chamber.geometry
    if geom == "sphere":
        # Radial fundamental of a closed sphere: zeroth-order spherical
        # Bessel j0(k r) = sinc(k r). First node at the wall → k = π / R.
        if chamber.radius <= 0.0:
            return 1.0
        kr = math.pi * r / chamber.radius
        if kr < 1e-9:
            return 1.0
        return abs(math.sin(kr) / kr)
    if geom == "cylinder_axial":
        L = chamber.length if chamber.length is not None else 2.0 * chamber.radius
        if L <= 0.0:
            return 1.0
        return abs(math.cos(math.pi * z / L))
    if geom == "cylinder_radial":
        # First radial mode J0(k r) — pressure antinode at axis
        if chamber.radius <= 0.0:
            return 1.0
        # Use sinc as a low-order proxy (J0 ≈ 1 - (kr)²/4 near axis)
        kr = 2.405 * r / chamber.radius   # 2.405 = first zero of J0
        if kr < 1e-9:
            return 1.0
        return max(0.0, 1.0 - 0.25 * kr * kr)
    if geom in ("horn_open_bath", "hifu_focus", "pistol_jet"):
        # Local plane-wave / focal-spot approximation — bubble assumed at
        # the field maximum. v2.0 returns 1.0; full focal profile is v3.
        return 1.0
    raise ValueError(f"unknown chamber geometry {geom!r}")


# ---------------------------------------------------------------------------
# Multi-transducer combine — produces a single equivalent v1 AcousticDrive
# ---------------------------------------------------------------------------
def combine_drives(
    transducers: list[Transducer],
    drive_schedule: DriveSchedule,
    bubble_position: Tuple[float, float, float],
    chamber: Chamber,
) -> AcousticDrive:
    """Reduce the multi-transducer schedule to a single v1 `AcousticDrive`.

    Rules for v2.0:
      * Empty schedule (no transducers, or all amplitudes zero) → silent
        sinusoid drive (`f=1.0, P_A=0.0`); used by impulsive populations
        such as `pistol_shrimp_event`.
      * Single transducer → pass-through with the spatial factor folded
        into `standing_wave_factor`.
      * Multi transducer, all sinusoids at the same frequency → complex
        superposition: amplitude = |Σ A_k exp(i φ_k)|, phase chosen so
        the resulting waveform matches the magnitude of the sum.
      * Mixed waveform kinds, or sinusoids at different frequencies, or
        multi-transducer impulsive → `NotImplementedError`.

    Returns a v1 `AcousticDrive` ready to feed `sonolumen.run()`.
    """
    waveforms = drive_schedule.waveforms or {}

    # Map transducer name → (Transducer, AcousticDrive) for ones with a waveform.
    paired: list[Tuple[Transducer, AcousticDrive]] = []
    for tx in transducers:
        wf = waveforms.get(tx.name)
        if wf is None:
            continue
        paired.append((tx, wf))

    if not paired:
        # Silent drive — used by impulsive populations with no acoustic forcing.
        return AcousticDrive(kind="sinusoid", f=1.0, P_A=0.0)

    factor = standing_wave_factor(chamber, bubble_position)

    if len(paired) == 1:
        tx, drv = paired[0]
        # Fold the spatial factor into the drive's standing_wave_factor.
        from dataclasses import replace
        return replace(drv, standing_wave_factor=drv.standing_wave_factor * factor)

    # Multi-transducer: must all share kind + frequency.
    kinds = {drv.kind for _, drv in paired}
    if len(kinds) > 1:
        raise NotImplementedError(
            f"mixed drive kinds across transducers ({kinds}) is v3; "
            "use a single transducer or one shared kind."
        )
    kind = kinds.pop()

    if kind != "sinusoid":
        raise NotImplementedError(
            f"multi-transducer combine for kind={kind!r} is v3; "
            "use a single transducer or kind='sinusoid'."
        )

    freqs = {drv.f for _, drv in paired}
    if len(freqs) > 1:
        raise NotImplementedError(
            f"multi-transducer combine across distinct frequencies ({freqs}) "
            "is v3; use a single frequency."
        )
    f = freqs.pop()

    # Complex superposition. Each transducer contributes A_k * exp(i φ_k).
    # The make_p_a sinusoid is `-A sin(ω t + φ)`, so the negative sign
    # cancels out in superposition: combined amplitude/phase fall out of
    # standard complex addition.
    re = 0.0
    im = 0.0
    for _tx, drv in paired:
        re += drv.P_A * math.cos(drv.phase)
        im += drv.P_A * math.sin(drv.phase)
    P_A_combined = math.hypot(re, im)
    phase_combined = math.atan2(im, re) if P_A_combined > 0.0 else 0.0

    n_cycles = max(drv.n_cycles for _, drv in paired)

    return AcousticDrive(
        kind="sinusoid",
        f=f,
        P_A=P_A_combined,
        phase=phase_combined,
        n_cycles=n_cycles,
        standing_wave_factor=factor,
    )


def pressure_field_query(
    chamber: Chamber,
    transducers: list[Transducer],
    drive_schedule: DriveSchedule,
    position: Tuple[float, float, float],
    t: float,
) -> float:
    """Evaluate p_a at `position`, time `t`. §12.4.

    v2.0 builds the equivalent drive, calls `make_p_a`, returns the
    instantaneous value. Used by the §15 UI to render the standing-wave
    field; the bubble itself sees the same field via `Scenario.run()`.
    """
    from sonolumen.drive import make_p_a
    drv = combine_drives(transducers, drive_schedule, position, chamber)
    return float(make_p_a(drv)(t))

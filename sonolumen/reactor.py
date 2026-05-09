"""Reactor object — chamber + transducer + Q. Minimal v1.

Section 3.2 / §11.4. The reactor object is mostly a passthrough; the
standing-wave factor is a position-dependent scalar that multiplies the
drive amplitude to model placement on/off the pressure antinode.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Reactor:
    """Cavitation chamber + transducer.

    Geometry attributes are informational in v1; the standing-wave-factor
    is the only quantity the bubble dynamics directly use (multiplies
    drive amplitude). Compute via `standing_wave_factor_spherical()` etc.
    """
    geometry: str = "spherical"           # 'spherical' | 'cylindrical'
    radius: float = 0.05                  # m, chamber radius
    length: float = 0.10                  # m, chamber length (cylindrical)
    Q: float = 1000.0                     # cavity Q
    transducer_kind: str = "PZT"
    drive_position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    standing_wave_factor: float = 1.0


def fundamental_frequency(reactor: Reactor, c_L: float) -> float:
    """Lowest cavity eigenfrequency (E3, §3.2)."""
    if reactor.geometry == "spherical":
        return c_L / (2.0 * reactor.radius)
    if reactor.geometry == "cylindrical":
        # axial fundamental
        return c_L / (2.0 * reactor.length)
    raise ValueError(f"unknown reactor geometry {reactor.geometry!r}")


def lowest_radial_frequency(reactor: Reactor, c_L: float) -> float:
    """Cylindrical resonator radial fundamental (E3, J0' first root)."""
    if reactor.geometry != "cylindrical":
        raise ValueError("radial mode only defined for cylindrical reactor")
    j0_prime_first_root = 3.832
    return c_L * j0_prime_first_root / (2.0 * math.pi * reactor.radius)

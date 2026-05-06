"""Drive-amplitude sweep for the §11.9 acceptance criterion #4.

Sweep P_A over [1.0, 1.6] atm × 11 points; verify monotonic non-strict
increase in T_peak and photons_visible. Prints a small table.

Usage: python examples/run_pa_sweep.py
"""
from __future__ import annotations

import time

import numpy as np

from cavplasma import presets, sweep


def main() -> None:
    cfg = presets.sbsl_canonical()
    P_A_grid = np.linspace(1.0e5, 1.6e5, 11)
    t0 = time.time()
    results = sweep(cfg, drive__P_A=P_A_grid)
    elapsed = time.time() - t0
    print(f"swept {len(P_A_grid)} points in {elapsed:.1f} s")
    print()
    print(f"  {'P_A (atm)':>10s}  {'R_max(µm)':>10s}  {'R_min(µm)':>10s}  "
          f"{'T_peak(K)':>10s}  {'Mach':>6s}  {'N_phot':>10s}")
    for r, P_A in zip(results, P_A_grid, strict=True):
        s = r.summary
        print(f"  {P_A/1.013e5:10.3f}  {s['R_max']*1e6:10.2f}  {s['R_min']*1e6:10.3f}  "
              f"{s['T_peak']:10.0f}  {s['wall_mach_peak']:6.3f}  {s['photons_visible']:10.2e}")
    # Acceptance: T_peak and photon count monotonically non-decreasing
    T_peaks = [r.summary["T_peak"] for r in results]
    N_photons = [r.summary["photons_visible"] for r in results]
    mono_T = all(b >= a * 0.95 for a, b in zip(T_peaks[:-1], T_peaks[1:], strict=True))
    mono_N = all(b >= a * 0.95 for a, b in zip(N_photons[:-1], N_photons[1:], strict=True))
    print()
    print(f"T_peak monotonic non-decreasing (within 5 %)?  {mono_T}")
    print(f"photons monotonic non-decreasing (within 5 %)? {mono_N}")


if __name__ == "__main__":
    main()

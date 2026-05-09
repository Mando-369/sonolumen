"""Run the pistol-shrimp preset (§9.8) and print the summary.

Usage: python examples/run_pistol_shrimp.py
"""
from __future__ import annotations

import time

from sonolumen import presets, run


def main() -> None:
    cfg = presets.pistol_shrimp()
    t0 = time.time()
    result = run(cfg)
    elapsed = time.time() - t0
    print(f"pistol_shrimp: integration succeeded in {elapsed:.2f} s")
    print()
    print("=== summary ===")
    for k, v in result.summary.items():
        if isinstance(v, float):
            print(f"  {k:30s} {v:.4g}")
        else:
            print(f"  {k:30s} {v!r}")
    print()
    print("§9.8 / §10.2 expected vs computed:")
    s = result.summary
    print(f"  bubble lifetime ≈ {s['rayleigh_collapse_time']*1e6:.0f} µs (expected ≈ 300 µs)")
    print(f"  T_peak: expected > 5e3 K (lower bound, [L2001]); got {s['T_peak']:.0f} K")
    print(f"  T_peak band per §10.2: 5e3–2e4 K (weakly constrained)")
    print(f"  photons_visible (emitted): {s['photons_visible']:.2e}")


if __name__ == "__main__":
    main()

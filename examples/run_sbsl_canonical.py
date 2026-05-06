"""Run the canonical SBSL preset and print the §11.3 summary.

Usage: python examples/run_sbsl_canonical.py
"""
from __future__ import annotations

import time

from cavplasma import presets, run


def main() -> None:
    cfg = presets.sbsl_canonical()
    t0 = time.time()
    result = run(cfg)
    elapsed = time.time() - t0
    print(f"sbsl_canonical: integration succeeded in {elapsed:.2f} s")
    print()
    print("=== summary (§11.3) ===")
    for k, v in result.summary.items():
        if isinstance(v, float):
            print(f"  {k:30s} {v:.4g}")
        else:
            print(f"  {k:30s} {v!r}")
    print()
    print("=== §9.9 expected vs computed ===")
    s = result.summary
    print(f"  R_max [µm]:               expected 30–50,        got {s['R_max']*1e6:.2f}")
    print(f"  R_min [µm]:               expected 0.5–0.8,      got {s['R_min']*1e6:.3f}")
    print(f"  T_peak [K]:               expected 1.5e4–4e4,    got {s['T_peak']:.0f}")
    print(f"  n_e_peak [m⁻³]:           expected 1e25–1e27,    got {s['n_e_peak']:.2e}")
    print(f"  Mach (wall):              expected 0.5–1.5,      got {s['wall_mach_peak']:.3f}")
    print(f"  photons_visible (emit):    expected 1e5–1e7 (det.) → as-emitted ≈ {s['photons_visible']:.2e}")


if __name__ == "__main__":
    main()

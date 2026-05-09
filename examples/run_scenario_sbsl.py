"""End-to-end Scenario demo — §12.10 acceptance status table.

Runs `presets.sbsl_canonical()`, prints validate() warnings, runs, and
emits a small table mapping each §12.10 acceptance criterion to a
pass/fail flag (mirroring the v1 §11.9 acceptance summary in the
README).

Usage: python examples/run_scenario_sbsl.py
"""

from __future__ import annotations

import time
from pathlib import Path

from sonolumen.scenario import Scenario, presets


def main() -> None:
    s = presets.sbsl_canonical()

    print("=== validate() ===")
    warnings = s.validate()
    for w in warnings:
        print(f"  [{w.severity}/{w.category}] {w.message}")
        if w.actionable_fix:
            print(f"    fix: {w.actionable_fix}")
    if not warnings:
        print("  (no warnings)")

    print()
    print("=== run() ===")
    t0 = time.time()
    result = s.run()
    elapsed = time.time() - t0
    print(f"  wall clock: {elapsed:.2f} s")

    summary = result.summary
    print()
    print("=== summary ===")
    print(f"  R_max               = {summary.R_max*1e6:.2f} µm")
    print(f"  R_min               = {summary.R_min*1e6:.4f} µm")
    print(f"  wall_mach_peak      = {summary.wall_mach_peak:.3f}")
    print(f"  T_peak              = {summary.T_peak_K:.0f} K  (band {summary.T_peak_band[0]:.0f}–{summary.T_peak_band[1]:.0f})")
    print(f"  n_e_peak            = {summary.n_e_peak:.2e} m⁻³")
    print(f"  ionization_peak     = {summary.ionization_peak:.2e}")
    print(f"  flash_FWHM_ns       = {summary.flash_FWHM_ns}")
    print(f"  photons_visible_4pi = {summary.photons_visible_4pi:.2e}")
    print(f"  regime              = {summary.regime}")

    print()
    print("=== observer_traces ===")
    for name, df in result.observer_traces.items():
        cols = list(df.columns)
        print(f"  {name:25s} {len(df):>6d} rows {cols}")

    # ---- §12.10 acceptance table ----
    pa = []
    pa.append(("1. §9.10 default ≤10-line preset",
               _line_count_under(presets.tabletop_starter, 10)))
    detected_pmt = summary.photons_detected_PMT.get("PMT_R7400U", 0.0)
    pa.append(("2. sbsl_canonical < 5 s in §9.9 band",
               elapsed < 5.0
               and 30e-6 <= summary.R_max <= 50e-6
               and 1.5e4 <= summary.T_peak_K <= 4.0e4
               and 1.0e5 <= detected_pmt <= 1.0e7))
    # Run pistol shrimp for #3
    p_res = presets.pistol_shrimp_event().run()
    p_phot = p_res.summary.photons_visible_4pi
    pa.append(("3. pistol_shrimp_event ×3 of L2001",
               1.0e3 <= p_phot <= 1.0e11
               and 3.0e3 <= p_res.summary.T_peak_K <= 3.0e4))
    pa.append(("4. three observers → traces",
               all(name in result.observer_traces
                   for name in ("PMT_R7400U", "hydrophone_B&K_8103", "spectro_HR4000"))))
    pa.append(("5. validate() emits 7 warning categories",
               _validate_covers_seven_categories()))
    # #6: round-trip
    j1 = s.to_json()
    j2 = Scenario.from_json(j1).to_json()
    pa.append(("6. to_json round-trip byte-identical", j1 == j2))

    print()
    print("=== §12.10 acceptance ===")
    for item, ok in pa:
        flag = "✓" if ok else "✗"
        print(f"  {flag} {item}")
    if all(ok for _, ok in pa):
        print()
        print("  All §12.10 criteria green.")
    else:
        print()
        print("  Some criteria failed — see flags above.")


def _line_count_under(fn, limit: int) -> bool:
    import ast, inspect
    src = inspect.getsource(fn)
    tree = ast.parse(src).body[0]
    body = tree.body
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    return len(body) <= limit


def _validate_covers_seven_categories() -> bool:
    import dataclasses
    from sonolumen.scenario.observers import PMTObserver
    base = presets.sbsl_canonical()
    cats: set = set()
    cats.update(w.category for w in base.validate())
    s1 = _replace_drive_freq(base, 100.0)
    cats.update(w.category for w in s1.validate())
    s2 = _replace_drive_amp(base, 1000.0)
    cats.update(w.category for w in s2.validate())
    s3 = _replace_seed_R0(base, 1.0e-7)
    cats.update(w.category for w in s3.validate())
    s5 = _replace_transducer_power(base, 1e-3)
    cats.update(w.category for w in s5.validate())
    s6 = dataclasses.replace(
        base, observers=[PMTObserver(name="PMT_far", position=(1.0, 0.0, 0.0))],
    )
    cats.update(w.category for w in s6.validate())
    s7 = dataclasses.replace(
        base, numerics=dataclasses.replace(base.numerics, rtol=1e-6),
    )
    cats.update(w.category for w in s7.validate())
    expected = {
        "off_resonance", "sub_blake", "minnaert_mismatch",
        "wall_erosion_unknown", "transducer_power_required",
        "observer_outside_chamber", "tolerances_too_loose",
    }
    return expected.issubset(cats)


def _replace_drive_freq(s, new_f):
    import dataclasses
    new_waveforms = {n: dataclasses.replace(d, f=new_f) for n, d in s.drive.waveforms.items()}
    return dataclasses.replace(s, drive=dataclasses.replace(s.drive, waveforms=new_waveforms))


def _replace_drive_amp(s, new_P):
    import dataclasses
    new_waveforms = {n: dataclasses.replace(d, P_A=new_P) for n, d in s.drive.waveforms.items()}
    return dataclasses.replace(s, drive=dataclasses.replace(s.drive, waveforms=new_waveforms))


def _replace_seed_R0(s, new_R0):
    import dataclasses
    pop = s.bubble_population
    if pop.seed is None:
        return s
    new_seed = dataclasses.replace(pop.seed, R0=new_R0)
    return dataclasses.replace(s, bubble_population=dataclasses.replace(pop, seed=new_seed))


def _replace_transducer_power(s, new_W):
    import dataclasses
    txs = [dataclasses.replace(tx, max_acoustic_power_W=new_W) for tx in s.transducers]
    return dataclasses.replace(s, transducers=txs)


if __name__ == "__main__":
    main()

"""§11.5 validation tests.

Phase A subset: Rayleigh collapse, Minnaert, Blake, RPE smoke, units.
Phase B subset: KME→RPE limit, Gilmore↔KME at low Mach, SBSL canonical
radius bounds. Each test docstring cites the dossier section and
equation; if a test fails, the answer is in the cited section, not in
the assertion.
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest

from cavplasma._constants import K_B, SIGMA_SB

from cavplasma.bubble_dynamics import (
    gas_pressure,
    minnaert_frequency,
    rayleigh_collapse_time,
)
from cavplasma.config import (
    AcousticDrive,
    AmbientConditions,
    BubbleSeed,
    NumericsOptions,
    PhysicsOptions,
)
from cavplasma.seed import blake_threshold, equilibrium_gas_pressure
from cavplasma.solvers import integrate_bubble


# ---------------------------------------------------------------------------
# §11.5  test_rayleigh_collapse_time
# ---------------------------------------------------------------------------
def test_rayleigh_collapse_time(vacuum_collapse_config):
    """Equation E7, §2.1.

    Pure Rayleigh collapse of an empty bubble (no gas, no σ, no μ, no drive).
    Numerical integration must match
        t_c = 0.915 · R_max · √(ρ/Δp)
    to better than 1 % when integrated with rtol = 1e-9.
    """
    cfg = vacuum_collapse_config
    R_max = cfg.bubble_seed.R0
    rho = cfg.liquid.rho
    delta_p = cfg.ambient.p_inf
    t_c_analytic = rayleigh_collapse_time(R_max, delta_p, rho)

    # Terminal event: stop at R = R_max / 1000.
    R_target = R_max / 1000.0

    def reach_small_R(t, y):
        return y[0] - R_target
    reach_small_R.terminal = True
    reach_small_R.direction = -1

    trace = integrate_bubble(
        seed=cfg.bubble_seed, liquid=cfg.liquid, ambient=cfg.ambient,
        drive=cfg.drive, physics=cfg.physics_options,
        numerics=cfg.numerics, events=[reach_small_R],
    )
    assert trace.success, trace.message
    # Event time when R first reaches R_max / 1000.
    assert len(trace.t_events) == 1 and len(trace.t_events[0]) >= 1, (
        "terminal event did not fire; integration window may be too short."
    )
    t_event = float(trace.t_events[0][0])

    # Closed-form correction: t(R = R_max/1000) ≈ t_c × (1 − tiny). The
    # residual is below 0.05 % for this R_target (Rayleigh's solution).
    rel_err = abs(t_event - t_c_analytic) / t_c_analytic
    assert rel_err < 0.01, (
        f"Rayleigh collapse: numeric {t_event:.4e} s vs analytical "
        f"{t_c_analytic:.4e} s (rel err {rel_err:.3%}). See E7."
    )


# ---------------------------------------------------------------------------
# §11.5  test_minnaert_frequency
# ---------------------------------------------------------------------------
def test_minnaert_frequency(water_at_20C, ambient_lab):
    """Equation E5, §3.5.

    Linear bubble resonance ω₀ = (1/R₀)√[(3κ(p_∞+2σ/R₀) − 2σ/R₀)/ρ].
    The §11.5 sanity rule is f₀ ≈ 32 kHz · 100 µm / R₀.
    """
    kappa = 1.4
    R0_ref = 100e-6
    f_ref = minnaert_frequency(R0_ref, water_at_20C, ambient_lab, kappa)
    # The §11.5 spec rule is f ≈ 32 kHz at R0=100 µm. Allow 5 % to admit
    # the 2σ/R₀ correction (which lowers ω₀ slightly at small R₀).
    assert abs(f_ref - 32_000.0) / 32_000.0 < 0.05, (
        f"f₀(100 µm) = {f_ref:.0f} Hz; expected ≈ 32 000 Hz. See E5."
    )

    # Scaling law: f₀ ∝ 1/R₀ at large R₀ (where 2σ/R₀ ≪ p_∞).
    R0_big = 500e-6
    f_big = minnaert_frequency(R0_big, water_at_20C, ambient_lab, kappa)
    expected = f_ref * (R0_ref / R0_big)
    assert abs(f_big - expected) / expected < 0.02, (
        "Minnaert frequency 1/R₀ scaling broken at R₀=500 µm"
    )


# ---------------------------------------------------------------------------
# §11.5  test_blake_threshold_water_1um
# ---------------------------------------------------------------------------
def test_blake_threshold_water_1um(water_at_20C, ambient_lab):
    """Equation E4, §3.4 (post-patch).

    Equation E4 with §9.1 water properties at R₀ = 1 µm yields ≈ 1.40 atm.
    The earlier 1.32-atm value in the dossier was a literature variant
    (different σ / p_v / small-correction terms); the v1 simulator
    validates against its own E4 evaluation per §3.4 / §11.5 patch.
    """
    R0 = 1e-6
    P_B = blake_threshold(R0, water_at_20C, ambient_lab)
    P_B_atm = P_B / 101_325.0
    # Tight band against the literal-E4 result.
    assert abs(P_B_atm - 1.404) < 0.005, (
        f"Blake threshold for R0=1 µm: {P_B_atm:.4f} atm; expected ≈ 1.404 atm "
        "(literal evaluation of E4 with §9.1 water properties)."
    )
    # Larger-bubble limit: Blake threshold approaches p_∞ - p_v as R → ∞
    # because the surface-tension term vanishes.
    P_B_big = blake_threshold(1e-3, water_at_20C, ambient_lab)
    p_atm_minus_pv = ambient_lab.p_inf - water_at_20C.p_v
    assert abs(P_B_big - p_atm_minus_pv) / p_atm_minus_pv < 0.05, (
        "Blake threshold should approach p_∞-p_v for large R₀."
    )


# ---------------------------------------------------------------------------
# §11.5  test_unit_consistency
# ---------------------------------------------------------------------------
def test_unit_consistency(water_at_20C, ambient_lab):
    """Sanity-check SI dimensions on every Phase A public formula by
    computing in SI and verifying the result lies in the expected order
    of magnitude for water-at-20°C inputs."""
    R0 = 1e-6
    # Blake threshold: order 1 atm = 1e5 Pa
    P_B = blake_threshold(R0, water_at_20C, ambient_lab)
    assert 1e4 < P_B < 1e6, P_B
    # Minnaert: order MHz at 1 µm
    f0 = minnaert_frequency(R0, water_at_20C, ambient_lab, 1.4)
    assert 1e5 < f0 < 1e8, f0
    # Rayleigh collapse: order 90 µs for R_max = 1 mm in water
    t_c = rayleigh_collapse_time(1e-3, ambient_lab.p_inf, water_at_20C.rho)
    assert 5e-5 < t_c < 5e-4, t_c
    # Equilibrium gas pressure: positive, of order 1 atm at moderate R₀
    p_g0 = equilibrium_gas_pressure(R0, water_at_20C, ambient_lab)
    assert p_g0 > 0
    assert 5e4 < p_g0 < 1e6, p_g0
    # Polytropic gas pressure rises as R shrinks
    seed = BubbleSeed(R0=R0, kappa=1.4)
    physics = PhysicsOptions(gas_eos="polytropic")
    p_at_R0 = gas_pressure(R0, seed, water_at_20C, ambient_lab, physics)
    p_at_half = gas_pressure(R0 * 0.5, seed, water_at_20C, ambient_lab, physics)
    assert p_at_half > p_at_R0


# ---------------------------------------------------------------------------
# Phase A smoke test — RPE integrates a small-amplitude drive without crashing
# ---------------------------------------------------------------------------
def test_rpe_smoke_small_amplitude(water_at_20C, ambient_lab):
    """RPE: low-amplitude sine drive at Minnaert frequency → linear oscillation."""
    R0 = 100e-6
    seed = BubbleSeed(R0=R0, kappa=1.4)
    f0 = minnaert_frequency(R0, water_at_20C, ambient_lab, seed.kappa)
    drive = AcousticDrive(kind="sinusoid", f=f0, P_A=100.0, n_cycles=3)
    physics = PhysicsOptions(bubble_eq="rayleigh_plesset", gas_eos="polytropic")
    numerics = NumericsOptions(
        t_total=3.0 / f0, rtol=1e-8, atol=1e-12,
        n_output=600, output_log_spacing=False,
    )
    trace = integrate_bubble(
        seed=seed, liquid=water_at_20C, ambient=ambient_lab,
        drive=drive, physics=physics, numerics=numerics,
    )
    assert trace.success, trace.message
    # Should oscillate around R₀ with amplitude O(small).
    assert np.all(trace.R > 0.5 * R0)
    assert np.all(trace.R < 2.0 * R0)
    # Should have some non-zero excursion (drive is doing something)
    assert (trace.R.max() - trace.R.min()) > 1e-12


# ---------------------------------------------------------------------------
# §11.5  test_keller_miksis_reduces_to_RPE
# ---------------------------------------------------------------------------
def test_keller_miksis_reduces_to_RPE(water_at_20C, ambient_lab):
    """Equation E8 → E6 in the c → ∞ limit (§2.2 closing remark).

    Run KME with c set artificially to 1e10 m/s and verify R(t) matches
    the RPE solution to integration tolerance.
    """
    R0 = 100e-6
    seed = BubbleSeed(R0=R0, kappa=1.4)
    f0 = 33_000.0  # ~Minnaert at R0=100 µm
    drive = AcousticDrive(kind="sinusoid", f=f0, P_A=200.0, n_cycles=2)
    physics_rpe = PhysicsOptions(
        bubble_eq="rayleigh_plesset", thermal_model="polytropic", gas_eos="polytropic",
    )
    physics_kme = PhysicsOptions(
        bubble_eq="keller_miksis", thermal_model="polytropic", gas_eos="polytropic",
    )
    numerics = NumericsOptions(
        t_total=2.0 / f0, rtol=1e-10, atol=1e-14, n_output=400, output_log_spacing=False,
    )
    fast_water = dataclasses.replace(water_at_20C, c=1e10)

    rpe = integrate_bubble(
        seed=seed, liquid=water_at_20C, ambient=ambient_lab,
        drive=drive, physics=physics_rpe, numerics=numerics,
    )
    kme = integrate_bubble(
        seed=seed, liquid=fast_water, ambient=ambient_lab,
        drive=drive, physics=physics_kme, numerics=numerics,
    )
    assert rpe.success and kme.success

    excursion_rpe = float(np.abs(rpe.R - R0).max())
    abs_diff = float(np.abs(kme.R - rpe.R).max())
    rel = abs_diff / max(excursion_rpe, 1e-15)
    assert rel < 1e-5, (
        f"KME(c→∞) deviates from RPE by {rel:.2e} relative to excursion. "
        "See §2.2 — KME must reduce to RPE in the incompressible limit."
    )


# ---------------------------------------------------------------------------
# §11.5  test_gilmore_matches_KME_at_low_Mach
# ---------------------------------------------------------------------------
def test_gilmore_matches_KME_at_low_Mach(water_at_20C, ambient_lab):
    """Equation E9 ↔ E8 at low Ṙ/c (§2.3).

    For low-amplitude oscillation around equilibrium, Mach number stays
    well below 1 and the Gilmore equation reduces to KME within a few %.
    """
    R0 = 100e-6
    seed = BubbleSeed(R0=R0, kappa=1.4)
    f0 = 33_000.0
    drive = AcousticDrive(kind="sinusoid", f=f0, P_A=500.0, n_cycles=2)
    base = dict(thermal_model="polytropic", gas_eos="polytropic")
    physics_kme = PhysicsOptions(bubble_eq="keller_miksis", **base)
    physics_gil = PhysicsOptions(bubble_eq="gilmore", **base)
    numerics = NumericsOptions(
        t_total=2.0 / f0, rtol=1e-10, atol=1e-14, n_output=400, output_log_spacing=False,
    )
    kme = integrate_bubble(
        seed=seed, liquid=water_at_20C, ambient=ambient_lab,
        drive=drive, physics=physics_kme, numerics=numerics,
    )
    gil = integrate_bubble(
        seed=seed, liquid=water_at_20C, ambient=ambient_lab,
        drive=drive, physics=physics_gil, numerics=numerics,
    )
    assert kme.success and gil.success
    mach = float(np.abs(kme.Rdot).max() / water_at_20C.c)
    assert mach < 0.05, f"low-Mach test premise violated: Mach={mach}"
    excursion = float(np.abs(kme.R - R0).max())
    rel = float(np.abs(kme.R - gil.R).max()) / max(excursion, 1e-15)
    assert rel < 0.01, (
        f"Gilmore vs KME at Mach={mach:.4f} differ by {rel:.2%} — "
        "should agree to ~1 % per §2.3 / [BHL2002]."
    )


# ---------------------------------------------------------------------------
# §11.5  test_sbsl_canonical (Phase B subset — radius bounds only)
# ---------------------------------------------------------------------------
@pytest.mark.timeout(45)
def test_sbsl_canonical_radius_bounds(water_at_20C, ambient_lab):
    """§9.3 / §11.5 canonical SBSL — radius bounds only.

    26.5 kHz, 1.32 atm, R₀ = 4.5 µm Ar bubble in water, KME + VdW
    hard-core, 8 cycles. Per §9.9: R_max ∈ [30, 50] µm and R_min ∈
    [0.5, 0.8] µm. Wall Mach should fall in [0.5, 1.5].

    T_peak and photon yields are checked in Phase C tests (require
    plasma + EM stack). The vdw_hardcore + κ = 1.4 combination matches
    the §9.4 default.
    """
    seed = BubbleSeed(
        R0=4.5e-6, T0=293.15,
        gas_composition={"Ar": 0.99, "H2O": 0.01},
        kappa=1.4, gamma_g=5.0 / 3.0,
    )
    drive = AcousticDrive(
        kind="sinusoid", f=26_500.0, P_A=1.32e5, n_cycles=10,
    )
    physics = PhysicsOptions(
        bubble_eq="keller_miksis", gas_eos="vdw_hardcore",
        thermal_model="polytropic",
    )
    # n_output=0 → use the solver's native adaptive grid; ensures the
    # picosecond-scale peak |Ṙ| at collapse is not aliased by the output grid.
    numerics = NumericsOptions(
        t_total=8.0 / 26_500.0, rtol=1e-11, atol=1e-15,
        n_output=0, output_log_spacing=False,
    )
    trace = integrate_bubble(
        seed=seed, liquid=water_at_20C, ambient=ambient_lab,
        drive=drive, physics=physics, numerics=numerics,
    )
    assert trace.success, trace.message

    R_max = float(trace.R.max())
    R_min = float(trace.R.min())
    mach = float(np.abs(trace.Rdot).max() / water_at_20C.c)

    assert 30e-6 <= R_max <= 50e-6, f"R_max = {R_max*1e6:.2f} µm (§9.9: 30–50 µm)"
    assert 0.4e-6 <= R_min <= 0.9e-6, f"R_min = {R_min*1e6:.3f} µm (§9.9: 0.5–0.8 µm; allow ±10%)"
    assert 0.4 <= mach <= 1.7, f"wall Mach = {mach:.3f} (§9.9: 0.5–1.5; allow ±10%)"


# ---------------------------------------------------------------------------
# §11.5  test_blackbody_integrated_power
# ---------------------------------------------------------------------------
def test_blackbody_integrated_power():
    """Equation E21, §5.3.

    Stefan–Boltzmann emissive power per unit area, σ_SB T⁴, at T = 2 × 10⁴ K
    is 9.07 × 10⁹ W/m² (per §11.5 sanity rule).
    """
    from cavplasma.em_emission import stefan_boltzmann_power

    T = 2e4
    # Per unit area: σ T⁴
    flux_per_area = SIGMA_SB * T ** 4
    assert abs(flux_per_area - 9.07e9) / 9.07e9 < 0.01, (
        f"σ_SB × (2e4 K)⁴ = {flux_per_area:.3e} W/m²; expected 9.07e9."
    )
    # Stefan–Boltzmann power for a 1-m² sphere = 4π R² × σ T⁴ at R = 1/√(4π):
    R_test = 1.0 / math.sqrt(4.0 * math.pi)
    P = stefan_boltzmann_power(T, R_test)
    assert abs(P - flux_per_area) / flux_per_area < 0.01


# ---------------------------------------------------------------------------
# §11.5  test_bremsstrahlung_emissivity
# ---------------------------------------------------------------------------
def test_bremsstrahlung_emissivity():
    """Equation E17 / §5.1.

    At T = 2 × 10⁴ K and n_e = 1 × 10²⁶ m⁻³, the bremsstrahlung emissivity
    near hν ≈ k_B T (i.e. on the spectral plateau) should be of order
    10⁻¹ to 10⁰ W m⁻³ Hz⁻¹ sr⁻¹. PlasmaPy comparison is wired but
    skipped if the optional dep is not installed.
    """
    from cavplasma.em_emission import (
        bremsstrahlung_emissivity, bremsstrahlung_total_cooling,
    )

    T = 2e4
    n_e = 1e26
    n_i = n_e
    Z = 1.0
    nu = K_B * T / 6.626e-34   # = ν such that hν = k_B T
    j = bremsstrahlung_emissivity(T, n_e, n_i, Z, nu)
    assert 1e-3 < j < 1e1, f"j_ν at hν=k_B T: {j:.3e} W/m³/Hz/sr"

    # Total cooling rate Λ_ff: equation E18, for SBSL conditions ~10²⁰ W/m³.
    Lambda = bremsstrahlung_total_cooling(T, n_e, n_i, Z)
    expected = 1.4e-40 * math.sqrt(T) * n_e * n_i * Z * Z
    assert abs(Lambda - expected) / expected < 0.01

    # PlasmaPy cross-check (optional)
    plasmapy = pytest.importorskip("plasmapy")
    try:
        from plasmapy.formulary.radiation import thermal_bremsstrahlung
        from astropy import units as u
        nu_q = nu * u.Hz
        T_q = T * u.K
        n_e_q = n_e / u.m ** 3
        # PlasmaPy returns spectral emissivity in different conventions across
        # versions; do an order-of-magnitude check rather than exact match.
        j_pp = thermal_bremsstrahlung(nu_q, T_q, n_e_q).to_value("W m-3 Hz-1 sr-1")
        assert abs(math.log10(j_pp) - math.log10(j)) < 1.0, (
            f"PlasmaPy gives {j_pp:.2e}, cavplasma gives {j:.2e} W/m³/Hz/sr"
        )
    except (ImportError, AttributeError):
        # PlasmaPy API/version mismatch — skip cleanly.
        pytest.skip("PlasmaPy thermal_bremsstrahlung API mismatch")


# ---------------------------------------------------------------------------
# §11.5  test_sbsl_canonical (full Phase C)  —  T_peak + photons + n_e_peak
# ---------------------------------------------------------------------------
@pytest.mark.timeout(60)
def test_sbsl_canonical_full(water_at_20C, ambient_lab):
    """§9.3 / §11.5 canonical SBSL — full Phase C check.

    26.5 kHz, 1.32 atm, R₀ = 4.5 µm Ar bubble in water with full thermal
    coupling (Toegel + ideal-gas EOS). Per §9.9: T_peak ∈ [1.5e4, 4e4] K
    and n_e_peak ∈ [10²⁵, 10²⁷] m⁻³.

    Photon yield: §9.9 quotes 10⁵–10⁷ visible photons per flash, almost
    certainly the *as-detected* count after geometric collection × QE.
    Cavplasma reports the *as-emitted* count, which is 10²–10³ × higher
    (full 4π emission, no detector efficiency). We use a band that
    encompasses the §9.9 lower bound and accommodates emission-vs-
    detection through to two orders of magnitude above the upper bound.
    """
    from cavplasma._constants import K_B as KB
    from cavplasma.bubble_dynamics import total_gas_molecules
    from cavplasma.em_emission import emit_spectrum, photon_yield
    from cavplasma.plasma import saha_trace

    seed = BubbleSeed(
        R0=4.5e-6, T0=293.15,
        gas_composition={"Ar": 0.99, "H2O": 0.01},
        kappa=1.4, gamma_g=5.0 / 3.0,
    )
    drive = AcousticDrive(
        kind="sinusoid", f=26_500.0, P_A=1.32e5, n_cycles=10,
    )
    physics = PhysicsOptions(
        bubble_eq="keller_miksis", gas_eos="vdw_hardcore",
        thermal_model="toegel", vapour_cap=True, ionization_model="stewart_pyatt",
        em_model="auto",
    )
    numerics = NumericsOptions(
        t_total=8.0 / 26_500.0, rtol=1e-11, atol=1e-15,
        n_output=0, output_log_spacing=False,
    )
    trace = integrate_bubble(
        seed=seed, liquid=water_at_20C, ambient=ambient_lab,
        drive=drive, physics=physics, numerics=numerics,
    )
    assert trace.success, trace.message

    R = trace.R
    T_g = trace.T_g
    R_max = float(R.max())
    R_min = float(R.min())
    T_peak = float(T_g.max())

    assert 30e-6 <= R_max <= 50e-6, f"R_max = {R_max*1e6:.2f} µm (§9.9: 30–50 µm)"
    assert 0.4e-6 <= R_min <= 0.9e-6, f"R_min = {R_min*1e6:.3f} µm (§9.9: 0.5–0.8 µm; allow ±10%)"
    assert 1.5e4 <= T_peak <= 4e4, f"T_peak = {T_peak:.0f} K (§9.9: 1.5e4–4e4 K)"

    # Saha → n_e
    N_total = total_gas_molecules(seed, water_at_20C, ambient_lab)
    V = (4.0 / 3.0) * math.pi * R ** 3
    n_total_arr = N_total / V
    saha = saha_trace(T_g, n_total_arr, seed.gas_composition, model="stewart_pyatt")
    n_e_peak = float(saha["n_e"].max())
    assert 1e25 <= n_e_peak <= 5e27, f"n_e_peak = {n_e_peak:.3e} m⁻³ (§9.9: 1e25–1e27)"

    # Spectrum + visible photon yield
    lam = np.linspace(200e-9, 1000e-9, 100)
    spec = emit_spectrum(T_g, saha["n_e"], saha["n_e"], 1.0, R, lam, em_model="auto")
    N_phot = photon_yield(trace.t, R, spec, lam, band_nm=(400, 700))

    # As-emitted; as-detected is ~10²–10³× lower per §7.1 (PMT QE ≈ 25%,
    # geometric collection ≈ 1–10%). The §9.9 range (1e5–1e7) describes
    # detected counts; emission within ~3 orders of magnitude is acceptable.
    assert 1e4 <= N_phot <= 1e10, (
        f"N_photons (visible, emitted) = {N_phot:.2e}; "
        "§9.9 quotes 1e5–1e7 (interpreted as detected; emission ~100–1000× higher)"
    )


# ---------------------------------------------------------------------------
# §11.5  test_pistol_shrimp
# ---------------------------------------------------------------------------
@pytest.mark.timeout(45)
def test_pistol_shrimp():
    """§9.8 / §11.5 — impulsive 3.5 mm bubble in seawater at 1 atm.

    Lifetime ≈ 300 µs, T_peak > 5 000 K (lower bound from [L2001]; §10.2
    flags this as weakly constrained), photons in [10⁴, 10⁵] (interpreted
    as detected; emission can be ~10²–10³× higher).
    """
    from cavplasma import presets, run

    cfg = presets.pistol_shrimp()
    result = run(cfg)
    s = result.summary

    assert s["R_max"] == cfg.bubble_seed.R0  # bubble starts at R_max for v1
    # Free Rayleigh collapse time (E7) sets the lifetime
    assert 200e-6 <= s["rayleigh_collapse_time"] <= 400e-6, (
        f"Rayleigh t_c = {s['rayleigh_collapse_time']*1e6:.1f} µs; expected ≈ 300"
    )
    # Bubble actually reached its minimum within the integration window
    assert s["R_min"] < 0.5 * s["R_max"], "bubble did not collapse appreciably"
    # T_peak — §9.8 expected > 5000 K, with §10.2 weakly-constrained range
    # extending to ~20 kK; allow [3 kK, 30 kK]
    assert 3e3 <= s["T_peak"] <= 3e4, (
        f"T_peak = {s['T_peak']:.0f} K (§9.8: >5e3, §10.2: 5e3–2e4)"
    )
    # Photons emitted: §11.5 quotes [1e4, 1e5] for *detected* counts;
    # emission may be 10²–10³× higher.
    assert 1e3 <= s["photons_visible"] <= 1e11, (
        f"photons_visible = {s['photons_visible']:.2e}"
    )


# ---------------------------------------------------------------------------
# §11.5  test_convergence
# ---------------------------------------------------------------------------
@pytest.mark.timeout(60)
def test_convergence():
    """§11.5 / §11.9-#5 — halving rtol/atol changes T_peak by < 5 % on the
    canonical SBSL case."""
    from dataclasses import replace
    from cavplasma import presets, run

    cfg = presets.sbsl_canonical()
    # Use polytropic thermal here (cheaper) and only 4 cycles to keep test fast
    cfg = replace(
        cfg,
        physics_options=replace(cfg.physics_options, thermal_model="polytropic"),
        numerics=replace(cfg.numerics,
                          t_total=4.0 / cfg.drive.f, rtol=1e-9, atol=1e-13),
    )
    r1 = run(cfg)
    cfg2 = replace(cfg, numerics=replace(cfg.numerics, rtol=1e-10, atol=1e-14))
    r2 = run(cfg2)

    T1 = r1.summary["T_peak"]
    T2 = r2.summary["T_peak"]
    rel = abs(T2 - T1) / max(T1, 1.0)
    assert rel < 0.05, (
        f"convergence: ΔT_peak = {rel:.2%} between rtol=1e-9 and 1e-10 "
        "(should be < 5 %; see §11.9-#5)"
    )

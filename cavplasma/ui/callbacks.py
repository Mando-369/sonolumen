"""Dash callbacks. §15.9 callback graph.

The Dash @callback decorators are *thin wrappers* around plain Python
functions defined here as `apply_*` / `render_*`. The wrappers live in
`register_callbacks(app)`, which `app.py` calls at startup. Pure
functions are independently importable and unit-testable without
spinning up a Dash server.
"""

from __future__ import annotations

import dataclasses
import io
import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, dcc, html, no_update

from cavplasma.config import AcousticDrive, BubbleSeed
from cavplasma.liquids import preset as _liquid_preset
from cavplasma.scenario import Scenario, presets as scenario_presets
from cavplasma.scenario.types import (
    BubblePopulation,
    DriveSchedule,
    PhysicsOptions,
    NumericsOptions,
)
from cavplasma.ui import figures
from cavplasma.ui.audio import hydrophone_to_wav, wav_to_data_uri
from cavplasma.ui.state import (
    result_to_store,
    scenario_from_store,
    scenario_to_store,
)
from cavplasma.ui.style import (
    ANIMATION_FRAME_BUDGET,
    NOTEBOOK_MAX_ENTRIES,
    REGIME_COLOR,
    REGIME_DESCRIPTION,
    SEVERITY_COLOR,
)


# ===========================================================================
# Scenario_store mutators (controls → scenario_store)
# ===========================================================================
def apply_controls(
    scenario_payload: Optional[str],
    *,
    liquid_name: str,
    ambient_T: float,
    ambient_p: float,
    drive_f_hz: float,
    drive_pa_atm: float,
    drive_cycles: int,
    bubble_R0_log10: float,
    gas_ar: float,
    gas_h2o: float,
    gas_air: float,
    phys_bubble_eq: str,
    phys_thermal: str,
    phys_ionization: str,
    num_rtol_log10: float,
    num_conv: bool,
    chamber_geometry: Optional[str] = None,
    chamber_radius_cm: Optional[float] = None,
    chamber_wall: Optional[str] = None,
    chamber_Q: Optional[float] = None,
) -> str:
    """Apply control values to the scenario_store. Returns updated JSON."""
    base = scenario_from_store(scenario_payload) or scenario_presets.sbsl_canonical()

    # Liquid
    try:
        liquid = _liquid_preset(liquid_name)
    except Exception:
        liquid = base.liquid

    # Chamber — geometry / radius / wall material / Q. The wall_material
    # name maps to a fully-populated WallMaterial via the §13 catalog;
    # falls back to whatever the base scenario had if the catalog miss.
    chamber = base.chamber
    if (chamber_geometry is not None or chamber_radius_cm is not None
            or chamber_wall is not None or chamber_Q is not None):
        wall = chamber.wall_material
        if chamber_wall:
            try:
                from cavplasma.material.materials import get as _wall_get
                wall = _wall_get(chamber_wall)
            except Exception:                                              # noqa: BLE001
                # Catalog miss — keep existing wall_material.
                pass
        chamber = dataclasses.replace(
            chamber,
            geometry=chamber_geometry or chamber.geometry,
            radius=(float(chamber_radius_cm) / 100.0
                    if chamber_radius_cm is not None else chamber.radius),
            wall_material=wall,
            Q=float(chamber_Q) if chamber_Q is not None else chamber.Q,
        )

    # Ambient — `ambient_p` slider is now log₁₀(p_∞ in kPa) so a single
    # control covers vacuum (~30 kPa) → 10 km seawater (~100 MPa).
    p_inf_pa = (10.0 ** float(ambient_p)) * 1_000.0
    ambient = dataclasses.replace(
        base.ambient,
        p_inf=p_inf_pa,
        T_inf=ambient_T,
    )

    # Drive — slider value is already in Hz; only convert P_A to Pa.
    f_hz = float(drive_f_hz)
    P_A_pa = drive_pa_atm * 101_325.0
    new_waveforms: dict = {}
    for tx_name, drv in base.drive.waveforms.items():
        new_waveforms[tx_name] = dataclasses.replace(
            drv, f=f_hz, P_A=P_A_pa, n_cycles=int(drive_cycles),
        )
    if not new_waveforms and base.transducers:
        # Build a default waveform on the first transducer
        new_waveforms = {base.transducers[0].name: AcousticDrive(
            kind="sinusoid", f=f_hz, P_A=P_A_pa, n_cycles=int(drive_cycles),
        )}
    drive_schedule = dataclasses.replace(base.drive, waveforms=new_waveforms)

    # Bubble — only update R0 + gas composition; preserve other seed fields.
    pop = base.bubble_population
    if pop.seed is not None:
        R0_m = 10.0 ** bubble_R0_log10 * 1e-6
        gas: dict = {}
        if gas_ar:
            gas["Ar"] = float(gas_ar)
        if gas_h2o:
            gas["H2O"] = float(gas_h2o)
        if gas_air:
            gas["N2"] = 0.78 * float(gas_air)
            gas["O2"] = 0.21 * float(gas_air)
            gas["Ar"] = float(gas_ar) + 0.0093 * float(gas_air)
        if not gas:
            gas = pop.seed.gas_composition
        new_seed = dataclasses.replace(pop.seed, R0=R0_m, gas_composition=gas)
        new_pop = dataclasses.replace(pop, seed=new_seed)
    else:
        new_pop = pop

    physics = dataclasses.replace(
        base.physics_options,
        bubble_eq=phys_bubble_eq,
        thermal_model=phys_thermal,
        ionization_model=phys_ionization,
    )
    numerics = dataclasses.replace(
        base.numerics,
        rtol=10.0 ** num_rtol_log10,
        convergence_test=bool(num_conv),
    )

    new_scenario = dataclasses.replace(
        base,
        chamber=chamber,
        liquid=liquid,
        ambient=ambient,
        drive=drive_schedule,
        bubble_population=new_pop,
        physics_options=physics,
        numerics=numerics,
    )
    return scenario_to_store(new_scenario)


def apply_preset(name: str) -> str:
    """Replace the scenario_store with a named §12.8 preset."""
    factory = getattr(scenario_presets, name, None)
    if factory is None:
        raise ValueError(f"unknown preset {name!r}")
    return scenario_to_store(factory())


def scenario_to_control_values(scenario: Scenario) -> dict:
    """Project a Scenario back into the 15 control-input values used by
    the UI sliders / dropdowns. Used by the preset-confirmation and
    JSON-load callbacks to keep the visible controls in sync with the
    just-loaded scenario, so the next slider nudge doesn't silently
    overwrite the loaded values from stale slider positions.

    Slider step rounding (e.g. drive_f log10 → 0.05 step) means the
    sync is lossy at the kHz level; the scenario_store written by the
    follow-up `_apply_controls` will be ≈SBSL canonical, not bit-equal.
    """
    import math

    drv = next(iter(scenario.drive.waveforms.values()), None)
    if drv is not None:
        drive_f_hz = float(drv.f)
        drive_pa_atm = drv.P_A / 101_325.0
        drive_cycles = drv.n_cycles
    else:
        drive_f_hz = 26_500.0
        drive_pa_atm = 1.32
        drive_cycles = 8

    seed = scenario.bubble_population.seed
    if seed is not None:
        bubble_R0_log10 = math.log10(max(seed.R0, 1e-12) * 1e6)
        gas = seed.gas_composition or {}
    else:
        bubble_R0_log10 = 0.65
        gas = {}

    # ambient_p slider is now log₁₀(p_∞ in kPa) — covers vacuum → Mariana.
    p_inf_kpa = max(scenario.ambient.p_inf / 1_000.0, 1e-3)
    return {
        "chamber_geometry":  scenario.chamber.geometry,
        "chamber_radius_cm": scenario.chamber.radius * 100.0,
        "chamber_wall":      (scenario.chamber.wall_material.name
                                if scenario.chamber.wall_material else "borosilicate_glass"),
        "chamber_Q":         scenario.chamber.Q,
        "liquid_dropdown":   scenario.liquid.name,
        "ambient_T":         scenario.ambient.T_inf,
        "ambient_p":         math.log10(p_inf_kpa),
        "drive_f":           drive_f_hz,
        "drive_pa":          drive_pa_atm,
        "drive_cycles":      drive_cycles,
        "bubble_R0":         bubble_R0_log10,
        "gas_ar":            float(gas.get("Ar", 0.0)),
        "gas_h2o":           float(gas.get("H2O", 0.0)),
        "gas_air":           0.0,
        "phys_bubble_eq":    scenario.physics_options.bubble_eq,
        "phys_thermal":      scenario.physics_options.thermal_model,
        "phys_ionization":   scenario.physics_options.ionization_model,
        "num_rtol":          math.log10(max(scenario.numerics.rtol, 1e-30)),
        "num_conv":          bool(scenario.numerics.convergence_test),
    }


# ===========================================================================
# Run (TEST button) — Scenario → ScenarioResult
# ===========================================================================
def run_test(scenario_payload: Optional[str]) -> tuple[Optional[dict], str]:
    """Execute scenario.run() and pack into a result_store dict."""
    s = scenario_from_store(scenario_payload)
    if s is None:
        return None, "no scenario loaded"
    t0 = time.time()
    try:
        result = s.run()
    except ValueError as exc:
        return None, f"validate() blocked the run: {exc}"
    except Exception as exc:                                            # noqa: BLE001
        return None, f"run failed: {type(exc).__name__}: {exc}"
    elapsed = time.time() - t0
    payload = result_to_store(result)
    payload["wall_clock_s"] = elapsed
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    # Stash the v1 spectrum trace separately so the spectrum figure can
    # rebuild it server-side (too big to round-trip via dcc.Store).
    payload["__has_v1_result__"] = True
    return payload, f"ran in {elapsed:.2f} s"


# ===========================================================================
# Render — figures + right-column cards
# ===========================================================================
def render_figures(
    scenario_payload: Optional[str],
    result_payload: Optional[dict],
    server_v1_result: Optional[Any] = None,
) -> dict:
    """Build all six centre-column figures from the stores. Returns a dict
    keyed by graph id → Figure. `server_v1_result` is the live in-memory
    ScenarioResult (carries the dense spectrum) used for the spectrum
    surface; rebuilt by `_run_test_and_cache` in the live app.
    """
    s = scenario_from_store(scenario_payload)
    out: dict = {}
    out["chamber_fig"] = figures.chamber_figure(s) if s else _empty(
        "Chamber cross-section")
    out["field_fig"] = (
        figures.standing_wave_field_figure(s, t_anim=0.0) if s else _empty(
            "Standing wave field")
    )
    if result_payload:
        out["bubble_fig"] = figures.bubble_dynamics_figure(result_payload)
        out["plasma_fig"] = figures.plasma_diagnostics_figure(result_payload)
        out["detector_fig"] = figures.detector_traces_figure(result_payload)
    else:
        out["bubble_fig"] = _empty("Bubble dynamics")
        out["plasma_fig"] = _empty("Plasma diagnostics")
        out["detector_fig"] = _empty("Detector traces")
    if server_v1_result is not None:
        out["spectrum_fig"] = figures.spectrum_surface_figure(server_v1_result)
    elif result_payload:
        out["spectrum_fig"] = _empty("Spectrum surface (preview only)")
    else:
        out["spectrum_fig"] = _empty("Spectrum surface")
    return out


# ===========================================================================
# Live coupling — analytical adaptation between the three core physics
# sliders (drive_f, drive_pa, R₀). Lightweight: no forward simulation,
# just Minnaert + Blake + R_max/R₀ algebra. Used by the auto-adapt
# toggle in the Auto-design panel and by the always-on status chip.
# ===========================================================================
def _minnaert_constant(p_inf_pa: float, gamma: float, rho: float) -> float:
    """Returns f_M × R₀ (Hz·m) for the Minnaert frequency.

    f_M = (1/(2π R₀)) · √(3γ p_∞ / ρ), so f_M × R₀ is the proportionality
    constant that depends only on (γ, p_∞, ρ) — i.e. on the gas + liquid
    + ambient. We use this to maintain a fixed `drive/Minnaert` ratio
    when the user moves drive_f or R₀ with the auto-adapt toggle on.
    """
    import math
    return math.sqrt(3.0 * gamma * p_inf_pa / rho) / (2.0 * math.pi)


def _blake_threshold_atm(R0_m: float, p_inf_atm: float = 1.0,
                          sigma: float = 0.0728) -> float:
    """Approximate Blake threshold P_A in atm for a bubble of radius R₀.

    `P_B ≈ p_∞ × √(1 + (8σ/(3p_∞ R₀))³ × (4/27))` — simplified Blake,
    ignoring viscous + non-condensable corrections. Adequate for a live
    UI status chip; not a substitute for `cavplasma.seed.blake_threshold`.
    """
    import math
    p_inf_pa = p_inf_atm * 101_325.0
    surface_term = 2.0 * sigma / R0_m
    if surface_term <= 0:
        return p_inf_atm
    P_B_pa = p_inf_pa * (1.0 + (4.0 / 27.0) * (surface_term / p_inf_pa) ** 1.5)
    return P_B_pa / 101_325.0


def _classify_live(drive_f_hz: float, drive_pa_atm: float, R0_m: float,
                    p_inf_atm: float = 1.0,
                    chamber_radius_m: float = 0.05,
                    chamber_c: float = 1482.0,
                    chamber_Q: float = 1000.0) -> tuple[str, str]:
    """Return (severity, message) for the live status chip.

    severity ∈ {"success", "warning", "danger", "secondary"}.

    Rough analytical regime predictor — uses Blake threshold, off-
    resonance attenuation, and a P_A/p_∞ → R_max/R₀ scaling to
    decide which regime the configuration is heading toward, without
    running the simulator.
    """
    import math

    # 1. Sub-Blake check
    P_B = _blake_threshold_atm(R0_m, p_inf_atm)
    if drive_pa_atm < P_B:
        return ("secondary",
                f"sub-Blake — P_A {drive_pa_atm:.2f} atm below "
                f"threshold ≈ {P_B:.2f} atm. Increase drive amplitude "
                f"or reduce R₀.")

    # 2. Off-resonance check — only warn for *severe* off-mode drives.
    # Geometric eigenmodes are stricter than real chambers (which have
    # structural compliance broadening Q-bandwidth), so let near-mode
    # drives pass silently. Threshold = 250× attenuation, chosen so
    # SBSL canonical (~212×) and the n=4 stable preset (~65×) don't
    # false-positive but the user's 1 MHz / 10 kHz traps (>600×) fire.
    modes = [n * chamber_c / (2.0 * chamber_radius_m) for n in (1, 2, 3, 4)]
    f_closest = min(modes, key=lambda f: abs(f - drive_f_hz))
    Δf = drive_f_hz - f_closest
    atten = math.sqrt(1.0 + (Δf * 2.0 * chamber_Q / f_closest) ** 2)
    if atten > 1000.0:
        return ("danger",
                f"far off-resonance ({atten:.0f}× attenuation; closest "
                f"mode {f_closest/1000:.1f} kHz). Real-world drive at "
                f"the bubble would be negligible.")
    if atten > 250.0:
        return ("warning",
                f"off-resonance ({atten:.0f}× attenuation; closest mode "
                f"{f_closest/1000:.1f} kHz). Move drive freq to a chamber "
                f"mode for realistic transducer drive.")

    # 3. Estimate R_max/R₀ from P_A/p_∞ — empirical fit calibrated
    # against Lofstedt 1995 / Hilgenfeldt-Lohse SBSL data:
    #   P_A/p_∞ = 1.32 → R_max/R₀ ≈ 8 (SBSL canonical)
    #   P_A/p_∞ = 1.5  → R_max/R₀ ≈ 12 (Suslick H₂SO₄+Xe)
    # Linear fit: R_max/R₀ ≈ 22 · (P_A/p_∞ - 1) + 1, clipped at 1.
    pa_ratio = drive_pa_atm / p_inf_atm
    if pa_ratio <= 1.0:
        return ("warning",
                f"drive/p_∞ ratio {pa_ratio:.2f} ≤ 1 — bubble pressure "
                f"won't reverse. Increase drive_pa to push past p_∞.")
    R_max_over_R0 = max(1.0, 22.0 * (pa_ratio - 1.0) + 1.0)

    # 4. Predict regime from R_max/R₀
    if R_max_over_R0 < 3.0:
        return ("warning",
                f"linear regime — R_max/R₀ ≈ {R_max_over_R0:.1f} < 3. "
                f"Bubble won't collapse violently. Increase P_A.")
    if R_max_over_R0 > 20.0:
        return ("danger",
                f"unstable likely — R_max/R₀ ≈ {R_max_over_R0:.1f} > 20. "
                f"Shape modes will grow; bubble will fragment. Reduce P_A "
                f"or R₀.")
    if R_max_over_R0 > 12.0:
        return ("warning",
                f"violent regime — R_max/R₀ ≈ {R_max_over_R0:.1f} (5–12 "
                f"is the sweet spot). Mach likely > 0.3. Reduce P_A.")

    return ("success",
            f"in SBSL band — R_max/R₀ ≈ {R_max_over_R0:.1f}, on-mode, "
            f"above Blake. Click TEST to verify.")


def _adapt_partner_slider(triggered: str,
                            drive_f_hz: float, drive_pa_atm: float, R0_m: float,
                            p_inf_atm: float, gamma: float, rho: float,
                            ) -> tuple[Optional[float], Optional[float]]:
    """Return (new_drive_f_hz, new_R0_m) where one is no_update.

    Coupling rule: hold the user-touched slider fixed, adapt the
    *other one of (drive_f, R₀)* so the drive/Minnaert ratio stays
    constant. drive_pa is not adapted — user controls it independently.
    """
    K = _minnaert_constant(p_inf_atm * 101_325.0, gamma, rho)  # f_M·R₀ const
    if triggered == "drive_f":
        # Use the canonical SBSL drive/Minnaert ratio of 0.033.
        # f_M_target = drive_f / 0.033 → R₀_target = K / f_M_target
        f_M_target = drive_f_hz / 0.033
        R0_target = K / f_M_target if f_M_target > 0 else R0_m
        return None, R0_target
    if triggered == "bubble_R0":
        f_M_target = K / R0_m if R0_m > 0 else 1.0
        f_drive_target = f_M_target * 0.033
        return f_drive_target, None
    return None, None


def autodesign_find(target_T_kK: float, must_be_stable: bool,
                     max_transducer_atm: float,
                     base_scenario_payload: Optional[str],
                     ) -> tuple[Optional[str], str, list]:
    """Heuristic auto-design — instant. Returns (payload, status, diagnostic_rows)."""
    from cavplasma.suggestions import (
        DesignTarget, DesignConstraints, initial_design,
    )
    base = scenario_from_store(base_scenario_payload) or None
    target = DesignTarget(
        T_peak_K=float(target_T_kK) * 1000.0,
        must_be_stable_spherical=bool(must_be_stable),
        feasible_transducer_atm=float(max_transducer_atm),
    )
    constraints = DesignConstraints()
    try:
        designed, diag = initial_design(target, constraints, base=base)
    except Exception as exc:                                            # noqa: BLE001
        return None, f"design failed: {type(exc).__name__}: {exc}", []
    rows = [
        html.Li(diag.get("drive_freq_rationale", "")),
        html.Li(diag.get("R0_rationale", "")),
        html.Li(diag.get("P_A_rationale", "")),
    ]
    diagnostic = html.Div([
        html.Em("how it picked the parameters:"),
        html.Ul(rows, style={"marginTop": "0.4em",
                             "paddingLeft": "1.2em"}),
    ])
    return (
        scenario_to_store(designed),
        f"design loaded — TEST to verify it hits {target_T_kK:.0f} kK",
        diagnostic,
    )


def autodesign_refine(target_T_kK: float, must_be_stable: bool,
                       max_transducer_atm: float,
                       scenario_payload: Optional[str],
                       ) -> tuple[Optional[str], str, list]:
    """Refine via 3×3 grid search — slower but better. Same outputs."""
    from cavplasma.suggestions import DesignTarget, refine_design
    s = scenario_from_store(scenario_payload)
    if s is None:
        return None, "no scenario to refine — click 'Find parameters' first", []
    target = DesignTarget(
        T_peak_K=float(target_T_kK) * 1000.0,
        must_be_stable_spherical=bool(must_be_stable),
        feasible_transducer_atm=float(max_transducer_atm),
    )
    try:
        refined, diag = refine_design(s, target)
    except Exception as exc:                                            # noqa: BLE001
        return None, f"refine failed: {type(exc).__name__}: {exc}", []
    best = diag.get("best_summary", {})
    rows: list = [
        html.Li(f"evaluated {diag.get('n_evaluations', 0)} grid points"),
        html.Li(f"best score = {diag.get('best_score', 0):.3f} (lower is better)"),
    ]
    if best:
        rows.extend([
            html.Li(f"best regime = {best.get('regime', '?')}"),
            html.Li(f"best T_peak = {best.get('T_peak_K', 0):.0f} K"),
            html.Li(f"best R_max = {best.get('R_max_um', 0):.1f} µm"),
            html.Li(f"best Mach = {best.get('wall_mach', 0):.3f}"),
        ])
    diagnostic = html.Div([
        html.Em("refinement summary:"),
        html.Ul(rows, style={"marginTop": "0.4em",
                             "paddingLeft": "1.2em"}),
    ])
    return (
        scenario_to_store(refined),
        f"refined — TEST to verify it lands stably",
        diagnostic,
    )


def render_regime_card(result_payload: Optional[dict]) -> Any:
    if not result_payload:
        return dbc.Alert("No run yet — click TEST to populate.",
                         color="secondary")
    summary = result_payload.get("summary", {})
    regime = summary.get("regime", "stable_spherical")
    color = {
        "stable_spherical":   "success",
        "marginal":           "warning",
        "unstable_likely":    "danger",
        "sub_blake":          "secondary",
        "linear_oscillation": "warning",     # dossier §16/§17 — yellow, not green
        "transducer_limited": "danger",
    }.get(regime, "info")
    desc = REGIME_DESCRIPTION.get(regime, "")
    rationale = summary.get("regime_rationale") or []

    # Build the audit-trail expandable. Each entry is [name, status, detail].
    # FIRED is the rule that picked the label; PASS rules are why earlier
    # checks didn't match. We render FIRED in bold + the regime colour
    # and PASS muted; SKIP italicised.
    audit_rows = []
    for entry in rationale:
        if not entry or len(entry) < 3:
            continue
        name, status, detail = entry[0], entry[1], entry[2]
        if status == "FIRED":
            badge_color = {"FIRED": color}.get(status, "secondary")
            audit_rows.append(html.Div([
                dbc.Badge(status, color=badge_color, className="me-2"),
                html.B(name), html.Span(" — "), html.Span(detail),
            ], className="mb-1"))
        elif status == "PASS":
            audit_rows.append(html.Div([
                dbc.Badge(status, color="secondary",
                          className="me-2", style={"opacity": 0.6}),
                html.Span(name, style={"opacity": 0.7}),
                html.Span(" — ", style={"opacity": 0.7}),
                html.Small(detail, style={"opacity": 0.7}),
            ], className="mb-1"))
        else:  # SKIP
            audit_rows.append(html.Div([
                dbc.Badge(status, color="light", text_color="muted",
                          className="me-2"),
                html.Em(name, style={"opacity": 0.5}),
                html.Em(" — " + detail, style={"opacity": 0.5}),
            ], className="mb-1"))

    audit_block = []
    if audit_rows:
        audit_block = [
            html.Hr(className="my-2"),
            html.Details([
                html.Summary("why this regime?",
                             style={"cursor": "pointer", "fontSize": "0.85em"}),
                html.Div(audit_rows, className="mt-2", style={"fontSize": "0.8em"}),
            ]),
        ]

    return dbc.Alert(
        [html.B(regime), html.Br(), desc] + audit_block,
        color=color,
    )


def render_headline_table(result_payload: Optional[dict]) -> list:
    if not result_payload:
        return []
    rows = figures.headline_summary_text(result_payload)
    return [
        html.Tr([html.Td(label), html.Td(value)]) for label, value in rows
    ]


def render_suggestions(result_payload: Optional[dict]) -> list:
    if not result_payload:
        return [html.Em("No run yet.")]
    items: list = []
    for sg in result_payload.get("suggestions", []):
        if sg["category"] == "caveat":
            continue
        sev_color = SEVERITY_COLOR.get(sg["severity"], "#444")
        items.append(html.Div([
            html.Div([
                html.Span(f"[{sg['severity']}/{sg['rule_id']}]",
                          style={"color": sev_color, "fontWeight": "bold"}),
                html.Span(" "),
                html.Span(sg["message"]),
            ]),
            html.Div([
                html.Em(sg["rationale"]), html.Br(),
                html.Small(sg["dossier_ref"], style={"color": "#aaa"}),
            ], style={"marginLeft": "1em", "fontSize": "0.85em"}),
        ], className="mb-2"))
    if not items:
        items = [html.Em("No actionable suggestions for this run.")]
    return items


def render_caveats(result_payload: Optional[dict]) -> list:
    if not result_payload:
        return []
    items: list = []
    for sg in result_payload.get("suggestions", []):
        if sg["category"] != "caveat":
            continue
        items.append(html.Div([
            html.Span(f"[{sg['rule_id']}] ", style={"fontWeight": "bold"}),
            html.Span(sg["message"]),
            html.Br(),
            html.Small(sg["dossier_ref"], style={"color": "#aaa"}),
        ], className="mb-2"))
    return items or [html.Em("(none)")]


def wall_pressure_capability(scenario: Any) -> dict:
    """Compute the wall material's pressure ratings for the current chamber.

    Returns a dict with four MPa-valued caps:

      * static_yield_MPa   — DC internal pressure causing wall yield
                              (Tresca, thick sphere): P = (2/3)·σ_Y·(1−(a/b)³)
      * static_collapse_MPa — DC pressure for full-section plastic collapse:
                              P = 2·σ_Y·ln(b/a)
      * dynamic_yield_MPa  — single-impulse yield (p_Y_dynamic, ~1.5–2× σ_Y)
      * fatigue_MPa        — high-cycle fatigue limit (relevant for SBSL
                              continuous operation, ~10⁹ shock cycles)

    Different ratings apply to different scenarios:

      * pistol_shrimp / single-shot impulse → compare peak wall pressure
        to dynamic_yield_MPa
      * SBSL continuous operation         → compare to fatigue_MPa
      * static ambient `p_∞` only         → compare to static_yield_MPa
    """
    import math
    chamber = scenario.chamber
    wall = chamber.wall_material
    a = max(chamber.radius, 1e-6)
    b = a + max(chamber.wall_thickness, 1e-6)

    # Tresca thick-sphere — only valid for closed cavities (sphere /
    # cylinder). Open-bath geometries don't have a wall pressure rating.
    if chamber.geometry not in ("sphere", "cylinder_axial", "cylinder_radial"):
        return {
            "geometry_supports_wall": False,
            "static_yield_MPa": None,
            "static_collapse_MPa": None,
            "dynamic_yield_MPa": None,
            "fatigue_MPa": None,
            "wall_name": wall.name if wall else "n/a",
        }

    # σ_Y is in Pa; thickness ratio gives a dimensionless multiplier.
    sigma_Y = max(wall.sigma_Y, 1.0)
    static_yield = (2.0 / 3.0) * sigma_Y * (1.0 - (a / b) ** 3)
    static_collapse = 2.0 * sigma_Y * math.log(b / a)

    # Dynamic & fatigue limits are absolute material caps — same factor
    # of (1 − (a/b)³) applied so the geometry shows up.
    dynamic_yield = (2.0 / 3.0) * wall.p_Y_dynamic * (1.0 - (a / b) ** 3)
    fatigue = (2.0 / 3.0) * wall.fatigue_limit * (1.0 - (a / b) ** 3)

    return {
        "geometry_supports_wall": True,
        "static_yield_MPa": static_yield / 1e6,
        "static_collapse_MPa": static_collapse / 1e6,
        "dynamic_yield_MPa": dynamic_yield / 1e6,
        "fatigue_MPa": fatigue / 1e6,
        "wall_name": wall.name,
        "wall_thickness_mm": chamber.wall_thickness * 1000.0,
        "chamber_radius_cm": chamber.radius * 100.0,
    }


_LIQUID_INTRO: dict[str, str] = {
    "water": ("Standard cavitation reference. Most published SBSL data "
               "is in water. High vapor pressure (~2.3 kPa) puts ~3 kPa of "
               "water vapor inside the bubble; that vapor's vibrational/"
               "rotational modes absorb collapse energy → T_peak typically "
               "15–25 kK."),
    "seawater": ("Pistol-shrimp's natural medium. ~3% denser and stiffer "
                  "than fresh water. Salinity barely changes vapor pressure, "
                  "so collapse violence and T_peak are similar to water."),
    "glycerin": ("Hot SBSL without acid. Viscosity is ~1400× water → "
                  "bubbles are ultra-shape-stable; you can drive them past "
                  "the usual instability limit. Vapor pressure is "
                  "near-zero → no endothermic quenching → T_peak runs "
                  "~25 kK with Ar gas. Viscous and hard to clean."),
    "sulfuric_98": ("The Suslick recipe — concentrated H₂SO₄. "
                     "Near-zero vapor pressure + the densest liquid in the "
                     "catalog → the most violent SBSL collapse on record. "
                     "T_peak hits 30–40 kK with Xe gas (Flannigan & Suslick "
                     "2005). CORROSIVE: PTFE seals only, exhaust hood, "
                     "full PPE."),
    "silicone_oil_100cSt": ("Inert lab-research liquid. Very viscous "
                              "and low surface tension → clean platform for "
                              "studying shape-mode growth. Lowest sound "
                              "speed in the catalog (980 m/s vs 1480 in "
                              "water) shifts every chamber resonance ~33% "
                              "lower."),
}


def render_liquid_properties_card(scenario: Any) -> Any:
    """Catalog properties of the current liquid + T/p-corrected sound
    speed + interpretive notes. Updates live as the user changes
    `liquid` / `T_∞` / `p_∞`.
    """
    if scenario is None or scenario.liquid is None:
        return html.Em("Pick a liquid to see properties.",
                        style={"opacity": 0.6})
    liq = scenario.liquid
    amb = scenario.ambient

    # T/p-corrected sound speed (the value the simulator actually uses).
    try:
        from cavplasma.liquids import corrected_sound_speed_for
        c_corrected = corrected_sound_speed_for(liq, amb)
    except Exception:                                                    # noqa: BLE001
        c_corrected = liq.c
    Z_corrected_MRayl = liq.rho * c_corrected / 1e6

    # Vapor-pressure regime classification.
    if liq.p_v < 10.0:
        pv_label = "near-zero — no quenching, hot plasma possible"
        pv_color = "#859900"      # solarized green
    elif liq.p_v < 1000.0:
        pv_label = "low — mild quenching"
        pv_color = "#b58900"      # solarized yellow
    else:
        pv_label = "high — vapor strongly quenches T_peak"
        pv_color = "#cb4b16"      # solarized orange

    # Viscosity regime classification.
    if liq.mu < 5e-3:
        mu_label = "low — normal shape modes"
        mu_color = None
    elif liq.mu < 0.1:
        mu_label = "moderate — some damping"
        mu_color = "#b58900"
    else:
        mu_label = "high — bubbles ultra-stable"
        mu_color = "#268bd2"

    rows = [
        html.Tr([html.Td("Name"),
                  html.Td(html.Code(liq.name,
                                     style={"fontSize": "0.9em"}))]),
        html.Tr([html.Td("Density ρ"),
                  html.Td(f"{liq.rho:.0f} kg/m³")]),
        html.Tr([html.Td("Sound speed (catalog, 20 °C / 1 atm)"),
                  html.Td(f"{liq.c:.0f} m/s")]),
        html.Tr([html.Td("Sound speed (current T, p)"),
                  html.Td(f"{c_corrected:.0f} m/s   (Δ {c_corrected-liq.c:+.0f})")]),
        html.Tr([html.Td("Acoustic impedance Z = ρc"),
                  html.Td(f"{Z_corrected_MRayl:.2f} MRayl")]),
        html.Tr([html.Td("Viscosity μ"),
                  html.Td([f"{liq.mu:.2e} Pa·s   ",
                           html.Em(mu_label,
                                    style={"color": mu_color,
                                           "opacity": 0.85})])]),
        html.Tr([html.Td("Surface tension σ"),
                  html.Td(f"{liq.sigma*1000:.1f} mN/m")]),
        html.Tr([html.Td("Vapor pressure p_v"),
                  html.Td([f"{liq.p_v:.1f} Pa   ",
                           html.Em(pv_label,
                                    style={"color": pv_color,
                                           "opacity": 0.9})])]),
        html.Tr([html.Td("Tait (B, n)"),
                  html.Td(f"{liq.B_tait/1e6:.0f} MPa, n = {liq.n_tait:.2f}")]),
        html.Tr([html.Td("B/A nonlinearity"),
                  html.Td(f"{liq.beta_BoverA:.1f}")]),
        html.Tr([html.Td("Absorption"),
                  html.Td(f"{liq.alpha_dB_cm_MHz2:.3f} dB/(cm·MHz²)")]),
    ]

    intro = _LIQUID_INTRO.get(liq.name)
    intro_block = []
    if intro:
        intro_block = [
            dbc.Alert(intro, color="info", className="py-2 mb-2",
                       style={"fontSize": "0.83em"}),
        ]

    return html.Div(intro_block + [
        dbc.Table(html.Tbody(rows), striped=True, hover=False, size="sm",
                   className="mb-0", style={"fontSize": "0.85em"}),
    ])


def render_wall_capability_card(scenario: Any,
                                  result_payload: Optional[dict]) -> Any:
    """UI card showing what the wall can take vs what the run delivers.

    Pulls wall_pressure_capability() for the static numbers, then if a
    result is available shows peak wall pressure from the §13 observer
    and a colour-coded margin.
    """
    if scenario is None:
        return html.Em("Pick a chamber to see wall ratings.",
                        style={"opacity": 0.6})
    cap = wall_pressure_capability(scenario)
    if not cap.get("geometry_supports_wall"):
        return html.Div([
            html.Em(f"Geometry '{scenario.chamber.geometry}' has no closed "
                     f"wall — pressure ratings don't apply."),
        ], className="text-muted small")

    rows = [
        html.Tr([html.Td("Wall material"), html.Td(cap["wall_name"])]),
        html.Tr([html.Td("Geometry"),
                  html.Td(f"R={cap['chamber_radius_cm']:.1f} cm, "
                          f"t={cap['wall_thickness_mm']:.1f} mm")]),
        html.Tr([html.Td("Static yield (DC pressure)"),
                  html.Td(f"{cap['static_yield_MPa']:.1f} MPa")]),
        html.Tr([html.Td("Static plastic collapse"),
                  html.Td(f"{cap['static_collapse_MPa']:.1f} MPa")]),
        html.Tr([html.Td("Dynamic yield (single shock)"),
                  html.Td(f"{cap['dynamic_yield_MPa']:.1f} MPa")]),
        html.Tr([html.Td("Fatigue limit (cyclic)"),
                  html.Td(f"{cap['fatigue_MPa']:.1f} MPa")]),
    ]

    # Compare against the actual peak wall pressure from §13 observer.
    margin_block: list = []
    if result_payload:
        wall_loads = result_payload.get("wall_loads") or {}
        peak_wall_pa = 0.0
        # observer_traces may include a stress probe with a wall_pressure col
        for sub in (result_payload.get("observer_traces") or {}).values():
            wp = sub.get("wall_pressure") or []
            if wp:
                try:
                    peak_wall_pa = max(peak_wall_pa, max(abs(x) for x in wp))
                except ValueError:
                    pass
        if peak_wall_pa <= 0.0:
            # Fall back to peak_pressure_at_observer (hydrophone) as a
            # rough proxy when no stress probe was attached.
            for v in (result_payload.get("summary", {})
                       .get("peak_pressure_at_observer") or {}).values():
                peak_wall_pa = max(peak_wall_pa, abs(float(v or 0.0)))
        if peak_wall_pa > 0.0:
            peak_MPa = peak_wall_pa / 1e6
            # Compute margins
            dyn_margin = (cap["dynamic_yield_MPa"] - peak_MPa) \
                / max(cap["dynamic_yield_MPa"], 1e-9)
            fat_margin = (cap["fatigue_MPa"] - peak_MPa) \
                / max(cap["fatigue_MPa"], 1e-9)
            colour = ("success" if peak_MPa < cap["fatigue_MPa"]
                       else "warning" if peak_MPa < cap["dynamic_yield_MPa"]
                       else "danger")
            verdict = (
                "OK — peak below fatigue limit, chamber survives "
                "indefinite cycling." if colour == "success"
                else "Cyclic risk — peak above fatigue limit but below "
                "dynamic yield. Single-shot OK, repeat use erodes the wall."
                if colour == "warning"
                else "Wall failure — peak EXCEEDS dynamic yield. The "
                "chamber would crack on this shot."
            )
            margin_block = [
                html.Hr(className="my-2"),
                html.Div([
                    html.B(f"Peak wall pressure: {peak_MPa:.1f} MPa"),
                    html.Br(),
                    html.Span(f"vs dynamic yield: margin {dyn_margin*100:+.0f}%"),
                    html.Br(),
                    html.Span(f"vs fatigue limit: margin {fat_margin*100:+.0f}%"),
                ]),
                dbc.Alert(verdict, color=colour, className="py-1 mt-2 mb-0",
                           style={"fontSize": "0.85em"}),
            ]

    return html.Div([
        dbc.Table(html.Tbody(rows), striped=True, hover=False, size="sm",
                   className="mb-0", style={"fontSize": "0.85em"}),
    ] + margin_block)


def render_material_summary(result_payload: Optional[dict]) -> list:
    if not result_payload:
        return []
    pieces: list = []
    er = result_payload.get("erosion")
    if er:
        pieces.append(html.Div([
            html.B("Wall: "),
            f"{er['material_name']} · severity {er['severity']:.2e} · ",
            f"T_inc {er['T_inc_hours']:.0f} h · ",
            f"MDPR {er['MDPR_um_per_h']:.2f} µm/h",
        ]))
    tx = result_payload.get("transducer_lifetime")
    if tx:
        pieces.append(html.Div([
            html.B("Transducer: "),
            f"{tx['grade']} · {tx['lifetime_hours']:.0f} h · ",
            f"T_steady {tx['steady_state_T_K']:.0f} K · {tx['notes']}",
        ]))
    th = result_payload.get("thermal_state")
    if th:
        pieces.append(html.Div([
            html.B("Thermal: "),
            f"ΔT {th['delta_T_steady_K']:.1f} K · ",
            f"τ {th['time_constant_s']:.0f} s · ",
            ("will boil" if th["will_boil"] else "stable"),
        ]))
    return pieces or [html.Em("(no §13 data)")]


# ===========================================================================
# Animation
# ===========================================================================
def animation_frame_figure(
    scenario_payload: Optional[str],
    result_payload: Optional[dict],
    frame_idx: int,
) -> go.Figure:
    """Return the standing-wave field figure at the requested frame.

    Frames cycle through one acoustic period at the current drive freq.
    The expensive spatial-factor evaluation is cached inside
    `figures._spatial_field_grid`, so each frame is essentially a
    multiply + figure construction.
    """
    s = scenario_from_store(scenario_payload)
    if s is None:
        return _empty("Standing wave field")
    drv = next(iter(s.drive.waveforms.values()), None)
    if drv is None or drv.P_A == 0.0 or drv.f <= 0.0:
        return figures.standing_wave_field_figure(s, t_anim=0.0, n_grid=40)
    period = 1.0 / drv.f
    n_frames = ANIMATION_FRAME_BUDGET
    t = (frame_idx % n_frames) / n_frames * period
    return figures.standing_wave_field_figure(s, t_anim=t, n_grid=40)


def _animation_time_readout(scenario_payload: Optional[str], frame_idx: int) -> str:
    """Format a 'frame N/60 · t = X.XX µs / period Y.YY µs' caption."""
    from cavplasma.ui.style import ANIMATION_FRAME_BUDGET
    s = scenario_from_store(scenario_payload)
    base = f"frame {int(frame_idx)}/{ANIMATION_FRAME_BUDGET}"
    if s is None:
        return base
    drv = next(iter(s.drive.waveforms.values()), None)
    if drv is None or drv.f <= 0.0 or drv.P_A == 0.0:
        return base
    period_s = 1.0 / drv.f
    t_us = (frame_idx / ANIMATION_FRAME_BUDGET) * period_s * 1e6
    period_us = period_s * 1e6
    return f"{base} · t = {t_us:.3f} µs / {period_us:.2f} µs"


# ===========================================================================
# Audio (Listen button)
# ===========================================================================
def render_audio(result_payload: Optional[dict]) -> str:
    """Build a base64 data: URI from the hydrophone observer trace."""
    if not result_payload:
        return ""
    obs = result_payload.get("observer_traces", {})
    # Find a hydrophone-like observer trace
    target = None
    for name, sub in obs.items():
        if "p_rad" in sub or "V" in sub:
            target = sub
            break
    if target is None:
        return ""
    t = np.array(target.get("time", []))
    V = np.array(target.get("V", target.get("p_rad", [])))
    if len(t) < 2 or len(V) < 2:
        return ""
    wav = hydrophone_to_wav(t, V, pitch_factor=8.0,
                             target_duration_s=2.0)
    return wav_to_data_uri(wav)


# ===========================================================================
# Notebook (§15.6)
# ===========================================================================
def append_notebook(
    result_payload: Optional[dict],
    notebook: list,
) -> list:
    if not result_payload:
        return notebook
    summary = result_payload.get("summary", {})
    entry = {
        "timestamp": result_payload.get("timestamp", ""),
        "wall_clock_s": result_payload.get("wall_clock_s", 0.0),
        "regime": summary.get("regime", ""),
        "T_peak_K": summary.get("T_peak_K", 0.0),
        "n_e_peak": summary.get("n_e_peak", 0.0),
        "photons_4pi": summary.get("photons_visible_4pi", 0.0),
        "R_max_um": summary.get("R_max", 0.0) * 1e6,
        "wall_mach": summary.get("wall_mach_peak", 0.0),
    }
    new_notebook = list(notebook or []) + [entry]
    if len(new_notebook) > NOTEBOOK_MAX_ENTRIES:
        new_notebook = new_notebook[-NOTEBOOK_MAX_ENTRIES:]
    return new_notebook


def render_notebook_regime_strip(notebook: list) -> Any:
    """Build a horizontal strip of coloured tiles, one per notebook entry.

    Each tile is coloured by the run's regime (REGIME_COLOR) and tooltipped
    with the entry index + regime + key headline numbers. Pattern-finding
    sweeps look like a banded rainbow: sub_blake (grey) → linear_oscillation
    (yellow) → stable_spherical (green) → marginal (amber) → unstable_likely
    (red). Spotting the green band is the goal.
    """
    if not notebook:
        return html.Em("No runs yet — TEST a scenario to begin.",
                        style={"opacity": 0.5, "fontSize": "0.85em"})
    tiles = []
    for i, entry in enumerate(notebook):
        regime = entry.get("regime", "") or "unknown"
        color = REGIME_COLOR.get(regime, "#444")
        tooltip = (f"#{i+1}  {regime}\n"
                    f"T_peak = {entry.get('T_peak_K', 0):.0f} K\n"
                    f"R_max = {entry.get('R_max_um', 0):.1f} µm\n"
                    f"Mach = {entry.get('wall_mach', 0):.3f}\n"
                    f"photons = {entry.get('photons_4pi', 0):.1e}")
        tiles.append(html.Div(
            "",
            title=tooltip,
            style={
                "backgroundColor": color,
                "minWidth": "16px",
                "height": "24px",
                "borderRight": "1px solid #002b36",
                "flex": "1",
                "cursor": "help",
            },
        ))
    return html.Div([
        html.Small("regime history (oldest → newest)",
                   className="text-muted",
                   style={"fontSize": "0.75em"}),
        html.Div(
            tiles,
            style={
                "display": "flex",
                "flexDirection": "row",
                "border": "1px solid #586e75",
                "borderRadius": "3px",
                "overflow": "hidden",
                "marginTop": "2px",
            },
        ),
    ])


def render_notebook_table(notebook: list) -> Any:
    if not notebook:
        return html.Em("No runs yet.")
    rows = [
        html.Tr([
            html.Td(i + 1),
            html.Td(entry["timestamp"][:19].replace("T", " ")),
            html.Td(f"{entry['wall_clock_s']:.2f}"),
            html.Td(entry["regime"]),
            html.Td(f"{entry['T_peak_K']:.0f}"),
            html.Td(f"{entry['photons_4pi']:.2e}"),
            html.Td(f"{entry['R_max_um']:.1f}"),
            html.Td(f"{entry['wall_mach']:.2f}"),
        ])
        for i, entry in enumerate(notebook)
    ]
    return dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("#"), html.Th("timestamp"), html.Th("wall (s)"),
                html.Th("regime"), html.Th("T_peak (K)"),
                html.Th("photons 4π"), html.Th("R_max (µm)"),
                html.Th("Mach"),
            ])),
            html.Tbody(rows),
        ],
        striped=True, hover=True, size="sm",
    )


def notebook_to_csv_bytes(notebook: list) -> str:
    if not notebook:
        return "timestamp,wall_clock_s,regime,T_peak_K,n_e_peak,photons_4pi,R_max_m,wall_mach_peak\n"
    df = pd.DataFrame(notebook)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


# ===========================================================================
# Helpers
# ===========================================================================
def _empty(title: str) -> go.Figure:
    from cavplasma.ui.style import PLOT_TEMPLATE
    fig = go.Figure()
    fig.update_layout(template=PLOT_TEMPLATE, title=title, height=220,
                      margin=dict(l=20, r=20, t=40, b=40),
                      annotations=[dict(text="(no data yet)", x=0.5, y=0.5,
                                         xref="paper", yref="paper",
                                         showarrow=False,
                                         font=dict(size=12, color="#aaa"))])
    return fig


# ===========================================================================
# Server-side cache for the latest live ScenarioResult — needed for the
# spectrum surface (full em.S_t_lambda is too big for dcc.Store).
# ===========================================================================
_LATEST_RESULT: dict[str, Any] = {"result": None}


def cache_latest_result(result: Any) -> None:
    _LATEST_RESULT["result"] = result


def latest_cached_result() -> Optional[Any]:
    return _LATEST_RESULT.get("result")


# ===========================================================================
# Callback registration — called by app.py
# ===========================================================================
def register_callbacks(app: Any) -> None:
    """Wire all @callback decorators onto the Dash app."""

    # ----------------------------------------------------------------------
    # Preset flow: dropdown → confirmation modal → apply (+ sync controls)
    # ----------------------------------------------------------------------
    @app.callback(
        Output("preset_modal", "is_open"),
        Output("preset_pending", "data"),
        Output("preset_modal_name", "children"),
        Input("preset_dropdown", "value"),
        State("preset_last_loaded", "data"),
        prevent_initial_call=True,
    )
    def _open_preset_modal(value, last_loaded):                         # noqa: ANN001
        # Skip the confirmation when the dropdown is being silently reverted
        # by `_cancel_preset` (value == last_loaded means no real change).
        if not value or value == last_loaded:
            return False, None, no_update
        return True, value, value

    @app.callback(
        Output("scenario_store", "data", allow_duplicate=True),
        Output("preset_modal", "is_open", allow_duplicate=True),
        Output("preset_last_loaded", "data"),
        Output("scenario_source_label", "children", allow_duplicate=True),
        Output("liquid_dropdown", "value"),
        Output("ambient_T", "value"),
        Output("ambient_p", "value"),
        Output("drive_f", "value"),
        Output("drive_pa", "value"),
        Output("drive_cycles", "value"),
        Output("bubble_R0", "value"),
        Output("gas_ar", "value"),
        Output("gas_h2o", "value"),
        Output("gas_air", "value"),
        Output("phys_bubble_eq", "value"),
        Output("phys_thermal", "value"),
        Output("phys_ionization", "value"),
        Output("num_rtol", "value"),
        Output("num_conv", "value"),
        Output("chamber_geometry", "value"),
        Output("chamber_radius_cm", "value"),
        Output("chamber_wall", "value"),
        Output("chamber_Q", "value"),
        Input("preset_modal_confirm", "n_clicks"),
        State("preset_pending", "data"),
        prevent_initial_call=True,
    )
    def _confirm_preset(n_clicks, pending):                             # noqa: ANN001
        if not n_clicks or not pending:
            return [no_update] * 23
        try:
            payload = apply_preset(pending)
        except Exception:                                               # noqa: BLE001
            return [no_update] * 23
        scenario = scenario_from_store(payload)
        ctrls = scenario_to_control_values(scenario)
        return (
            payload,                          # scenario_store
            False,                            # close modal
            pending,                          # preset_last_loaded
            f"loaded preset · {pending}",     # scenario_source_label
            ctrls["liquid_dropdown"],
            ctrls["ambient_T"],
            ctrls["ambient_p"],
            ctrls["drive_f"],
            ctrls["drive_pa"],
            ctrls["drive_cycles"],
            ctrls["bubble_R0"],
            ctrls["gas_ar"],
            ctrls["gas_h2o"],
            ctrls["gas_air"],
            ctrls["phys_bubble_eq"],
            ctrls["phys_thermal"],
            ctrls["phys_ionization"],
            ctrls["num_rtol"],
            ctrls["num_conv"],
            ctrls["chamber_geometry"],
            ctrls["chamber_radius_cm"],
            ctrls["chamber_wall"],
            ctrls["chamber_Q"],
        )

    @app.callback(
        Output("preset_modal", "is_open", allow_duplicate=True),
        Output("preset_dropdown", "value"),
        Input("preset_modal_cancel", "n_clicks"),
        State("preset_last_loaded", "data"),
        prevent_initial_call=True,
    )
    def _cancel_preset(n_clicks, last_loaded):                          # noqa: ANN001
        if not n_clicks:
            return no_update, no_update
        # Revert dropdown to the last confirmed value (or back to placeholder
        # if nothing has been loaded yet).
        return False, last_loaded

    # ----------------------------------------------------------------------
    # Bidirectional slider ↔ input sync. Each numeric slider has a
    # paired clickable input box (built by `_slider_with_input` in the
    # layout). Two clientside callbacks per pair:
    #
    #   slider -> input : mirror the slider's value into the input
    #   input  -> slider: snap the slider to the typed value
    #
    # For log-scale sliders (ambient_p, bubble_R0) the slider stores
    # the log value while the input shows the linear value; the
    # conversion is in the JS callback. Equality guard (>1e-6 abs diff)
    # breaks the loop when both sides agree.
    # ----------------------------------------------------------------------
    def _wire_slider_input_pair(slider_id, input_id, scale="linear"):
        """Register two clientside callbacks for one slider/input pair.

        scale="linear": values are equal between slider and input.
        scale="log10":  slider stores log₁₀(x); input shows x.
        """
        # slider -> input
        if scale == "log10":
            slider_to_input_js = f"""
            function(slider_value, current_input) {{
                if (slider_value === null || slider_value === undefined) return current_input;
                const linear = Math.pow(10, slider_value);
                if (current_input !== null && current_input !== undefined
                    && Math.abs((Math.log10(current_input) - slider_value)) < 0.001)
                    return current_input;
                return Math.round(linear * 100) / 100;
            }}
            """
        else:
            slider_to_input_js = f"""
            function(slider_value, current_input) {{
                if (slider_value === null || slider_value === undefined) return current_input;
                if (current_input !== null && current_input !== undefined
                    && Math.abs(current_input - slider_value) < 1e-6)
                    return current_input;
                return slider_value;
            }}
            """
        app.clientside_callback(
            slider_to_input_js,
            Output(input_id, "value"),
            Input(slider_id, "value"),
            State(input_id, "value"),
        )
        # input -> slider
        if scale == "log10":
            input_to_slider_js = f"""
            function(input_value, current_slider) {{
                if (input_value === null || input_value === undefined || input_value <= 0)
                    return current_slider;
                const log_v = Math.log10(input_value);
                if (current_slider !== null && current_slider !== undefined
                    && Math.abs(log_v - current_slider) < 0.001)
                    return current_slider;
                return Math.round(log_v * 1000) / 1000;
            }}
            """
        else:
            input_to_slider_js = f"""
            function(input_value, current_slider) {{
                if (input_value === null || input_value === undefined)
                    return current_slider;
                if (current_slider !== null && current_slider !== undefined
                    && Math.abs(input_value - current_slider) < 1e-6)
                    return current_slider;
                return input_value;
            }}
            """
        app.clientside_callback(
            input_to_slider_js,
            Output(slider_id, "value", allow_duplicate=True),
            Input(input_id, "value"),
            State(slider_id, "value"),
            prevent_initial_call=True,
        )

    # Wire every slider/input pair created by `_slider_with_input` in
    # layout.py. Order: chamber → ambient → drive → bubble → numerics
    # → auto-design.
    _wire_slider_input_pair("chamber_radius_cm", "chamber_radius_cm_input")
    _wire_slider_input_pair("ambient_T", "ambient_T_input")
    _wire_slider_input_pair("ambient_p", "ambient_p_input", scale="log10")
    _wire_slider_input_pair("drive_f", "drive_f_input")
    _wire_slider_input_pair("drive_pa", "drive_pa_input")
    _wire_slider_input_pair("drive_cycles", "drive_cycles_input")
    _wire_slider_input_pair("bubble_R0", "bubble_R0_input", scale="log10")
    _wire_slider_input_pair("num_rtol", "num_rtol_input")
    _wire_slider_input_pair("autodesign_T_target_kK",
                             "autodesign_T_target_kK_input")
    _wire_slider_input_pair("autodesign_max_pa", "autodesign_max_pa_input")

    # ----------------------------------------------------------------------
    # Live readouts for log-scale ambient sliders. p_∞ is stored as
    # log₁₀(kPa); the readout shows the actual pressure in human units
    # (Pa / kPa / MPa with seawater-depth equivalent). T_∞ readout
    # adds a °C conversion next to the K reading.
    # ----------------------------------------------------------------------
    app.clientside_callback(
        """
        function(value) {
            if (value === null || value === undefined) return '';
            const T_C = (value - 273.15);
            return value.toFixed(0) + ' K   ≡   ' + T_C.toFixed(1) + ' °C';
        }
        """,
        Output("ambient_T_readout", "children"),
        Input("ambient_T", "value"),
    )

    app.clientside_callback(
        """
        function(value) {
            if (value === null || value === undefined) return '';
            const p_kPa = Math.pow(10, value);
            const p_Pa = p_kPa * 1000.0;
            const p_atm = p_kPa / 101.325;
            // Hydrostatic equivalent depth in seawater (1025 kg/m³, 9.81 m/s²)
            const depth_m = Math.max(0, (p_Pa - 101325) / (1025 * 9.81));
            // Choose a readable unit
            let p_str;
            if (p_kPa < 1) {
                p_str = (p_kPa * 1000).toFixed(1) + ' Pa';
            } else if (p_kPa < 1000) {
                p_str = p_kPa.toFixed(1) + ' kPa';
            } else if (p_kPa < 1e6) {
                p_str = (p_kPa / 1000).toFixed(2) + ' MPa';
            } else {
                p_str = (p_kPa / 1e6).toFixed(2) + ' GPa';
            }
            let extra = ' (' + p_atm.toFixed(2) + ' atm';
            if (depth_m >= 1) {
                extra += ', ≈ ' + depth_m.toFixed(0) + ' m seawater';
            }
            extra += ')';
            return p_str + extra;
        }
        """,
        Output("ambient_p_readout", "children"),
        Input("ambient_p", "value"),
    )

    # Disable chamber_radius and chamber_Q sliders when the chosen
    # geometry doesn't actually use them (open-bath / HIFU / pistol_jet).
    # Avoids the user wondering why their changes have no effect.
    @app.callback(
        Output("chamber_radius_cm", "disabled"),
        Output("chamber_Q", "disabled"),
        Output("chamber_geom_note", "children"),
        Input("chamber_geometry", "value"),
    )
    def _toggle_chamber_geom_controls(geometry):                         # noqa: ANN001
        is_open_bath = geometry in ("pistol_jet", "hifu_focus", "horn_open_bath")
        if is_open_bath:
            note = ("open-bath / HIFU / pistol-jet: bubble is assumed at "
                    "the focal antinode with full drive amplitude. "
                    "radius and Q are not used by the current model.")
        else:
            note = ""
        return is_open_bath, is_open_bath, note

    # Apply control values (debounced via Dash's natural batching)
    @app.callback(
        Output("scenario_store", "data"),
        Input("liquid_dropdown", "value"),
        Input("ambient_T", "value"),
        Input("ambient_p", "value"),
        Input("drive_f", "value"),
        Input("drive_pa", "value"),
        Input("drive_cycles", "value"),
        Input("bubble_R0", "value"),
        Input("gas_ar", "value"),
        Input("gas_h2o", "value"),
        Input("gas_air", "value"),
        Input("phys_bubble_eq", "value"),
        Input("phys_thermal", "value"),
        Input("phys_ionization", "value"),
        Input("num_rtol", "value"),
        Input("num_conv", "value"),
        Input("chamber_geometry", "value"),
        Input("chamber_radius_cm", "value"),
        Input("chamber_wall", "value"),
        Input("chamber_Q", "value"),
        State("scenario_store", "data"),
    )
    def _apply_controls(*args):                                          # noqa: ANN001
        scenario_payload = args[-1]
        keys = (
            "liquid_name", "ambient_T", "ambient_p", "drive_f_hz",
            "drive_pa_atm", "drive_cycles", "bubble_R0_log10",
            "gas_ar", "gas_h2o", "gas_air", "phys_bubble_eq",
            "phys_thermal", "phys_ionization", "num_rtol_log10", "num_conv",
            "chamber_geometry", "chamber_radius_cm", "chamber_wall", "chamber_Q",
        )
        kwargs = dict(zip(keys, args[:-1]))
        return apply_controls(scenario_payload, **kwargs)

    # TEST button → run + cache + populate result_store. Also hides the
    # progress bar on completion. The clientside callback below shows
    # the bar immediately on press (so the user gets instant feedback),
    # and we hide it here when the run actually returns.
    @app.callback(
        Output("result_store", "data"),
        Output("run_status", "children"),
        Output("run_progress_container", "style", allow_duplicate=True),
        Output("run_elapsed_tick", "disabled", allow_duplicate=True),
        Input("run_button", "n_clicks"),
        State("scenario_store", "data"),
        prevent_initial_call=True,
    )
    def _run(n_clicks, scenario_payload):                                # noqa: ANN001
        hide_progress = {"display": "none", "marginTop": "8px"}
        if not n_clicks:
            return no_update, no_update, no_update, no_update
        # Live run that also caches the dense ScenarioResult server-side
        s = scenario_from_store(scenario_payload)
        if s is None:
            return None, "no scenario", hide_progress, True
        t0 = time.time()
        try:
            result = s.run()
        except ValueError as exc:
            return (None, f"validate() blocked: {exc}",
                    hide_progress, True)
        except Exception as exc:                                         # noqa: BLE001
            return (None, f"run failed: {type(exc).__name__}: {exc}",
                    hide_progress, True)
        elapsed = time.time() - t0
        cache_latest_result(result)
        payload = result_to_store(result)
        payload["wall_clock_s"] = elapsed
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        return (payload, f"ran in {elapsed:.2f} s",
                hide_progress, True)

    # Clientside: show the progress bar + start the elapsed-time interval
    # the moment the user clicks TEST. Done clientside so the visual
    # feedback is instantaneous (no round-trip to the server).
    app.clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks) {
                return [
                    {display: 'block', marginTop: '8px'},
                    false,
                    Date.now()
                ];
            }
            return [
                {display: 'none', marginTop: '8px'},
                true,
                null
            ];
        }
        """,
        Output("run_progress_container", "style"),
        Output("run_elapsed_tick", "disabled"),
        Output("run_started_at", "data"),
        Input("run_button", "n_clicks"),
        prevent_initial_call=True,
    )

    # Clientside: tick the elapsed-time label inside the progress bar so
    # the user can see seconds advancing during a long run. Computed
    # purely from the timestamp set on click — no need to round-trip
    # state through the server.
    app.clientside_callback(
        """
        function(n_intervals, started_at) {
            if (!started_at) {
                return 'Running…';
            }
            const elapsed = (Date.now() - started_at) / 1000.0;
            return 'Running… ' + elapsed.toFixed(1) + ' s';
        }
        """,
        Output("run_progress_bar", "label"),
        Input("run_elapsed_tick", "n_intervals"),
        State("run_started_at", "data"),
        prevent_initial_call=True,
    )

    # Render figures from stores
    @app.callback(
        Output("chamber_fig", "figure"),
        Output("bubble_fig", "figure"),
        Output("plasma_fig", "figure"),
        Output("spectrum_fig", "figure"),
        Output("detector_fig", "figure"),
        Output("field_fig", "figure"),
        Input("scenario_store", "data"),
        Input("result_store", "data"),
    )
    def _render(scenario_payload, result_payload):                      # noqa: ANN001
        figs = render_figures(scenario_payload, result_payload,
                               server_v1_result=latest_cached_result())
        return (figs["chamber_fig"], figs["bubble_fig"], figs["plasma_fig"],
                figs["spectrum_fig"], figs["detector_fig"], figs["field_fig"])

    # Render right column
    @app.callback(
        Output("regime_card", "children"),
        Output("headline_table", "children"),
        Output("suggestions_list", "children"),
        Output("caveats_list", "children"),
        Output("material_summary", "children"),
        Output("wall_capability_card", "children"),
        Output("liquid_properties_card", "children"),
        Input("result_store", "data"),
        Input("scenario_store", "data"),
    )
    def _render_results(result_payload, scenario_payload):              # noqa: ANN001
        # Wall capability + liquid properties update live with the
        # scenario_store input (so the user can shop materials / liquids
        # without having to click TEST first); the margin/result rows
        # only appear after a run.
        scenario = scenario_from_store(scenario_payload)
        return (
            render_regime_card(result_payload),
            render_headline_table(result_payload),
            render_suggestions(result_payload),
            render_caveats(result_payload),
            render_material_summary(result_payload),
            render_wall_capability_card(scenario, result_payload),
            render_liquid_properties_card(scenario),
        )

    # Listen button → set <audio> src to base64 WAV
    @app.callback(
        Output("audio_player", "src"),
        Input("listen_btn", "n_clicks"),
        State("result_store", "data"),
        prevent_initial_call=True,
    )
    def _listen(n_clicks, result_payload):                              # noqa: ANN001
        if not n_clicks:
            return no_update
        return render_audio(result_payload)

    # ----------------------------------------------------------------------
    # Animation: play / scrub / render. Five callbacks:
    #   1. Toggle button → flip anim_state.playing
    #   2. Anim state → tick disabled + status pill
    #   3. Tick interval → advance anim_state.frame (slider follows via #4)
    #   4. anim_state.frame → time_slider.value (visual sync for play)
    #   5. time_slider.value → anim_state.frame (user scrub; equality guard
    #      breaks the loop with #4 since auto-sync writes value == frame)
    #   6. Render → field_fig + time readout from anim_state
    #
    # The equality guard in #5 is what fixes the "play advances one frame
    # and stops" bug: with updatemode="drag" the slider's value prop fires
    # both on user drag *and* on programmatic auto-sync from #4. Without the
    # guard, every tick would re-pause the animation from the scrub path.
    # ----------------------------------------------------------------------
    @app.callback(
        Output("anim_state", "data"),
        Output("anim_toggle", "children"),
        Input("anim_toggle", "n_clicks"),
        State("anim_state", "data"),
        prevent_initial_call=True,
    )
    def _toggle_anim(n_clicks, state):                                  # noqa: ANN001
        new_playing = not (state or {}).get("playing", False)
        new_state = {"playing": new_playing,
                     "frame": (state or {}).get("frame", 0)}
        return new_state, ("❚❚ Pause" if new_playing else "▶ Play")

    @app.callback(
        Output("animation_tick", "disabled"),
        Output("anim_status", "children"),
        Input("anim_state", "data"),
    )
    def _anim_enabled(state):                                           # noqa: ANN001
        playing = (state or {}).get("playing", False)
        return (not playing,
                "playing" if playing else "paused")

    @app.callback(
        Output("anim_state", "data", allow_duplicate=True),
        Input("animation_tick", "n_intervals"),
        State("anim_state", "data"),
        prevent_initial_call=True,
    )
    def _tick(n_intervals, state):                                      # noqa: ANN001
        from cavplasma.ui.style import ANIMATION_FRAME_BUDGET
        if not (state or {}).get("playing", False):
            return no_update
        next_frame = ((state or {}).get("frame", 0) + 1) % ANIMATION_FRAME_BUDGET
        return {"playing": True, "frame": next_frame}

    @app.callback(
        Output("time_slider", "value"),
        Input("anim_state", "data"),
    )
    def _sync_slider(state):                                            # noqa: ANN001
        # Mirror anim_state.frame → slider position. The follow-up
        # `_scrub` callback's equality guard ensures this auto-sync
        # is treated as a no-op (not a user scrub).
        return int((state or {}).get("frame", 0))

    @app.callback(
        Output("anim_state", "data", allow_duplicate=True),
        Output("anim_toggle", "children", allow_duplicate=True),
        Input("time_slider", "value"),
        State("anim_state", "data"),
        prevent_initial_call=True,
    )
    def _scrub(slider_value, state):                                    # noqa: ANN001
        # Distinguish user-drag from programmatic auto-sync (#4 above):
        # if the slider's value already matches anim_state.frame, this
        # firing was caused by `_sync_slider` mirroring anim_state, not
        # by the user. In that case, no_update breaks the loop.
        if slider_value is None:
            return no_update, no_update
        current_frame = int((state or {}).get("frame", 0))
        if int(slider_value) == current_frame:
            return no_update, no_update
        return ({"playing": False, "frame": int(slider_value)}, "▶ Play")

    @app.callback(
        Output("field_fig", "figure", allow_duplicate=True),
        Output("time_readout", "children"),
        Input("anim_state", "data"),
        State("scenario_store", "data"),
        State("result_store", "data"),
        prevent_initial_call=True,
    )
    def _render_anim(state, scenario_payload, result_payload):          # noqa: ANN001
        from cavplasma.ui.style import ANIMATION_FRAME_BUDGET
        frame_idx = (state or {}).get("frame", 0) % ANIMATION_FRAME_BUDGET
        fig = animation_frame_figure(scenario_payload, result_payload, frame_idx)
        readout = _animation_time_readout(scenario_payload, frame_idx)
        return fig, readout

    # Notebook
    @app.callback(
        Output("notebook_store", "data"),
        Input("result_store", "data"),
        State("notebook_store", "data"),
    )
    def _append_notebook(result_payload, notebook):                     # noqa: ANN001
        return append_notebook(result_payload, notebook or [])

    @app.callback(
        Output("notebook_table", "children"),
        Output("notebook_regime_strip", "children"),
        Input("notebook_store", "data"),
    )
    def _render_notebook(notebook):                                     # noqa: ANN001
        return (
            render_notebook_table(notebook or []),
            render_notebook_regime_strip(notebook or []),
        )

    @app.callback(
        Output("notebook_export_download", "data"),
        Input("notebook_export_btn", "n_clicks"),
        State("notebook_store", "data"),
        prevent_initial_call=True,
    )
    def _export_notebook(n_clicks, notebook):                           # noqa: ANN001
        if not n_clicks:
            return no_update
        csv_text = notebook_to_csv_bytes(notebook or [])
        return dict(content=csv_text, filename="cavplasma_notebook.csv")

    @app.callback(
        Output("notebook_store", "data", allow_duplicate=True),
        Input("notebook_clear_btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _clear_notebook(n_clicks):                                      # noqa: ANN001
        if not n_clicks:
            return no_update
        return []

    # ----------------------------------------------------------------------
    # Auto-design — heuristic find + grid-search refine
    # ----------------------------------------------------------------------
    def _autodesign_outputs(payload, label, status, diagnostic):
        """Pack the 22-output tuple shared by both autodesign callbacks."""
        if payload is None:
            return ([no_update] * 20) + [status, diagnostic]
        scenario = scenario_from_store(payload)
        ctrls = scenario_to_control_values(scenario)
        return [
            payload,
            label,
            ctrls["liquid_dropdown"],
            ctrls["ambient_T"],
            ctrls["ambient_p"],
            ctrls["drive_f"],
            ctrls["drive_pa"],
            ctrls["drive_cycles"],
            ctrls["bubble_R0"],
            ctrls["gas_ar"],
            ctrls["gas_h2o"],
            ctrls["gas_air"],
            ctrls["phys_bubble_eq"],
            ctrls["phys_thermal"],
            ctrls["phys_ionization"],
            ctrls["num_rtol"],
            ctrls["chamber_geometry"],
            ctrls["chamber_radius_cm"],
            ctrls["chamber_wall"],
            ctrls["chamber_Q"],
            status,
            diagnostic,
        ]

    @app.callback(
        Output("scenario_store", "data", allow_duplicate=True),
        Output("scenario_source_label", "children", allow_duplicate=True),
        Output("liquid_dropdown", "value", allow_duplicate=True),
        Output("ambient_T", "value", allow_duplicate=True),
        Output("ambient_p", "value", allow_duplicate=True),
        Output("drive_f", "value", allow_duplicate=True),
        Output("drive_pa", "value", allow_duplicate=True),
        Output("drive_cycles", "value", allow_duplicate=True),
        Output("bubble_R0", "value", allow_duplicate=True),
        Output("gas_ar", "value", allow_duplicate=True),
        Output("gas_h2o", "value", allow_duplicate=True),
        Output("gas_air", "value", allow_duplicate=True),
        Output("phys_bubble_eq", "value", allow_duplicate=True),
        Output("phys_thermal", "value", allow_duplicate=True),
        Output("phys_ionization", "value", allow_duplicate=True),
        Output("num_rtol", "value", allow_duplicate=True),
        Output("chamber_geometry", "value", allow_duplicate=True),
        Output("chamber_radius_cm", "value", allow_duplicate=True),
        Output("chamber_wall", "value", allow_duplicate=True),
        Output("chamber_Q", "value", allow_duplicate=True),
        Output("autodesign_status", "children"),
        Output("autodesign_diagnostic", "children"),
        Input("autodesign_find_btn", "n_clicks"),
        State("autodesign_T_target_kK", "value"),
        State("autodesign_must_be_stable", "value"),
        State("autodesign_max_pa", "value"),
        State("scenario_store", "data"),
        prevent_initial_call=True,
    )
    def _autodesign_find_cb(n, T_target, stable, max_pa, base_payload):  # noqa: ANN001
        if not n:
            return [no_update] * 22
        payload, status, diagnostic = autodesign_find(
            T_target, stable, max_pa, base_payload)
        return _autodesign_outputs(
            payload,
            f"auto-design · target {T_target:.0f} kK · heuristic",
            status, diagnostic,
        )

    @app.callback(
        Output("scenario_store", "data", allow_duplicate=True),
        Output("scenario_source_label", "children", allow_duplicate=True),
        Output("liquid_dropdown", "value", allow_duplicate=True),
        Output("ambient_T", "value", allow_duplicate=True),
        Output("ambient_p", "value", allow_duplicate=True),
        Output("drive_f", "value", allow_duplicate=True),
        Output("drive_pa", "value", allow_duplicate=True),
        Output("drive_cycles", "value", allow_duplicate=True),
        Output("bubble_R0", "value", allow_duplicate=True),
        Output("gas_ar", "value", allow_duplicate=True),
        Output("gas_h2o", "value", allow_duplicate=True),
        Output("gas_air", "value", allow_duplicate=True),
        Output("phys_bubble_eq", "value", allow_duplicate=True),
        Output("phys_thermal", "value", allow_duplicate=True),
        Output("phys_ionization", "value", allow_duplicate=True),
        Output("num_rtol", "value", allow_duplicate=True),
        Output("chamber_geometry", "value", allow_duplicate=True),
        Output("chamber_radius_cm", "value", allow_duplicate=True),
        Output("chamber_wall", "value", allow_duplicate=True),
        Output("chamber_Q", "value", allow_duplicate=True),
        Output("autodesign_status", "children", allow_duplicate=True),
        Output("autodesign_diagnostic", "children", allow_duplicate=True),
        Input("autodesign_refine_btn", "n_clicks"),
        State("autodesign_T_target_kK", "value"),
        State("autodesign_must_be_stable", "value"),
        State("autodesign_max_pa", "value"),
        State("scenario_store", "data"),
        prevent_initial_call=True,
    )
    def _autodesign_refine_cb(n, T_target, stable, max_pa, payload):     # noqa: ANN001
        if not n:
            return [no_update] * 22
        new_payload, status, diagnostic = autodesign_refine(
            T_target, stable, max_pa, payload)
        return _autodesign_outputs(
            new_payload,
            f"auto-design · target {T_target:.0f} kK · refined (3×3 grid)",
            status, diagnostic,
        )

    # ----------------------------------------------------------------------
    # Live status chip — always on. Predicts the regime analytically
    # from (drive_f, drive_pa, R₀) without running the simulator, so the
    # user gets instant feedback as they explore.
    # ----------------------------------------------------------------------
    @app.callback(
        Output("couple_status_chip", "children"),
        Input("drive_f", "value"),
        Input("drive_pa", "value"),
        Input("bubble_R0", "value"),
        Input("ambient_p", "value"),
    )
    def _live_status_chip(f_hz_in, pa_atm, R0_log10, p_log10):           # noqa: ANN001
        if any(v is None for v in (f_hz_in, pa_atm, R0_log10, p_log10)):
            return no_update
        f_hz = float(f_hz_in)                              # slider is now in Hz
        R0_m = (10.0 ** float(R0_log10)) * 1e-6            # log10(µm) → m
        p_atm = (10.0 ** float(p_log10))                   # log10(kPa) → kPa
        p_atm = (p_atm * 1000.0) / 101_325.0               # → atm
        severity, message = _classify_live(
            f_hz, float(pa_atm), R0_m, p_inf_atm=p_atm,
        )
        # severity → bootstrap colour
        return dbc.Alert(message, color=severity,
                          className="py-1 mb-0",
                          style={"fontSize": "0.85em"})

    # ----------------------------------------------------------------------
    # Auto-adapt as a *proposal* — moving a slider doesn't move its
    # partner; instead it writes a payload to coupling_proposal that
    # the user can Apply (commit) or Dismiss (cancel). Avoids surprise
    # jumps and gives the user authority over every parameter change.
    # ----------------------------------------------------------------------
    @app.callback(
        Output("coupling_proposal", "data"),
        Input("drive_f", "value"),
        Input("bubble_R0", "value"),
        Input("couple_sliders_toggle", "value"),
        State("ambient_p", "value"),
        State("liquid_dropdown", "value"),
        prevent_initial_call=True,
    )
    def _propose_couple(f_hz_in, R0_log10, couple_on,                    # noqa: ANN001
                          p_log10, liquid_name):
        import math
        if not couple_on:
            return None        # toggle off → clear any pending proposal
        triggered = ctx.triggered_id
        if triggered == "couple_sliders_toggle":
            # Toggle just turned on; wait for an actual slider move.
            return None
        if triggered not in ("drive_f", "bubble_R0"):
            return no_update
        if any(v is None for v in (f_hz_in, R0_log10, p_log10)):
            return None

        # drive_f slider value is now plain Hz; only R₀ and ambient_p
        # remain on log scale (R₀: log10(µm); p: log10(kPa)).
        f_hz = float(f_hz_in)
        R0_m = (10.0 ** float(R0_log10)) * 1e-6
        p_atm = (10.0 ** float(p_log10)) * 1000.0 / 101_325.0
        try:
            from cavplasma.liquids import preset
            liq = preset(liquid_name or "water")
        except Exception:                                                # noqa: BLE001
            from cavplasma.liquids import preset
            liq = preset("water")
        gamma = 5.0 / 3.0

        new_f_hz, new_R0_m = _adapt_partner_slider(
            triggered, f_hz, drive_pa_atm=0.0,
            R0_m=R0_m, p_inf_atm=p_atm, gamma=gamma, rho=liq.rho,
        )

        # Build the proposal only when the partner would move by >5 %
        # relative. Below that we don't bother the user.
        if triggered == "drive_f" and new_R0_m is not None and new_R0_m > 0:
            candidate_log10 = math.log10(new_R0_m * 1e6)
            abs_delta = abs(new_R0_m - R0_m) / R0_m
            if abs_delta > 0.05:
                return {
                    "target": "bubble_R0",
                    "current_log10": float(R0_log10),
                    "proposed_log10": round(candidate_log10, 3),
                    "current_um": R0_m * 1e6,
                    "proposed_um": new_R0_m * 1e6,
                    "rationale": (f"keeps drive/Minnaert ratio at the SBSL "
                                  f"canonical 0.033 for the new drive freq "
                                  f"{f_hz/1000:.1f} kHz"),
                }
        if triggered == "bubble_R0" and new_f_hz is not None and new_f_hz > 0:
            abs_delta = abs(new_f_hz - f_hz) / f_hz
            if abs_delta > 0.05:
                return {
                    "target": "drive_f",
                    "current_hz": f_hz,
                    # drive_f slider is now in Hz, so "proposed_hz" is
                    # the value to write directly into the slider.
                    "proposed_hz": round(new_f_hz, 1),
                    "rationale": (f"keeps drive/Minnaert ratio at the SBSL "
                                  f"canonical 0.033 for the new R₀ "
                                  f"{R0_m*1e6:.2f} µm"),
                }
        return None        # no meaningful adaptation needed

    @app.callback(
        Output("couple_proposal_card", "style"),
        Output("couple_proposal_text", "children"),
        Input("coupling_proposal", "data"),
    )
    def _render_proposal(proposal):                                      # noqa: ANN001
        if not proposal:
            return {"display": "none"}, no_update
        target = proposal.get("target")
        if target == "drive_f":
            cur_hz = proposal["current_hz"]
            new_hz = proposal["proposed_hz"]
            text = html.Div([
                html.Span("🎯 ", style={"fontSize": "1.1em"}),
                html.B("Auto-adapt suggestion: drive frequency"), html.Br(),
                html.Span(f"{cur_hz:,.0f} Hz → {new_hz:,.0f} Hz",
                            className="text-info"), html.Br(),
                html.Small(proposal.get("rationale", ""),
                           style={"opacity": 0.85}),
            ])
        elif target == "bubble_R0":
            cur = proposal["current_um"]
            new = proposal["proposed_um"]
            text = html.Div([
                html.Span("🎯 ", style={"fontSize": "1.1em"}),
                html.B("Auto-adapt suggestion: R₀"), html.Br(),
                html.Span(f"{cur:.2f} µm → {new:.2f} µm",
                            className="text-info"), html.Br(),
                html.Small(proposal.get("rationale", ""),
                           style={"opacity": 0.85}),
            ])
        else:
            return {"display": "none"}, no_update
        return {"display": "block"}, text

    @app.callback(
        Output("drive_f", "value", allow_duplicate=True),
        Output("bubble_R0", "value", allow_duplicate=True),
        Output("coupling_proposal", "data", allow_duplicate=True),
        Input("couple_apply_btn", "n_clicks"),
        State("coupling_proposal", "data"),
        prevent_initial_call=True,
    )
    def _apply_proposal(n_clicks, proposal):                              # noqa: ANN001
        if not n_clicks or not proposal:
            return no_update, no_update, no_update
        target = proposal.get("target")
        if target == "drive_f":
            # drive_f slider is in Hz now — write proposed Hz directly.
            return proposal.get("proposed_hz"), no_update, None
        if target == "bubble_R0":
            # bubble_R0 still on log scale — write proposed_log10.
            return no_update, proposal.get("proposed_log10"), None
        return no_update, no_update, no_update

    @app.callback(
        Output("coupling_proposal", "data", allow_duplicate=True),
        Input("couple_dismiss_btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def _dismiss_proposal(n_clicks):                                      # noqa: ANN001
        if not n_clicks:
            return no_update
        return None

    # Save / Load
    @app.callback(
        Output("save_download", "data"),
        Input("save_btn", "n_clicks"),
        State("scenario_store", "data"),
        prevent_initial_call=True,
    )
    def _save(n_clicks, scenario_payload):                              # noqa: ANN001
        if not n_clicks:
            return no_update
        return dict(content=scenario_payload or "{}",
                    filename="cavplasma_scenario.json")

    @app.callback(
        Output("scenario_store", "data", allow_duplicate=True),
        Output("scenario_source_label", "children", allow_duplicate=True),
        Output("liquid_dropdown", "value", allow_duplicate=True),
        Output("ambient_T", "value", allow_duplicate=True),
        Output("ambient_p", "value", allow_duplicate=True),
        Output("drive_f", "value", allow_duplicate=True),
        Output("drive_pa", "value", allow_duplicate=True),
        Output("drive_cycles", "value", allow_duplicate=True),
        Output("bubble_R0", "value", allow_duplicate=True),
        Output("gas_ar", "value", allow_duplicate=True),
        Output("gas_h2o", "value", allow_duplicate=True),
        Output("gas_air", "value", allow_duplicate=True),
        Output("phys_bubble_eq", "value", allow_duplicate=True),
        Output("phys_thermal", "value", allow_duplicate=True),
        Output("phys_ionization", "value", allow_duplicate=True),
        Output("num_rtol", "value", allow_duplicate=True),
        Output("num_conv", "value", allow_duplicate=True),
        Output("chamber_geometry", "value", allow_duplicate=True),
        Output("chamber_radius_cm", "value", allow_duplicate=True),
        Output("chamber_wall", "value", allow_duplicate=True),
        Output("chamber_Q", "value", allow_duplicate=True),
        Input("load_upload", "contents"),
        State("load_upload", "filename"),
        prevent_initial_call=True,
    )
    def _load(contents, filename):                                       # noqa: ANN001
        if not contents:
            return [no_update] * 21
        try:
            import base64
            _header, b64 = contents.split(",", 1)
            text = base64.b64decode(b64).decode("utf-8")
            scenario = Scenario.from_json(text)
        except Exception as exc:                                          # noqa: BLE001
            label = f"failed to load {filename or 'file'}: {type(exc).__name__}"
            return ([no_update, label]
                    + [no_update] * 19)
        ctrls = scenario_to_control_values(scenario)
        # Pull the scenario's own metadata.name when present, otherwise
        # show the uploaded filename. Helps the user tell whether the
        # file's metadata is informative or whether they need to look
        # at the filename only.
        scenario_name = scenario.metadata.get("name") if scenario.metadata else None
        if scenario_name and filename and scenario_name not in filename:
            label = f"loaded · {filename}  (scenario.name = {scenario_name})"
        elif filename:
            label = f"loaded · {filename}"
        else:
            label = "loaded · (unnamed JSON)"
        return (
            text,
            label,
            ctrls["liquid_dropdown"],
            ctrls["ambient_T"],
            ctrls["ambient_p"],
            ctrls["drive_f"],
            ctrls["drive_pa"],
            ctrls["drive_cycles"],
            ctrls["bubble_R0"],
            ctrls["gas_ar"],
            ctrls["gas_h2o"],
            ctrls["gas_air"],
            ctrls["phys_bubble_eq"],
            ctrls["phys_thermal"],
            ctrls["phys_ionization"],
            ctrls["num_rtol"],
            ctrls["num_conv"],
            ctrls["chamber_geometry"],
            ctrls["chamber_radius_cm"],
            ctrls["chamber_wall"],
            ctrls["chamber_Q"],
        )

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
    drive_f_log10: float,
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
) -> str:
    """Apply control values to the scenario_store. Returns updated JSON."""
    base = scenario_from_store(scenario_payload) or scenario_presets.sbsl_canonical()

    # Liquid
    try:
        liquid = _liquid_preset(liquid_name)
    except Exception:
        liquid = base.liquid

    # Ambient — `ambient_p` slider is now log₁₀(p_∞ in kPa) so a single
    # control covers vacuum (~30 kPa) → 10 km seawater (~100 MPa).
    p_inf_pa = (10.0 ** float(ambient_p)) * 1_000.0
    ambient = dataclasses.replace(
        base.ambient,
        p_inf=p_inf_pa,
        T_inf=ambient_T,
    )

    # Drive — convert sliders back to SI
    f_hz = 10.0 ** drive_f_log10 * 1_000.0     # slider was log10(f_kHz)
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
        drive_f_log10 = math.log10(max(drv.f, 1.0) / 1000.0)
        drive_pa_atm = drv.P_A / 101_325.0
        drive_cycles = drv.n_cycles
    else:
        drive_f_log10 = 1.42
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
        "liquid_dropdown":   scenario.liquid.name,
        "ambient_T":         scenario.ambient.T_inf,
        "ambient_p":         math.log10(p_inf_kpa),
        "drive_f":           drive_f_log10,
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


def render_regime_card(result_payload: Optional[dict]) -> dbc.Alert:
    if not result_payload:
        return dbc.Alert("No run yet — click TEST to populate.",
                         color="secondary")
    regime = result_payload.get("summary", {}).get("regime", "stable_spherical")
    color = {
        "stable_spherical":   "success",
        "marginal":           "warning",
        "unstable_likely":    "danger",
        "sub_blake":          "secondary",
        "linear_oscillation": "warning",     # dossier §16/§17 — yellow, not green
        "transducer_limited": "danger",
    }.get(regime, "info")
    desc = REGIME_DESCRIPTION.get(regime, "")
    return dbc.Alert([html.B(regime), html.Br(), desc], color=color)


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
        Input("preset_modal_confirm", "n_clicks"),
        State("preset_pending", "data"),
        prevent_initial_call=True,
    )
    def _confirm_preset(n_clicks, pending):                             # noqa: ANN001
        if not n_clicks or not pending:
            return [no_update] * 18
        try:
            payload = apply_preset(pending)
        except Exception:                                               # noqa: BLE001
            return [no_update] * 18
        scenario = scenario_from_store(payload)
        ctrls = scenario_to_control_values(scenario)
        return (
            payload,         # scenario_store
            False,           # close modal
            pending,         # preset_last_loaded
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
        State("scenario_store", "data"),
    )
    def _apply_controls(*args):                                          # noqa: ANN001
        scenario_payload = args[-1]
        keys = (
            "liquid_name", "ambient_T", "ambient_p", "drive_f_log10",
            "drive_pa_atm", "drive_cycles", "bubble_R0_log10",
            "gas_ar", "gas_h2o", "gas_air", "phys_bubble_eq",
            "phys_thermal", "phys_ionization", "num_rtol_log10", "num_conv",
        )
        kwargs = dict(zip(keys, args[:-1]))
        return apply_controls(scenario_payload, **kwargs)

    # TEST button → run + cache + populate result_store
    @app.callback(
        Output("result_store", "data"),
        Output("run_status", "children"),
        Input("run_button", "n_clicks"),
        State("scenario_store", "data"),
        prevent_initial_call=True,
    )
    def _run(n_clicks, scenario_payload):                                # noqa: ANN001
        if not n_clicks:
            return no_update, no_update
        # Live run that also caches the dense ScenarioResult server-side
        s = scenario_from_store(scenario_payload)
        if s is None:
            return None, "no scenario"
        t0 = time.time()
        try:
            result = s.run()
        except ValueError as exc:
            return None, f"validate() blocked: {exc}"
        except Exception as exc:                                         # noqa: BLE001
            return None, f"run failed: {type(exc).__name__}: {exc}"
        elapsed = time.time() - t0
        cache_latest_result(result)
        payload = result_to_store(result)
        payload["wall_clock_s"] = elapsed
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        return payload, f"ran in {elapsed:.2f} s"

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
        Input("result_store", "data"),
    )
    def _render_results(result_payload):                                # noqa: ANN001
        return (
            render_regime_card(result_payload),
            render_headline_table(result_payload),
            render_suggestions(result_payload),
            render_caveats(result_payload),
            render_material_summary(result_payload),
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
        Input("notebook_store", "data"),
    )
    def _render_notebook(notebook):                                     # noqa: ANN001
        return render_notebook_table(notebook or [])

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
        Input("load_upload", "contents"),
        prevent_initial_call=True,
    )
    def _load(contents):                                                # noqa: ANN001
        if not contents:
            return [no_update] * 16
        try:
            import base64
            _header, b64 = contents.split(",", 1)
            text = base64.b64decode(b64).decode("utf-8")
            scenario = Scenario.from_json(text)
        except Exception:                                                # noqa: BLE001
            return [no_update] * 16
        ctrls = scenario_to_control_values(scenario)
        return (
            text,
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
        )

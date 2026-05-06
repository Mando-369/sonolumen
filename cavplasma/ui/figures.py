"""Plotly figure factories for the §15 UI. §15.4.

All functions take either a `Scenario` (for static / standing-wave-field
views) or a UI `result_payload` dict produced by `state.result_to_store`,
and return a `plotly.graph_objects.Figure`. Pure functions — they don't
talk to the Dash app, so the test suite uses them directly.
"""

from __future__ import annotations

import math
from typing import Any, Optional

import numpy as np
import plotly.graph_objects as go

from cavplasma.scenario import Scenario
from cavplasma.scenario.field import combine_drives, standing_wave_factor
from cavplasma.ui.style import (
    PLOT_HEIGHT_LARGE,
    PLOT_HEIGHT_MED,
    PLOT_HEIGHT_SMALL,
    PLOT_TEMPLATE,
)


# ---------------------------------------------------------------------------
# §15.4.1 — Chamber cross-section
# ---------------------------------------------------------------------------
def chamber_figure(scenario: Scenario, t_anim: Optional[float] = None) -> go.Figure:
    """2-D cross-section: chamber outline + transducers + bubble + observers.

    Static at `t_anim=None`; when an `t_anim` is supplied, the bubble's
    rendered radius shrinks/expands sinusoidally for a quick preview
    (full radius traces require a `result` payload — see
    `chamber_animation_figure`).
    """
    fig = go.Figure()
    chamber = scenario.chamber
    R = chamber.radius
    # Outline
    if chamber.geometry == "sphere":
        theta = np.linspace(0.0, 2.0 * math.pi, 200)
        x = R * np.cos(theta)
        y = R * np.sin(theta)
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines", name="chamber",
            line=dict(color="#cccccc", width=2),
            hoverinfo="skip", showlegend=False,
        ))
    else:
        L = chamber.length if chamber.length is not None else 2.0 * R
        fig.add_trace(go.Scatter(
            x=[-R, R, R, -R, -R], y=[-L/2, -L/2, L/2, L/2, -L/2],
            mode="lines", line=dict(color="#cccccc", width=2),
            hoverinfo="skip", showlegend=False, name="chamber",
        ))

    # Transducers
    for tx in scenario.transducers:
        x_tx, y_tx, _ = tx.position
        fig.add_trace(go.Scatter(
            x=[x_tx], y=[y_tx], mode="markers+text",
            marker=dict(symbol="square", size=18, color="#1f77b4"),
            text=[tx.name], textposition="top center",
            name=f"transducer {tx.name}", hoverinfo="text",
        ))

    # Bubble (renders at a representative size)
    pop = scenario.bubble_population
    if pop.seed_position is not None:
        bx, by, _ = pop.seed_position
    else:
        bx, by = 0.0, 0.0
    if pop.seed is not None:
        # Render bubble at 100× R₀ for visibility (typical R_max ~ 10 R₀)
        bubble_size_m = 50.0 * pop.seed.R0
    else:
        bubble_size_m = 0.001
    if t_anim is not None:
        # Rough sinusoidal animation for the preview
        bubble_size_m *= (1.0 + 0.5 * math.sin(2.0 * math.pi * t_anim))
    # Plot bubble as a circle approximation
    btheta = np.linspace(0.0, 2.0 * math.pi, 60)
    bx_c = bx + bubble_size_m * np.cos(btheta)
    by_c = by + bubble_size_m * np.sin(btheta)
    fig.add_trace(go.Scatter(
        x=bx_c, y=by_c, mode="lines", fill="toself",
        fillcolor="rgba(255, 200, 0, 0.4)",
        line=dict(color="#ffae00", width=1),
        name="bubble", hoverinfo="text",
        text=f"R₀ = {pop.seed.R0*1e6:.2f} µm" if pop.seed else "",
    ))

    # Observers
    for obs in scenario.observers:
        ox, oy, _ = obs.position
        fig.add_trace(go.Scatter(
            x=[ox], y=[oy], mode="markers+text",
            marker=dict(symbol="diamond", size=12, color="#d62728"),
            text=[obs.name], textposition="bottom center",
            name=f"observer {obs.name}", hoverinfo="text",
        ))

    fig.update_layout(
        title="Chamber cross-section",
        template=PLOT_TEMPLATE,
        height=PLOT_HEIGHT_MED,
        xaxis=dict(scaleanchor="y", scaleratio=1, range=[-1.2 * R, 1.2 * R],
                   title="x (m)", showgrid=True),
        yaxis=dict(range=[-1.2 * R, 1.2 * R], title="y (m)", showgrid=True),
        showlegend=False,
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


# ---------------------------------------------------------------------------
# §15.4.2 — Bubble dynamics traces
# ---------------------------------------------------------------------------
def bubble_dynamics_figure(payload: dict) -> go.Figure:
    """Two-row figure: R(t) on top, Ṙ(t) on bottom."""
    bubble = payload.get("bubble", {})
    t = np.array(bubble.get("time", []))
    R = np.array(bubble.get("R", []))
    Rdot = np.array(bubble.get("Rdot", []))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t * 1e6, y=R * 1e6, name="R(t)", mode="lines",
        line=dict(color="#1f77b4", width=2), yaxis="y1",
    ))
    fig.add_trace(go.Scatter(
        x=t * 1e6, y=Rdot, name="Ṙ(t)", mode="lines",
        line=dict(color="#d62728", width=1.4), yaxis="y2",
    ))
    fig.update_layout(
        title="Bubble dynamics",
        template=PLOT_TEMPLATE, height=PLOT_HEIGHT_MED,
        xaxis=dict(title="t (µs)"),
        yaxis=dict(title="R (µm)", side="left"),
        yaxis2=dict(title="Ṙ (m/s)", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        margin=dict(l=50, r=50, t=40, b=40),
    )
    return fig


def phase_space_figure(payload: dict) -> go.Figure:
    bubble = payload.get("bubble", {})
    R = np.array(bubble.get("R", []))
    Rdot = np.array(bubble.get("Rdot", []))
    fig = go.Figure(go.Scatter(
        x=np.abs(R) * 1e6, y=Rdot, mode="lines",
        line=dict(color="#7f7f7f", width=1),
    ))
    fig.update_layout(
        title="Phase space — Ṙ vs R",
        template=PLOT_TEMPLATE, height=PLOT_HEIGHT_SMALL,
        xaxis=dict(title="R (µm)", type="log"),
        yaxis=dict(title="Ṙ (m/s)"),
        margin=dict(l=50, r=20, t=40, b=40),
    )
    return fig


# ---------------------------------------------------------------------------
# §15.4.3 — Plasma diagnostics
# ---------------------------------------------------------------------------
def plasma_diagnostics_figure(payload: dict) -> go.Figure:
    bubble = payload.get("bubble", {})
    plasma = payload.get("plasma", {})
    t = np.array(bubble.get("time", []))
    T_g = np.array(bubble.get("T_g", []))
    n_e = np.array(plasma.get("n_e", []))
    x_e = np.array(plasma.get("x_e", []))
    summary = payload.get("summary", {})
    band = summary.get("T_peak_band", [0, 0])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t * 1e6, y=T_g, name="T_g(t)", mode="lines",
        line=dict(color="#9467bd", width=2), yaxis="y1",
    ))
    if len(n_e):
        fig.add_trace(go.Scatter(
            x=t * 1e6, y=n_e, name="n_e(t)", mode="lines",
            line=dict(color="#2ca02c", width=1.4), yaxis="y2",
        ))
    if len(x_e):
        fig.add_trace(go.Scatter(
            x=t * 1e6, y=x_e, name="x_e(t)", mode="lines",
            line=dict(color="#ff7f0e", width=1, dash="dash"), yaxis="y3",
        ))
    # T_peak band shading per §10.1 / §15.4.3
    if band[0] and band[1] and len(t):
        fig.add_hrect(
            y0=band[0], y1=band[1],
            line_width=0, fillcolor="rgba(148, 103, 189, 0.10)",
            layer="below", yref="y1",
            annotation_text="§10.1 T_peak band",
            annotation_position="top right",
        )
    fig.update_layout(
        title="Plasma diagnostics",
        template=PLOT_TEMPLATE, height=PLOT_HEIGHT_MED,
        xaxis=dict(title="t (µs)"),
        yaxis=dict(title="T_g (K)", type="log"),
        yaxis2=dict(title="n_e (m⁻³)", overlaying="y", side="right",
                    type="log", showgrid=False),
        yaxis3=dict(title="x_e", overlaying="y", side="right",
                    position=0.95, showgrid=False, range=[0, 1]),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        margin=dict(l=50, r=80, t=40, b=40),
    )
    return fig


# ---------------------------------------------------------------------------
# §15.4.4 — Spectrum surface
# ---------------------------------------------------------------------------
def spectrum_surface_figure(scenario_result: Any) -> go.Figure:
    """Build the spectrum heatmap directly from the v1 SimulationResult.

    `scenario_result` here is the full ScenarioResult (server-side, with
    `_v1_result`). The UI calls this only on the server; the dense
    spectrum array is too big to round-trip via dcc.Store.
    """
    if scenario_result is None:
        return _empty_figure("Spectrum surface (no result yet)")
    sim = scenario_result._v1_result
    if sim is None:
        return _empty_figure("Spectrum surface (no v1 trace)")

    spec = sim.em.get("S_t_lambda")
    lam_m = sim.em.get("lambda_grid_m")
    t = sim.t
    if spec is None or lam_m is None or len(spec) == 0:
        return _empty_figure("Spectrum surface (empty)")

    # Downsample time axis if too dense for browser
    if len(t) > 200:
        idx = np.linspace(0, len(t) - 1, 200).astype(int)
        t_down = t[idx]
        spec_down = spec[idx, :]
    else:
        t_down = t
        spec_down = spec

    # Use log10 for the colorscale; clip below 1e-30 to avoid -inf
    log_spec = np.log10(np.maximum(spec_down, 1e-30))
    fig = go.Figure(go.Heatmap(
        x=t_down * 1e6, y=lam_m * 1e9, z=log_spec.T,
        colorscale="Viridis",
        colorbar=dict(title="log₁₀ S(λ,t)"),
    ))
    fig.update_layout(
        title="Emission spectrum S(λ, t)",
        template=PLOT_TEMPLATE, height=PLOT_HEIGHT_MED,
        xaxis=dict(title="t (µs)"),
        yaxis=dict(title="λ (nm)"),
        margin=dict(l=50, r=20, t=40, b=40),
    )
    return fig


# ---------------------------------------------------------------------------
# §15.4.5 — Detector traces
# ---------------------------------------------------------------------------
def detector_traces_figure(payload: dict) -> go.Figure:
    """Stacked subplots, one per observer time-series trace."""
    obs_traces = payload.get("observer_traces", {})
    if not obs_traces:
        return _empty_figure("Detector traces (no observers)")

    # Pick the metric column for each observer (V_PMT, V, p_rad, …)
    plottable: list[tuple[str, str, list, list]] = []
    for name, sub in obs_traces.items():
        t = sub.get("time", [])
        if not t:
            continue
        for col in ("V_PMT", "V", "p_rad", "wall_pressure"):
            if col in sub:
                plottable.append((name, col, t, sub[col]))
                break

    if not plottable:
        return _empty_figure("Detector traces (no time-series)")

    fig = go.Figure()
    for i, (name, col, t, y) in enumerate(plottable):
        fig.add_trace(go.Scatter(
            x=np.array(t) * 1e6, y=y, name=f"{name} · {col}",
            mode="lines", line=dict(width=1.2),
        ))
    fig.update_layout(
        title="Detector / observer traces",
        template=PLOT_TEMPLATE, height=PLOT_HEIGHT_MED,
        xaxis=dict(title="t (µs)"),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        margin=dict(l=50, r=20, t=40, b=40),
    )
    return fig


# ---------------------------------------------------------------------------
# §15.4.6 — Standing-wave field heatmap
# ---------------------------------------------------------------------------
def standing_wave_field_figure(
    scenario: Scenario, t_anim: float = 0.0, *, n_grid: int = 50,
) -> go.Figure:
    """Heatmap of p_a(x, y, t_anim) over the chamber cross-section.

    Pure analytic mode (§12.4). For a sphere centred on the origin:
      p(r, t) = factor(r) · sum over transducers of A_k sin(2π f_k t + φ_k).
    """
    chamber = scenario.chamber
    R = chamber.radius
    xs = np.linspace(-R, R, n_grid)
    ys = np.linspace(-R, R, n_grid)
    grid = np.zeros((n_grid, n_grid))

    drv = combine_drives(
        scenario.transducers, scenario.drive,
        scenario.bubble_population.seed_position or (0.0, 0.0, 0.0),
        chamber,
    )
    if drv.P_A == 0.0:
        # No drive — flat field
        fig = go.Figure(go.Heatmap(
            x=xs, y=ys, z=grid,
            colorscale="RdBu", zmid=0.0,
        ))
        fig.update_layout(
            title="Pressure field (no drive)",
            template=PLOT_TEMPLATE, height=PLOT_HEIGHT_MED,
            xaxis=dict(scaleanchor="y", scaleratio=1, title="x (m)"),
            yaxis=dict(title="y (m)"),
            margin=dict(l=50, r=20, t=40, b=40),
        )
        return fig

    omega = 2.0 * math.pi * drv.f
    # Time-domain factor (additive convention: p_a = -P_A sin(ωt + φ))
    time_factor = -drv.P_A * math.sin(omega * t_anim + drv.phase)

    for ix, x in enumerate(xs):
        for iy, y in enumerate(ys):
            r = math.hypot(x, y)
            if r > R:
                grid[iy, ix] = np.nan
                continue
            # Spatial factor uses the chamber's analytic eigenmode
            spatial = standing_wave_factor(chamber, (x, y, 0.0))
            grid[iy, ix] = spatial * time_factor

    z_abs = np.nanmax(np.abs(grid)) or 1.0
    fig = go.Figure(go.Heatmap(
        x=xs, y=ys, z=grid,
        colorscale="RdBu", zmin=-z_abs, zmax=z_abs,
        colorbar=dict(title="p_a (Pa)"),
    ))
    # Bubble overlay
    pop = scenario.bubble_population
    if pop.seed_position is not None:
        bx, by, _ = pop.seed_position
        fig.add_trace(go.Scatter(
            x=[bx], y=[by], mode="markers",
            marker=dict(symbol="circle", size=10, color="#ffae00",
                        line=dict(color="black", width=1)),
            name="bubble", hoverinfo="name",
        ))
    fig.update_layout(
        title=f"Pressure field at t = {t_anim*1e6:.2f} µs",
        template=PLOT_TEMPLATE, height=PLOT_HEIGHT_MED,
        xaxis=dict(scaleanchor="y", scaleratio=1, title="x (m)",
                   range=[-1.05 * R, 1.05 * R]),
        yaxis=dict(title="y (m)", range=[-1.05 * R, 1.05 * R]),
        showlegend=False,
        margin=dict(l=50, r=20, t=40, b=40),
    )
    return fig


# ---------------------------------------------------------------------------
# Headline numbers — small "card" figure for the right column
# ---------------------------------------------------------------------------
def headline_summary_text(payload: dict) -> list[tuple[str, str]]:
    """Return a list of (label, value) tuples for §15.5 headline card."""
    s = payload.get("summary", {})
    rows: list[tuple[str, str]] = []
    rows.append(("regime", str(s.get("regime", ""))))
    rows.append(("R_max", f"{s.get('R_max', 0)*1e6:.2f} µm"))
    rows.append(("R_min", f"{s.get('R_min', 0)*1e6:.4f} µm"))
    rows.append(("wall Mach", f"{s.get('wall_mach_peak', 0):.3f}"))
    band = s.get("T_peak_band", (0.0, 0.0))
    rows.append(("T_peak", f"{s.get('T_peak_K', 0):.0f} K  ({band[0]:.0f}–{band[1]:.0f})"))
    rows.append(("n_e_peak", f"{s.get('n_e_peak', 0):.2e} m⁻³"))
    rows.append(("Γ peak", f"{s.get('Gamma_peak', 0):.2f}"))
    rows.append(("photons (4π)", f"{s.get('photons_visible_4pi', 0):.2e}"))
    pdc = s.get("photons_detected_PMT", {})
    if pdc:
        first_key = next(iter(pdc))
        rows.append((f"photons @ {first_key}", f"{pdc[first_key]:.2e}"))
    lifetime = s.get("expected_wall_lifetime_hours")
    if lifetime is not None:
        rows.append(("wall lifetime", f"{lifetime:.0f} h"))
    flash = s.get("flash_FWHM_ns")
    if flash is not None:
        rows.append(("flash FWHM", f"{flash:.2f} ns"))
    return rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title, template=PLOT_TEMPLATE, height=PLOT_HEIGHT_SMALL,
        annotations=[dict(text="(no data)", x=0.5, y=0.5,
                          xref="paper", yref="paper",
                          showarrow=False, font=dict(size=14, color="#aaa"))],
        margin=dict(l=20, r=20, t=40, b=40),
    )
    return fig

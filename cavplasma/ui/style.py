"""Colour scheme + layout constants for the §15 Dash app.

Centralised here so the figure factories (`figures.py`) and the layout
modules share one palette. Colours chosen to match §15.5 spec:
green / amber / red regime indicators and a continuous blue-to-red
pressure field for the standing-wave heatmap.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Regime indicator palette (§14.2 → §15.5)
# ---------------------------------------------------------------------------
REGIME_COLOR: dict[str, str] = {
    "stable_spherical":   "#2ca02c",   # green
    "marginal":           "#ff7f0e",   # amber
    "unstable_likely":    "#d62728",   # red
    "sub_blake":          "#7f7f7f",   # grey
    "linear_oscillation": "#b58900",   # solarized yellow — "nothing happening"
    "transducer_limited": "#d62728",
}


REGIME_DESCRIPTION: dict[str, str] = {
    "stable_spherical":   "Stable single-bubble dynamics — SBSL band. T_peak in 10⁴ K range, growth ratio 5–20×.",
    "marginal":           "Past Mach 0.3 — collapse violence is shape-stability marginal.",
    "unstable_likely":    "Parametric / Rayleigh–Taylor index above 1; expect fragmentation.",
    "sub_blake":          "Drive does not exceed the Blake threshold — no cavitation.",
    "linear_oscillation": "Bubble pumped near a resonance / off chamber Q-bandwidth — linear sloshing with no real collapse, no plasma. Move drive frequency or amplitude to escape.",
    "transducer_limited": "Requested drive exceeds transducer capacity.",
}


# ---------------------------------------------------------------------------
# Severity colours (suggestions / warnings)
# ---------------------------------------------------------------------------
SEVERITY_COLOR: dict[str, str] = {
    "error":   "#d62728",
    "warning": "#ff7f0e",
    "info":    "#1f77b4",
}


# ---------------------------------------------------------------------------
# Plot defaults — Solarized-dark palette to match the SOLAR Bootstrap theme.
# Solarized base palette (Ethan Schoonover):
#   base03  #002b36   — darkest bg
#   base02  #073642   — panel bg
#   base01  #586e75   — emphasised secondary text
#   base00  #657b83   — secondary text
#   base0   #839496   — primary text
#   base1   #93a1a1   — emphasised primary
#   yellow  #b58900   blue   #268bd2   green  #859900
#   red     #dc322f   magenta #d33682   cyan   #2aa198
# ---------------------------------------------------------------------------
PLOT_HEIGHT_SMALL = 220
PLOT_HEIGHT_MED = 320
PLOT_HEIGHT_LARGE = 460

BG_PRIMARY = "#002b36"     # Solarized base03 (matches SOLAR app shell)
BG_PANEL = "#073642"       # Solarized base02
TEXT_MUTED = "#93a1a1"     # Solarized base1


def _register_solarized_template() -> str:
    """Register the 'solarized_dark' Plotly template and return its name.

    Idempotent — re-registration is a no-op. Returned name is used as
    the default `template=` for every figure factory in `figures.py`.
    """
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
    except ImportError:
        return "plotly_dark"
    if "solarized_dark" not in pio.templates:
        pio.templates["solarized_dark"] = go.layout.Template(
            layout=dict(
                paper_bgcolor=BG_PRIMARY,
                plot_bgcolor=BG_PANEL,
                font=dict(color="#839496"),                   # base0
                title=dict(font=dict(color=TEXT_MUTED)),
                xaxis=dict(gridcolor="#586e75", zerolinecolor="#586e75",
                           linecolor="#586e75",
                           tickfont=dict(color="#839496"),
                           title=dict(font=dict(color="#93a1a1"))),
                yaxis=dict(gridcolor="#586e75", zerolinecolor="#586e75",
                           linecolor="#586e75",
                           tickfont=dict(color="#839496"),
                           title=dict(font=dict(color="#93a1a1"))),
                legend=dict(font=dict(color="#93a1a1"),
                            bgcolor="rgba(0,0,0,0)"),
                colorway=[
                    "#268bd2",   # blue
                    "#cb4b16",   # orange
                    "#859900",   # green
                    "#b58900",   # yellow
                    "#d33682",   # magenta
                    "#2aa198",   # cyan
                    "#dc322f",   # red
                    "#6c71c4",   # violet
                ],
            )
        )
    return "plotly_dark+solarized_dark"


PLOT_TEMPLATE = _register_solarized_template()


# ---------------------------------------------------------------------------
# Animation
# ---------------------------------------------------------------------------
ANIMATION_FPS = 30
ANIMATION_TICK_MS = 33                # 1000 / 30 ≈ 33 ms
ANIMATION_FRAME_BUDGET = 60           # max number of frames sent to the browser


# ---------------------------------------------------------------------------
# Notebook ring buffer (§15.6 + §15.11 #8)
# ---------------------------------------------------------------------------
NOTEBOOK_MAX_ENTRIES = 20

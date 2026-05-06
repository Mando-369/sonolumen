"""Dash layout components — controls + visualization + results + notebook.

§15.3 / §15.4 / §15.5 / §15.6 in one file. Each `*_panel()` function
returns a `dbc` component wired to dcc.Store ids. Callbacks live in
`callbacks.py`; they read these element ids by string.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from cavplasma.ui.style import (
    ANIMATION_FRAME_BUDGET,
    ANIMATION_TICK_MS,
    PLOT_HEIGHT_LARGE,
    PLOT_HEIGHT_MED,
    PLOT_HEIGHT_SMALL,
    PLOT_TEMPLATE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _empty_fig(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(template=PLOT_TEMPLATE, title=title,
                      height=PLOT_HEIGHT_SMALL,
                      margin=dict(l=20, r=20, t=40, b=40))
    return fig


def _accordion_item(title: str, body, item_id: str) -> dbc.AccordionItem:
    return dbc.AccordionItem(body, title=title, item_id=item_id)


# ---------------------------------------------------------------------------
# §15.3 — Controls panel
# ---------------------------------------------------------------------------
def controls_panel() -> dbc.Card:
    return dbc.Card(
        [
            dbc.CardHeader(html.B("Controls")),
            dbc.CardBody(
                [
                    dbc.Accordion(
                        [
                            _accordion_item("Liquid", _liquid_controls(), "liq"),
                            _accordion_item("Ambient", _ambient_controls(), "amb"),
                            _accordion_item("Drive", _drive_controls(), "drv"),
                            _accordion_item("Bubble", _bubble_controls(), "bub"),
                            _accordion_item("Physics", _physics_controls(), "phy"),
                            _accordion_item("Numerics", _numerics_controls(), "num"),
                        ],
                        always_open=True, start_collapsed=True,
                        active_item=["drv", "bub"],
                    ),
                    html.Br(),
                    dbc.Button("TEST  ▶", id="run_button", color="primary",
                               size="lg", className="w-100"),
                    html.Div(id="run_status", className="text-muted small mt-2"),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col(
                            dcc.Dropdown(
                                id="preset_dropdown",
                                options=[
                                    {"label": "SBSL canonical", "value": "sbsl_canonical"},
                                    {"label": "pistol shrimp", "value": "pistol_shrimp_event"},
                                    {"label": "tabletop starter", "value": "tabletop_starter"},
                                ],
                                placeholder="Load preset…",
                                clearable=False,
                            ),
                            width=12,
                        ),
                    ], className="g-2"),
                    html.Br(),
                    dbc.Row([
                        dbc.Col(dbc.Button("Save JSON", id="save_btn",
                                           color="secondary", size="sm",
                                           className="w-100"), width=6),
                        dbc.Col(dcc.Upload(
                            dbc.Button("Load JSON", color="secondary", size="sm",
                                       className="w-100"),
                            id="load_upload", multiple=False,
                        ), width=6),
                    ], className="g-2"),
                    dcc.Download(id="save_download"),
                ],
            ),
        ],
    )


def _liquid_controls() -> html.Div:
    return html.Div([
        dbc.Label("Liquid preset"),
        dcc.Dropdown(
            id="liquid_dropdown",
            options=[
                {"label": "water", "value": "water"},
                {"label": "seawater", "value": "seawater"},
                {"label": "glycerin", "value": "glycerin"},
                {"label": "98 % H₂SO₄", "value": "sulfuric_98"},
                {"label": "silicone oil 100 cSt", "value": "silicone_oil_100cSt"},
            ],
            value="water", clearable=False,
        ),
    ])


def _ambient_controls() -> html.Div:
    # `ambient_p` is stored as log₁₀(p_∞ in kPa). The conversion back to
    # Pa happens in `apply_controls`. Range covers ~30 kPa (high-altitude
    # / partial vacuum experiments) up to ~100 MPa (≈ 10 km seawater
    # depth, Challenger Deep). Marks call out common operating regimes
    # so the user has anchors when sweeping across depth.
    return html.Div([
        dbc.Label("T_∞ (K)"),
        dcc.Slider(id="ambient_T", min=273, max=323, value=293,
                   step=1, marks={273: "0 °C", 293: "20 °C", 323: "50 °C"}),
        html.Br(),
        dbc.Label("p_∞ (log₁₀ kPa) — covers vacuum → Mariana"),
        dcc.Slider(
            id="ambient_p", min=1.5, max=5.0, value=2.005, step=0.025,
            marks={
                1.5:  "30 kPa",         # high altitude / partial vacuum
                2.0:  "1 atm",          # sea surface
                3.0:  "1 MPa",          # ≈ 90 m seawater
                4.0:  "10 MPa",         # ≈ 1 km seawater
                5.0:  "100 MPa",        # ≈ 10 km — Challenger Deep
            },
            tooltip={"placement": "bottom", "always_visible": False,
                     "template": "log₁₀(kPa) = {value}"},
        ),
    ])


def _drive_controls() -> html.Div:
    return html.Div([
        dbc.Label("Frequency (kHz, log)"),
        dcc.Slider(
            id="drive_f", min=0, max=3.7, value=1.42, step=0.05,
            marks={0: "1", 1: "10", 1.4: "26.5", 2: "100", 3: "1k", 3.7: "5k"},
            tooltip={"always_visible": False},
        ),
        html.Br(),
        dbc.Label("Drive amplitude (atm)"),
        dcc.Slider(
            id="drive_pa", min=0.1, max=10.0, value=1.32, step=0.05,
            marks={0.5: "0.5", 1.0: "1", 1.32: "1.32", 3.0: "3", 10.0: "10"},
            tooltip={"always_visible": False},
        ),
        html.Br(),
        dbc.Label("Cycles to integrate"),
        dcc.Slider(id="drive_cycles", min=1, max=20, step=1, value=8,
                   marks={1: "1", 8: "8", 20: "20"}),
    ])


def _bubble_controls() -> html.Div:
    return html.Div([
        dbc.Label("R₀ (µm, log)"),
        dcc.Slider(
            id="bubble_R0", min=-1, max=4, value=0.65, step=0.05,
            marks={-1: "0.1", 0: "1", 1: "10", 2: "100", 3: "1000", 4: "10⁴"},
            tooltip={"always_visible": False},
        ),
        html.Br(),
        dbc.Label("Gas (mole fraction)"),
        dbc.Row([
            dbc.Col([dbc.Label("Ar"),
                     dcc.Input(id="gas_ar", type="number", value=0.99,
                               step=0.01, min=0, max=1, size="sm",
                               className="form-control form-control-sm")],
                    width=4),
            dbc.Col([dbc.Label("H₂O"),
                     dcc.Input(id="gas_h2o", type="number", value=0.01,
                               step=0.001, min=0, max=1, size="sm",
                               className="form-control form-control-sm")],
                    width=4),
            dbc.Col([dbc.Label("Air"),
                     dcc.Input(id="gas_air", type="number", value=0.0,
                               step=0.01, min=0, max=1, size="sm",
                               className="form-control form-control-sm")],
                    width=4),
        ], className="g-2"),
    ])


def _physics_controls() -> html.Div:
    return html.Div([
        dbc.Label("Bubble equation"),
        dcc.Dropdown(id="phys_bubble_eq",
                     options=[
                         {"label": "Keller–Miksis", "value": "keller_miksis"},
                         {"label": "Rayleigh–Plesset", "value": "rayleigh_plesset"},
                         {"label": "Gilmore", "value": "gilmore"},
                     ],
                     value="keller_miksis", clearable=False),
        html.Br(),
        dbc.Label("Thermal model"),
        dcc.Dropdown(id="phys_thermal",
                     options=[
                         {"label": "Toegel reduced ODE", "value": "toegel"},
                         {"label": "Polytropic", "value": "polytropic"},
                     ],
                     value="toegel", clearable=False),
        html.Br(),
        dbc.Label("Ionization model"),
        dcc.Dropdown(id="phys_ionization",
                     options=[
                         {"label": "Stewart–Pyatt", "value": "stewart_pyatt"},
                         {"label": "Ideal Saha", "value": "ideal_saha"},
                     ],
                     value="stewart_pyatt", clearable=False),
    ])


def _numerics_controls() -> html.Div:
    return html.Div([
        dbc.Label("rtol (log10)"),
        dcc.Slider(id="num_rtol", min=-13, max=-6, value=-11, step=1,
                   marks={-13: "1e-13", -11: "1e-11", -8: "1e-8", -6: "1e-6"}),
        html.Br(),
        dbc.Label("Convergence test"),
        dbc.Switch(id="num_conv", value=False, label="Enable §11.5 #5 ΔT_peak check"),
    ])


# ---------------------------------------------------------------------------
# §15.4 — Visualization panel
# ---------------------------------------------------------------------------
def visualization_panel() -> dbc.Card:
    return dbc.Card(
        [
            dbc.CardHeader(html.B("Virtual experiment")),
            dbc.CardBody([
                dcc.Graph(id="chamber_fig", figure=_empty_fig("Chamber cross-section")),
                dcc.Graph(id="bubble_fig", figure=_empty_fig("Bubble dynamics")),
                dcc.Graph(id="plasma_fig", figure=_empty_fig("Plasma diagnostics")),
                dcc.Graph(id="spectrum_fig", figure=_empty_fig("Spectrum surface")),
                dcc.Graph(id="detector_fig", figure=_empty_fig("Detector traces")),
                dcc.Graph(id="field_fig", figure=_empty_fig("Standing wave field")),
                dbc.Row([
                    dbc.Col(
                        dbc.Button("▶ Play", id="anim_toggle",
                                   color="info", size="sm",
                                   style={"minWidth": "92px"}),
                        width="auto"),
                    dbc.Col(
                        dcc.Slider(
                            id="time_slider",
                            min=0, max=ANIMATION_FRAME_BUDGET - 1,
                            step=1, value=0,
                            marks=None,
                            tooltip={"placement": "bottom",
                                     "always_visible": False,
                                     "template": "frame {value}"},
                            updatemode="drag",
                        ),
                        width=True),
                    dbc.Col(
                        html.Div(id="time_readout",
                                 className="text-muted small",
                                 style={"minWidth": "200px",
                                        "textAlign": "right"}),
                        width="auto"),
                ], className="g-2 align-items-center mt-1"),
                html.Div(id="anim_status",
                         className="text-muted small text-end"),
            ]),
        ],
    )


# ---------------------------------------------------------------------------
# §15.5 — Results panel
# ---------------------------------------------------------------------------
def results_panel() -> dbc.Card:
    return dbc.Card(
        [
            dbc.CardHeader(html.B("Results & suggestions")),
            dbc.CardBody([
                # Regime indicator
                html.Div(id="regime_card", className="mb-3"),

                # Headline numbers
                html.H6("Headline numbers"),
                html.Table(id="headline_table",
                           className="table table-sm table-striped"),

                # Suggestions
                html.H6("Suggestions"),
                html.Div(id="suggestions_list"),

                # Caveats
                html.H6("Caveats"),
                html.Div(id="caveats_list"),

                html.Hr(),

                # Listen button (§15.5)
                dbc.Button("🔊 Listen to event", id="listen_btn",
                           color="secondary", size="sm",
                           className="w-100 mb-2"),
                html.Audio(id="audio_player", controls=True,
                           style={"width": "100%"}),

                # §13 wall-stress mini summary
                html.Hr(),
                html.H6("Wall + transducer + thermal"),
                html.Div(id="material_summary",
                         className="text-muted small"),
            ]),
        ],
    )


# ---------------------------------------------------------------------------
# §15.6 — Lab notebook bottom panel
# ---------------------------------------------------------------------------
def notebook_panel() -> dbc.Card:
    return dbc.Card(
        [
            dbc.CardHeader(html.B("Lab notebook")),
            dbc.CardBody([
                html.Div(id="notebook_table"),
                html.Br(),
                dbc.Row([
                    dbc.Col(
                        dbc.Button("Export CSV", id="notebook_export_btn",
                                   color="secondary", size="sm"),
                        width="auto"),
                    dbc.Col(
                        dbc.Button("Clear", id="notebook_clear_btn",
                                   color="warning", size="sm"),
                        width="auto"),
                ]),
                dcc.Download(id="notebook_export_download"),
            ]),
        ],
    )


# ---------------------------------------------------------------------------
# Top-level layout
# ---------------------------------------------------------------------------
def _preset_confirm_modal() -> dbc.Modal:
    """§15 — confirmation modal for preset / JSON load.

    Loading a preset overwrites every slider, dropdown, and toggle in
    the controls panel. The modal makes that explicit so the user
    doesn't lose work to a single dropdown click.
    """
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Overwrite current settings?")),
            dbc.ModalBody([
                html.P([
                    "Loading ",
                    html.Span(id="preset_modal_name", className="fw-bold"),
                    " will replace every control value with the preset's settings.",
                ]),
                html.P("Continue?"),
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="preset_modal_cancel",
                           color="secondary", outline=True),
                dbc.Button("Load preset", id="preset_modal_confirm",
                           color="primary"),
            ]),
        ],
        id="preset_modal", is_open=False, centered=True, backdrop="static",
    )


def app_layout() -> dbc.Container:
    return dbc.Container(
        [
            html.H4("cavplasma — single-bubble cavitation plasma reactor",
                    className="mt-3 mb-3"),
            dbc.Row(
                [
                    dbc.Col(controls_panel(), width=3),
                    dbc.Col(visualization_panel(), width=6),
                    dbc.Col(results_panel(), width=3),
                ],
                className="g-2",
            ),
            dbc.Row(
                [
                    dbc.Col(notebook_panel(), width=12),
                ],
                className="g-2 mt-2",
            ),
            _preset_confirm_modal(),
            dcc.Store(id="scenario_store"),
            dcc.Store(id="result_store"),
            dcc.Store(id="notebook_store", storage_type="session", data=[]),
            dcc.Store(id="anim_state", data={"playing": False, "frame": 0}),
            dcc.Store(id="preset_pending", data=None),
            dcc.Store(id="preset_last_loaded", data=None),
            dcc.Interval(id="animation_tick", interval=ANIMATION_TICK_MS,
                         disabled=True),
        ],
        fluid=True,
    )

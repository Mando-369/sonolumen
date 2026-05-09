"""Dash layout components — controls + visualization + results + notebook.

§15.3 / §15.4 / §15.5 / §15.6 in one file. Each `*_panel()` function
returns a `dbc` component wired to dcc.Store ids. Callbacks live in
`callbacks.py`; they read these element ids by string.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html

from sonolumen.ui.style import (
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


def _slider_with_input(
    slider_id: str, *, slider_min: float, slider_max: float,
    slider_value: float, slider_step: float,
    input_id: str | None = None,
    input_min: float | None = None, input_max: float | None = None,
    input_step: float = 0,
    marks: dict | None = None,
    tooltip: dict | None = None,
    units: str = "",
):
    """Slider paired with a clickable numeric input that mirrors its value.

    The input has id `<slider_id>_input` by default. Bidirectional sync
    is wired in `callbacks.register_callbacks` via clientside callbacks
    — typing a value into the input snaps the slider to it (rounded by
    the slider's step), dragging the slider updates the input live.

    For log-scale sliders the slider stores the log value; pass the
    log range via slider_min/slider_max and the linear range via
    input_min/input_max — the bidirectional sync converts via 10^x.

    `units` is just a small grey suffix label after the input box for
    quick recognition (e.g. "Hz", "atm", "µm").
    """
    if input_id is None:
        input_id = f"{slider_id}_input"
    if input_min is None:
        input_min = slider_min
    if input_max is None:
        input_max = slider_max
    if input_step == 0:
        input_step = slider_step

    slider = dcc.Slider(
        id=slider_id, min=slider_min, max=slider_max, value=slider_value,
        step=slider_step, marks=marks or {},
        tooltip=tooltip or {"placement": "top", "always_visible": False},
    )
    input_box = dbc.Input(
        id=input_id, type="number",
        min=input_min, max=input_max, step=input_step,
        value=slider_value,        # default; clientside sync corrects on first drag
        className="form-control form-control-sm",
    )
    return dbc.Row([
        dbc.Col(slider, width=8, className="d-flex align-items-center"),
        dbc.Col(
            html.Div(
                [input_box, html.Span(
                    " " + units if units else "",
                    className="text-muted small ms-1",
                    style={"fontSize": "0.78em"},
                )],
                className="d-flex align-items-center",
            ),
            width=4),
    ], className="g-2 align-items-center")


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
                            _accordion_item("Chamber", _chamber_controls(), "cham"),
                            _accordion_item("Liquid", _liquid_controls(), "liq"),
                            _accordion_item("Ambient", _ambient_controls(), "amb"),
                            _accordion_item("Drive", _drive_controls(), "drv"),
                            _accordion_item("Bubble", _bubble_controls(), "bub"),
                            _accordion_item("Physics", _physics_controls(), "phy"),
                            _accordion_item("Numerics", _numerics_controls(), "num"),
                            _accordion_item("Auto-design (target → params)",
                                            _autodesign_controls(), "auto"),
                        ],
                        always_open=True, start_collapsed=True,
                        active_item=["drv", "bub"],
                    ),
                    html.Br(),
                    dbc.Button("TEST  ▶", id="run_button", color="primary",
                               size="lg", className="w-100"),
                    # Animated progress bar — shown immediately on click via
                    # a clientside callback (so the user knows the press
                    # registered), hidden by the run callback when complete.
                    # Combined with `run_elapsed_tick` below, the label text
                    # also counts elapsed seconds so the user can tell whether
                    # a run is actually progressing or stuck.
                    html.Div(
                        id="run_progress_container",
                        style={"display": "none", "marginTop": "8px"},
                        children=[
                            dbc.Progress(
                                id="run_progress_bar",
                                value=100,
                                animated=True,
                                striped=True,
                                color="info",
                                label="Running…",
                                style={"height": "22px",
                                       "fontSize": "0.85em"},
                            ),
                        ],
                    ),
                    # dcc.Loading wraps the status row — shows a spinner
                    # over the result while the run callback is in flight.
                    dcc.Loading(
                        id="run_loading",
                        type="default",
                        color="#268bd2",   # solarized blue, matches button
                        children=[
                            html.Div(id="run_status",
                                     className="text-muted small mt-2"),
                        ],
                    ),
                    # 250-ms tick driving the elapsed-time label inside the
                    # progress bar. Starts/stops based on run_progress_container
                    # display style so it idles when no run is active.
                    dcc.Interval(id="run_elapsed_tick",
                                 interval=250, disabled=True),
                    dcc.Store(id="run_started_at", data=None),
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
                    # Shows what's currently in the scenario store: a preset
                    # name when one is loaded from the dropdown, or the file
                    # name when one is uploaded via Load JSON. Updated by the
                    # _confirm_preset and _load callbacks.
                    html.Div(
                        id="scenario_source_label",
                        className="text-muted small mt-1",
                        style={"fontStyle": "italic"},
                    ),
                    dcc.Download(id="save_download"),
                ],
            ),
        ],
    )


def _chamber_controls() -> html.Div:
    """Chamber geometry / wall material / size / Q.

    radius and Q only enter the model for closed cavities (sphere /
    cylinder_axial / cylinder_radial). For pistol-jet, HIFU focus,
    and horn/open-bath geometries, the bubble is assumed to sit at
    a focal antinode with full drive amplitude — radius and Q do
    nothing in the current model. The two sliders are disabled in
    that mode by `_toggle_chamber_geom_controls` in callbacks.py.
    """
    return html.Div([
        dbc.Label("Chamber geometry — `chamber_geometry` in dossier"),
        dcc.Dropdown(
            id="chamber_geometry",
            options=[
                {"label": "Closed sphere",                  "value": "sphere"},
                {"label": "Cylinder (axial mode)",          "value": "cylinder_axial"},
                {"label": "Cylinder (radial mode)",         "value": "cylinder_radial"},
                {"label": "Open water / pistol-jet",        "value": "pistol_jet"},
                {"label": "HIFU focal spot",                "value": "hifu_focus"},
                {"label": "Horn / open bath",               "value": "horn_open_bath"},
            ],
            value="sphere", clearable=False,
        ),
        html.Div(id="chamber_geom_note",
                  className="text-muted small mt-1",
                  style={"fontSize": "0.78em", "fontStyle": "italic"}),
        html.Br(),
        dbc.Label("Chamber radius — `chamber_radius`"),
        _slider_with_input(
            slider_id="chamber_radius_cm", slider_min=1, slider_max=50,
            slider_value=5, slider_step=0.5, input_step=0.1,
            marks={1: "1 cm", 5: "5 cm", 10: "10 cm", 25: "25 cm", 50: "50 cm"},
            tooltip={"placement": "top", "always_visible": False,
                     "template": "{value} cm"},
            units="cm",
        ),
        html.Br(),
        dbc.Label("Wall material — `wall_material.name`"),
        dcc.Dropdown(
            id="chamber_wall",
            options=[
                {"label": "Borosilicate glass (Pyrex, transparent)",
                 "value": "borosilicate_glass"},
                {"label": "Fused silica (transparent, UV)",
                 "value": "fused_silica"},
                {"label": "Stainless 316",      "value": "stainless_316"},
                {"label": "Stainless 304",      "value": "stainless_304"},
                {"label": "Aluminum 6061",      "value": "aluminum_6061"},
                {"label": "Aluminum 1100",      "value": "aluminum_1100"},
                {"label": "Brass C36000",       "value": "brass_C36000"},
                {"label": "Ti-6Al-4V",          "value": "titanium_6al4v"},
                {"label": "Inconel 625",        "value": "inconel_625"},
                {"label": "Open water (no wall)",
                 "value": "open_water"},
            ],
            value="borosilicate_glass", clearable=False,
        ),
        html.Br(),
        dbc.Label("Quality factor Q — `chamber_Q`"),
        dbc.Input(id="chamber_Q", type="number",
                   value=1000, min=1, max=100000, step=10,
                   className="form-control form-control-sm"),
        html.Div(
            "Q sets the chamber's acoustic ringing for closed cavities — "
            "high Q amplifies on-resonance drives but tightens bandwidth "
            "(typical SBSL Pyrex sphere: 100–1000).",
            className="text-muted small mt-1",
            style={"fontSize": "0.78em"},
        ),
    ])


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
    # ambient_p is stored as log₁₀(p_∞ in kPa) so the slider can span
    # vacuum (~30 kPa) → Challenger Deep (~100 MPa) on a single bar.
    # The raw log value is hard to read, so a clientside callback in
    # callbacks.py keeps `ambient_p_readout` showing the actual unit-
    # resolved value (kPa / MPa) live as the user drags. Tooltips are
    # placed on top so they don't get clipped by the Drive panel below.
    return html.Div([
        dbc.Label("T_∞ — `ambient_T` in dossier"),
        _slider_with_input(
            slider_id="ambient_T", slider_min=273, slider_max=323,
            slider_value=293, slider_step=1, input_step=0.1,
            marks={273: "0 °C", 293: "20 °C", 323: "50 °C"},
            tooltip={"placement": "top", "always_visible": False,
                     "template": "{value} K"},
            units="K",
        ),
        html.Div(id="ambient_T_readout",
                  className="text-muted small mt-1",
                  style={"fontSize": "0.85em", "fontStyle": "italic"}),
        html.Br(),
        dbc.Label("p_∞ — `ambient_p`, covers vacuum → Mariana"),
        # Slider stores log₁₀(kPa); paired input shows the actual kPa
        # value via a log/linear conversion in the bidirectional sync
        # callback wired in callbacks.py.
        _slider_with_input(
            slider_id="ambient_p", slider_min=1.5, slider_max=5.0,
            slider_value=2.005, slider_step=0.025,
            input_id="ambient_p_input",
            input_min=30, input_max=100_000, input_step=1,
            marks={
                1.5:  "30 kPa",
                2.0:  "1 atm",
                3.0:  "1 MPa",
                4.0:  "10 MPa",
                5.0:  "100 MPa",
            },
            tooltip={"placement": "top", "always_visible": False,
                     "template": "log₁₀(kPa) = {value}"},
            units="kPa",
        ),
        html.Div(id="ambient_p_readout",
                  className="text-muted small mt-1",
                  style={"fontSize": "0.85em", "fontStyle": "italic"}),
    ])


def _drive_controls() -> html.Div:
    # The drive_f slider's value IS the frequency in Hz (linear, no log).
    # apply_controls reads it as a plain Hz value; nothing else needs to
    # know about the slider scale. Range 1 kHz – 200 kHz at 100 Hz steps
    # covers the SBSL operating regime densely; the auto-design panel can
    # reach above this when the user genuinely needs MHz-range drives.
    return html.Div([
        dbc.Label("Drive frequency f — `drive_f` in dossier"),
        _slider_with_input(
            slider_id="drive_f", slider_min=1_000, slider_max=200_000,
            slider_value=26_500, slider_step=100, input_step=1,
            marks={1_000: "1 kHz", 15_000: "15 kHz", 26_500: "26.5 kHz",
                   50_000: "50 kHz", 100_000: "100 kHz", 200_000: "200 kHz"},
            tooltip={"placement": "top", "always_visible": False,
                     "template": "{value} Hz"},
            units="Hz",
        ),
        html.Br(),
        dbc.Label("Drive amplitude P_A — `drive_pa` in dossier"),
        _slider_with_input(
            slider_id="drive_pa", slider_min=0.1, slider_max=10.0,
            slider_value=1.32, slider_step=0.05, input_step=0.01,
            marks={0.5: "0.5 atm", 1.0: "1 atm", 1.32: "1.32 atm",
                   3.0: "3 atm", 10.0: "10 atm"},
            tooltip={"placement": "top", "always_visible": False},
            units="atm",
        ),
        html.Br(),
        dbc.Label("Cycles to integrate"),
        _slider_with_input(
            slider_id="drive_cycles", slider_min=1, slider_max=20,
            slider_value=8, slider_step=1, input_step=1,
            marks={1: "1", 8: "8", 20: "20"},
            tooltip={"placement": "top", "always_visible": False},
            units="cycles",
        ),
    ])


def _bubble_controls() -> html.Div:
    return html.Div([
        dbc.Label("Bubble R₀ — `bubble_R0` in dossier"),
        # Slider stores log₁₀(R₀ in µm); paired input shows the actual
        # µm value via the log/linear conversion in callbacks.py.
        _slider_with_input(
            slider_id="bubble_R0", slider_min=-1, slider_max=4,
            slider_value=0.65, slider_step=0.05,
            input_id="bubble_R0_input",
            input_min=0.1, input_max=10_000, input_step=0.1,
            marks={-1: "0.1 µm", 0: "1 µm", 1: "10 µm",
                   2: "100 µm", 3: "1 mm", 4: "10 mm"},
            tooltip={"placement": "top", "always_visible": False,
                     "template": "log₁₀(µm) = {value}"},
            units="µm",
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


def _autodesign_controls() -> html.Div:
    """Inverse-design panel — target outcome → parameters.

    Two related features bundled together:

      * One-shot inverse design: target T_peak + filters → heuristic
        scenario (instant) or grid-refined scenario (~15 s).
      * Live auto-adapt: when the toggle is on, moving any of the
        three core physics sliders (drive_f, drive_pa, R₀) causes the
        other two to track via simple analytical relations
        (Minnaert frequency, Blake threshold, SBSL band scaling),
        so the bubble stays in a useful regime as the user explores.
        A live status chip warns when the configuration drifts off
        the SBSL ridge — sub-Blake, off-resonance, or past Mach 0.3.
    """
    return html.Div([
        dbc.Label("Target T_peak"),
        _slider_with_input(
            slider_id="autodesign_T_target_kK",
            slider_min=5, slider_max=50, slider_value=20,
            slider_step=1, input_step=0.5,
            marks={5: "5", 15: "15", 25: "25", 35: "35", 50: "50"},
            tooltip={"placement": "top", "always_visible": False,
                     "template": "{value} kK"},
            units="kK",
        ),
        html.Br(),
        dbc.Switch(id="autodesign_must_be_stable", value=True,
                   label="Require stable_spherical regime"),
        html.Br(),
        dbc.Label("Max transducer P_A — feasibility"),
        _slider_with_input(
            slider_id="autodesign_max_pa",
            slider_min=1, slider_max=20, slider_value=5.0,
            slider_step=0.5, input_step=0.1,
            marks={1: "1", 5: "5", 10: "10", 20: "20"},
            tooltip={"placement": "top", "always_visible": False},
            units="atm",
        ),
        html.Hr(),
        dbc.Row([
            dbc.Col(dbc.Button("Find parameters", id="autodesign_find_btn",
                                color="info", size="sm", className="w-100"),
                    width=6),
            dbc.Col(dbc.Button("Refine (~15 s)", id="autodesign_refine_btn",
                                color="info", size="sm", outline=True,
                                className="w-100"),
                    width=6),
        ], className="g-2"),
        html.Div(id="autodesign_status",
                  className="text-muted small mt-2"),
        html.Div(id="autodesign_diagnostic",
                  className="small mt-2",
                  style={"fontSize": "0.85em"}),
        html.Hr(),
        # Live coupling — one slider drives, the system *proposes*
        # adapted partners. User accepts or dismisses; sliders only
        # change on Apply. Avoids surprise jumps.
        dbc.Switch(id="couple_sliders_toggle", value=False,
                   label="Auto-adapt: propose coupled drive freq / R₀"),
        html.Div(
            "When ON, moving one slider previews the partner value "
            "needed to track the SBSL ridge. Sliders only change when "
            "you click Apply.",
            className="text-muted small mt-1",
            style={"fontSize": "0.78em"},
        ),
        # Status chip — coloured pill summarising the current
        # configuration's predicted regime, updated live as any of the
        # three physics sliders moves (regardless of toggle state).
        html.Div(id="couple_status_chip", className="mt-2"),
        # Proposal preview — shown only when the auto-adapt toggle is
        # on AND moving a slider would shift its partner by > 1 % in
        # log-space. Two buttons: Apply (push the proposed value into
        # the partner slider, write to scenario_store) and Dismiss
        # (clear the proposal, leave sliders alone).
        dbc.Card(
            id="couple_proposal_card",
            style={"display": "none"},
            color="info",
            outline=True,
            className="mt-2",
            children=dbc.CardBody([
                html.Div(id="couple_proposal_text",
                          style={"fontSize": "0.88em"}),
                dbc.Row([
                    dbc.Col(dbc.Button(
                        "Apply", id="couple_apply_btn",
                        color="info", size="sm", className="w-100"),
                        width=6),
                    dbc.Col(dbc.Button(
                        "Dismiss", id="couple_dismiss_btn",
                        color="secondary", outline=True, size="sm",
                        className="w-100"),
                        width=6),
                ], className="g-2 mt-2"),
            ], className="py-2"),
        ),
        # State store — holds the pending proposal payload between the
        # _propose_couple callback (writes) and the _apply / _dismiss
        # callbacks (reads + clears).
        dcc.Store(id="coupling_proposal", data=None),
    ])


def _numerics_controls() -> html.Div:
    return html.Div([
        dbc.Label("rtol (relative tolerance, log10) — `num_rtol`"),
        _slider_with_input(
            slider_id="num_rtol", slider_min=-13, slider_max=-6,
            slider_value=-11, slider_step=1, input_step=1,
            marks={-13: "1e-13", -11: "1e-11", -8: "1e-8", -6: "1e-6"},
            tooltip={"placement": "top", "always_visible": False,
                     "template": "log₁₀ = {value}"},
            units="log₁₀",
        ),
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

                # Wall pressure capability — what the chosen material +
                # geometry can take, vs. what the simulation predicts the
                # wall sees during collapse. Updated live as the user
                # changes wall_material / radius / thickness.
                html.Hr(),
                html.H6("Wall pressure capability"),
                html.Div(id="wall_capability_card"),

                # Liquid properties — every catalog field of the chosen
                # liquid, plus the T/p-corrected sound speed and
                # acoustic impedance, plus interpretive notes (vapor
                # quenching, viscous damping, etc.). Updated live as
                # the user changes liquid / T_∞ / p_∞.
                html.Hr(),
                html.H6("Liquid properties"),
                html.Div(id="liquid_properties_card"),

                # Bubble properties — derived numbers for the current
                # R₀ + liquid + ambient + drive: Minnaert frequency,
                # Blake threshold, drive/Minnaert ratio, Laplace
                # pressure, regime indicator. Updates live.
                html.Hr(),
                html.H6("Bubble properties"),
                html.Div(id="bubble_properties_card"),
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
                # Regime-history strip — one coloured tile per run, in
                # chronological order, so a parameter sweep visually
                # shows the sequence of regimes (sub_blake → linear →
                # stable → marginal → unstable). Hover gives the entry
                # number + regime label.
                html.Div(id="notebook_regime_strip", className="mb-2"),
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
            html.H4("sonolumen — single-bubble cavitation plasma reactor",
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

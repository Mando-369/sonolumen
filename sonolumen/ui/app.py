"""Dash app entry point. §15.10.

Run via:

    python -m sonolumen.ui            # → http://localhost:8050

The app is constructed lazily by `create_app()` so unit tests can build
+ inspect callbacks without spinning up a server.
"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc

from sonolumen.ui.callbacks import register_callbacks
from sonolumen.ui.layout import app_layout


def create_app() -> dash.Dash:
    """Build the Dash app + register all callbacks."""
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.SOLAR],
        title="sonolumen — single-bubble cavitation reactor",
        suppress_callback_exceptions=True,
    )
    app.layout = app_layout()
    register_callbacks(app)
    return app


def run_server(host: str = "127.0.0.1", port: int = 8050,
               debug: bool = False) -> None:
    """Run the Dash development server."""
    app = create_app()
    app.run(host=host, port=port, debug=debug)

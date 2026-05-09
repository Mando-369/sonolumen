"""sonolumen.ui — Plotly Dash UI for the §12 Scenario layer (§15).

Public API:

    from sonolumen.ui import create_app
    app = create_app()
    app.run(port=8050)

Or from the command line:

    python -m sonolumen.ui

The UI consumes the §12 Scenario API + §13 material module + §14
suggestions engine; v1, v2, §13, §14 are read-only dependencies.
"""

from sonolumen.ui.app import create_app, run_server

__all__ = ["create_app", "run_server"]

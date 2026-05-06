"""`python -m cavplasma.ui` entry point.

By default, serves the Dash app via the **waitress** production WSGI
server — no Flask development-server warning, no autoreload. Suitable
for personal lab use on `127.0.0.1`.

Pass `--debug` to switch to the Dash development server, which adds
auto-reload + Dash dev tools but emits the standard Flask warning.

§15.12 explicit out-of-scope: cloud deployment, multi-user, auth.
"""

from __future__ import annotations

import argparse
import logging

from cavplasma.ui.app import create_app, run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="cavplasma Dash UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument(
        "--debug", action="store_true",
        help="run via the Dash development server (auto-reload + dev tools, "
             "emits Flask 'development server' warning).",
    )
    args = parser.parse_args()

    if args.debug:
        print(f"cavplasma UI (dev server) starting on http://{args.host}:{args.port}")
        run_server(host=args.host, port=args.port, debug=True)
        return

    # Production: waitress. No warning, single-process, single-thread by default.
    try:
        from waitress import serve as waitress_serve
    except ImportError:                                                 # noqa: TRY300
        print("waitress not installed; falling back to Dash dev server "
              "(install with: pip install waitress).")
        run_server(host=args.host, port=args.port, debug=False)
        return

    # Quiet down waitress's own info logger; keep warnings.
    logging.getLogger("waitress").setLevel(logging.WARNING)
    app = create_app()
    print(f"cavplasma UI starting on http://{args.host}:{args.port}")
    print("(Ctrl-C to stop)")
    waitress_serve(app.server, host=args.host, port=args.port,
                    threads=4, ident="cavplasma")


if __name__ == "__main__":
    main()

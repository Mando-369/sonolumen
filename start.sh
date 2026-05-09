#!/usr/bin/env bash
# start.sh — launch the sonolumen Dash UI on http://127.0.0.1:8050.
#
# Usage:
#   ./start.sh                  # production WSGI (waitress), auto-opens browser
#   ./start.sh --debug          # Dash dev server (auto-reload + dev tools)
#   ./start.sh --port 9000      # custom port
#   ./start.sh --host 0.0.0.0   # bind to all interfaces
#   ./start.sh --no-browser     # skip the auto-open
#
# All other flags are forwarded to `python -m sonolumen.ui`.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
    cat >&2 <<EOF
error: .venv/bin/python not found in $SCRIPT_DIR

Create the virtual environment first:

    python3 -m venv .venv
    .venv/bin/pip install -e '.[ui]'

Then re-run ./start.sh.
EOF
    exit 1
fi

OPEN_BROWSER=1
HOST="127.0.0.1"
PORT="8050"
ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-browser)
            OPEN_BROWSER=0
            shift
            ;;
        --host)
            HOST="$2"
            ARGS+=("$1" "$2")
            shift 2
            ;;
        --host=*)
            HOST="${1#*=}"
            ARGS+=("$1")
            shift
            ;;
        --port)
            PORT="$2"
            ARGS+=("$1" "$2")
            shift 2
            ;;
        --port=*)
            PORT="${1#*=}"
            ARGS+=("$1")
            shift
            ;;
        -h|--help)
            sed -n '2,12p' "$0"
            exit 0
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

URL="http://${HOST}:${PORT}"

echo
echo "  sonolumen UI"
echo "  ${URL}"
echo "  Ctrl-C to stop"
echo

# Auto-open browser on macOS — but only after waitress has actually bound
# the socket and is serving. Polling avoids the "site can't be reached"
# race seen with a fixed sleep on slow startups.
if [[ "$OPEN_BROWSER" == "1" ]] && command -v open >/dev/null 2>&1; then
    (
        # Wait up to 30 s for HTTP 200, then open the browser. If we time
        # out, just open it anyway and let the user see the real error.
        for _ in $(seq 1 60); do
            if curl -sS -o /dev/null --max-time 1 "$URL" 2>/dev/null; then
                break
            fi
            sleep 0.5
        done
        open "$URL"
    ) &
fi

exec .venv/bin/python -m sonolumen.ui ${ARGS[@]+"${ARGS[@]}"}

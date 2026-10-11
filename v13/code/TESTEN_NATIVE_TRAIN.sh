#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PYTHONPATH="$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
exec "$PYTHON_BIN" "$APP_DIR/scripts/test_native_norm_shadow.py" --installed-home "${V13_HOME:-$HOME/v13}" "$@"

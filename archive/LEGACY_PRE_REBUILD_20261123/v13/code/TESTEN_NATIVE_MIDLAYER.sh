#!/usr/bin/env bash
set -Eeuo pipefail
V13_MIDLAYER_APP="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_MIDLAYER_PYTHON="$(command -v python3 || command -v python)"
export PYTHONPATH="$V13_MIDLAYER_APP${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
exec "$V13_MIDLAYER_PYTHON" "$V13_MIDLAYER_APP/scripts/test_native_midlayer_effect.py" --installed-home "${V13_HOME:-$HOME/v13}" "$@"

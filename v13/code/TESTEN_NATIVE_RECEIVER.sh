#!/usr/bin/env bash
set -Eeuo pipefail
V13_RECEIVER_APP="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_RECEIVER_PYTHON="$(command -v python3 || command -v python)"
export PYTHONPATH="$V13_RECEIVER_APP${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
exec "$V13_RECEIVER_PYTHON" "$V13_RECEIVER_APP/scripts/test_native_receiver_effect.py" --installed-home "${V13_HOME:-$HOME/v13}" "$@"

#!/usr/bin/env bash
# Independent bounded candidate; preserve the original device-check report.
set -Eeuo pipefail
V13_BOUNDED_APP="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_BOUNDED_PYTHON="$(command -v python3 || command -v python)"
export PYTHONPATH="$V13_BOUNDED_APP${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
exec "$V13_BOUNDED_PYTHON" "$V13_BOUNDED_APP/scripts/tool_forecast_bounded_phone_candidate.py" --installed-home "${V13_HOME:-$HOME/v13}" "$@"

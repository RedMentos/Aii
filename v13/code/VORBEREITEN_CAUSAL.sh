#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
V13_CAUSAL_APP="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_CAUSAL_PYTHON="$(command -v python3 || command -v python)"
export PYTHONPATH="$V13_CAUSAL_APP${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
exec "$V13_CAUSAL_PYTHON" -m v13.causal_prepare --home "${V13_HOME:-$HOME/v13}" "$@"

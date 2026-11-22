#!/usr/bin/env bash
set -Eeuo pipefail
V13_PORT_APP="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_PORT_PYTHON="$(command -v python3 || command -v python)"
export PYTHONPATH="$V13_PORT_APP${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
# Setup is explicit and separate so an active chat cannot trigger a concurrent
# installer. The collector checks installed pins and takes coordinator.lock.
exec "$V13_PORT_PYTHON" "$V13_PORT_APP/scripts/test_native_prefill_port.py" --installed-home "${V13_HOME:-$HOME/v13}" "$@"

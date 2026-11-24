#!/usr/bin/env bash
set -euo pipefail
V13_TEST_APP="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
V13_TEST_PYTHON="${V13_PYTHON:-python3}"
export PYTHONPATH="$V13_TEST_APP${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
V13_TEST_HOME="${V13_HOME:-$HOME/v13}"
V13_TEST_OUT="$V13_TEST_HOME/exports/step2-$(date -u +%Y%m%dT%H%M%S).json"
exec "$V13_TEST_PYTHON" "$V13_TEST_APP/tests/integration_step2_utility.py" --installed-home "$V13_TEST_HOME" --out "$V13_TEST_OUT" "$@"

#!/usr/bin/env bash
set -Eeuo pipefail
V13_TEST_APP="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_TEST_RESUME=0
for V13_TEST_ARG in "$@"; do
  if [[ "$V13_TEST_ARG" == --resume || "$V13_TEST_ARG" == --resume=* ]]; then V13_TEST_RESUME=1; fi
done
if [[ "$V13_TEST_RESUME" == 0 ]]; then V13_NO_AUTOSTART=1 bash "$V13_TEST_APP/setup.sh"; fi
V13_TEST_PYTHON="$(command -v python3 || command -v python)"
export PYTHONPATH="$V13_TEST_APP${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
exec "$V13_TEST_PYTHON" "$V13_TEST_APP/scripts/acceptance.py" --installed-home "${V13_HOME:-$HOME/v13}" "$@"

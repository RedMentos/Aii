#!/usr/bin/env bash
# Werkzeug-Folgen-Vorhersage auf diesem Gerät: Tap-Werkzeug bauen, Paritäts-Gate, Live-Prüfung (245 Aufrufe), Bericht.
# Mit --with-learning zusätzlich die Lern-Prüfung (610 Aufrufe, lang).
# Vorher `bash setup.sh` (gepinnte Laufzeit + Modelle). Kein Chat gleichzeitig. Bericht: ~/v13/exports/tool-forecast-*/report.json
set -Eeuo pipefail
V13_TF_APP="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_TF_PYTHON="$(command -v python3 || command -v python)"
export PYTHONPATH="$V13_TF_APP${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
exec "$V13_TF_PYTHON" "$V13_TF_APP/scripts/test_tool_forecast_phone.py" --installed-home "${V13_HOME:-$HOME/v13}" "$@"

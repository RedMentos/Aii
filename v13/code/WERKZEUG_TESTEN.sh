#!/usr/bin/env bash
# Handy-Paket Werkzeug-Vorhersage: Vorprüfung, ggf. Einrichtung, Messung mit Frist, Ergebnis-ZIP in Downloads.
# Stufen: bash WERKZEUG_TESTEN.sh paritaet | kurz (Standard) | voll. Anleitung: WERKZEUG_ANLEITUNG.txt
set -Eeuo pipefail
V13_WZ_APP="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_WZ_PYTHON="$(command -v python3 || command -v python || true)"
if [[ -z "$V13_WZ_PYTHON" ]]; then
  if [[ "${PREFIX:-}" == *com.termux* ]]; then pkg install -y python; V13_WZ_PYTHON="$(command -v python3 || command -v python)"
  else printf 'Python 3 fehlt.\n' >&2; exit 2; fi
fi
export PYTHONPATH="$V13_WZ_APP${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
exec "$V13_WZ_PYTHON" "$V13_WZ_APP/scripts/werkzeug_handy.py" "$@"

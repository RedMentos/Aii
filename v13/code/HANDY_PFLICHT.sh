#!/usr/bin/env bash
# WP-Z7 Handy-Pflichtmessungen: RAM, Beobachter-Residenz, Wiederholung, Werkzeug-Vorhersage, Langlauf; Ergebnis-ZIP in Downloads.
# Stufen: bash HANDY_PFLICHT.sh kurz (Standard) | voll.  Einzelne Schritte: --nur ram,residenz.  Anleitung: docs/HANDY_PFLICHT.md
set -Eeuo pipefail
V13_HP_APP="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_HP_PYTHON="$(command -v python3 || command -v python || true)"
if [[ -z "$V13_HP_PYTHON" ]]; then
  if [[ "${PREFIX:-}" == *com.termux* ]]; then pkg install -y python; V13_HP_PYTHON="$(command -v python3 || command -v python)"
  else printf 'Python 3 fehlt.\n' >&2; exit 2; fi
fi
export PYTHONPATH="$V13_HP_APP${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
exec "$V13_HP_PYTHON" "$V13_HP_APP/scripts/handy_pflicht.py" "$@"

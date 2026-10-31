#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
V13_APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_DATA_HOME="${V13_HOME:-$HOME/v13}"
trap 'printf "\nInstallation unterbrochen (Zeile %s). Nach Beheben erneut starten; fertige Downloads werden geprüft und wiederverwendet.\n" "$LINENO" >&2' ERR
printf 'V13 Age-0 · lokale Modelle · Einrichtung startet\n'
if [[ "${PREFIX:-}" == *com.termux* ]]; then
  pkg update -y
  pkg install -y python python-numpy clang cmake ninja make curl tar libandroid-spawn
else
  command -v python3 >/dev/null || { printf 'Python 3 fehlt. Bitte installieren.\n'; exit 1; }
  command -v g++ >/dev/null || command -v clang++ >/dev/null || { printf 'C++ Compiler fehlt.\n'; exit 1; }
fi
V13_PYTHON="$(command -v python3 || command -v python)"
"$V13_PYTHON" - <<'PY'
import sys
if sys.version_info < (3,10):raise SystemExit('Python >=3.10 erforderlich')
PY
if ! "$V13_PYTHON" -c 'import numpy' 2>/dev/null; then
  "$V13_PYTHON" -m pip install 'numpy>=1.24,<3'
fi
if ! "$V13_PYTHON" -m pip install 'prompt-toolkit==3.0.52'; then
  printf 'Vollbild-UI nicht verfügbar; einfache Textoberfläche bleibt nutzbar.\n'
fi
export PYTHONPATH="$V13_APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
mkdir -p "$V13_DATA_HOME"
"$V13_PYTHON" -m v13.bootstrap --home "$V13_DATA_HOME"
"$V13_PYTHON" - "$V13_APP_DIR" "$V13_DATA_HOME" "$V13_PYTHON" <<'PY'
from pathlib import Path
import sys,shlex
app,home,python=sys.argv[1:];h=Path(home).expanduser().resolve();p=h/'bin/v13'
text='#!/usr/bin/env bash\nset -e\nexport NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1\nexport PYTHONPATH='+shlex.quote(app)+'\nexec '+shlex.quote(python)+' -m v13 --home '+shlex.quote(str(h))+' "$@"\n'
p.write_text(text);p.chmod(0o700)
PY
if [[ "${PREFIX:-}" == *com.termux* ]]; then
  ln -sfn "$V13_DATA_HOME/bin/v13" "$PREFIX/bin/v13"
fi
"$V13_PYTHON" "$V13_APP_DIR/scripts/install_selftest.py" --cohort run102_c3
printf '\nErster echter Modelltest. Auf dem Handy kann das einige Minuten dauern.\n'
if ! "$V13_DATA_HOME/bin/v13" probe; then
  printf '\nMindestens ein Modelltest ist fehlgeschlagen. Der Bericht liegt in exports/native-probe.json. Mit :doctor/:logs prüfen; der Chat zeigt auch Fehler ausdrücklich an.\n'
fi
printf '\nStartbereit: %s/bin/v13 chat\n' "$V13_DATA_HOME"
if [[ -t 0 && "${V13_NO_AUTOSTART:-0}" != 1 ]]; then
  exec "$V13_DATA_HOME/bin/v13" chat --welcome
fi

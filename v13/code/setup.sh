#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
V13_APP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_DATA_HOME="${V13_HOME:-$HOME/v13}"
trap 'printf "\nInstallation unterbrochen (Zeile %s). Nach Beheben erneut starten; fertige Downloads werden geprüft und wiederverwendet.\n" "$LINENO" >&2' ERR
printf 'V13 Age-0 · lokale Modelle · Einrichtung startet\n'
# Source-only diagnostics are explicitly offline and must never run a package
# manager, including the Termux prologue. Normal installation is unchanged.
V13_OFFLINE_DIAGNOSTIC="${V13_SOURCE_ONLY_DIAGNOSTIC:-0}"
if [[ "$V13_OFFLINE_DIAGNOSTIC" == "1" ]]; then
  command -v python3 >/dev/null || command -v python >/dev/null || {
    printf 'SOURCE_ONLY_DIAGNOSTIC: vorhandenes Python fehlt; keine automatische Installation.\n' >&2
    exit 2
  }
elif [[ "${PREFIX:-}" == *com.termux* ]]; then
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
# Verify extracted source bytes before pip, V13 imports, bootstrap or model probe.
# This is an integrity check, not a publisher signature. Never ignore failure.
"$V13_PYTHON" -I -S "$V13_APP_DIR/scripts/verify_installed_source_run194.py" --root "$V13_APP_DIR"
if [[ "$V13_OFFLINE_DIAGNOSTIC" == "1" ]]; then
  if ! "$V13_PYTHON" -c 'import numpy' 2>/dev/null; then
    printf 'SOURCE_ONLY_DIAGNOSTIC: numpy fehlt; offline keine Paketinstallation.\n' >&2
    exit 2
  fi
else
  if ! "$V13_PYTHON" -c 'import numpy' 2>/dev/null; then
    "$V13_PYTHON" -m pip install 'numpy>=1.24,<3'
  fi
  if ! "$V13_PYTHON" -m pip install 'prompt-toolkit==3.0.52'; then
    printf 'Vollbild-UI nicht verfügbar; einfache Textoberfläche bleibt nutzbar.\n'
  fi
fi
export PYTHONPATH="$V13_APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1
mkdir -p "$V13_DATA_HOME"
if [[ "${V13_SOURCE_ONLY_DIAGNOSTIC:-0}" == "1" ]]; then
  # Explicit no-network source diagnostic. Do not attempt or claim native model
  # installation, model inference, Redmi proof, or a full selftest acceptance.
  "$V13_PYTHON" - "$V13_DATA_HOME" <<'PY'
from pathlib import Path
import sys
from v13.config import initialize
initialize(Path(sys.argv[1]))
PY
else
  "$V13_PYTHON" -m v13.bootstrap --home "$V13_DATA_HOME"
fi
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
if [[ "${V13_SOURCE_ONLY_DIAGNOSTIC:-0}" == "1" ]]; then
  printf '\nSOURCE_ONLY_DIAGNOSTIC: source integrity verified; Age-0 CLI initialized.\n'
  printf 'NO_NATIVE_MODEL / NO_REDMi / NO_JEPA_PROOF. Full selftest and model probe NOT RUN.\n'
  printf 'STEP2=UTILITY_FAIL B3_L1=FAIL Body-JEPA=UNAVAILABLE jepa_weight=0 V13=INCOMPLETE\n'
  "$V13_DATA_HOME/bin/v13" doctor
  printf '\nSource-only diagnostic finished. Normal setup requires pinned model downloads and native proof.\n'
  exit 0
fi
# Only the explicit portable subset is a supported phone-install preflight.
# Full unfiltered selftest remains available for source-wide regression with
# external pinned artifacts/dependencies; its known RED is never promoted.
printf '\nPORTABLE_SELFTEST: 94 Live-Softwaretests, keine volle Quellcode-Suite.\n'
"$V13_DATA_HOME/bin/v13" selftest --portable
printf 'Vollständige, ungefilterte Quellcode-Prüfung (mit externen Belegen): v13 selftest\n'
printf '\nErster echter Modelltest. Auf dem Handy kann das einige Minuten dauern.\n'
if ! "$V13_DATA_HOME/bin/v13" probe; then
  printf '\nMindestens ein Modelltest ist fehlgeschlagen. Der Bericht liegt in exports/native-probe.json. Mit :doctor/:logs prüfen; der Chat zeigt auch Fehler ausdrücklich an.\n'
fi
printf '\nStartbereit: %s/bin/v13 chat\n' "$V13_DATA_HOME"
if [[ -t 0 && "${V13_NO_AUTOSTART:-0}" != 1 ]]; then
  exec "$V13_DATA_HOME/bin/v13" chat --welcome
fi

#!/data/data/com.termux/files/usr/bin/bash
# Install a reversible, reviewed runtime candidate. Models are not downloaded.
set -Eeuo pipefail
umask 077
BRANCH="gpt6/v13-private-remote-bridge-20261111"
SOURCE="https://github.com/RedMentos/Aii.git"
ROOT="$HOME/.v13-runtime-recovery-source"
DATA="${V13_HOME:-$HOME/v13}"
fail() { printf '\nV13 RUNTIME ERROR: %s\n' "$*" >&2; exit 1; }
command -v pkg >/dev/null 2>&1 || fail "Diesen Befehl in Termux ausfuehren."
[[ -f "$DATA/bin/v13" ]] || fail "Bestehende V13-Installation fehlt."
pkg install -y git python patch || fail "Paketinstallation fehlgeschlagen."
python -c 'import numpy' || fail "NumPy fehlt: pkg install python-numpy"
if [[ -e "$ROOT" ]]; then
  [[ -d "$ROOT/.git" ]] || fail "Quellordner ist keine Git-Kopie."
  [[ "$(git -C "$ROOT" remote get-url origin)" == "$SOURCE" ]] || fail "Anderes Quell-Repository."
  [[ "$(git -C "$ROOT" branch --show-current)" == "$BRANCH" ]] || fail "Anderer Quell-Branch."
  [[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || fail "Lokale Quellaenderungen bleiben erhalten."
  git -C "$ROOT" fetch --no-tags --filter=blob:none origin "$BRANCH"
  git -C "$ROOT" merge --ff-only FETCH_HEAD
else
  git clone --depth 1 --single-branch --filter=blob:none --sparse --branch "$BRANCH" "$SOURCE" "$ROOT"
fi
git -C "$ROOT" sparse-checkout set v13/code/v13 v13/code/scripts v13/code/specs v13/code/candidates v13/code/tests
CODE="$ROOT/v13/code"
REVISION="$(git -C "$ROOT" rev-parse HEAD)"
BUILD="$HOME/.v13-runtime-builds/$REVISION/code"
cd "$CODE"
if [[ ! -e "$BUILD" ]]; then
  python scripts/stage_integrated_candidate.py --output "$BUILD"
fi
# Explicit local activation of a candidate, not a promotion of scientific gates.
# The helper validates all staged files and refuses a running V13 first.
python scripts/activate_termux_recovery.py --code-dir "$BUILD" --home "$DATA" --activate
printf '\nV13-Laufzeit umgestellt; vorhandene Modelle und Gespraeche bleiben lokal.\n'
printf 'Jetzt im Browser Chat starten. Fuer Dauerbetrieb dort separat senden:\n'
printf '  :idle on\n  :idle status\n'
printf 'Das aktiviert den vorhandenen Hintergrundplaner, kein Training grosser Modellgewichte.\n'
printf 'Fuer den B1-Test separat: :budget observer_seconds 90, danach :probe.\n'
printf 'Rueckweg (nur Programmstart, keine Daten zuruecksetzen):\n'
printf 'python %q --code-dir %q --home %q --rollback\n' "$CODE/scripts/activate_termux_recovery.py" "$BUILD" "$DATA"

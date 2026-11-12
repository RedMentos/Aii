#!/data/data/com.termux/files/usr/bin/bash
# V13 one-command Termux read-only private AI diagnostics.
# No password/token is entered into a ChatGPT conversation.
set -Eeuo pipefail
umask 077
BRANCH="gpt6/v13-private-remote-bridge-20261111"
SOURCE="https://github.com/RedMentos/Aii.git"
ROOT="$HOME/.v13-agent-source"
PRIVATE="$HOME/.v13-private"
CONFIG="$PRIVATE/remote.json"
RELAY="RedMentos/Aiiii"
fail() { printf '\nV13 SETUP ERROR: %s\n' "$*" >&2; exit 1; }
command -v pkg >/dev/null 2>&1 || fail "Dieses Skript muss in Termux laufen."
printf '\nV13: automatische Einrichtung des privaten Diagnosekanals\n'
printf 'Einmal GitHub im Browser bestaetigen; kein Passwort im Chat.\n'
printf 'Hinweis: GitHub CLI OAuth kann Zugriff auf weitere Repositories haben.\n\n'
pkg install -y git python gh curl || fail "Termux-Paketinstallation fehlgeschlagen"
command -v gh >/dev/null || fail "gh fehlt trotz Installation"

if [[ -e "$ROOT" ]]; then
  [[ -d "$ROOT/.git" ]] || fail "$ROOT existiert bereits, ist aber keine V13-Git-Kopie"
  [[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || fail "Lokale Codeaenderungen vorhanden; kein Ueberschreiben"
  git -C "$ROOT" fetch --depth 1 origin "$BRANCH" || fail "GitHub-Update fehlgeschlagen"
  git -C "$ROOT" checkout -B "$BRANCH" FETCH_HEAD || fail "Checkout fehlgeschlagen"
else
  git clone --depth 1 --filter=blob:none --sparse --single-branch \
    --branch "$BRANCH" "$SOURCE" "$ROOT" || fail "GitHub-Download fehlgeschlagen"
fi

git -C "$ROOT" sparse-checkout set --no-cone \
  v13/code/v13/__init__.py \
  v13/code/v13/remote_maintenance_bridge.py \
  v13/code/v13/owner_read_bridge.py \
  v13/code/v13/mobile_dashboard.py \
  v13/code/v13/mobile_dashboard.html \
  v13/code/v13/managed_console.py \
  v13/code/v13/source_updater.py \
  v13/code/scripts/v13-update \
  v13/code/v13/termux_patch_staging.py \
  v13/code/docs/PRIVATE_REMOTE_BRIDGE_20261111.md \
  v13/code/docs/ONE_COMMAND_TERMUX_20261111.md || fail "Sparse Checkout fehlgeschlagen"
[[ -s "$ROOT/v13/code/v13/owner_read_bridge.py" ]] || fail "Diagnoseprogramm fehlt"

if ! gh auth status -h github.com >/dev/null 2>&1; then
  printf '\nGitHub-Anmeldung: Browser oeffnen und den angezeigten Code bestaetigen.\n'
  gh auth login -h github.com -p https -w --scopes repo || fail "GitHub-Anmeldung abgebrochen"
fi
LOGIN="$(gh api user --jq '.login' 2>/dev/null)" || fail "GitHub-Konto nicht erreichbar"
[[ "$LOGIN" == "RedMentos" ]] || fail "Eingeloggt als '$LOGIN', erwartet RedMentos"
IS_PRIVATE="$(gh api "repos/$RELAY" --jq '.private' 2>/dev/null)" || fail "Privates Repository nicht erreichbar"
[[ "$IS_PRIVATE" == "true" ]] || fail "REPOSITORY NICHT PRIVAT; Einrichtung gestoppt"
CAN_WRITE="$(gh api "repos/$RELAY" --jq '.permissions.push' 2>/dev/null)" || fail "GitHub-Rechte nicht abrufbar"
[[ "$CAN_WRITE" == "true" ]] || fail "Keine Schreibberechtigung fuer Diagnoseantworten"

mkdir -p "$PRIVATE" "$PRIVATE/bridge-state" "$PRIVATE/bridge-stage"
chmod 700 "$PRIVATE" "$PRIVATE/bridge-state" "$PRIVATE/bridge-stage"
if [[ -e "$CONFIG" ]]; then
  [[ -f "$CONFIG" && ! -L "$CONFIG" ]] || fail "Unsichere vorhandene Konfiguration"
  chmod 600 "$CONFIG"
  printf 'Bestehende Konfiguration wird nicht ueberschrieben.\n'
else
  V13_ROOT="$ROOT" V13_PRIVATE="$PRIVATE" V13_CONFIG="$CONFIG" python - <<'PY'
import json, os, secrets
from pathlib import Path
home = Path(os.environ["V13_PRIVATE"])
root = Path(os.environ["V13_ROOT"])
out = Path(os.environ["V13_CONFIG"])
config = {
  "relay_repo": "RedMentos/Aiiii",
  "source_repo": "RedMentos/Aii",
  "installed_root": str(root),
  "state_dir": str(home / "bridge-state"),
  "staging_root": str(home / "bridge-stage"),
  "status_file": str(home / "live-status.json"),
  "keys": {"agent-owner": secrets.token_hex(32)},
  "authors": {"agent-owner": ["RedMentos"]},
  "permissions": {"agent-owner": ["HEALTH", "LEARNING_STATUS", "DIAGNOSTICS"]},
  "remote_apply_enabled": False,
  "apply_paths": [],
  "poll_seconds": 45
}
with out.open("x") as fp:
    json.dump(config, fp, indent=2)
out.chmod(0o600)
PY
fi

export PYTHONPATH="$ROOT/v13/code"
# Preserve existing phone-generated per-agent keys. Only extend the preexisting
# RedMentos read-only scope by an allowlisted structured technical diagnostic.
python - <<'PY'
import json, os
from pathlib import Path
p=Path.home()/".v13-private/remote.json"
if p.is_symlink(): raise SystemExit("ABBRUCH: private Konfiguration ist ein Symlink")
cfg=json.loads(p.read_text())
if cfg.get("relay_repo")!="RedMentos/Aiiii" or cfg.get("remote_apply_enabled") is not False:
    raise SystemExit("ABBRUCH: Keine Read-only-Konfiguration")
authors=cfg.get("authors",{}).get("agent-owner",[])
perms=cfg.get("permissions",{}).get("agent-owner",[])
if authors!=["RedMentos"] or not isinstance(perms,list) or set(perms)-{"HEALTH","LEARNING_STATUS","DIAGNOSTICS"}:
    raise SystemExit("ABBRUCH: unbekannte Agent-Rechte; keine automatische Rechteaenderung")
desired=["HEALTH","LEARNING_STATUS","DIAGNOSTICS"]
if perms!=desired:
    cfg["permissions"]["agent-owner"]=desired
    tmp=p.with_suffix(".new")
    with tmp.open("x") as f:
        json.dump(cfg,f,indent=2)
        f.flush()
        os.fsync(f.fileno())
    tmp.chmod(0o600)
    os.replace(tmp,p)
    print("Private Diagnoseberechtigung hinzugefuegt; Schluessel unveraendert.")
PY
python - <<'PY'
import os
from v13.remote_maintenance_bridge import private_config
cfg = private_config(os.path.expanduser("~/.v13-private/remote.json"))
if cfg["relay_repo"] != "RedMentos/Aiiii" or cfg.get("remote_apply_enabled"):
    raise SystemExit("ABBRUCH: Konfiguration ist nicht read-only")
if cfg["permissions"].get("agent-owner") != ["HEALTH", "LEARNING_STATUS", "DIAGNOSTICS"]:
    raise SystemExit("ABBRUCH: unerwartete Agent-Rechte")
print("Lokale read-only-Konfiguration validiert.")
PY

printf '\nTeste jetzt privaten GitHub-Zugang...\n'
python -m v13.owner_read_bridge once --config "$CONFIG" || fail "Verbindungstest fehlgeschlagen"
if [[ -e "$PRIVATE/bridge.pid" ]]; then
  OLD_PID="$(cat "$PRIVATE/bridge.pid" 2>/dev/null || true)"
  if [[ "$OLD_PID" =~ ^[0-9]+$ ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    # Only stop our own previous read-only poller. Never kill an unknown PID.
    CMDLINE="$(tr '\0' ' ' < "/proc/$OLD_PID/cmdline" 2>/dev/null || true)"
    if [[ "$CMDLINE" != *"v13.owner_read_bridge serve"* ]]; then
      fail "Aktive PID gehoert nicht eindeutig zur Bridge; bitte Prozess zuerst pruefen"
    fi
    printf 'Aktualisiere laufenden V13-Diagnose-Agenten (PID %s).\n' "$OLD_PID"
    kill "$OLD_PID" || fail "Konnte vorherigen Agenten nicht stoppen"
    for ATTEMPT in 1 2 3 4 5; do
      kill -0 "$OLD_PID" 2>/dev/null || break
      sleep 1
    done
    kill -0 "$OLD_PID" 2>/dev/null && fail "Vorheriger Diagnose-Agent ist noch aktiv"
  fi
fi
nohup python -m v13.owner_read_bridge serve --config "$CONFIG" \
  >> "$PRIVATE/bridge.log" 2>&1 < /dev/null &
PID="$!"
printf '%s\n' "$PID" > "$PRIVATE/bridge.pid"
sleep 2
kill -0 "$PID" 2>/dev/null || fail "Agent nicht gestartet; siehe ~/.v13-private/bridge.log"
printf '\n=== V13 PRIVATE BRIDGE: STARTED ===\n'
printf 'Privates Relay: https://github.com/RedMentos/Aiiii\n'
printf 'Agent-PID: %s\n' "$PID"
printf 'Diagnosen: HEALTH / LEARNING_STATUS (nur Lesen)\n'
printf 'PATCH_APPLY: AUS; kein allgemeiner Fernzugriff; kein offener Handy-Port.\n'
printf 'Android kann Hintergrundprozesse beenden; Redmi-Laufzeit noch zu pruefen.\n'
printf 'Im Chat: "Teste jetzt die V13 Live-Diagnose".\n'


printf '\nStarte lokale klickbare V13-Oberflaeche...\n'
# One-time optional Android Files access. Denied permission never exposes files.
if [[ ! -d "$HOME/storage/downloads" ]] && command -v termux-setup-storage >/dev/null; then
  printf 'Bitte Android-Zugriff auf Downloads bestaetigen, damit Diagnose-ZIPs gespeichert werden koennen.\n'
  termux-setup-storage || true
fi
# Older installers could leave *multiple* localhost dashboard processes.
# Reconcile all owner-owned exact dashboard Python processes, not just ui.pid.
# Never touch V13 model processes or unrelated Termux commands.
python - <<'PY'
import os, signal, time
from pathlib import Path

mine = os.getuid()
current = os.getpid()
targets = []
for p in Path("/proc").iterdir():
    if not p.name.isdecimal() or int(p.name) == current:
        continue
    try:
        if p.stat().st_uid != mine:
            continue
        args = [a.decode("utf-8", "replace")
                for a in (p / "cmdline").read_bytes().split(b"\0") if a]
    except (OSError, PermissionError):
        continue
    if (len(args) >= 4 and args[-3:] == ["-m", "v13.mobile_dashboard", "ui"]
            and Path(args[0]).name.startswith("python")):
        targets.append(int(p.name))
for pid in targets:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
if targets:
    deadline = time.monotonic() + 8
    for pid in targets:
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
                stat = (Path("/proc") / str(pid) / "stat").read_text()
                if stat.rsplit(")", 1)[1].strip().startswith("Z"):
                    break  # zombie means stopped; harmless until reaped
            except (ProcessLookupError, OSError):
                break
            time.sleep(.15)
        else:
            raise SystemExit("V13 UI: previous dashboard remains alive (PID " + str(pid) + ")")
    print("V13 UI: " + str(len(targets)) + " earlier local server(s) stopped.")
PY
: > "$PRIVATE/ui.log"
V13_UI_NO_AUTO_OPEN=1 nohup python -m v13.mobile_dashboard ui > "$PRIVATE/ui.log" 2>&1 < /dev/null &
UI_PID="$!"
printf '%s\n' "$UI_PID" > "$PRIVATE/ui.pid"
sleep 2
kill -0 "$UI_PID" 2>/dev/null || fail "Lokale UI startet nicht; siehe ~/.v13-private/ui.log"
UI_URL="$(grep -m 1 -Eo 'http://127\.0\.0\.1:[0-9]+/t/[a-f0-9]{48}/' "$PRIVATE/ui.log" 2>/dev/null || true)"
if [[ -n "$UI_URL" ]]; then
  printf '\nV13 TOUCH-OBERFLAECHE: %s\n' "$UI_URL"
  termux-open-url "$UI_URL" || printf 'Android Browser bitte mit dieser URL oeffnen.\n'
else
  printf 'UI-Start pruefen: tail -n 30 "$HOME/.v13-private/ui.log"\n'
fi
printf 'V13-Buttons: Nachricht senden, Gehirnstatus, Modelle testen, Diagnose-ZIP, Stopp.\n'
printf 'GitHub-Diagnoseabruf: nur erlaubte technische Fakten, keine Rohprotokolle.\n'

if [[ -n "$PREFIX" && -d "$PREFIX/bin" ]]; then
  cp "$ROOT/v13/code/scripts/v13-update" "$PREFIX/bin/v13-update"
  chmod 700 "$PREFIX/bin/v13-update"
fi
printf 'Code-Aktualisierung: v13-update (oder ein Button im Browser).\n'

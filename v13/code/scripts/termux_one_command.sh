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

# Never replace a dashboard while it owns a live model/chat process. Those
# children have their own process session and would outlive a killed UI.
# A saved local stop is an explicit user decision, not a successful startup.
# An explicit new V13 start/install command authorizes a controlled restart.
# Old UI versions do not yet implement the lifecycle files, so stop only
# recognized current-user V13 chat processes via their isolated process group.
# Do not signal other Termux/Python processes or kill a running task with SIGKILL.
python - <<'PY'
import json, os, signal, time
from pathlib import Path

home = Path.home()
private = home / ".v13-private"
if (private / "bridge-state/STOP").exists():
    raise SystemExit("V13: privater Agent wurde bewusst gestoppt. "
                     "Zum Fortsetzen erst owner_read_bridge resume ausführen; kein automatischer Neustart.")
proc = Path("/proc")
if not proc.is_dir():
    raise SystemExit("V13: Prozesssicht fehlt, sicherer Neustart nicht möglich.")
own = os.getuid()
expected_launcher = str(home / "v13/bin/v13")
seen = 0
targets = []
unknown_v13 = []
for p in proc.iterdir():
    if not p.name.isdecimal() or int(p.name) == os.getpid():
        continue
    try:
        if p.stat().st_uid != own:
            continue
        args = [x.decode("utf-8","replace") for x in (p/"cmdline").read_bytes().split(b"\0") if x]
        env = (p/"environ").read_bytes().split(b"\0")
        if b"HOME="+os.fsencode(home) not in env:
            # An unfamiliar V13 process owned by the same Termux UID is
            # still a conflict, but must NEVER be signalled automatically.
            if any(a == "v13" or a.endswith("/bin/v13") for a in args):
                unknown_v13.append(int(p.name))
            continue
    except OSError:
        continue
    if not args:
        continue
    seen += 1
    controlled = (expected_launcher in args and "chat" in args)
    module = ("-m" in args and "v13" in args and "chat" in args)
    if controlled or module:
        targets.append(int(p.name))
    elif any(a == "v13" or a.endswith("/bin/v13") for a in args):
        unknown_v13.append(int(p.name))
if unknown_v13:
    raise SystemExit("V13: Ein nicht verwalteter V13-Prozess ist aktiv. "
                     "Zum Schutz der Daten zuerst V13 beenden; kein fremder Prozess wird gestoppt.")
if seen == 0:
    raise SystemExit("V13: Prozesssicht unsicher, Einrichtung gestoppt.")
if not targets:
    print("V13: keine aktive Chat-Sitzung; kein Stop nötig.")
else:
    print(f"V13: beende {len(targets)} erkannte lokale Chat-Sitzung(en) automatisch ...")
    def alive(pid):
        try:
            fields=(proc/str(pid)/"stat").read_text().rsplit(")",1)[1].split()
            return fields[0] != "Z"
        except (FileNotFoundError, ProcessLookupError):
            return False
    own_group=os.getpgrp()
    for pid in targets:
        try:
            group=os.getpgid(pid)
            if group==pid and group!=own_group:
                os.killpg(group,signal.SIGINT)
            else:
                os.kill(pid,signal.SIGINT)
        except ProcessLookupError:
            continue
    deadline=time.monotonic()+12
    while time.monotonic()<deadline and any(alive(pid) for pid in targets):
        time.sleep(.15)
    # Only the same explicitly identified session, never the parent's shell.
    for pid in targets:
        if not alive(pid):
            continue
        try:
            group=os.getpgid(pid)
            if group==pid and group!=own_group:
                os.killpg(group,signal.SIGTERM)
            else:
                os.kill(pid,signal.SIGTERM)
        except ProcessLookupError:
            continue
    deadline=time.monotonic()+7
    while time.monotonic()<deadline and any(alive(pid) for pid in targets):
        time.sleep(.15)
    if any(alive(pid) for pid in targets):
        raise SystemExit("V13: Chat kann nicht sicher beendet werden. Kein Update angewendet.")
    private.mkdir(mode=0o700,parents=True,exist_ok=True)
    if private.is_symlink() or private.stat().st_mode & 0o077:
        raise SystemExit("V13: privater Speicher nicht geschützt.")
    flag=private/"v13-lifecycle-resume.json"
    if flag.is_symlink():
        raise SystemExit("V13: unsicherer Neustartmarker.")
    with flag.open("w") as out:
        json.dump({"schema":"v13.lifecycle.resume/1", "reason":"INSTALL",
                   "expires":int(time.time())+900},out)
        out.flush()
        os.fsync(out.fileno())
    flag.chmod(0o600)
    print("V13: Chat beendet; automatischer Neustart nach Installation vorgemerkt.")
PY

# Stop idle old dashboards before changing their on-disk HTML/Python sources.
# Freeze each verified owner-owned UI briefly, so it cannot launch a child
# between the child check and termination. A live session is preserved.
python - <<'PY_DASHBOARD'
import os, signal, time
from pathlib import Path

mine = os.getuid()
targets = []
frozen = []

def process_state(pid):
    try:
        return (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()[0]
    except FileNotFoundError:
        return None

try:
    for p in Path("/proc").iterdir():
        if not p.name.isdecimal() or int(p.name) == os.getpid():
            continue
        try:
            if p.stat().st_uid != mine:
                continue
            args = [a.decode("utf-8", "replace")
                    for a in (p / "cmdline").read_bytes().split(b"\0") if a]
            # Other test homes or checkouts can run under the same Linux UID.
            # Only reconcile this installer's own Termux home.
            expected_home = b"HOME=" + os.fsencode(Path.home())
            if expected_home not in (p / "environ").read_bytes().split(b"\0"):
                continue
        except OSError:
            continue
        if (len(args) >= 4 and args[-3:] == ["-m", "v13.mobile_dashboard", "ui"]
                and Path(args[0]).name.startswith("python")):
            targets.append(int(p.name))
    for pid in targets:
        try:
            os.kill(pid, signal.SIGSTOP)
            frozen.append(pid)
        except ProcessLookupError:
            continue
        deadline = time.monotonic() + 2
        while process_state(pid) not in (None, "Z", "T", "t"):
            if time.monotonic() >= deadline:
                raise SystemExit("V13 UI: vorherige Oberflaeche kann nicht sicher angehalten werden.")
            time.sleep(.01)
    for p in Path("/proc").iterdir():
        if not p.name.isdecimal():
            continue
        try:
            if p.stat().st_uid != mine:
                continue
            fields = (p / "stat").read_text().rsplit(")", 1)[1].split()
        except FileNotFoundError:
            continue
        if int(fields[1]) in frozen and fields[0] != "Z":
            raise SystemExit("V13 UI: aktive V13-Sitzung oder Update erkannt. Zuerst V13 beenden "
                             "bzw. Update abwarten, dann erneut versuchen. Oberflaeche bleibt erhalten.")
    for pid in frozen:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
finally:
    for pid in frozen:
        try:
            os.kill(pid, signal.SIGCONT)
        except ProcessLookupError:
            pass

for pid in frozen:
    deadline = time.monotonic() + 8
    while process_state(pid) not in (None, "Z"):
        if time.monotonic() >= deadline:
            raise SystemExit("V13 UI: vorherige Oberflaeche ist noch aktiv; kein Quellupdate.")
        time.sleep(.1)
if frozen:
    print("V13 UI: " + str(len(frozen)) + " vorherige inaktive Oberflaeche(n) beendet.")
PY_DASHBOARD

if [[ -e "$ROOT" ]]; then
  [[ -d "$ROOT/.git" ]] || fail "$ROOT existiert bereits, ist aber keine V13-Git-Kopie"
  [[ "$(git -C "$ROOT" remote get-url origin)" == "$SOURCE" ]] || fail "Unerwartetes Quell-Repository; kein Update"
  [[ "$(git -C "$ROOT" symbolic-ref --quiet --short HEAD)" == "$BRANCH" ]] || fail "Anderer oder abgetrennter Quell-Branch; kein Update"
  [[ -z "$(git -C "$ROOT" status --porcelain --untracked-files=no)" ]] || fail "Lokale Codeaenderungen vorhanden; kein Ueberschreiben"
  git -C "$ROOT" fetch --no-tags --filter=blob:none origin "$BRANCH" || fail "GitHub-Update fehlgeschlagen"
  git -C "$ROOT" merge --ff-only FETCH_HEAD || fail "Quellhistorie nicht fast-forward; lokale Commits bleiben erhalten"
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
  v13/code/v13/pipeline_agent.py \
  v13/code/v13/lifecycle.py \
  v13/code/v13/chat_service.py \
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
  "permissions": {"agent-owner": ["HEALTH", "LEARNING_STATUS", "DIAGNOSTICS", "PIPELINE_STATUS", "LOG_PAGE"]},
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
# Do not let an older v13 package in the caller's working directory shadow
# the freshly downloaded dashboard and bridge modules.
cd "$ROOT/v13/code" || fail "Quellverzeichnis nicht erreichbar"
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
if authors!=["RedMentos"] or not isinstance(perms,list) or set(perms)-{"HEALTH","LEARNING_STATUS","DIAGNOSTICS","PIPELINE_STATUS","LOG_PAGE"}:
    raise SystemExit("ABBRUCH: unbekannte Agent-Rechte; keine automatische Rechteaenderung")
desired=["HEALTH","LEARNING_STATUS","DIAGNOSTICS","PIPELINE_STATUS","LOG_PAGE"]
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
if cfg["permissions"].get("agent-owner") != ["HEALTH", "LEARNING_STATUS", "DIAGNOSTICS", "PIPELINE_STATUS", "LOG_PAGE"]:
    raise SystemExit("ABBRUCH: unerwartete Agent-Rechte")
print("Lokale read-only-Konfiguration validiert.")
PY

# The user explicitly requested continuous automatic updates. Enable once,
# but respect any later explicit OFF choice in the click dashboard.
if [[ ! -e "$PRIVATE/auto-update-setup-completed" ]]; then
  [[ ! -L "$PRIVATE/auto-source-update.enabled" ]] || fail "Unsicherer Auto-Update-Schalter"
  printf 'yes\n' > "$PRIVATE/auto-source-update.enabled"
  chmod 600 "$PRIVATE/auto-source-update.enabled"
  printf 'configured\n' > "$PRIVATE/auto-update-setup-completed"
  chmod 600 "$PRIVATE/auto-update-setup-completed"
  printf 'Auto-Updates EIN: alle 15 Minuten, nur GitHub-CI-gruene Commits, niemals bei laufender V13-KI.\n'
else
  printf 'Vorhandene Auto-Update-Einstellung bleibt erhalten.\n'
fi

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
    if kill -0 "$OLD_PID" 2>/dev/null; then
      OLD_STAT="$(cat "/proc/$OLD_PID/stat" 2>/dev/null || true)"
      OLD_STATE="${OLD_STAT##*) }"
      [[ "$OLD_STATE" == Z\ * ]] || fail "Vorheriger Diagnose-Agent ist noch aktiv"
    fi
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
printf 'Diagnosen: HEALTH / LEARNING_STATUS / DIAGNOSTICS / PIPELINE_STATUS (nur Lesen)\n'
printf 'PATCH_APPLY: AUS; kein allgemeiner Fernzugriff; kein offener Handy-Port.\n'
printf 'Android kann Hintergrundprozesse beenden; Redmi-Laufzeit noch zu pruefen.\n'
printf 'Im Chat: "Teste jetzt die V13 Live-Diagnose".\n'



# The actual V13 model/chat must be independent of browser tabs and GitHub
# polling. Installer invocation explicitly starts it in the background.
printf '\nStarte die eigenstaendige V13-KI im Hintergrund...\n'
python - <<'PY'
from v13.chat_service import _desired
_desired(True)
print("V13 AI Autostart: EIN")
PY

# On reruns, replace an older daemon AFTER the installer has stopped V13's
# recognized chat session. Do not terminate unknown Python processes.
python - <<'PY'
import os, signal, time
from pathlib import Path
myuid=os.getuid()
targets=[]
for p in Path("/proc").iterdir():
    if not p.name.isdecimal() or int(p.name)==os.getpid():
        continue
    try:
        if p.stat().st_uid != myuid:
            continue
        args=[x.decode("utf-8","replace") for x in (p/"cmdline").read_bytes().split(b"\0") if x]
    except OSError:
        continue
    if (len(args)>=4 and args[-3:]==["-m","v13.chat_service","serve"]
            and Path(args[0]).name.startswith("python")):
        targets.append(int(p.name))
for pid in targets:
    try:os.kill(pid,signal.SIGTERM)
    except ProcessLookupError:pass
deadline=time.monotonic()+8
for pid in targets:
    while time.monotonic()<deadline:
        try:
            os.kill(pid,0)
            if (Path("/proc")/str(pid)/"stat").read_text().rsplit(")",1)[1].strip().startswith("Z"):
                break
        except (ProcessLookupError, OSError):
            break
        time.sleep(.1)
    else:
        raise SystemExit("V13: alter KI-Dienst konnte nicht sicher beendet werden")
PY
touch "$PRIVATE/ai-service.log"
chmod 600 "$PRIVATE/ai-service.log"
nohup python -m v13.chat_service serve >> "$PRIVATE/ai-service.log" 2>&1 < /dev/null &
AI_PID="$!"
printf '%s\n' "$AI_PID" > "$PRIVATE/ai-service.pid"
sleep 2
kill -0 "$AI_PID" 2>/dev/null || fail "V13 KI Hintergrunddienst nicht gestartet; siehe ~/.v13-private/ai-service.log"
python -m v13.chat_service status || fail "V13 KI nicht ueber lokalen Dienst erreichbar"
printf 'V13 KI: eigenstaendiger Hintergrunddienst. Browser kann geschlossen werden.\n'

printf '\nStarte lokale klickbare V13-Oberflaeche...\n'
# One-time optional Android Files access. Denied permission never exposes files.
if [[ ! -d "$HOME/storage/downloads" ]] && command -v termux-setup-storage >/dev/null; then
  printf 'Bitte Android-Zugriff auf Downloads bestaetigen, damit Diagnose-ZIPs gespeichert werden koennen.\n'
  termux-setup-storage || true
fi
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
printf 'Privater GitHub-Pipeline-Status: PIPELINE_STATUS (read-only).\n'
printf 'Automatik prueft Code im Relay-Dienst, auch wenn der Browser geschlossen ist.\n'

if [[ -n "$PREFIX" && -d "$PREFIX/bin" ]]; then
  cp "$ROOT/v13/code/scripts/v13-update" "$PREFIX/bin/v13-update"
  chmod 700 "$PREFIX/bin/v13-update"
fi
printf 'Code-Aktualisierung: v13-update (oder ein Button im Browser).\n'

# Optional Termux:Boot integration. Has no effect unless the separate official
# Termux:Boot Android add-on is installed and permitted by Android.
# No wake-lock or browser launch by default; no secret is stored in the hook.
BOOT="$HOME/.termux/boot"
mkdir -p "$BOOT"
chmod 700 "$BOOT"
# Optional boot re-entry for the actual V13 AI, independent of the
# updater/bridge hook. Runs ONLY when the official Termux:Boot addon exists.
AI_BOOT="$HOME/.termux/boot/v13-ai"
if [[ ! -e "$AI_BOOT" && ! -L "$AI_BOOT" ]]; then
  cat > "$AI_BOOT" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
PRIVATE="$HOME/.v13-private"
[[ -f "$PRIVATE/v13-ai-enabled.json" ]] || exit 0
export PYTHONPATH="$HOME/.v13-agent-source/v13/code"
cd "$HOME/.v13-agent-source/v13/code" || exit 0
python - <<'PY'
from v13.chat_service import _read_desired
raise SystemExit(0 if _read_desired() else 1)
PY
[[ "$?" == 0 ]] || exit 0
nohup python -m v13.chat_service serve >> "$PRIVATE/ai-service.log" 2>&1 < /dev/null &
printf '%s\n' "$!" > "$PRIVATE/ai-service.pid"
EOF
  chmod 700 "$AI_BOOT"
  printf 'Optionaler Termux:Boot Hook fuer die echte V13-KI eingerichtet.\n'
fi


BOOT_HOOK="$BOOT/v13-private-relay"
if [[ ! -e "$BOOT_HOOK" && ! -L "$BOOT_HOOK" ]]; then
  cat > "$BOOT_HOOK" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
PRIVATE="$HOME/.v13-private"
[[ -f "$PRIVATE/remote.json" && ! -e "$PRIVATE/bridge-state/STOP" ]] || exit 0
[[ -f "$PRIVATE/auto-source-update.enabled" ]] || exit 0
[[ "$(cat "$PRIVATE/auto-source-update.enabled" 2>/dev/null)" == "yes" ]] || exit 0
if [[ -r "$PRIVATE/bridge.pid" ]]; then
  OLD="$(cat "$PRIVATE/bridge.pid" 2>/dev/null || true)"
  if [[ "$OLD" =~ ^[0-9]+$ ]] && kill -0 "$OLD" 2>/dev/null; then
    CMD="$(tr '\0' ' ' < "/proc/$OLD/cmdline" 2>/dev/null || true)"
    [[ "$CMD" == *"v13.owner_read_bridge serve"* ]] && exit 0
  fi
fi
export PYTHONPATH="$HOME/.v13-agent-source/v13/code"
cd "$HOME/.v13-agent-source/v13/code" || exit 0
nohup python -m v13.owner_read_bridge serve --config "$PRIVATE/remote.json" \
  >> "$PRIVATE/bridge.log" 2>&1 < /dev/null &
printf '%s\n' "$!" > "$PRIVATE/bridge.pid"
EOF
  chmod 700 "$BOOT_HOOK"
  printf 'Optionaler Boot-Hook eingerichtet (nur mit separater Termux:Boot-App aktiv).\n'
else
  printf 'Bestehende Boot-Konfiguration bleibt erhalten.\n'
fi


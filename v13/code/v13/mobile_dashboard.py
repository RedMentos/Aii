"""Private, local-only browser buttons for V13 on Android Termux.

An explicit local browser is the UI. No public listener, remote shell, Android
accessibility permission, raw log upload, or unsupervised model-weight edits.
"""
from __future__ import annotations
import argparse
import ast
from datetime import datetime
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse
import zipfile
from .managed_console import ManagedConsole

PRIVATE = Path.home() / ".v13-private"
DATA = Path.home() / "v13"
MAX_TAIL = 100_000
BUNDLE_LIMIT = 200_000
PORT = 0  # OS-selected local port; no remote interface
AUTO_FILE = PRIVATE / "auto-source-update.enabled"
REMOTE_LOG_FLAG = PRIVATE / "share-v13-log-summary.enabled"
REMOTE_FULL_FLAG = PRIVATE / "share-v13-console.enabled"
KNOBS_UI = {
 "threads": (1, 8, 1, "CPU-Threads"),
 "answer_tokens": (16, 512, 16, "Antwort-Tokens"),
 "deadline_seconds": (5, 300, 5, "Antwort-Zeitlimit (Sek.)"),
 "temperature": (0, 1, 0.05, "Temperatur"),
 "body_residency_mb": (0, 2400, 100, "Modell-RAM-Budget (MB)"),
}
QUICK_COMMANDS = {
 ":help", ":status", ":doctor", ":doctor full", ":resources", ":models", ":brain map", ":brain status",
 ":world", ":worldmodel status", ":self", ":self model", ":memory", ":episodes status", ":learning record",
 ":learning shadow", ":learning commit", ":requests", ":learning", ":knobs", ":plasticity", ":objectives",
 ":components", ":jef status", ":sleep status", ":sleep digest", ":replay status", ":backup", ":notaus",
 ":gates all", ":gates summary", ":route auto", ":route simple", ":route detail", ":route gist", ":route both",
 ":observers off", ":observers background", ":probe", ":probe jef-modes", ":probe step12", ":probe body-state",
 ":scheduler", ":age", ":growth status", ":teacher compare", ":workspace status", ":bodyview status",
 ":neuromod status", ":homeostasis status", ":attention status", ":callosum status", ":ctxos status",
 ":fabric report", ":live", ":jefsource", ":register summary", ":permissions", ":ledger", ":logs",
 ":task", ":ratings", ":context", ":archive status", ":source", ":export dataset", ":focal",
 ":notaus status", ":stillstand status", ":organ list", ":organ status", ":verbot liste", ":regeln",
}

ALLOWED = {"doctor": ("doctor",), "probe": ("probe",), "ask": ("ask",)}
SECRET = re.compile(r"(?i)(github_pat_[a-z0-9_]+|gh[pousr]_[a-z0-9_]+|(?:token|password|authorization|api.?key)\s*[:=]\s*\S+)")
TERM = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")


def safe_text(raw):
    s = TERM.sub("", raw.decode("utf-8", errors="replace"))
    s = SECRET.sub("[REDACTED]", s)
    s = EMAIL.sub("[EMAIL]", s)
    return s


def bounded_tail(path, limit=MAX_TAIL):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        return b""
    size = path.stat().st_size
    with path.open("rb") as f:
        f.seek(max(0, size - limit))
        return f.read(limit)


def summary():
    """No human text, raw logs, filenames, paths, prompts or token values."""
    p = DATA / "exports/native-probe.json"
    out = {"schema": "v13.phone.diagnostic/1", "native_probe": "NO_PROBE", "roles": {}}
    # These fields intentionally reveal no user prompts, file paths, raw
    # tracebacks, shell history, or arbitrary Termux process information.
    ui_pid = PRIVATE / "ui.pid"
    out["dashboard_process"] = "UNKNOWN"
    if ui_pid.is_file() and not ui_pid.is_symlink() and ui_pid.stat().st_size <= 20:
        try:
            pid = int(ui_pid.read_text().strip())
            if 1 <= pid < 10**8:
                raw = (Path("/proc") / str(pid) / "cmdline").read_bytes()[:512]
                out["dashboard_process"] = ("RUNNING" if b"v13.mobile_dashboard" in raw else "NOT_VERIFIED")
        except (OSError, ValueError, PermissionError):
            out["dashboard_process"] = "NOT_VERIFIED"
    logdir = PRIVATE / "console-logs"
    if logdir.is_dir() and not logdir.is_symlink():
        recent = sorted(logdir.glob("v13-session-*.log"), reverse=True)[:8]
        out["managed_session_count"] = len([x for x in recent if x.is_file() and not x.is_symlink()])
        if recent and recent[0].is_file() and not recent[0].is_symlink():
            tail = safe_text(bounded_tail(recent[0], 512))
            matches = re.findall(r"\[V13 exited with code (-?\d+)\]", tail)
            if matches:
                out["last_session_exit_code"] = int(matches[-1])
            else:
                out["last_session_exit_code"] = "UNVERIFIED"
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 262144:
        return out
    try:
        report = json.loads(p.read_bytes())
        if not isinstance(report, dict):
            return out
        state = report.get("status")
        out["native_probe"] = state if state in ("SMOKE_PASS", "SMOKE_PARTIAL", "SMOKE_FAIL") else "UNKNOWN"
        role_map = report.get("roles", {})
        if isinstance(role_map, dict):
            for name in ("C3_LANGUAGE", "B1_DETAIL", "B2_GIST", "C2_CONTROL"):
                value = role_map.get(name)
                if not isinstance(value, dict):
                    continue
                item = {"ok": value.get("ok") is True}
                if "error" in value:
                    item["error_present"] = True  # freeform raw exception text deliberately omitted
                out["roles"][name] = item
        return out
    except (ValueError, UnicodeError, OSError):
        out["native_probe"] = "INVALID"
        return out


def remote_log_sharing_enabled():
    if REMOTE_LOG_FLAG.is_symlink():
        return False
    try:
        return REMOTE_LOG_FLAG.is_file() and REMOTE_LOG_FLAG.read_text().strip() == "yes"
    except OSError:
        return False


def set_remote_log_sharing(enabled):
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if PRIVATE.is_symlink() or PRIVATE.stat().st_mode & 0o077 or REMOTE_LOG_FLAG.is_symlink():
        raise RuntimeError("Unsichere Log-Freigabe")
    if enabled:
        if REMOTE_LOG_FLAG.exists():
            REMOTE_LOG_FLAG.unlink()
        with REMOTE_LOG_FLAG.open("x") as f:
            f.write("yes\n")
            f.flush()
            os.fsync(f.fileno())
        REMOTE_LOG_FLAG.chmod(0o600)
    else:
        REMOTE_LOG_FLAG.unlink(missing_ok=True)


def remote_console_excerpt():
    """Opt-in: recent technical console output, not user prompts or arbitrary Termux text."""
    if not remote_log_sharing_enabled():
        return {"state": "USER_NOT_OPTED_IN"}
    paths = sorted((PRIVATE / "console-logs").glob("v13-session-*.log"), reverse=True)
    if not paths:
        return {"state": "NO_MANAGED_SESSION"}
    text = safe_text(bounded_tail(paths[0], 16384))
    # Never forward entered questions, model responses or arbitrary prose to GitHub.
    # Supportive diagnostic lines only; line classifier is intentionally strict.
    ok = re.compile(r"(?i)^(?:\[V13 Fehler\]|\[Fehler\]|\[V13 exited with code|\[console capture error|(?:Traceback|File |  File |[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception):))")
    lines = []
    for line in text.splitlines():
        if ok.search(line):
            # Avoid file paths and quoted context; send only error type + exit code.
            kinds = re.findall(r"\b(?:RuntimeError|ValueError|TypeError|MemoryError|TimeoutError|OSError|AttributeError|FileNotFoundError|ImportError|PermissionError|KeyboardInterrupt|SystemExit|CalledProcessError)\b", line)
            if kinds:
                lines.append(kinds[0])
            elif "[V13 exited with code " in line:
                m = re.search(r"code (-?\d+)", line)
                if m: lines.append("EXIT_" + m.group(1))
            elif "Traceback" in line:
                lines.append("TRACEBACK_PRESENT")
    return {"state": "OPTED_IN_REDACTED", "lines": lines[-40:], "truncated": len(lines) > 40}


def remote_full_console_enabled():
    if REMOTE_FULL_FLAG.is_symlink():
        return False
    try:
        return REMOTE_FULL_FLAG.is_file() and REMOTE_FULL_FLAG.read_text().strip() == "yes"
    except OSError:
        return False


def set_remote_full_console(enabled):
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if PRIVATE.is_symlink() or PRIVATE.stat().st_mode & 0o077 or REMOTE_FULL_FLAG.is_symlink():
        raise RuntimeError("Unsichere Freigabe")
    if enabled:
        if REMOTE_FULL_FLAG.exists():
            REMOTE_FULL_FLAG.unlink()
        with REMOTE_FULL_FLAG.open("x") as f:
            f.write("yes\n")
            f.flush()
            os.fsync(f.fileno())
        REMOTE_FULL_FLAG.chmod(0o600)
    else:
        REMOTE_FULL_FLAG.unlink(missing_ok=True)


def remote_full_console():
    """User-opted-in bounded V13 excerpt, never arbitrary Termux shell sessions."""
    if not remote_full_console_enabled():
        return {"state": "USER_NOT_OPTED_IN"}
    paths = sorted((PRIVATE / "console-logs").glob("v13-session-*.log"), reverse=True)
    if not paths:
        return {"state": "NO_MANAGED_SESSION"}
    lines = safe_text(bounded_tail(paths[0], 9000)).splitlines()
    filtered = []
    for line in lines:
        if line.lstrip().startswith(("[du>", "du>")):
            filtered.append("[LOCAL_USER_INPUT_REDACTED]")
        else:
            filtered.append(line)
    content = "\n".join(filtered)[-6000:]
    return {"state": "USER_OPTED_IN", "captured_v13_only": True,
            "redacted_user_input": True, "max_chars": 6000, "text": content}


def diagnostics_zip(destination=None):
    """Local user-initiated ZIP. May contain chat text: never upload automatically."""
    outdir = Path.home() / "storage/downloads"
    if destination is None:
        if not outdir.is_dir() or outdir.is_symlink():
            raise RuntimeError("Download access missing: run termux-setup-storage once")
        destination = outdir / ("V13-Diagnose-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3) + ".zip")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    recent = sorted((PRIVATE / "console-logs").glob("v13-session-*.log"), reverse=True)
    allowlisted = (
        ("managed-v13-last.log", recent[0] if recent else PRIVATE / "absent.log"),
        ("managed-v13-previous.log", recent[1] if len(recent) > 1 else PRIVATE / "absent.log"),
        ("dashboard-last-run.log", PRIVATE / "v13-ui-last.log"),
        ("dashboard-previous-run.log", PRIVATE / "v13-ui-previous.log"),
        ("bridge.log", PRIVATE / "bridge.log"),
        ("native-build.log", DATA / "logs/build.log"),
        ("native-probe.json", DATA / "exports/native-probe.json"),
    )
    with zipfile.ZipFile(destination, "x", zipfile.ZIP_DEFLATED) as z:
        z.writestr("summary.json", json.dumps(summary(), sort_keys=True, indent=2))
        z.writestr("README.txt",
                   "Local V13 technical diagnostic attachment. It may contain user questions, generated text, paths, and other private information. REVIEW BEFORE SHARING. Not uploaded automatically.\n")
        for name, path in allowlisted:
            raw = bounded_tail(path, BUNDLE_LIMIT)
            if raw:
                z.writestr("logs/" + name, safe_text(raw))
    return destination


def automatic_updates_enabled():
    if AUTO_FILE.is_symlink():
        return False
    try:
        return AUTO_FILE.is_file() and AUTO_FILE.read_text().strip() == "yes"
    except OSError:
        return False


def set_automatic_updates(enabled):
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if PRIVATE.is_symlink() or PRIVATE.stat().st_mode & 0o077 or AUTO_FILE.is_symlink():
        raise RuntimeError("Unsichere Update-Einstellungen")
    if enabled:
        if AUTO_FILE.exists():
            AUTO_FILE.unlink()
        with AUTO_FILE.open("x") as f:
            f.write("yes\n")
            f.flush()
            os.fsync(f.fileno())
        AUTO_FILE.chmod(0o600)
    else:
        AUTO_FILE.unlink(missing_ok=True)


class RuntimeControls:
    def __init__(self):
        self.lock = threading.Lock()
        self.terminal = ManagedConsole()
        self.last_action = "Keine Aktion"
        self.update_busy = False
        self.update_result = "Noch kein GitHub-Update geprüft"

    def state(self):
        state = self.terminal.state()
        return state["running"], "V13-Chat", state["exit_code"], self.last_action

    def launch(self, mode, question=""):
        if mode not in ALLOWED:
            raise ValueError("unknown V13 action")
        self.terminal.start()
        if mode == "ask":
            return self.send(question)
        return self.send(":" + mode)

    def send(self, line):
        result = self.terminal.send(line)
        with self.lock:
            self.last_action = line.split(" ", 1)[0] if line.startswith(":") else "Nachricht"
        return result

    def stop(self):
        result = self.terminal.cancel()
        return result["status"]

    def shutdown(self):
        return self.send(":shutdown")

    def start_update(self, action):
        if action not in ("check", "apply", "auto", "rollback"):
            raise ValueError("Nicht freigegebene Update-Aktion")
        with self.lock:
            if self.update_busy:
                raise RuntimeError("Ein Update-Check laeuft bereits")
            self.update_busy = True
            self.update_result = "GitHub wird geprüft…"
        def worker():
            try:
                from v13 import source_updater
                if action == "check":
                    result = source_updater.status()
                elif action == "apply":
                    result = source_updater.apply()
                elif action == "auto":
                    result = source_updater.auto_apply()
                else:
                    result = source_updater.rollback()
                msg = result["status"] + " · " + str(result.get("changed_files", 0)) + " geänderte Dateien"
                if result["status"] in ("UPDATED", "ROLLED_BACK"):
                    msg += " · bitte neuen V13-Chat starten"
            except Exception as exc:
                msg = "Nicht durchgeführt: " + type(exc).__name__ + " · " + str(exc)[:200]
            with self.lock:
                self.update_result = msg
                self.update_busy = False
        threading.Thread(target=worker, daemon=True, name="v13-source-update").start()

    def update_status(self):
        with self.lock:
            return self.update_result, self.update_busy

    def output(self):
        return safe_text(self.terminal.output(MAX_TAIL).encode("utf-8"))


def _button(action, name, title, label, cls=""):
    return (f'<form method="POST" action="{html.escape(action, quote=True)}">'
            f'<input type="hidden" name="action" value="{html.escape(name, quote=True)}">'
            f'<button class="{cls}" type="submit">{html.escape(label)}</button></form>')


def _quick(action, command, label, cls="secondary"):
    return (f'<form method="POST" action="{html.escape(action, quote=True)}">'
            f'<input type="hidden" name="action" value="quick">'
            f'<input type="hidden" name="command" value="{html.escape(command, quote=True)}">'
            f'<button class="{cls}" type="submit">{html.escape(label)}</button></form>')


def operator_catalog():
    """Read actual V13 operator HELP without executing installed source code."""
    fallback = {c.split()[0] for c in QUICK_COMMANDS}
    paths = (Path.home() / "V13-Phone/v13/code/v13/operator.py",
             Path.home() / "v13-app-20260929/V13-Phone/v13/operator.py")
    for p in paths:
        try:
            if p.is_symlink() or not p.is_file() or p.stat().st_size > 350000:
                continue
            tree = ast.parse(p.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "HELP" for t in node.targets):
                    help_text = ast.literal_eval(node.value)
                    if isinstance(help_text, str):
                        commands = set(re.findall(r"(?<![A-Za-z0-9]):[a-z][a-z0-9_-]{1,30}", help_text))
                        return sorted(fallback | commands)[:250]
        except (OSError, ValueError, SyntaxError, UnicodeError):
            continue
    return sorted(fallback)


def _sliders(action):
    from math import isfinite
    p = DATA / "config/settings.json"
    try:
        source = json.loads(p.read_bytes()) if p.is_file() and not p.is_symlink() and p.stat().st_size < 50000 else {}
    except (ValueError, OSError):
        source = {}
    parts = []
    for key, (low, high, step, label) in KNOBS_UI.items():
        value = source.get(key, low)
        if type(value) not in (int, float) or not isfinite(value) or not low <= value <= high:
            value = low
        parts.append(
            f'<form method="POST" action="{html.escape(action, quote=True)}">'
            '<input type="hidden" name="action" value="knob">'
            f'<input type="hidden" name="knob" value="{html.escape(key, quote=True)}">'
            f'<label>{html.escape(label)} <output>{value}</output></label>'
            f'<input type="range" min="{low}" max="{high}" step="{step}" name="value" value="{value}" '
            'oninput="this.previousElementSibling.lastElementChild.value=this.value">'
            '<button type="submit" class="secondary">Übernehmen</button></form>')
    return "".join(parts)


def dashboard_html(token, controls, message="", csrf=""):
    running, mode, code, last = controls.state()
    state = "läuft" if running else "bereit" if code is None else f"beendet (Code {code})"
    current = summary()
    update_msg, update_busy = controls.update_status()
    auto_enabled = automatic_updates_enabled()
    shared = remote_log_sharing_enabled()
    full_shared = remote_full_console_enabled()
    roles = " · ".join(f"{html.escape(name)}: {'OK' if v.get('ok') else 'Fehler'}"
                       for name, v in current["roles"].items())
    action = "/t/" + token + "/action"
    msg = f'<p class="message">{html.escape(message)}</p>' if message else ""
    output = controls.output()
    extra = ' · '.join(controls.terminal.saved_sessions())
    top_buttons = "".join([
        _button(action, "start_chat", "Start", "V13 Chat starten"),
        _quick(action, ":doctor", "Gehirnstatus"),
        _quick(action, ":probe", "Modelle testen"),
        _button(action, "cancel", "Abbruch", "Antwort abbrechen", "danger"),
        _button(action, "shutdown", "Beenden", "V13 beenden", "secondary"),
    ])
    test_commands = [
        (":status", "Status"), (":brain map", "Gehirnkarte"), (":resources", "RAM / Ressourcen"),
        (":models", "Modelle"), (":world", "Weltbild"), (":self", "Selbstbild"),
        (":memory", "Gedächtnis"), (":requests", "Lernkandidaten"),
        (":learning", "Lernmodus"), (":plasticity", "Plastizität"),
        (":objectives", "Lernziele"), (":sleep status", "Schlaf / Replay"),
        (":gates summary", "Gates"), (":probe jef-modes", "JEF testen"),
        (":probe step12", "B1/B2 testen"), (":notaus status", "Notaus-Status"),
        (":help", "Alle Befehle"),
    ]
    quick_buttons = "".join(_quick(action, c, l) for c,l in test_commands)
    commands = operator_catalog()
    options = "".join(f'<option value="{html.escape(c, quote=True)}"></option>' for c in sorted(QUICK_COMMANDS))
    all_buttons = "".join(
        '<button class="secondary" type="button" '
        + 'onclick="document.getElementById(\'v13-command\').value=\'' + c
        + '\';document.getElementById(\'v13-command\').focus()">' + c + '</button>'
        for c in commands
    )
    page = f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>V13 – Redmi Kontrollzentrum</title>
<style>
:root{{color-scheme:dark;font-family:system-ui,sans-serif}}
body{{background:#10131a;color:#edf2fa;margin:0;padding:16px}}
main{{max-width:780px;margin:auto}}
h1{{font-size:1.7rem}} h2{{font-size:1.1rem}}
a{{color:#a6c7f8;font-weight:bold}}
section{{background:#1a202a;border:1px solid #303b4a;border-radius:16px;padding:16px;margin:12px 0}}
button{{background:#3977c8;color:white;padding:14px 17px;border:0;border-radius:10px;font-weight:bold;font-size:1rem;min-height:48px;cursor:pointer}}
button.secondary{{background:#394353}}button.danger{{background:#ac4848}}
.actions{{display:flex;gap:8px;flex-wrap:wrap}}.actions form{{flex:1}}.actions button{{width:100%}}
input{{width:100%;box-sizing:border-box;background:#111924;color:white;padding:14px;border:1px solid #56687e;border-radius:10px;font-size:1rem}}
input[type=range]{{padding:0;margin:14px 0;accent-color:#8eb4ed}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#0c1017;padding:12px;border-radius:8px;max-height:400px;overflow:auto;font-size:.82rem}}
small{{color:#b0bdcf}}.message{{color:#b8e4c4}}label{{display:block;margin-top:12px}}
</style></head><body><main>
<h1>V13 · Redmi Kontrollzentrum</h1>
<section><b>V13-Chat: <span id="v13-live-state">{html.escape(state)}</span></b>
<p><small>Letzte Aktion: {html.escape(last)} · Probe: {html.escape(current["native_probe"])} · {roles or "Noch keine Rollenmessung"}</small></p>{msg}
<div class="actions">{top_buttons}</div></section>
<section><h2>Mit V13 schreiben</h2>
<form method="POST" action="{action}"><input type="hidden" name="action" value="send">
<input name="command" aria-label="Nachricht an V13" maxlength="1600" placeholder="Deine Nachricht an V13 …" required>
<p><button type="submit">Nachricht senden</button></p></form>
<small>Die Nachrichten gehen ausschließlich an das lokal gestartete V13. Kein GitHub-Chat.</small></section>
<section><h2>Gehirn, Test & Status</h2>
<div class="actions">{quick_buttons}</div>
<details><summary>Weitere V13-Kommandos auswählen</summary>
<form method="POST" action="{action}"><input type="hidden" name="action" value="send">
<input id="v13-command" name="command" list="v13-options" placeholder=":Befehl und ggf. Parameter" required maxlength="1600">
<datalist id="v13-options">{options}</datalist><p><button type="submit">Befehl an V13 senden</button></p></form>
<small>Alle Befehlsnamen können per Klick ins Eingabefeld übernommen werden. Manche benötigen weitere Parameter oder gesonderte Bestätigung.</small><div class="actions">{all_buttons}</div>
</details></section>
<section><h2>Regler · lokale V13-Budgets</h2>
{_sliders(action)}
<small>Änderungen werden mit „Übernehmen“ über den vorhandenen V13-Operator ausgeführt und können einen laufenden Modellaufruf beeinflussen. Keine Modellgewichte werden automatisch verändert.</small></section>
<section><h2>Diagnose / Logaufzeichnung</h2>
<p>Alle Ausgaben und Eingaben der <b>über diese Oberfläche gestarteten V13-Sitzung</b> werden lokal gespeichert. Andere Termux-Sitzungen sind nicht rückwirkend lesbar.</p>
<div class="actions">
{_button(action,"zip","Export","Diagnose-ZIP in Downloads")}
{_button(action,"log_disable" if shared else "log_enable","Freigabe", "Fern-Fehlercodes AUS" if shared else "Fern-Fehlercodes EIN","secondary")}
{_button(action,"full_log_disable" if full_shared else "full_log_enable","Freigabe", "V13-Konsolenauszug AUS" if full_shared else "V13-Konsolenauszug TEILEN","secondary")}
</div><small>Private GitHub-Diagnose: {'technische Fehlercodes freigegeben' if shared else 'Fehlercodes aus'}; {'letzte V13-Ausgaben (max. 6000 Zeichen) auf Anfrage lesbar' if full_shared else 'Konsolentext nicht freigegeben'}. Achtung: V13-Ausgaben können private Chat-Inhalte enthalten, auch nach automatischer Token-Redaktion. Diese bleiben als private GitHub-Kommentare gespeichert. Keine anderen Termux-Sitzungen. ZIP vor dem Teilen prüfen.</small>
<small>Gesicherte lokale Sitzungen: {html.escape(extra or "Noch keine")}</small></section>
<section><h2>GitHub-Quellcode-Updates</h2><p><small>{html.escape(update_msg)}{' · läuft' if update_busy else ''}</small></p>
<div class="actions">
{_button(action,"check_update","Prüfen","Update prüfen","secondary")}
{_button(action,"apply_update","Update","Jetzt aktualisieren")}
{_button(action,"rollback_update","Rollback","Vorherige Version","secondary")}
{_button(action,"auto_disable" if auto_enabled else "auto_enable","Auto","Auto-Updates AUS" if auto_enabled else "Auto-Updates EIN","secondary")}
</div><small>Automatik: {'an' if auto_enabled else 'aus'}, alle 15 Minuten bei laufendem Kontrollzentrum. Nur geprüfte GitHub-Commits; kein Update einer laufenden V13-KI. Modelle/Chats bleiben getrennt.</small></section>
<section><h2>Aufgezeichnete V13-Ausgabe</h2><a href="/t/{token}/">↻ Ausgabe aktualisieren</a>
<pre id="v13-live-output">{html.escape(output[-MAX_TAIL:] or "Noch keine Ausgabe. V13 Chat starten.")}</pre></section>
<section><small>Lokaler Browser: 127.0.0.1. Keine fremde Termux-Shell, keine automatische Remote-Codeausführung, keine Kamera-/Android-Bedienung.</small></section>
</main>
<script>
(function(){{
  const output = document.getElementById('v13-live-output');
  const state = document.getElementById('v13-live-state');
  let previous = output.textContent;
  let inFlight = false;
  async function refresh(){{
    if (document.hidden || inFlight) return;
    inFlight = true;
    try{{
      const response = await fetch('/t/{token}/state', {{cache:'no-store', credentials:'same-origin'}});
      if(!response.ok) return;
      const data = await response.json();
      if(typeof data.output === 'string' && data.output !== previous){{
        const atBottom = output.scrollHeight - output.scrollTop - output.clientHeight < 80;
        output.textContent = data.output;
        previous = data.output;
        if(atBottom) output.scrollTop = output.scrollHeight;
      }}
      if(typeof data.state === 'string') state.textContent = data.state;
    }} catch (_) {{}} finally {{inFlight = false;}}
  }}
  setInterval(refresh, 1500);
}})();
</script>
</body></html>"""
    # Every browser action carries a separate CSRF secret, independent of
    # mobile privacy-browser Origin header behavior.
    hidden = '<input type="hidden" name="csrf" value="' + html.escape(csrf, quote=True) + '">' 
    return re.sub(r'(<form method="POST" action="[^"]+">)', lambda m: m.group(1) + hidden, page)


def serve(*, open_browser=True):
    controls = RuntimeControls()
    def auto_loop():
        while True:
            if automatic_updates_enabled():
                try:
                    controls.start_update("auto")
                except RuntimeError:
                    pass
            time.sleep(900)
    threading.Thread(target=auto_loop, daemon=True, name="v13-auto-updates").start()
    token = secrets.token_hex(24)
    csrf = secrets.token_hex(24)
    prefix = "/t/" + token
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # never log private URL or prompts
        def _headers(self, code=200, *, location=None, mime="text/html; charset=utf-8"):
            self.send_response(code)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            if location:
                self.send_header("Location", location)
            else:
                self.send_header("Content-Type", mime)
            self.end_headers()
        def _local_host(self):
            # Keep DNS-rebinding protection, but do not depend on Brave/Android
            # providing one exact Origin value for local browser form submits.
            port = str(self.server.server_port)
            return self.headers.get("Host", "").lower() in {
                "127.0.0.1:" + port, "localhost:" + port}

        def do_GET(self):
            if not self._local_host():
                self._headers(403)
                return
            if self.path == prefix + "/state":
                running, mode, exitcode, last = controls.state()
                state = "läuft" if running else "bereit" if exitcode is None else "beendet (" + str(exitcode) + ")"
                payload = {"state": state, "output": controls.output()[-50000:],
                           "last_action": last, "running": running}
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self._headers(mime="application/json; charset=utf-8")
                self.wfile.write(data)
                return
            if self.path != prefix + "/":
                self._headers(404)
                return
            data = dashboard_html(token, controls, csrf=csrf).encode("utf-8")
            self._headers()
            self.wfile.write(data)
        def do_POST(self):
            if self.path != prefix + "/action":
                self._headers(404)
                return
            length = self.headers.get("Content-Length", "")
            if not length.isdigit() or int(length) > 4000:
                self._headers(413)
                return
            if not self._local_host():
                self._headers(403)
                return
            try:
                fields = parse_qs(self.rfile.read(int(length)).decode("utf-8"), keep_blank_values=True)
                if fields.get("csrf") != [csrf]:
                    self._headers(403)
                    return
                action = fields.get("action", [""])[0]
                if action in ALLOWED:
                    question = fields.get("question", [""])[0] if action == "ask" else ""
                    controls.launch(action, question)
                    message = "V13 gestartet, Ausgabe wird lokal aufgezeichnet."
                elif action == "start_chat":
                    result = controls.terminal.start()
                    message = "V13 Chat " + result["status"]
                elif action == "send":
                    controls.send(fields.get("command", [""])[0])
                    message = "Eingabe an lokalen V13-Chat gesendet."
                elif action == "quick":
                    command = fields.get("command", [""])[0]
                    if command not in QUICK_COMMANDS:
                        raise ValueError("Nur bekannte Klickbefehle")
                    controls.send(command)
                    message = "V13-Befehl gesendet."
                elif action == "knob":
                    name = fields.get("knob", [""])[0]
                    if name not in KNOBS_UI:
                        raise ValueError("Unbekannter V13-Regler")
                    low, high, step, label = KNOBS_UI[name]
                    value = float(fields.get("value", [""])[0])
                    if not low <= value <= high or value != value:
                        raise ValueError("Wert außerhalb des Bereichs")
                    if isinstance(step, int):
                        if not value.is_integer() or (int(value) - low) % step:
                            raise ValueError("Nur ganze Reglerschritte")
                        formatted = str(int(value))
                    else:
                        formatted = str(round(value, 4))
                    controls.send(":budget " + name + " " + formatted)
                    message = "Regler " + label + " an V13 übergeben."
                elif action == "cancel":
                    message = controls.stop()
                elif action == "shutdown":
                    controls.shutdown()
                    message = "V13 wird beendet; Protokoll bleibt erhalten."
                elif action in ("log_enable", "log_disable"):
                    set_remote_log_sharing(action == "log_enable")
                    message = "Private technische Fern-Fehlercodes " + ("aktiviert" if action == "log_enable" else "deaktiviert")
                elif action in ("full_log_enable", "full_log_disable"):
                    set_remote_full_console(action == "full_log_enable")
                    message = "Private V13-Konsolenauszüge " + ("freigegeben" if action == "full_log_enable" else "gesperrt")
                elif action == "stop":
                    message = controls.stop()
                elif action == "zip":
                    dest = diagnostics_zip()
                    message = "Diagnose-ZIP erstellt: " + dest.name + " (in Downloads)"
                elif action in ("check_update", "apply_update", "rollback_update"):
                    controls.start_update({"check_update":"check","apply_update":"apply",
                                           "rollback_update":"rollback"}[action])
                    message = "Update-Auftrag gestartet; Ergebnis wird im Abschnitt GitHub-Updates angezeigt."
                elif action in ("auto_enable", "auto_disable"):
                    set_automatic_updates(action == "auto_enable")
                    message = "Automatische Updates " + ("aktiviert" if action == "auto_enable" else "deaktiviert")
                else:
                    raise ValueError("Unbekannte Aktion")
            except (OSError, ValueError, RuntimeError, UnicodeError) as exc:
                message = "Fehler: " + type(exc).__name__ + ": " + str(exc)[:200]
            data = dashboard_html(token, controls, message, csrf=csrf).encode("utf-8")
            self._headers()
            self.wfile.write(data)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    url = f"http://127.0.0.1:{server.server_port}{prefix}/"
    print("V13 LOKALE OBERFLAECHE: " + url, flush=True)
    if open_browser:
        try:
            subprocess.Popen(["termux-open-url", url], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            pass
    try:
        server.serve_forever(poll_interval=.5)
    finally:
        server.server_close()


def main(argv=None):
    parser = argparse.ArgumentParser(description="V13 local click dashboard")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("ui")
    sub.add_parser("summary")
    sub.add_parser("zip")
    args = parser.parse_args(argv)
    if args.action == "ui":
        serve()
    elif args.action == "summary":
        print(json.dumps(summary(), sort_keys=True))
    else:
        print(diagnostics_zip())


if __name__ == "__main__":
    main()

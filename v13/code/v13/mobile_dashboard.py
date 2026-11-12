"""Private, local-only browser buttons for V13 on Android Termux.

An explicit local browser is the UI. No public listener, remote shell, Android
accessibility permission, raw log upload, or unsupervised model-weight edits.
"""
from __future__ import annotations
import argparse
import fcntl
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
PORT = 18713  # canonical V13 localhost port; test override V13_UI_PORT=0
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
        # Send only explicitly allowlisted technical values over the private
        # channel, without raw exception strings, paths, or model output.
        cfg = report.get("effective_config")
        if isinstance(cfg, dict):
            budget = cfg.get("deadline_seconds")
            if type(budget) in (int, float) and 1 <= budget <= 3600:
                out["probe_deadline_seconds"] = round(budget, 1)
        role_map = report.get("roles", {})
        if isinstance(role_map, dict):
            for name in ("C3_LANGUAGE", "B1_DETAIL", "B2_GIST", "C2_CONTROL"):
                value = role_map.get(name)
                if not isinstance(value, dict):
                    continue
                item = {"ok": value.get("ok") is True}
                error = value.get("error")
                if isinstance(error, str):
                    item["error_present"] = True
                    if error.strip() == "Zeitbudget erreicht":
                        item["error_kind"] = "TIME_BUDGET"
                    elif "Abgebrochen" in error and len(error) < 180:
                        item["error_kind"] = "CANCELLED"
                    else:
                        item["error_kind"] = "REDACTED_ERROR"
                duration = value.get("duration_s")
                if type(duration) in (float, int) and 0 <= duration <= 36000:
                    item["duration_s"] = round(duration, 1)
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


def _ui_singleton_lock():
    """Allow exactly one V13 local control server per Termux home.

    The file descriptor retains an exclusive OS lock for the process lifetime,
    including an ordinary dashboard run. Closing on exec lets the refreshed
    server reacquire after its in-place update.
    """
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if PRIVATE.is_symlink() or PRIVATE.stat().st_mode & 0o077:
        raise RuntimeError("V13 privacy directory must be private")
    path = PRIVATE / "ui-singleton.lock"
    if path.is_symlink():
        raise RuntimeError("Unsafe dashboard lock")
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        if os.fstat(fd).st_uid != os.getuid():
            raise RuntimeError("Dashboard lock has wrong owner")
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("V13 dashboard is already running. Use its existing browser tab.") from exc
        return fd
    except BaseException:
        os.close(fd)
        raise


def _browser_token():
    """Persist the random local page path so old tabs can simply reload."""
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = PRIVATE / "ui-browser-token"
    if path.is_symlink():
        raise RuntimeError("Unsafe browser token link")
    if path.exists():
        st = path.stat()
        if not path.is_file() or st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise RuntimeError("Browser token is not private")
        value = path.read_text(encoding="ascii").strip()
        if not re.fullmatch(r"[a-f0-9]{48}", value):
            raise RuntimeError("Browser token is invalid")
        return value
    value = secrets.token_hex(24)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(value + "\n")
        out.flush()
        os.fsync(out.fileno())
    return value


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
        self.update_started = 0.0
        self.restart_requested = False
        self.restart_callback = None

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
        if action not in ("check", "apply", "auto", "rollback", "dashboard"):
            raise ValueError("Nicht freigegebene Update-Aktion")
        # Do not silently update code while the V13 process is running. The
        # result must be shown at click time, not hidden in a background log.
        if action in ("apply", "rollback", "dashboard") and self.terminal.state()["running"]:
            raise RuntimeError("V13 läuft noch. Erst im Chat auf 'V13 beenden' drücken; danach das Update starten.")
        with self.lock:
            if self.update_busy:
                raise RuntimeError("Ein Update-Check laeuft bereits")
            self.update_busy = True
            self.update_started = time.monotonic()
            self.update_result = "GitHub verbinden und geänderte Dateien prüfen …"
        def worker():
            try:
                from v13 import source_updater
                if action == "check":
                    result = source_updater.status()
                elif action == "apply":
                    result = source_updater.apply()
                elif action == "auto":
                    result = source_updater.auto_apply()
                elif action == "dashboard":
                    result = source_updater.apply_dashboard()
                else:
                    result = source_updater.rollback()
                msg = result["status"] + " · " + str(result.get("changed_files", 0)) + " geänderte Dateien"
                if action == "dashboard" and result["status"] == "UPDATED":
                    msg += " · Kontrollzentrum startet neu"
                elif result["status"] in ("UPDATED", "ROLLED_BACK"):
                    msg += " · V13 neu starten; Installation der Laufzeit getrennt prüfen"
            except subprocess.TimeoutExpired:
                msg = "Update abgebrochen: GitHub hat innerhalb des Zeitlimits nicht geantwortet. Verbindung prüfen, dann erneut versuchen."
            except Exception as exc:
                msg = "Update nicht durchgeführt: " + type(exc).__name__ + " · " + str(exc)[:200]
            with self.lock:
                self.update_result = msg
                self.update_busy = False
                needs_restart = (action == "dashboard" and msg.startswith("UPDATED"))
                if needs_restart:
                    self.restart_requested = True
            if needs_restart and self.restart_callback:
                self.restart_callback()
        threading.Thread(target=worker, daemon=True, name="v13-source-update").start()

    def update_status(self):
        with self.lock:
            if self.update_busy:
                elapsed = round(time.monotonic() - self.update_started)
                return self.update_result + " · " + str(elapsed) + " s", True
            return self.update_result, False

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



def _command_group(command):
    first = command.split()[0].lower()
    if first in (":models", ":probe", ":brain", ":bodyview", ":jef", ":jefsource", ":callosum", ":body"):
        return "Modelle & Gehirn"
    if first in (":world", ":worldmodel", ":self", ":memory", ":episodes", ":archive", ":context",
                 ":source", ":focal", ":register", ":ctxos", ":fabric", ":workspace"):
        return "Gedächtnis, Welt & Selbst"
    if first in (":learning", ":plasticity", ":objectives", ":neuromod", ":homeostasis", ":sleep",
                 ":replay", ":student", ":teacher", ":attention", ":growth", ":age"):
        return "Lernen, JEPA & Replay"
    if first in (":notaus", ":verbot", ":regeln", ":permissions", ":gates", ":stillstand",
                 ":ledger", ":backup"):
        return "Kontrolle & Schutz"
    return "System, Diagnose & Weiteres"


def _command_catalog_html():
    from collections import defaultdict
    groups = defaultdict(list)
    # Preserve all previously exposed specific commands AND the actual help
    # catalogue. A click only fills the composer; it cannot execute a command
    # accidentally, particularly one that requires parameters.
    commands = sorted(set(QUICK_COMMANDS) | set(operator_catalog()))
    for command in commands:
        groups[_command_group(command)].append(command)
    sections = []
    ordering = ("Modelle & Gehirn", "Gedächtnis, Welt & Selbst",
                "Lernen, JEPA & Replay", "Kontrolle & Schutz", "System, Diagnose & Weiteres")
    for i, label in enumerate(ordering):
        commands = groups.get(label, [])
        if not commands:
            continue
        buttons = "".join(
            '<button type="button" data-fill="' + html.escape(cmd, quote=True)
            + '" title="In den Chat übernehmen">' + html.escape(cmd) + '</button>'
            for cmd in commands
        )
        sections.append(
            '<details class="command-group"' + (" open" if i == 0 else "") + '><summary>'
            + html.escape(label) + ' (' + str(len(commands)) + ')</summary>'
            '<div class="command-list">' + buttons + '</div></details>'
        )
    return "".join(sections)


def _slider_grid(action):
    import math
    source = {}
    p = DATA / "config/settings.json"
    try:
        if p.is_file() and not p.is_symlink() and p.stat().st_size < 50000:
            source = json.loads(p.read_bytes())
    except (ValueError, OSError):
        source = {}
    if not isinstance(source, dict):
        source = {}
    cards = []
    for key, (low, high, step, label) in KNOBS_UI.items():
        value = source.get(key, low)
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            value = low
        cards.append(
            f'<form class="slider-form" method="POST" action="{html.escape(action,quote=True)}">'
            '<input type="hidden" name="action" value="knob">'
            f'<input type="hidden" name="knob" value="{html.escape(key,quote=True)}">'
            '<div><label class="field-title">'
            f'<span>{html.escape(label)}</span><output>{html.escape(str(value))}</output></label>'
            f'<input type="range" name="value" min="{low}" max="{high}" step="{step}" value="{value}">'
            '</div><button type="submit">Anwenden</button></form>'
        )
    return "".join(cards)


def dashboard_html(token, controls, message="", csrf="", generation=""):
    """One coherent phone workspace: chat/commands/settings/maintenance tabs."""
    running, _, code, last = controls.state()
    state = "V13 läuft" if running else "Bereit" if code is None else f"Beendet ({code})"
    current = summary()
    update_msg, update_busy = controls.update_status()
    auto_enabled = automatic_updates_enabled()
    errors_shared = remote_log_sharing_enabled()
    console_shared = remote_full_console_enabled()
    action = "/t/" + token + "/action"
    prefix = "/t/" + token
    def button(name, label, cls=""):
        return _button(action, name, name, label, cls)
    def quick(command,label):
        return _quick(action,command,label)
    roles = []
    for name in ("C3_LANGUAGE", "C2_CONTROL", "B1_DETAIL", "B2_GIST"):
        role = current["roles"].get(name)
        if not isinstance(role, dict):
            continue
        ok = role.get("ok")
        shown = {"C3_LANGUAGE":"C3 Sprache","C2_CONTROL":"C2 JEF",
                 "B1_DETAIL":"B1 Detail","B2_GIST":"B2 Gist"}[name]
        kind = "good" if ok else "bad"
        extra = " · OK" if ok else " · " + ("Zeitlimit" if role.get("error_kind") == "TIME_BUDGET" else "Fehler")
        roles.append('<span class="pill ' + kind + '">' + html.escape(shown + extra) + '</span>')
    template = Path(__file__).with_name("mobile_dashboard.html")
    if not template.is_file():
        raise RuntimeError("UI-Datei fehlt: Installation der Steuerzentrale aktualisieren")
    page = template.read_text(encoding="utf-8")
    replacement = {
        "@@STATE@@":html.escape(state),
        "@@GENERATION@@":html.escape(generation, quote=True),
        "@@FLASH_CLASS@@":"visible" if message else "",
        "@@FLASH@@":html.escape(message),
        "@@TOKEN@@":html.escape(token),
        "@@PREFIX@@":html.escape(prefix),
        "@@ACTION@@":html.escape(action,quote=True),
        "@@OUTPUT@@":html.escape(controls.output()[-MAX_TAIL:] or "Noch keine Ausgabe. V13 starten."),
        "@@START_BUTTON@@":button("start_chat","Chat starten","primary"),
        "@@STOP_BUTTON@@":button("cancel","Abbrechen","danger"),
        "@@STATUS_BUTTON@@":quick(":status","Status"),
        "@@HELP_BUTTON@@":quick(":help","Hilfe"),
        "@@SHUTDOWN_BUTTON@@":button("shutdown","V13 beenden","danger"),
        "@@TRANSCRIPT_URL@@":html.escape(prefix+"/transcript.txt",quote=True),
        "@@PROBE_STATUS@@":html.escape(current["native_probe"]),
        "@@ROLE_PILLS@@":"".join(roles) or '<span class="pill">Noch keine Messung</span>',
        "@@MODEL_BUTTONS@@":"".join([quick(c,l) for c,l in [
            (":doctor","Gehirnstatus"),(":probe","Modelle testen"),
            (":probe jef-modes","JEF testen"),(":probe step12","B1/B2 testen")]]),
        "@@COMMAND_CATEGORIES@@":_command_catalog_html(),
        "@@SLIDERS@@":_slider_grid(action),
        "@@UPDATE_STATUS@@":html.escape(update_msg),
        "@@UPDATE_HIDDEN@@":"" if update_busy else "hidden",
        "@@UPDATE_BUTTONS@@":"".join([
            button("check_update","Änderungen prüfen"),
            button("apply_update","V13-Code aktualisieren","primary"),
            button("rollback_update","Rückgängig"),
            button("auto_disable" if auto_enabled else "auto_enable",
                   "Auto-Updates AUS" if auto_enabled else "Auto-Updates EIN")
        ]),
        "@@DASHBOARD_UPDATE@@":button("dashboard_update","Steuerzentrale aktualisieren","primary"),
        "@@DIAG_BUTTONS@@":"".join([
            button("zip","Diagnose-ZIP"),
            button("log_disable" if errors_shared else "log_enable",
                   "Fern-Fehlercodes AUS" if errors_shared else "Fern-Fehlercodes EIN"),
            button("full_log_disable" if console_shared else "full_log_enable",
                   "Konsolentext AUS" if console_shared else "Konsolentext TEILEN"),
            button("shutdown","V13 beenden","danger")
        ]),
        "@@SESSION_COUNT@@":str(len(controls.terminal.saved_sessions()))
    }
    for key,val in replacement.items():
        page=page.replace(key,val)
    if "@@" in page:
        raise RuntimeError("Nicht ersetztes UI-Feld im Template")
    # A second per-process form secret is required, in addition to the private
    # local URL. No Origin dependency: Brave/Android may send Origin:null.
    hidden = ('<input type="hidden" name="csrf" value="'
              + html.escape(csrf,quote=True) + '">')
    return re.sub(r'(<form[^>]*\bmethod="POST"[^>]*>)',
                  lambda m:m.group(1)+hidden,page)

def serve(*, open_browser=True):
    instance_fd = _ui_singleton_lock()
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
    token = os.environ.get("V13_UI_RESTART_TOKEN") or _browser_token()
    csrf = os.environ.get("V13_UI_RESTART_CSRF") or secrets.token_hex(24)
    was_restarted = bool(os.environ.get("V13_UI_RESTART_PORT"))
    port = int(os.environ.get("V13_UI_RESTART_PORT") or os.environ.get("V13_UI_PORT") or str(PORT))
    if port != 0 and not 1024 <= port <= 65535:
        raise RuntimeError("Unsafe local control port")
    for key in ("V13_UI_RESTART_TOKEN","V13_UI_RESTART_CSRF","V13_UI_RESTART_PORT"):
        os.environ.pop(key,None)
    if not re.fullmatch(r"[a-f0-9]{48}",token) or not re.fullmatch(r"[a-f0-9]{48}",csrf):
        raise RuntimeError("Ungültiger lokaler UI-Neustart-Schlüssel")
    prefix = "/t/" + token
    generation = secrets.token_hex(12)
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
        def _reject(self, code, message):
            # Browser actions must always get a parseable response; otherwise
            # a denied CSRF request was surfaced as an opaque JSON syntax error.
            if "application/json" in self.headers.get("Accept", ""):
                data = json.dumps({"ok": False, "message": message},
                                  ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)
            else:
                self._headers(code, mime="text/plain; charset=utf-8")
                self.wfile.write(message.encode("utf-8"))

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
            if self.path in (prefix + "/transcript", prefix + "/transcript.txt"):
                data = controls.terminal.transcript(all_sessions=True).encode("utf-8")
                if len(data) > 64*1024*1024:
                    self._headers(413)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Content-Type-Options", "nosniff")
                if self.path.endswith(".txt"):
                    self.send_header("Content-Disposition", 'attachment; filename="V13-Chatverlauf.txt"')
                self.end_headers()
                self.wfile.write(data)
                return
            if self.path == prefix + "/state":
                running, mode, exitcode, last = controls.state()
                state = "läuft" if running else "bereit" if exitcode is None else "beendet (" + str(exitcode) + ")"
                update_result, update_busy = controls.update_status()
                payload = {"state": state, "output": controls.output()[-50000:],
                           "last_action": last, "running": running,
                           "update_result": update_result, "update_busy": update_busy,
                           "generation": generation}
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self._headers(mime="application/json; charset=utf-8")
                self.wfile.write(data)
                return
            if self.path != prefix + "/":
                self._headers(404)
                return
            data = dashboard_html(token, controls, csrf=csrf, generation=generation).encode("utf-8")
            self._headers()
            self.wfile.write(data)
        def do_POST(self):
            if self.path != prefix + "/action":
                self._reject(404, "Unbekannter Button-Endpunkt.")
                return
            length = self.headers.get("Content-Length", "")
            if not length.isdigit() or not 0 < int(length) <= 4000:
                self._reject(413, "Button-Anfrage ist leer oder zu groß.")
                return
            if not self._local_host():
                self._reject(403, "Ungültiger lokaler Browser-Host.")
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/x-www-form-urlencoded":
                self._reject(415, "Browser hat Formulardaten falsch gesendet. Steuerzentrale aktualisieren.")
                return
            try:
                fields = parse_qs(self.rfile.read(int(length)).decode("utf-8"), keep_blank_values=True)
                if fields.get("csrf") != [csrf]:
                    self._reject(403, "Sitzungsschlüssel ungültig. Aktuelle Seite neu laden.")
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
                elif action in ("check_update", "apply_update", "rollback_update", "dashboard_update"):
                    controls.start_update({"check_update":"check","apply_update":"apply",
                                           "rollback_update":"rollback", "dashboard_update":"dashboard"}[action])
                    message = "Update-Auftrag gestartet; Ergebnis wird im Abschnitt GitHub-Updates angezeigt."
                elif action in ("auto_enable", "auto_disable"):
                    set_automatic_updates(action == "auto_enable")
                    message = "Automatische Updates " + ("aktiviert" if action == "auto_enable" else "deaktiviert")
                else:
                    raise ValueError("Unbekannte Aktion")
            except (OSError, ValueError, RuntimeError, UnicodeError) as exc:
                message = "Fehler: " + type(exc).__name__ + ": " + str(exc)[:200]
            if "application/json" in self.headers.get("Accept", ""):
                accepted = not message.startswith("Fehler:")
                data = json.dumps({"ok": accepted, "message": message}, ensure_ascii=False).encode("utf-8")
                self._headers(200 if accepted else 400, mime="application/json; charset=utf-8")
            else:
                data = dashboard_html(token, controls, message, csrf=csrf, generation=generation).encode("utf-8")
                self._headers()
            self.wfile.write(data)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    def request_restart():
        # Finish the acknowledgement to the browser, then cleanly release the
        # socket before exec'ing Python with the fresh dashboard module.
        def shutdown_server():
            time.sleep(2)
            server.shutdown()
        threading.Thread(target=shutdown_server, name="v13-ui-refresh", daemon=True).start()
    controls.restart_callback = request_restart
    url = f"http://127.0.0.1:{server.server_port}{prefix}/"
    print("V13 LOKALE OBERFLAECHE: " + url, flush=True)
    if open_browser and not was_restarted and os.environ.get("V13_UI_NO_AUTO_OPEN") != "1":
        try:
            subprocess.Popen(["termux-open-url", url], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            pass
    try:
        server.serve_forever(poll_interval=.5)
    finally:
        server.server_close()
    if controls.restart_requested:
        os.environ["V13_UI_RESTART_PORT"] = str(server.server_port)
        os.environ["V13_UI_RESTART_TOKEN"] = token
        os.environ["V13_UI_RESTART_CSRF"] = csrf
        os.execv(sys.executable,[sys.executable,"-m","v13.mobile_dashboard","ui"])


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

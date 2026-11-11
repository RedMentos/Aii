"""Private, local-only browser buttons for V13 on Android Termux.

An explicit local browser is the UI. No public listener, remote shell, Android
accessibility permission, raw log upload, or unsupervised model-weight edits.
"""
from __future__ import annotations
import argparse
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

PRIVATE = Path.home() / ".v13-private"
DATA = Path.home() / "v13"
MAX_TAIL = 100_000
BUNDLE_LIMIT = 200_000
PORT = 0  # OS-selected local port; no remote interface
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


def diagnostics_zip(destination=None):
    """Local user-initiated ZIP. May contain chat text: never upload automatically."""
    outdir = Path.home() / "storage/downloads"
    if destination is None:
        if not outdir.is_dir() or outdir.is_symlink():
            raise RuntimeError("Download access missing: run termux-setup-storage once")
        destination = outdir / ("V13-Diagnose-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3) + ".zip")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    allowlisted = (
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


class RuntimeControls:
    def __init__(self):
        self.lock = threading.Lock()
        self.process = None
        self.mode = None
        self.last_action = "Keine Aktion"
        PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(PRIVATE, 0o700)

    def state(self):
        with self.lock:
            proc = self.process
            running = proc is not None and proc.poll() is None
            code = None if proc is None else proc.poll()
            return running, self.mode, code, self.last_action

    def launch(self, mode, question=""):
        if mode not in ALLOWED:
            raise ValueError("unknown fixed action")
        if mode == "ask":
            if not isinstance(question, str) or not 1 <= len(question.strip()) <= 1600:
                raise ValueError("Please enter a question (up to 1600 characters)")
            question = question.strip()
        launcher = DATA / "bin/v13"
        if launcher.is_symlink() or not launcher.is_file():
            raise RuntimeError("V13 isn't installed at ~/v13/bin/v13")
        cmd = [str(launcher), *ALLOWED[mode]]
        if mode == "ask":
            cmd.append(question)
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise RuntimeError("V13 is still processing. Wait or press Stop.")
            log = PRIVATE / "v13-ui-last.log"
            previous = PRIVATE / "v13-ui-previous.log"
            if previous.is_symlink() or log.is_symlink():
                raise RuntimeError("Unsafe local log symlink")
            if log.exists():
                os.replace(log, previous)
            with log.open("xb") as f:
                os.chmod(log, 0o600)
                # Important: no shell, no direct arbitrary terminal / file / remote commands.
                self.process = subprocess.Popen(
                    cmd, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT,
                    start_new_session=True, cwd=str(Path.home()))
            self.mode = mode
            self.last_action = mode
            return self.process.pid

    def stop(self):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                return "Kein von der Oberfläche gestarteter Prozess aktiv."
            proc = self.process
            os.killpg(proc.pid, signal.SIGINT)
            self.last_action = "Stop angefordert"
            return "Abbruchsignal an V13 gesendet."

    def output(self):
        return safe_text(bounded_tail(PRIVATE / "v13-ui-last.log", MAX_TAIL))


def dashboard_html(token, controls, message=""):
    running, mode, code, last = controls.state()
    state = "läuft" if running else "bereit" if code is None else f"beendet ({code})"
    current = summary()
    roles = " · ".join(f"{html.escape(name)}: {'OK' if v.get('ok') else 'Fehler'}"
                       for name, v in current["roles"].items())
    action = "/t/" + token + "/action"
    def form(name, label, cls=""):
        return f'<form method="POST" action="{action}"><input type="hidden" name="action" value="{name}"><button class="{cls}" type="submit">{label}</button></form>'
    msg = f'<p class="message">{html.escape(message)}</p>' if message else ""
    output = controls.output()
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="4">
<title>V13 – Redmi Kontrollzentrum</title>
<style>
:root{{color-scheme:dark;font-family:system-ui,sans-serif}}
body{{background:#10131a;color:#edf2fa;margin:0;padding:16px}}
main{{max-width:780px;margin:auto}}
h1{{font-size:1.7rem}} h2{{font-size:1.1rem}}
section{{background:#1a202a;border:1px solid #303b4a;border-radius:16px;padding:16px;margin:12px 0}}
button{{background:#3977c8;color:white;padding:14px 17px;border:0;border-radius:10px;font-weight:bold;font-size:1rem;min-height:48px;cursor:pointer}}
button.secondary{{background:#394353}}button.danger{{background:#ac4848}}
.actions{{display:flex;gap:8px;flex-wrap:wrap}} .actions form{{flex:1}} .actions button{{width:100%}}
input{{width:100%;box-sizing:border-box;background:#111924;color:white;padding:14px;border:1px solid #56687e;border-radius:10px;font-size:1rem}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#0c1017;padding:12px;border-radius:8px;max-height:390px;overflow:auto;font-size:.82rem}}
small{{color:#b0bdcf}}.message{{color:#b8e4c4}}
</style></head><body><main>
<h1>V13 · Redmi Kontrollzentrum</h1>
<section><b>V13: {html.escape(state)}</b><p>Letzte Aktion: {html.escape(last)}</p>
<small>Modelltest: {html.escape(current["native_probe"])} · {roles or "Noch keine Rollenmessung"}</small>{msg}</section>
<section><h2>KI ausprobieren</h2>
<form method="POST" action="{action}"><input type="hidden" name="action" value="ask">
<input name="question" aria-label="Frage an V13" maxlength="1600" placeholder="Schreib deine Frage an V13…" required>
<p><button type="submit">Nachricht senden</button></p></form></section>
<section><h2>Gehirn & Tests</h2><div class="actions">
{form("doctor","Gehirnstatus")}
{form("probe","Modelle testen")}
{form("zip","Diagnose-ZIP", "secondary")}
{form("stop","V13 stoppen", "danger")}</div>
<small>ZIP wird nur lokal in Downloads gespeichert. Vor dem Teilen prüfen: Protokolle können private Chattexte enthalten.</small></section>
<section><h2>Letzte Ausgabe</h2><pre>{html.escape(output[-MAX_TAIL:] or "Noch keine Ausgabe. Starte einen Test über die Knöpfe.")}</pre></section>
<section><small>Nur lokal auf 127.0.0.1. Kein freier Shell-Zugriff und keine automatischen Patches. Kein Rohlog-Upload nach GitHub.</small></section>
</main></body></html>"""


def serve(*, open_browser=True):
    controls = RuntimeControls()
    token = secrets.token_hex(24)
    prefix = "/t/" + token
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # never log private URL or prompts
        def _headers(self, code=200, *, location=None):
            self.send_response(code)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            if location:
                self.send_header("Location", location)
            else:
                self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
        def do_GET(self):
            if self.path != prefix + "/":
                self._headers(404)
                return
            data = dashboard_html(token, controls).encode("utf-8")
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
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            expected = "http://127.0.0.1:" + str(self.server.server_port)
            if host != "127.0.0.1:" + str(self.server.server_port) or origin not in (None, expected):
                self._headers(403)
                return
            try:
                fields = parse_qs(self.rfile.read(int(length)).decode("utf-8"), keep_blank_values=True)
                action = fields.get("action", [""])[0]
                if action in ALLOWED:
                    question = fields.get("question", [""])[0] if action == "ask" else ""
                    controls.launch(action, question)
                    message = "V13-Auftrag gestartet. Ausgabe erscheint unten."
                elif action == "stop":
                    message = controls.stop()
                elif action == "zip":
                    dest = diagnostics_zip()
                    message = "Diagnose-ZIP erstellt: " + dest.name + " (in Downloads)"
                else:
                    raise ValueError("Unbekannte Aktion")
            except (OSError, ValueError, RuntimeError, UnicodeError) as exc:
                message = "Fehler: " + type(exc).__name__ + ": " + str(exc)[:200]
            data = dashboard_html(token, controls, message).encode("utf-8")
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

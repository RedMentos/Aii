"""Captured V13 plain-text sessions for the local, touch-friendly control panel.

Captures ONLY V13 sessions started here, not other Termux shells or past scrollback.
Raw session output and user input remain in chmod-600 local files. No upload.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import threading
import time

HOME = Path.home()
PRIVATE = HOME / ".v13-private"
LOGS = PRIVATE / "console-logs"
MAX_SESSION_BYTES = 4 * 1024 * 1024
MAX_SESSIONS = 32
MAX_COMMAND_BYTES = 16_000


class ConsoleBusy(RuntimeError):
    pass


def _owner_private_directory(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    st = path.lstat()
    if not path.is_dir() or path.is_symlink() or st.st_uid != os.getuid() or st.st_mode & 0o077:
        raise RuntimeError("V13 diagnostics directory must be owner-only")


class ManagedConsole:
    def __init__(self, data_home=None, log_root=None):
        self.home = Path(data_home or HOME / "v13")
        self.logs = Path(log_root or LOGS)
        _owner_private_directory(self.logs.parent)
        _owner_private_directory(self.logs)
        self.lock = threading.RLock()
        self.process = None
        self.path = None
        self.last_exit = None
        self.started_at = None
        self.log_bytes = 0
        self.reader = None

    def _append(self, data):
        if not data:
            return
        with self.lock:
            path = self.path
            if path is None:
                return
            if self.log_bytes >= MAX_SESSION_BYTES:
                return
            remaining = MAX_SESSION_BYTES - self.log_bytes
            chunk = data[:remaining]
            if path.is_symlink():
                return
            with path.open("ab") as f:
                f.write(chunk)
            self.log_bytes += len(chunk)
            if len(chunk) < len(data):
                with path.open("ab") as f:
                    f.write(b"\n[V13 local log limit reached; further output is not saved]\n")
                self.log_bytes = MAX_SESSION_BYTES

    def _cleanup_old(self):
        entries = sorted((p for p in self.logs.glob("v13-session-*.log") if p.is_file() and not p.is_symlink()),
                         key=lambda p: p.stat().st_mtime, reverse=True)
        for entry in entries[MAX_SESSIONS:]:
            entry.unlink(missing_ok=True)

    def start(self):
        launcher = self.home / "bin" / "v13"
        if not launcher.is_file() or launcher.is_symlink():
            raise RuntimeError("Installiertes V13 fehlt: ~/v13/bin/v13")
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                return {"status": "ALREADY_RUNNING", "pid": self.process.pid}
            self._cleanup_old()
            filename = "v13-session-" + time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3) + ".log"
            path = self.logs / filename
            with path.open("x") as out:
                os.chmod(path, 0o600)
                out.write("V13 managed local session; private transcript; not uploaded.\n")
            env = dict(os.environ, PYTHONUNBUFFERED="1", NEEDLE_TELEMETRY="0", DO_NOT_TRACK="1")
            proc = subprocess.Popen(
                [str(launcher), "chat", "--plain"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, cwd=str(HOME), env=env,
                start_new_session=True, bufsize=0,
            )
            self.process = proc
            self.path = path
            self.started_at = time.time()
            self.last_exit = None
            self.log_bytes = path.stat().st_size
            self.reader = threading.Thread(target=self._drain, args=(proc, path), name="v13-terminal-recorder", daemon=True)
            self.reader.start()
            return {"status": "STARTED", "pid": proc.pid}

    def _drain(self, proc, path):
        try:
            while True:
                chunk = os.read(proc.stdout.fileno(), 4096)
                if not chunk:
                    break
                with self.lock:
                    if self.path == path:
                        self._append(chunk)
        except (OSError, ValueError) as exc:
            with self.lock:
                if self.path == path:
                    self._append(("\n[console capture error: " + type(exc).__name__ + "]\n").encode())
        finally:
            result = proc.wait()
            with self.lock:
                if self.path == path:
                    self.last_exit = result
                    self._append(("\n[V13 exited with code " + str(result) + "]\n").encode())

    def send(self, command):
        if not isinstance(command, str) or not command.strip():
            raise ValueError("Bitte V13-Nachricht oder Befehl eingeben")
        if "\x00" in command or "\r" in command or "\n" in command:
            raise ValueError("Nur einzelne V13-Chatzeilen werden akzeptiert")
        if len(command.encode("utf-8")) > MAX_COMMAND_BYTES:
            raise ValueError("V13-Nachricht zu lang")
        with self.lock:
            proc = self.process
            if proc is None or proc.poll() is not None or proc.stdin is None:
                raise ConsoleBusy("Zuerst V13 Chat starten")
            data = command.strip().encode("utf-8") + b"\n"
            # All UI-submitted local V13 commands are logged locally;
            # the remote bridge never receives these raw user inputs.
            path = self.path
            offset = (path.stat().st_size if path is not None and
                      path.is_file() and not path.is_symlink() else None)
            echo = b"\n[du> " + data.rstrip(b"\n") + b"]\n"
            self._append(echo)
            logged = (offset is not None and path.stat().st_size == offset + len(echo)
                      and self.log_bytes < MAX_SESSION_BYTES)
            proc.stdin.write(data)
            proc.stdin.flush()
            # Bind the accepted input to the exact session/log position while
            # holding the same lock as recorder, restart and competing sends.
            # A separate state RPC or filesystem stat cannot provide this.
            return {"status": "SENT", "session":path.name if path else None,
                    "offset":offset, "input_logged":logged}

    def cancel(self):
        with self.lock:
            proc = self.process
            if proc is None or proc.poll() is not None:
                return {"status": "NOT_RUNNING"}
            os.killpg(proc.pid, signal.SIGINT)
            return {"status": "CANCEL_REQUESTED"}

    def shutdown(self):
        return self.send(":shutdown")

    def state(self):
        with self.lock:
            proc = self.process
            running = proc is not None and proc.poll() is None
            return {
                "running": running,
                "exit_code": None if proc is None else proc.poll(),
                "pid": proc.pid if running else None,
                "started_at": self.started_at,
                "last_session": self.path.name if self.path else None,
                "log_capped": self.log_bytes >= MAX_SESSION_BYTES,
            }

    def output(self, limit=160_000):
        with self.lock:
            path = self.path
        if path is None or path.is_symlink() or not path.is_file():
            return ""
        with path.open("rb") as stream:
            stream.seek(max(0, path.stat().st_size - limit))
            return stream.read(limit).decode("utf-8", errors="replace")

    def transcript(self, *, all_sessions=True):
        """Local-only complete saved log, including prior preserved V13 sessions.

        Unlike the live-view tail, this endpoint reads the complete bounded
        recorded file(s). Never exposed via the private GitHub relay.
        """
        with self.lock:
            self._cleanup_old()
            newest = self.path
        if all_sessions:
            paths = sorted((p for p in self.logs.glob("v13-session-*.log")
                            if p.is_file() and not p.is_symlink()),
                           key=lambda p: p.name)
        else:
            paths = [newest] if newest is not None else []
        chunks = []
        for p in paths[-MAX_SESSIONS:]:
            if p is None or p.is_symlink() or not p.is_file():
                continue
            if p.stat().st_size > MAX_SESSION_BYTES + 512:
                continue
            with p.open("rb") as reader:
                chunk = reader.read(MAX_SESSION_BYTES + 512)
            chunks.append(("\n\n=== " + p.name + " ===\n").encode() + chunk)
        return b"".join(chunks).decode("utf-8", errors="replace")

    def saved_sessions(self):
        return [p.name for p in sorted(self.logs.glob("v13-session-*.log"), reverse=True)
                if p.is_file() and not p.is_symlink()][:MAX_SESSIONS]

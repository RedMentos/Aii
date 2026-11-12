"""Long-running *V13 AI* service on Android/Termux, separate from web UI.

Unlike the update poller, this keeps the actual V13 runtime alive with a
private Unix-socket interface. Browser tabs and the dashboard process do not
own the model process. All chat, memory, outputs and prompts remain local.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import secrets
import socket
import socketserver
import subprocess
import sys
import threading
import time

from .managed_console import ManagedConsole, _owner_private_directory
from . import lifecycle

PRIVATE = Path.home() / ".v13-private"
SOCKET = PRIVATE / "v13-ai.sock"
LOCK = PRIVATE / "v13-ai.lock"
DESIRED = PRIVATE / "v13-ai-enabled.json"
MAX_RPC = 18000
MAX_REPLY = 144 * 1024 * 1024  # 32 retained bounded transcripts, local only
MAX_TAIL = 160000
PROTOCOL = "v13-local-ai/1"


def _read_desired():
    if DESIRED.is_symlink():
        return False
    try:
        if DESIRED.is_file():
            st = DESIRED.stat()
            return (st.st_uid == os.getuid() and not st.st_mode & 0o077
                    and json.loads(DESIRED.read_text()).get("enabled") is True)
    except (OSError, ValueError):
        pass
    return False


def _desired(enabled):
    _owner_private_directory(PRIVATE)
    if DESIRED.is_symlink():
        raise RuntimeError("Unsafe V13 AI autostart config")
    path = PRIVATE / (".v13-ai-" + secrets.token_hex(6))
    try:
        with path.open("x") as stream:
            os.chmod(path, 0o600)
            json.dump({"schema":"v13.ai-autostart/1", "enabled":bool(enabled)}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        path.replace(DESIRED)
    finally:
        path.unlink(missing_ok=True)


def ai_info():
    return {"service":"V13_AI", "enabled":_read_desired()}


class ChatService:
    def __init__(self, console=None):
        self.console = console or ManagedConsole()
        self.lock = threading.RLock()
        self.next_retry = 0.0
        self.failures = 0
        self.last_start = 0.0
        self.paused = False
        self.pending_lifecycle = False
        self.reload_requested = False
        self.stop_deadline = 0.0
        self.status = "STARTING"

    def tick(self):
        """Watch the model independently of any browser; no arbitrary tools."""
        with self.lock:
            from . import pipeline_agent
            if lifecycle.service_stop(self.console, shutdown_wait=12, interrupt_wait=6):
                self.paused = True
                self.status = "PAUSED_FOR_UPDATE"
                self.pending_lifecycle = True
            snapshot = pipeline_agent.snapshot()
            # An updated service module must be reloaded before the new V13
            # model chat is re-opened. This independent daemon can restart
            # without restarting its browser client.
            if (pipeline_agent.refresh_requested("ai")
                    and snapshot["last_result"] != "CHECKING"):
                self.status = "RELOADING_AFTER_UPDATE"
                self.reload_requested = True
                return
            # Never restart a model in the middle of changing its source.
            if snapshot["last_result"] == "CHECKING" or lifecycle.STOP_REQUEST.is_file():
                return
            if self.paused:
                if _read_desired() and lifecycle.service_resume(self.console):
                    self.paused = False
                    self.pending_lifecycle = False
                    self.status = "RUNNING"
                    self.failures = 0
                # If a failed update never queued resume, self-recover when
                # the transaction is no longer active and stop request gone.
                elif self.pending_lifecycle:
                    if lifecycle.STOP_REQUEST.exists() or snapshot["last_result"] == "CHECKING":
                        return
                    self.paused = False
                    self.pending_lifecycle = False
            else:
                if _read_desired():
                    lifecycle.service_resume(self.console)
            state = self.console.state()
            now = time.monotonic()
            if state["running"] and not _read_desired():
                # The explicit OFF decision must actually stop the model.
                # Previously tick() overwrote STOPPING with RUNNING forever
                # when :shutdown was stuck in native inference.
                self.status = "STOPPING"
                if not self.stop_deadline:
                    self.stop_deadline = now + 12
                    try:
                        self.console.shutdown()
                    except (OSError, ValueError, RuntimeError):
                        pass
                elif now >= self.stop_deadline:
                    # Only the captured, isolated child may be terminated.
                    terminate = getattr(self.console, "terminate_owned", None)
                    if callable(terminate):
                        try:
                            terminate(term_wait=2.0, kill_wait=1.0)
                        except (OSError, ValueError, RuntimeError):
                            pass
                    self.stop_deadline = time.monotonic() + 5
                return
            if not state["running"]:
                self.stop_deadline = 0.0
            if state["running"]:
                self.status = "RUNNING"
                if self.last_start and now - self.last_start > 30:
                    self.failures = 0
                return
            if not _read_desired():
                self.status = "STOPPED_BY_USER"
                return
            # A model that exits immediately must not spin endlessly at
            # 2 startups per second, draining battery or damaging log storage.
            if self.last_start and self.next_retry <= self.last_start:
                if now - self.last_start < 30:
                    self.failures += 1
                    self.next_retry = now + min(300, 2 ** min(self.failures + 1, 8))
                else:
                    self.failures = 0
                    self.next_retry = now
            if now < self.next_retry:
                self.status = "RETRY_WAIT"
                return
            try:
                response = self.console.start()
            except (OSError, RuntimeError, ValueError):
                self.failures += 1
                self.next_retry = now + min(120, max(3, 2 ** min(self.failures, 6)))
                self.status = "LAUNCH_FAILED"
            else:
                self.last_start = now
                self.next_retry = now
                self.status = "RUNNING" if response["status"] in ("STARTED", "ALREADY_RUNNING") else "LAUNCH_FAILED"

    def command(self, name, data):
        with self.lock:
            if name == "state":
                s = self.console.state()
                s["daemon"] = self.status
                s["autostart"] = _read_desired()
                s["service"] = "RUNNING"
                return s
            if name == "start":
                _desired(True)
                self.stop_deadline = 0.0
                self.next_retry = 0
                self.paused = False
                self.console.start()
                self.last_start = time.monotonic()
                self.next_retry = self.last_start
                self.status = "RUNNING"
                return {"status":"STARTED"}
            if name == "send":
                command = data.get("line")
                if not isinstance(command, str):
                    raise ValueError("Invalid chat text")
                if command.strip() == ":shutdown":
                    return self.command("shutdown", {})
                return self.console.send(command)
            if name == "output":
                limit = data.get("limit", MAX_TAIL)
                if type(limit) is not int or not 0 <= limit <= MAX_TAIL:
                    raise ValueError("Invalid log limit")
                return self.console.output(limit)
            if name == "transcript":
                return self.console.transcript(all_sessions=True)
            if name == "saved_sessions":
                return self.console.saved_sessions()
            if name == "cancel":
                return self.console.cancel()
            if name == "shutdown":
                _desired(False)
                self.stop_deadline = time.monotonic() + 12
                if self.console.state()["running"]:
                    try:
                        self.console.shutdown()
                    except (OSError, ValueError, RuntimeError):
                        self.console.cancel()
                self.status = "STOPPING"
                return {"status":"SHUTDOWN_REQUESTED"}
            raise ValueError("Unknown AI service action")


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False
    request_queue_size = 16


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        # The private directory and socket permissions prevent access from
        # outside the same Termux UID; no TCP listener or remote tools.
        sock = self.request
        sock.settimeout(8)
        raw = b""
        try:
            while len(raw) <= MAX_RPC and not raw.endswith(b"\n"):
                chunk = sock.recv(min(4096, MAX_RPC + 1 - len(raw)))
                if not chunk:
                    break
                raw += chunk
            if len(raw) > MAX_RPC or not raw.endswith(b"\n"):
                raise ValueError("Request length or terminator invalid")
            req = json.loads(raw)
            if not isinstance(req, dict) or req.get("protocol") != PROTOCOL:
                raise ValueError("Protocol mismatch")
            result = self.server.ai.command(req.get("method"), req)
            reply = {"ok":True, "result":result}
        except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, json.JSONDecodeError) as exc:
            reply = {"ok":False, "error":type(exc).__name__, "message":str(exc)[:200]}
        payload = (json.dumps(reply, ensure_ascii=False) + "\n").encode("utf-8")
        if len(payload) <= MAX_REPLY:
            try:
                sock.sendall(payload)
            except OSError:
                pass


def call(method, **kwargs):
    if method not in {"state", "start", "send", "output", "transcript",
                      "saved_sessions", "cancel", "shutdown"}:
        raise ValueError("Unknown V13 background call")
    req = (json.dumps({"protocol":PROTOCOL, "method":method, **kwargs},
                      ensure_ascii=False) + "\n").encode("utf-8")
    if len(req) > MAX_RPC:
        raise ValueError("Chat request too long")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(12)
        sock.connect(str(SOCKET))
        sock.sendall(req)
        chunks = []
        size = 0
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_REPLY:
                raise RuntimeError("V13 AI reply exceeds local bound")
            chunks.append(chunk)
            if chunk.endswith(b"\n"):
                break
    if not chunks:
        raise RuntimeError("V13 AI background service returned no data")
    response = json.loads(b"".join(chunks))
    if not response.get("ok"):
        raise RuntimeError(response.get("message") or response.get("error") or "V13 AI service error")
    return response["result"]


def ensure_service(*, timeout=10):
    """Start an independent detached AI process if missing (not a UI child)."""
    try:
        call("state")
        return True
    except (ConnectionError, OSError, RuntimeError, TimeoutError):
        pass
    path = PRIVATE / "ai-service.log"
    _owner_private_directory(PRIVATE)
    if path.is_symlink():
        raise RuntimeError("Unsafe AI service log")
    # Launch from the installed source root, not HOME: otherwise the
    # detached daemon cannot import v13 when only the UI process' cwd made
    # that Python package importable. This was the browser-start timeout.
    source_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(source_root) + (os.pathsep + env["PYTHONPATH"]
                                           if env.get("PYTHONPATH") else "")
    with path.open("ab") as out:
        os.chmod(path, 0o600)
        subprocess.Popen([sys.executable, "-m", "v13.chat_service", "serve"],
                         stdin=subprocess.DEVNULL, stdout=out, stderr=out,
                         start_new_session=True, close_fds=True,
                         cwd=str(source_root), env=env)
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            call("state")
            return True
        except (ConnectionError, OSError, RuntimeError, TimeoutError):
            time.sleep(.1)
    raise RuntimeError("V13 AI background service could not be started")


class RemoteConsole:
    """Small API used by dashboard; state lives in the independent AI daemon."""
    def __init__(self, *args, **kwargs):
        ensure_service()

    def start(self): return call("start")
    def send(self, line): return call("send", line=line)
    def output(self, limit=MAX_TAIL): return call("output", limit=limit)
    def transcript(self, *, all_sessions=True): return call("transcript")
    def saved_sessions(self): return call("saved_sessions")
    def cancel(self): return call("cancel")
    def shutdown(self): return call("shutdown")
    def state(self): return call("state")


def serve():
    _owner_private_directory(PRIVATE)
    if LOCK.is_symlink() or SOCKET.is_symlink():
        raise RuntimeError("Unsafe V13 AI service filesystem")
    fd = os.open(LOCK, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0  # another background AI already owns the socket
        if SOCKET.exists():
            SOCKET.unlink()  # stale from previous owner; lock guarantees safety
        server = Server(str(SOCKET), Handler)
        os.chmod(SOCKET, 0o600)
        server.ai = ChatService()
        try:
            # A saved explicit OFF is never overridden. On a fresh install,
            # the installer opts in via the private desired-state file.
            def heartbeat():
                while True:
                    try:
                        server.ai.tick()
                        if server.ai.reload_requested:
                            server.shutdown()
                            return
                    except (OSError, ValueError, RuntimeError):
                        pass
                    time.sleep(.5)
            threading.Thread(target=heartbeat, name="v13-ai-supervisor", daemon=True).start()
            server.serve_forever(poll_interval=.5)
        finally:
            server.server_close()
            SOCKET.unlink(missing_ok=True)
        if server.ai.reload_requested:
            from . import pipeline_agent
            pipeline_agent.acknowledge_refresh("ai")
            # AI was already shut down for the transaction, so the fresh
            # service can safely reattach and start it using the resume marker.
            os.execv(sys.executable, [sys.executable, "-m", "v13.chat_service", "serve"])
    finally:
        os.close(fd)


def main(argv=None):
    p = argparse.ArgumentParser(description="V13 always-running local AI")
    p.add_argument("action", choices=("serve", "status", "start", "shutdown"))
    args=p.parse_args(argv)
    if args.action=="serve":
        return serve()
    if args.action=="status":
        print(json.dumps(call("state"), ensure_ascii=False));return 0
    ensure_service()
    print(json.dumps(call(args.action),ensure_ascii=False));return 0


if __name__=="__main__":
    sys.exit(main())

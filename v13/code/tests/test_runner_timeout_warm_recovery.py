import json
import os
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from v13 import runners
from v13.common import Limits


class DummyProcess:
    def __init__(self):
        self.pid = 99999999
        self.dead = False

    def poll(self):
        return 0 if self.dead else None

    def terminate(self):
        self.dead = True

    def kill(self):
        self.dead = True

    def wait(self, timeout=None):
        self.dead = True
        return 0


class ServerState:
    def __init__(self, *, hold_busy_after_disconnect=False):
        self.lock = threading.Lock()
        self.slot_busy = False
        self.request_count = 0
        self.cache_prompt_values = []
        self.disconnect_event = threading.Event()
        self.release_slot = threading.Event()
        self.hold_busy_after_disconnect = hold_busy_after_disconnect


def _server(state):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            return

        def _json(self, value):
            body = json.dumps(value).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()

        def do_GET(self):
            if self.path == "/slots":
                with state.lock:
                    busy = state.slot_busy
                self._json([{"id": 0, "is_processing": busy}])
                return
            self.send_error(404)

        def _chunk(self, payload):
            self.wfile.write(f"{len(payload):X}\r\n".encode() + payload + b"\r\n")
            self.wfile.flush()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if self.path != "/completion":
                self.send_error(404)
                return
            with state.lock:
                state.request_count += 1
                request_number = state.request_count
                state.cache_prompt_values.append(payload.get("cache_prompt"))
                state.slot_busy = True
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            if request_number > 1:
                try:
                    self._chunk(b'data: {"content":"ok","stop":true}\n\n')
                    self.wfile.write(b"0\r\n\r\n")
                    self.wfile.flush()
                finally:
                    with state.lock:
                        state.slot_busy = False
                return
            try:
                self._chunk(b'data: {"content":"partial","stop":false}\n\n')
                while True:
                    self._chunk(b'data: {"content":"","stop":false}\n\n')
                    time.sleep(0.025)
            except (BrokenPipeError, ConnectionResetError, OSError):
                state.disconnect_event.set()
                if state.hold_busy_after_disconnect:
                    state.release_slot.wait(2.0)
                with state.lock:
                    state.slot_busy = False
                return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _runner(tmp_path, server):
    home = tmp_path / "home"
    (home / "bin").mkdir(parents=True)
    binary = home / "bin" / "llama-server"
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o700)
    model = home / "models" / "body.gguf"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"fake-model")
    cfg = {
        "answer_tokens": 4,
        "temperature": 0.0,
        "context_tokens": 2048,
        "threads": 2,
        "native_batch_tokens": 128,
        "native_cache_ram_mb": 128,
        "native_ctx_checkpoints": 6,
        "native_memory_audit": False,
    }
    runner = runners.LlamaRunner(home, "B1_DETAIL", model, cfg)
    runner.port = server.server_port
    runner.proc = DummyProcess()
    runner.load = lambda cancel, deadline: None
    runner._prompt = lambda messages, cancel, deadline, reserve: ("prompt", 3, False)
    runner._loaded_stamp = runner._lifecycle_stamp()
    return runner


def _run_until_deadline(runner, seconds=0.25):
    cancel = threading.Event()
    deadline = time.monotonic() + seconds
    chunks = []
    with pytest.raises(Limits):
        for chunk in runner.generate([], cancel, deadline, max_tokens=4):
            chunks.append(chunk)
    return chunks


def test_deadline_disconnect_retains_idle_process_and_next_request_skips_cache(tmp_path, monkeypatch):
    state = ServerState()
    server, thread = _server(state)
    kill_calls = []
    monkeypatch.setattr(runners, "kill_process", lambda proc: (kill_calls.append(proc), proc.terminate()))
    try:
        runner = _runner(tmp_path, server)
        process = runner.proc
        chunks = _run_until_deadline(runner)
        assert chunks == ["partial"]
        assert state.disconnect_event.wait(1.0)
        assert runner.proc is process
        assert process.poll() is None
        recovery = runner.last_metrics["interruption_recovery"]
        assert recovery["retained"] is True
        assert recovery["status"] == "WARM_RETAINED_AFTER_IDLE_SLOT"
        assert recovery["slot_idle"] is True
        assert runner._clear_next_prompt_cache is True
        assert kill_calls == []

        output = list(runner.generate([], threading.Event(), time.monotonic() + 2.0, max_tokens=4))
        assert output == ["ok"]
        assert state.cache_prompt_values == [True, False]
        assert runner._clear_next_prompt_cache is False
        assert runner.proc is process
        assert process.poll() is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join(1.0)


def test_deadline_busy_slot_fails_closed_and_reaps_process(tmp_path, monkeypatch):
    state = ServerState(hold_busy_after_disconnect=True)
    server, thread = _server(state)
    monkeypatch.setattr(runners, "WARM_RECOVERY_DRAIN_SECONDS", 0.10)
    kill_calls = []
    monkeypatch.setattr(runners, "kill_process", lambda proc: (kill_calls.append(proc), proc.terminate()))
    try:
        runner = _runner(tmp_path, server)
        process = runner.proc
        chunks = _run_until_deadline(runner)
        assert chunks == ["partial"]
        assert state.disconnect_event.wait(1.0)
        recovery = runner.last_metrics["interruption_recovery"]
        assert recovery["retained"] is False
        assert recovery["status"] == "UNLOADED_AFTER_UNSAFE_SLOT_STATE"
        assert recovery["reason"] == "SLOT_REMAINED_BUSY"
        assert runner.proc is None
        assert process.poll() == 0
        assert kill_calls == [process]
        state.release_slot.set()
    finally:
        state.release_slot.set()
        server.shutdown()
        server.server_close()
        thread.join(1.0)

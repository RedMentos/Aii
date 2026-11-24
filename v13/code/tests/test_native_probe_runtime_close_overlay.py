import importlib.util
import queue
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13 import native_probe_approval as approval


CODE = Path(__file__).resolve().parents[1]
OVERLAY_PATH = CODE / "scripts" / "integrated_native_probe_runtime_close_overlay_20261124.py"


def _overlay():
    spec = importlib.util.spec_from_file_location("v14_native_probe_runtime_close_overlay_test", OVERLAY_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _runtime_close_class():
    source = (CODE / "v13" / "runtime.py").read_bytes()
    patched = _overlay().apply_sources({"v13/runtime.py": source}, code_dir=CODE)["v13/runtime.py"]
    assert patched.count(b"guard_runtime_close(self)") == 1
    assert patched.index(b"guard_runtime_close(self)") < patched.index(b"with self.lock:self.stop.set()")
    method_start = patched.index(b"    def close(self):")
    method = patched[method_start:].decode("utf-8")
    namespace = {"__name__": "v13.runtime_close_overlay_test", "__package__": "v13"}
    exec("class RuntimeCloseHarness:\n" + method, namespace)
    return namespace["RuntimeCloseHarness"]


class _Worker:
    def join(self, timeout=None):
        return None

    def is_alive(self):
        return False


class _Unloader:
    def unload(self):
        return None


class _Store:
    def __init__(self, runtime, closed_event):
        self.runtime = runtime
        self.closed_event = closed_event

    def queue_stats(self):
        return {"count": 0}

    def queue_paused(self):
        return False

    def close(self):
        assert self.runtime.current is None
        assert self.runtime._native_probe_active is False
        assert self.runtime._native_probe_done.is_set()
        assert self.runtime.paused is False
        self.closed_event.set()


def _runtime():
    cls = _runtime_close_class()
    runtime = cls()
    runtime.lock = threading.RLock()
    runtime.stop = threading.Event()
    runtime.cancel_event = threading.Event()
    runtime.wake = threading.Event()
    runtime.jobs = queue.Queue()
    runtime.current = None
    runtime.paused = False
    runtime.status = "Bereit"
    runtime.closed = False
    runtime.worker = _Worker()
    runtime.pool = _Unloader()
    runtime.needle = _Unloader()
    runtime.memory = SimpleNamespace(semantic_keys=SimpleNamespace(encoder=_Unloader()))
    runtime.learner = SimpleNamespace(proc=None)
    runtime.store_closed = threading.Event()
    runtime.store = _Store(runtime, runtime.store_closed)
    return runtime


def test_captured_close_callback_waits_for_native_probe_lease_before_store_close():
    runtime = _runtime()
    saved_close = runtime.close  # Simulates a UI/shutdown callback bound before a probe starts.
    started = threading.Event()
    probe_finished = threading.Event()
    errors = []

    def probe():
        with approval.runtime_probe_lease(runtime):
            started.set()
            while not runtime.cancel_event.wait(0.01):
                pass
            probe_finished.set()

    probe_thread = threading.Thread(target=probe, name="test-native-probe-lease")
    probe_thread.start()
    assert started.wait(1.0)

    def close():
        try:
            saved_close()
        except BaseException as exc:
            errors.append(exc)

    close_thread = threading.Thread(target=close, name="test-captured-runtime-close")
    close_thread.start()
    close_thread.join(2.0)
    probe_thread.join(2.0)

    assert not close_thread.is_alive()
    assert not probe_thread.is_alive()
    assert not errors
    assert probe_finished.is_set()
    assert runtime.store_closed.is_set()
    assert runtime.closed is True


def test_captured_close_callback_fails_closed_if_probe_ignores_cancellation(monkeypatch):
    monkeypatch.setattr(approval, "PROBE_CLOSE_WAIT_SECONDS", 0.02)
    runtime = _runtime()
    saved_close = runtime.close
    started = threading.Event()
    release = threading.Event()
    errors = []

    def probe():
        with approval.runtime_probe_lease(runtime):
            started.set()
            release.wait(2.0)  # Deliberately ignores cancellation for the negative control.

    probe_thread = threading.Thread(target=probe, name="test-stuck-native-probe")
    probe_thread.start()
    assert started.wait(1.0)

    with pytest.raises(RuntimeError, match="Store remains open"):
        saved_close()

    assert runtime.closed is False
    assert not runtime.store_closed.is_set()
    assert runtime.store.queue_stats()["count"] == 0

    release.set()
    probe_thread.join(2.0)
    assert not probe_thread.is_alive()
    saved_close()
    assert runtime.closed is True
    assert runtime.store_closed.is_set()


def test_probe_owner_cannot_close_runtime_from_inside_its_own_lease():
    runtime = _runtime()
    saved_close = runtime.close
    errors = []

    def probe():
        with approval.runtime_probe_lease(runtime):
            with pytest.raises(RuntimeError, match="inside active native probe"):
                saved_close()
            assert runtime.closed is False
            assert not runtime.store_closed.is_set()

    thread = threading.Thread(target=probe, name="test-native-probe-owner")
    thread.start()
    thread.join(2.0)
    assert not thread.is_alive()
    saved_close()
    assert runtime.closed is True
    assert runtime.store_closed.is_set()


def test_close_overlay_rejects_missing_or_ambiguous_runtime_anchor():
    overlay = _overlay()
    with pytest.raises(ValueError, match="anchor expected exactly once"):
        overlay.apply_sources({"v13/runtime.py": b"class Runtime:\\n    pass\\n"}, code_dir=CODE)
    source = (CODE / "v13" / "runtime.py").read_bytes()
    with pytest.raises(ValueError, match="anchor expected exactly once"):
        overlay.apply_sources({"v13/runtime.py": source + b"\\n" + source[source.index(b"    def close(self):"):source.index(b"    def close(self):")+len(b"    def close(self):\\n        if self.closed:return\\n")]}, code_dir=CODE)

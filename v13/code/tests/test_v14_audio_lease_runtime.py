"""Staged Runtime E2E for shared RAW EAR consent lease and revocation cleanup.

All PCM and model outputs here are synthetic. No microphone, native model or
Android permission is exercised.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_staged_audio_lease_covers_bodies_and_complete_c3_then_revokes(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "audio_lease_stage", CODE / "scripts/stage_integrated_candidate.py"
    )
    stage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage)
    destination = tmp_path / "audio-review"
    manifest = stage.stage(CODE, destination)

    assert manifest["status"] == "SHADOW_REVIEW_ONLY"
    assert manifest["builder"].endswith("termux_runtime_recovery_candidate_20261121.py")
    staged_runtime = (destination / "v13/runtime.py").read_text()
    staged_focal = (destination / "v13/focal.py").read_text()
    staged_store = (destination / "v13/audio_context_store.py").read_text()
    assert "audio_consent_lease" in staged_runtime
    assert "consent_lease=audio_window.get('_consent_lease')" in staged_runtime
    assert "SCALE_AWARE_C4_RULE" in staged_focal
    assert "LOCAL_EXACT_ARITHMETIC" in staged_runtime
    assert "def revoke_source" in staged_store
    assert "def sweep_revoked" in staged_store
    assert "def close_runtime" in staged_store

    script = r'''
import json
import math
import struct
from pathlib import Path
import sys
import threading
import time
from contextlib import contextmanager
from unittest.mock import Mock

from v13.inputs import last_context
from v13.operator import Operator
from v13.runtime import Runtime


def tone():
    rate = 16000
    count = rate // 2
    samples = [int(6000 * math.sin(2 * math.pi * 140 * i / rate))
               for i in range(count)]
    return struct.pack("<" + "h" * count, *samples)


class Provider:
    def __init__(self, active=True):
        self.lock = threading.Lock()
        self.callback_lock = threading.Lock()
        self.active = active
        self.callbacks = []

    def check(self, source_id, receipt):
        if not self.lock.acquire(timeout=0.05):
            raise RuntimeError("consent_check re-entered a non-reentrant provider lock")
        try:
            return (self.active and source_id == "mic-test-1"
                    and receipt == "opaque-local-receipt")
        finally:
            self.lock.release()

    @contextmanager
    def guard(self, source_id, receipt):
        self.lock.acquire()
        try:
            yield (self.active and source_id == "mic-test-1"
                   and receipt == "opaque-local-receipt")
        finally:
            self.lock.release()

    def subscribe(self, source_id, receipt, callback):
        if source_id != "mic-test-1" or receipt != "opaque-local-receipt":
            raise ValueError("subscription scope mismatch")
        with self.callback_lock:
            self.callbacks.append(callback)

        def unsubscribe():
            with self.callback_lock:
                if callback in self.callbacks:
                    self.callbacks.remove(callback)
        return unsubscribe

    def revoke(self):
        with self.lock:
            self.active = False
        with self.callback_lock:
            callbacks = list(self.callbacks)
            self.callbacks.clear()
        for callback in callbacks:
            callback()


def make_window(provider):
    return {
        "pcm16": tone(),
        "sample_rate": 16000,
        "start_ms": 0,
        "source_id": "mic-test-1",
        "consent_receipt": "opaque-local-receipt",
        "consent_check": provider.check,
        "consent_guard": provider.guard,
        "consent_revocation_subscribe": provider.subscribe,
        "finality": "FINAL",
    }


def configure(runtime):
    runtime.sleep.cycle.set_policy("enabled", "off")
    runtime.cfg.update(
        deadline_seconds=90, observer_seconds=5, max_reentry=0,
        observer_mode="background", b2_quote_select="off",
        offer_quote_context_chars=0, b2_state_slots=0,
    )
    operator = Operator(runtime)
    operator.run(":effort max")
    operator.run(":ctxos active")
    runtime._route = Mock(return_value=("both", {"source": "SYNTHETIC_AUDIO_E2E"}))
    runtime.learner.output_delta = Mock(return_value=None)


class Runner:
    def __init__(
        self, role, seen, entered=None, release=None, first_chunk=None,
        finished=None, cancel_observed=None,
    ):
        self.role = role
        self.seen = seen
        self.entered = entered
        self.release = release
        self.first_chunk = first_chunk
        self.finished = finished
        self.cancel_observed = cancel_observed
        self.last_metrics = {
            "role": role, "status": "FINAL", "generated_tokens": 5,
            "synthetic": True,
        }

    def generate(self, messages, cancel, deadline, *args, **kwargs):
        self.seen[self.role] = messages
        if self.role == "B1_DETAIL":
            yield json.dumps({
                "summary": "The rent is 120 euros.",
                "quotes": ["The rent is 120 euros."],
                "uncertainty": "low", "needs_reentry": False,
            })
        elif self.role == "B2_GIST":
            yield json.dumps({
                "summary": "A long-term reserve is needed.",
                "quotes": ["The plan preserves a long-term reserve."],
                "uncertainty": "low", "needs_reentry": False,
            })
        else:
            if self.entered is not None:
                self.entered.set()
            # The lease must remain active after the first streamed chunk too.
            try:
                yield "First response chunk."
                if self.first_chunk is not None:
                    self.first_chunk.set()
                if self.cancel_observed is not None:
                    cancel_deadline = time.monotonic() + 8
                    while self.release is not None and not self.release.wait(0.01):
                        if cancel is not None and cancel.is_set():
                            self.cancel_observed.set()
                            return
                        if time.monotonic() >= cancel_deadline:
                            raise TimeoutError("test did not observe Runtime.cancel")
                    if cancel is not None and cancel.is_set():
                        self.cancel_observed.set()
                        return
                elif self.release is not None and not self.release.wait(8):
                    raise TimeoutError("test did not release the second C3 chunk")
                yield "Second response chunk."
            finally:
                if self.finished is not None:
                    self.finished.set()


question = (
    "Compare details with planning. The rent is 120 euros. "
    "The plan preserves a long-term reserve."
)

# Scenario 1: the same lease protects PCM admission, context reads, both bodies
# and the entire C3 iterator. Revocation cannot complete during generation.
home = Path(sys.argv[1]) / "blocked"
runtime = Runtime(home)
provider = Provider()
entered = threading.Event()
first_chunk = threading.Event()
finished = threading.Event()
release = threading.Event()
revoke_started = threading.Event()
revoke_finished = threading.Event()
seen = {}
try:
    configure(runtime)
    runners = {
        role: Runner(
            role, seen,
            entered if role == "C3_LANGUAGE" else None,
            release if role == "C3_LANGUAGE" else None,
            first_chunk if role == "C3_LANGUAGE" else None,
            finished if role == "C3_LANGUAGE" else None,
        )
        for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
    }
    runtime.pool.get = Mock(side_effect=lambda role: runners[role])
    event_id = runtime.submit(question, audio_window=make_window(provider))
    assert entered.wait(30), "normal Runtime turn did not reach C3 generation"
    assert first_chunk.wait(5), "C3 did not stream its first chunk before revocation"

    def revoke():
        revoke_started.set()
        provider.revoke()
        revoke_finished.set()

    revoker = threading.Thread(target=revoke, daemon=True)
    revoker.start()
    assert revoke_started.wait(5)
    blocked_after_first_chunk = not revoke_finished.wait(0.15)
    assert not finished.is_set(), "C3 iterator unexpectedly finished before its second chunk"
    release.set()

    deadline = time.monotonic() + 30
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runtime.idle(), "synthetic audio Runtime turn did not settle"
    assert revoke_finished.wait(5), "revocation did not finish after C3 returned"
    revoker.join(timeout=5)

    assert blocked_after_first_chunk, (
        "provider revocation completed after the first C3 chunk but before iterator exhaustion"
    )
    assert finished.is_set(), "Runtime returned without exhausting the full C3 iterator"
    assert runtime.last_answer()["status"] == "FINAL"
    assert "RAW_EAR_ACOUSTIC" in json.dumps(seen["C3_LANGUAGE"], ensure_ascii=False)
    assert "audio_context" in json.dumps(seen["B1_DETAIL"], ensure_ascii=False)
    assert "audio_context" in json.dumps(seen["B2_GIST"], ensure_ascii=False)
    rows = runtime.store.rows(
        "SELECT deleted FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT'"
    )
    assert rows and all(row["deleted"] == 1 for row in rows), rows
    assert provider.check("mic-test-1", "opaque-local-receipt") is False
    saved_context = last_context(runtime.store, runtime.session)
    assert saved_context and saved_context["event_id"] == event_id
    assert saved_context["messages"] is None and saved_context["preview"] == ""
    # A later text-only turn remains usable and stores no revoked acoustic layer.
    runtime.pool.get = Mock(side_effect=lambda role: Runner(role, seen))
    runtime.submit(question)
    deadline = time.monotonic() + 30
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runtime.idle() and runtime.last_answer()["status"] == "FINAL"
    text_context = last_context(runtime.store, runtime.session)
    assert text_context and text_context["messages"] is not None
    assert "RAW_EAR_ACOUSTIC" not in json.dumps(text_context["messages"], ensure_ascii=False)
finally:
    release.set()
    runtime.close()

# Scenario 2: a revoked receipt is rejected before the normal turn; text-only
# chat remains available and no acoustic source is written.
home = Path(sys.argv[1]) / "pre-revoked"
runtime = Runtime(home)
provider = Provider(active=False)
provider.revoke()
seen = {}
try:
    configure(runtime)
    runners = {
        role: Runner(role, seen)
        for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
    }
    runtime.pool.get = Mock(side_effect=lambda role: runners[role])
    runtime.submit(question, audio_window=make_window(provider))
    deadline = time.monotonic() + 30
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runtime.idle(), "text fallback after revoked audio did not settle"
    assert runtime.last_answer()["status"] == "FINAL"
    assert "RAW_EAR_ACOUSTIC" not in json.dumps(seen["C3_LANGUAGE"], ensure_ascii=False)
    assert runtime.store.rows(
        "SELECT id FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT' AND deleted=0"
    ) == []
finally:
    runtime.close()

# Scenario 3: a real Runtime.cancel() interrupts the blocked C3 iterator,
# releases the provider lease, and lets a concurrent revocation tombstone audio.
home = Path(sys.argv[1]) / "cancelled"
runtime = Runtime(home)
provider = Provider()
entered = threading.Event()
first_chunk = threading.Event()
finished = threading.Event()
cancel_observed = threading.Event()
release = threading.Event()
revoke_started = threading.Event()
revoke_finished = threading.Event()
seen = {}
try:
    configure(runtime)
    runners = {
        role: Runner(
            role, seen,
            entered if role == "C3_LANGUAGE" else None,
            release if role == "C3_LANGUAGE" else None,
            first_chunk if role == "C3_LANGUAGE" else None,
            finished if role == "C3_LANGUAGE" else None,
            cancel_observed if role == "C3_LANGUAGE" else None,
        )
        for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
    }
    runtime.pool.get = Mock(side_effect=lambda role: runners[role])
    runtime.submit(question, audio_window=make_window(provider))
    assert entered.wait(30), "cancel test did not reach C3 generation"
    assert first_chunk.wait(5), "cancel test did not stream its first C3 chunk"

    def revoke_after_cancel():
        revoke_started.set()
        provider.revoke()
        revoke_finished.set()

    revoker = threading.Thread(target=revoke_after_cancel, daemon=True)
    revoker.start()
    assert revoke_started.wait(5)
    blocked_before_cancel = not revoke_finished.wait(0.15)
    runtime.cancel()
    assert cancel_observed.wait(5), "C3 runner did not observe Runtime.cancel"
    assert finished.wait(5), "C3 iterator did not exit after Runtime.cancel"

    deadline = time.monotonic() + 30
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runtime.idle(), "cancelled audio Runtime turn did not settle"
    assert revoke_finished.wait(5), "revocation stayed blocked after C3 cancellation"
    revoker.join(timeout=5)
    assert blocked_before_cancel, "revocation completed before Runtime.cancel released the lease"
    rows = runtime.store.rows(
        "SELECT deleted FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT'"
    )
    assert rows and all(row["deleted"] == 1 for row in rows), rows
    assert provider.check("mic-test-1", "opaque-local-receipt") is False
    saved_context = last_context(runtime.store, runtime.session)
    assert saved_context and saved_context["messages"] is None and saved_context["preview"] == ""
finally:
    release.set()
    runtime.close()

# Scenario 4: Runtime.close() must cancel an in-flight C3 iterator before
# the worker/Store is torn down, while a concurrent provider revoke is waiting.
home = Path(sys.argv[1]) / "closing"
runtime = Runtime(home)
provider = Provider()
entered = threading.Event()
first_chunk = threading.Event()
finished = threading.Event()
cancel_observed = threading.Event()
release = threading.Event()
revoke_started = threading.Event()
revoke_finished = threading.Event()
seen = {}
configure(runtime)
runners = {
    role: Runner(
        role, seen,
        entered if role == "C3_LANGUAGE" else None,
        release if role == "C3_LANGUAGE" else None,
        first_chunk if role == "C3_LANGUAGE" else None,
        finished if role == "C3_LANGUAGE" else None,
        cancel_observed if role == "C3_LANGUAGE" else None,
    )
    for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
}
runtime.pool.get = Mock(side_effect=lambda role: runners[role])
runtime.submit(question, audio_window=make_window(provider))
assert entered.wait(30), "close test did not reach C3 generation"
assert first_chunk.wait(5), "close test did not stream its first C3 chunk"


def revoke_before_close():
    revoke_started.set()
    provider.revoke()
    revoke_finished.set()


revoker = threading.Thread(target=revoke_before_close, daemon=True)
revoker.start()
assert revoke_started.wait(5)
blocked_before_close = not revoke_finished.wait(0.15)
closer = threading.Thread(target=runtime.close, daemon=True)
closer.start()
assert cancel_observed.wait(5), "Runtime.close did not cancel the blocked C3 iterator"
assert finished.wait(5), "C3 iterator did not exit during Runtime.close"
closer.join(timeout=10)
assert not closer.is_alive(), "Runtime.close hung while releasing the audio lease"
assert revoke_finished.wait(5), "provider revocation remained blocked after Runtime.close"
revoker.join(timeout=5)
assert blocked_before_close, "revocation completed before Runtime.close cancelled the lease"
assert runtime.closed is True
assert getattr(runtime, "_audio_contexts", {}) == {}
assert getattr(runtime, "_audio_revocation_contexts", {}) == {}
with provider.callback_lock:
    assert provider.callbacks == []

print("PASS: staged A5 -> B1/B2 -> multi-chunk C3 lease spans iterator; Runtime.cancel and Runtime.close release lease for revocation; tombstones, unsubscribe and text fallback stay safe")
'''
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "private-home")],
        cwd=destination,
        env=dict(os.environ, PYTHONPATH=str(destination), PYTHONDONTWRITEBYTECODE="1"),
        text=True, capture_output=True, timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: staged A5 -> B1/B2 -> multi-chunk C3 lease spans iterator" in result.stdout
    assert "Runtime.cancel and Runtime.close release lease for revocation" in result.stdout

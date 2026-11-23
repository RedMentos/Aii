"""Core regression for two-phase audio consent revocation.

The staged Runtime uses synthetic PCM16 and fake B1/B2/C3 runners. It does not
open a microphone or prove native Android execution.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_two_phase_revocation_cancels_c3_and_legacy_subscription_falls_back(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "audio_two_phase_stage", CODE / "scripts/stage_integrated_candidate.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("V14 staged Runtime builder unavailable")
    stage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage)
    destination = tmp_path / "audio-two-phase"
    manifest = stage.stage(CODE, destination)
    assert manifest["status"] == "SHADOW_REVIEW_ONLY"

    script = r'''
import json
import math
import struct
from contextlib import contextmanager
from pathlib import Path
import sys
import threading
import time
from unittest.mock import Mock

from v13.common import Cancelled
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
        self.subscriptions = []
        self.guard_entered = threading.Event()
        self.request_dispatched = threading.Event()
        self.completion_dispatched = threading.Event()
        self.request_was_while_guard_held = False
        self.completion_after_guard_released = False
        self.scope_id = None

    def check(self, source_id, receipt):
        if not self.lock.acquire(timeout=0.05):
            raise RuntimeError("consent_check re-entered a non-reentrant provider lock")
        try:
            return self.active and source_id == "mic-test-1" and receipt == "opaque-local-receipt"
        finally:
            self.lock.release()

    @contextmanager
    def guard(self, source_id, receipt):
        self.lock.acquire()
        self.guard_entered.set()
        try:
            yield self.active and source_id == "mic-test-1" and receipt == "opaque-local-receipt"
        finally:
            self.lock.release()

    def subscribe(self, source_id, receipt, scope_id, on_revoke_requested, on_revoked):
        if (source_id != "mic-test-1" or receipt != "opaque-local-receipt"
                or type(scope_id) is not str or not scope_id
                or not callable(on_revoke_requested) or not callable(on_revoked)):
            raise ValueError("two-phase subscription scope mismatch")
        self.scope_id = scope_id
        entry = (on_revoke_requested, on_revoked)
        with self.callback_lock:
            self.subscriptions.append(entry)
        def unsubscribe():
            with self.callback_lock:
                if entry in self.subscriptions:
                    self.subscriptions.remove(entry)
        return unsubscribe

    def legacy_subscribe(self, source_id, receipt, callback):
        raise AssertionError("legacy completion-only provider must not be invoked")

    def revoke(self):
        with self.callback_lock:
            subscriptions = list(self.subscriptions)
        self.request_was_while_guard_held = self.lock.locked()
        for request, _ in subscriptions:
            request()
        self.request_dispatched.set()
        with self.lock:
            self.active = False
        self.completion_after_guard_released = not self.lock.locked()
        for _, completion in subscriptions:
            completion()
        self.completion_dispatched.set()


def make_window(provider, legacy=False):
    return {
        "pcm16": tone(),
        "sample_rate": 16000,
        "start_ms": 0,
        "source_id": "mic-test-1",
        "consent_receipt": "opaque-local-receipt",
        "consent_check": provider.check,
        "consent_guard": provider.guard,
        "consent_revocation_subscribe": provider.legacy_subscribe if legacy else provider.subscribe,
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
    runtime._route = Mock(return_value=("both", {"source": "SYNTHETIC_AUDIO_REVOKE"}))
    runtime.learner.output_delta = Mock(return_value=None)


class Runner:
    def __init__(self, role, seen, entered=None, first_chunk=None, cancel_observed=None):
        self.role = role
        self.seen = seen
        self.entered = entered
        self.first_chunk = first_chunk
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
            yield "First response chunk."
            if self.first_chunk is not None:
                self.first_chunk.set()
            if self.cancel_observed is None:
                yield "Text-only response."
                return
            stop_at = time.monotonic() + 8
            while not cancel.is_set():
                if time.monotonic() >= stop_at:
                    raise TimeoutError("provider request did not cancel C3")
                time.sleep(0.005)
            self.cancel_observed.set()
            raise Cancelled("audio consent revocation requested")


def wait_idle(runtime, seconds=30):
    deadline = time.monotonic() + seconds
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runtime.idle(), "Runtime did not settle"


question = (
    "Compare details with planning. The rent is 120 euros. "
    "The plan preserves a long-term reserve."
)

# Positive: request callback fires before the provider waits for the guard;
# C3 observes Runtime cancellation, releases the lease, then completion tombstones.
home = Path(sys.argv[1]) / "request"
runtime = Runtime(home)
provider = Provider()
entered = threading.Event()
first_chunk = threading.Event()
cancel_observed = threading.Event()
seen = {}
revoker = None
try:
    configure(runtime)
    runners = {
        role: Runner(
            role, seen,
            entered if role == "C3_LANGUAGE" else None,
            first_chunk if role == "C3_LANGUAGE" else None,
            cancel_observed if role == "C3_LANGUAGE" else None,
        )
        for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
    }
    runtime.pool.get = Mock(side_effect=lambda role: runners[role])
    runtime.submit(question, audio_window=make_window(provider))
    assert entered.wait(30), "Runtime did not reach C3"
    assert first_chunk.wait(5), "C3 did not emit its first chunk"
    revoker = threading.Thread(target=provider.revoke, daemon=True)
    revoker.start()
    assert provider.request_dispatched.wait(3), "pre-lock request callback did not fire"
    assert provider.request_was_while_guard_held is True, "request callback was not sent while Runtime held the guard"
    assert cancel_observed.wait(5), "C3 did not observe the request cancellation"
    wait_idle(runtime)
    assert provider.completion_dispatched.wait(5), "completion callback did not run after lease release"
    revoker.join(timeout=5)
    assert not revoker.is_alive(), "provider revocation remained blocked after C3 cancellation"
    assert provider.completion_after_guard_released is True
    assert provider.scope_id == runtime.store.generation_id
    assert runtime.last_answer()["status"] == "CANCELLED"
    assert "RAW_EAR_ACOUSTIC" in json.dumps(seen["C3_LANGUAGE"], ensure_ascii=False)
    assert "audio_context" in json.dumps(seen["B1_DETAIL"], ensure_ascii=False)
    assert "audio_context" in json.dumps(seen["B2_GIST"], ensure_ascii=False)
    rows = runtime.store.rows(
        "SELECT deleted FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT'"
    )
    assert rows and all(row["deleted"] == 1 for row in rows), rows
    saved = last_context(runtime.store, runtime.session)
    assert saved and saved["messages"] is None and saved["preview"] == ""
    assert provider.subscriptions == []
    assert runtime.store.integrity(True) == []
finally:
    if revoker is not None:
        revoker.join(timeout=1)
    runtime.close()

# Negative: a legacy completion-only provider is rejected and text remains usable.
home = Path(sys.argv[1]) / "legacy"
runtime = Runtime(home)
provider = Provider()
seen = {}
try:
    configure(runtime)
    runners = {role: Runner(role, seen) for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")}
    runtime.pool.get = Mock(side_effect=lambda role: runners[role])
    runtime.submit(question, audio_window=make_window(provider, legacy=True))
    wait_idle(runtime)
    assert runtime.last_answer()["status"] == "FINAL"
    assert "RAW_EAR_ACOUSTIC" not in json.dumps(seen["C3_LANGUAGE"], ensure_ascii=False)
    assert "audio_context" not in json.dumps(seen["B1_DETAIL"], ensure_ascii=False)
    assert "audio_context" not in json.dumps(seen["B2_GIST"], ensure_ascii=False)
    assert runtime.store.rows(
        "SELECT id FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT' AND deleted=0"
    ) == []
    assert provider.guard_entered.is_set() is False
    assert provider.subscriptions == []
finally:
    runtime.close()

# Persisted packet/source/blob cleanup after a completed turn.
for shared in (False, True):
    home = Path(sys.argv[1]) / ("shared-blob" if shared else "unshared-blob")
    runtime = Runtime(home)
    provider = Provider()
    seen = {}
    try:
        configure(runtime)
        runners = {role: Runner(role, seen) for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")}
        runtime.pool.get = Mock(side_effect=lambda role: runners[role])
        event_id = runtime.submit(question, audio_window=make_window(provider))
        wait_idle(runtime)
        assert runtime.last_answer()["status"] == "FINAL"
        packets_before = runtime.store.rows("SELECT id,payload FROM packets")
        assert any("mic-test-1" in row["payload"] for row in packets_before), "audio PerceptPacket missing before revoke"
        source_rows = runtime.store.rows(
            "SELECT id,hash,deleted FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT'"
        )
        assert len(source_rows) == 1 and source_rows[0]["deleted"] == 0, source_rows
        derived = source_rows[0]
        blob_path = Path(runtime.store.home) / "data/blobs" / derived["hash"]
        assert blob_path.is_file(), "derived audio blob missing before revoke"
        if shared:
            context = runtime._audio_revocation_contexts[event_id]
            body = runtime.store.read_source(context["summary_source_ref"])
            duplicate = runtime.store.source(body, "AUDIO_SHARED_TEST")
            assert duplicate["sha256"] == derived["hash"]
        provider.revoke()
        source_after = runtime.store.one(
            "SELECT hash,deleted FROM sources WHERE id=?", (derived["id"],)
        )
        assert source_after and source_after["deleted"] == 1
        packets_after = runtime.store.rows("SELECT id,payload FROM packets")
        assert not any("mic-test-1" in row["payload"] for row in packets_after), (
            "revocation left a source-bound acoustic PerceptPacket in SQLite"
        )
        active_refs = runtime.store.one(
            "SELECT COUNT(*) AS n FROM sources WHERE hash=? AND deleted=0",
            (derived["hash"],),
        )["n"]
        if shared:
            assert active_refs >= 1 and blob_path.is_file(), "shared audio blob was incorrectly removed"
        else:
            assert active_refs == 0 and not blob_path.exists(), "unshared audio blob survived revocation"
        saved = last_context(runtime.store, runtime.session)
        assert saved and saved["messages"] is None and saved["preview"] == ""
        assert provider.subscriptions == []
        assert runtime.store.integrity(True) == []
    finally:
        runtime.close()

print("PASS: two-phase revoke cancels C3, deletes packets/context, preserves shared blobs, and rejects legacy providers")
'''
    result = subprocess.run(
        [sys.executable, "-c", script, str(tmp_path / "private-home")],
        cwd=destination,
        env=dict(os.environ, PYTHONPATH=str(destination), PYTHONDONTWRITEBYTECODE="1"),
        text=True, capture_output=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: two-phase revoke cancels C3" in result.stdout

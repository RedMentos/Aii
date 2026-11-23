"""Staged Runtime E2E for shared RAW EAR consent lease and revocation cleanup.

All PCM and model outputs here are synthetic. No microphone, native model or
Android permission is exercised.
"""
import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_audio_context_store_blob_cleanup_imports_path():
    source_path = CODE / "scripts/integrated_audio_context_candidate_20261121.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    generated_module = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id == "result"
            and isinstance(target.slice, ast.Constant)
            and target.slice.value == "v13/audio_context_store.py"
            for target in node.targets
        ):
            continue
        generated_module = ast.literal_eval(node.value)
        break
    assert isinstance(generated_module, bytes), "audio context Store source was not generated"
    assert b"Path(store.home)" in generated_module, "blob cleanup no longer uses a scoped Store path"
    assert b"from pathlib import Path" in generated_module, (
        "generated audio_context_store.py uses Path without importing it"
    )


def test_staged_audio_lease_full_lifecycle_qa(tmp_path):
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
from unittest.mock import Mock, patch

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

    def subscribe(self, source_id, receipt, *callbacks):
        if source_id != "mic-test-1" or receipt != "opaque-local-receipt":
            raise ValueError("subscription scope mismatch")
        if len(callbacks) == 1:
            scope_id, request_cancel, cleanup = None, None, callbacks[0]
        elif len(callbacks) == 3:
            scope_id, request_cancel, cleanup = callbacks
        else:
            raise TypeError("subscription must provide scope, request and completion callbacks")
        entry = (scope_id, request_cancel, cleanup)
        with self.callback_lock:
            self.callbacks.append(entry)

        def unsubscribe():
            with self.callback_lock:
                if entry in self.callbacks:
                    self.callbacks.remove(entry)
        return unsubscribe

    def revoke(self):
        with self.callback_lock:
            callbacks = list(self.callbacks)
            self.callbacks.clear()
        # Request cancellation before waiting on the Runtime-held provider guard.
        for _, request_cancel, _ in callbacks:
            if callable(request_cancel):
                request_cancel()
        with self.lock:
            self.active = False
        # Completion cleanup runs after the provider guard and registry lock.
        for _, _, cleanup in callbacks:
            cleanup()


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


class TwoPhaseProvider(Provider):
    """Provider contract: request cancellation before waiting for the held lease.

    The legacy one-callback form is accepted only to make the missing phase
    observable in the regression. The reviewed contract supplies both
    on_revoke_requested and on_revoked callbacks.
    """
    def __init__(self, active=True):
        super().__init__(active=active)
        self.request_started = threading.Event()
        self.request_count = 0
        self.cleanup_lock_states = []

    def subscribe(self, source_id, receipt, *callbacks):
        if source_id != "mic-test-1" or receipt != "opaque-local-receipt":
            raise ValueError("subscription scope mismatch")
        if len(callbacks) == 1:
            scope_id, request_cancel, cleanup = None, None, callbacks[0]
        elif len(callbacks) == 2:
            scope_id, request_cancel, cleanup = None, callbacks[0], callbacks[1]
        elif len(callbacks) == 3:
            scope_id, request_cancel, cleanup = callbacks
        else:
            raise TypeError("two-phase subscription requires scope, request and cleanup callbacks")
        if cleanup is None or not callable(cleanup):
            raise TypeError("post-revocation cleanup callback required")
        if request_cancel is not None and not callable(request_cancel):
            raise TypeError("pre-lock cancellation callback must be callable")
        self.scope_id = scope_id
        entry = (scope_id, request_cancel, cleanup)
        with self.callback_lock:
            self.callbacks.append(entry)

        def unsubscribe():
            with self.callback_lock:
                if entry in self.callbacks:
                    self.callbacks.remove(entry)
        return unsubscribe

    def revoke(self):
        with self.callback_lock:
            callbacks = list(self.callbacks)
            self.callbacks.clear()
        # Phase 1: do not acquire the provider lock; the Runtime lease may hold it.
        for _, request_cancel, _ in callbacks:
            if callable(request_cancel):
                self.request_count += 1
                request_cancel()
        self.request_started.set()
        # Phase 2: wait for the Runtime lease to exit, then revoke authority.
        with self.lock:
            self.active = False
        # Cleanup must run only after the provider guard is released.
        for _, _, cleanup in callbacks:
            self.cleanup_lock_states.append(self.lock.locked())
            cleanup()


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
                            raise Cancelled("provider consent revoked")
                        if time.monotonic() >= cancel_deadline:
                            raise TimeoutError("test did not observe Runtime.cancel")
                    if cancel is not None and cancel.is_set():
                        self.cancel_observed.set()
                        raise Cancelled("provider consent revoked")
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

    assert provider.lock.locked(), "provider guard was not held during C3 streaming"
    assert not finished.is_set(), "C3 iterator unexpectedly finished before its second chunk"
    release.set()

    deadline = time.monotonic() + 30
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runtime.idle(), "synthetic audio Runtime turn did not settle"
    assert finished.is_set(), "Runtime returned without exhausting the full C3 iterator"
    assert runtime.last_answer()["status"] == "FINAL"
    # Revoke only after the complete stream has released its provider lease.
    provider.revoke()
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

    runtime.cancel()
    assert cancel_observed.wait(5), "C3 runner did not observe Runtime.cancel"
    assert finished.wait(5), "C3 iterator did not exit after Runtime.cancel"

    deadline = time.monotonic() + 30
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runtime.idle(), "cancelled audio Runtime turn did not settle"
    provider.revoke()
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


closer = threading.Thread(target=runtime.close, daemon=True)
closer.start()
assert cancel_observed.wait(5), "Runtime.close did not cancel the blocked C3 iterator"
assert finished.wait(5), "C3 iterator did not exit during Runtime.close"
closer.join(timeout=10)
assert not closer.is_alive(), "Runtime.close hung while releasing the audio lease"
assert runtime.closed is True
assert getattr(runtime, "_audio_contexts", {}) == {}
assert getattr(runtime, "_audio_revocation_contexts", {}) == {}
with provider.callback_lock:
    assert provider.callbacks == []
provider.revoke()

failures = []

# Scenario 5: the provider's pre-lock request callback cancels the active C3
# stream, allowing the lease to release before the provider obtains its guard.
home = Path(sys.argv[1]) / "prelock-revocation"
runtime = Runtime(home)
provider = TwoPhaseProvider()
entered = threading.Event()
first_chunk = threading.Event()
finished = threading.Event()
cancel_observed = threading.Event()
release = threading.Event()
revoke_started = threading.Event()
revoke_finished = threading.Event()
seen = {}
revoker = None
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
    assert entered.wait(30), "two-phase revoke test did not reach C3"
    assert first_chunk.wait(5), "two-phase revoke test did not stream first chunk"

    def revoke():
        revoke_started.set()
        provider.revoke()
        revoke_finished.set()

    revoker = threading.Thread(target=revoke, daemon=True)
    revoker.start()
    assert revoke_started.wait(5)
    assert provider.request_started.wait(5), "provider did not issue pre-lock revoke request"
    assert cancel_observed.wait(5), (
        "provider revoke request did not cancel the matching C3 turn before waiting for its guard"
    )
    assert finished.wait(5), "C3 iterator did not exit after pre-lock cancellation"
    deadline = time.monotonic() + 30
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runtime.idle(), "pre-lock-cancelled audio turn did not settle"
    assert revoke_finished.wait(5), "provider revoke did not complete after C3 released its lease"
    revoker.join(timeout=5)
    assert runtime.last_answer()["status"] == "CANCELLED"
    assert provider.request_count == 1
    assert provider.cleanup_lock_states == [False], provider.cleanup_lock_states
    rows = runtime.store.rows(
        "SELECT deleted FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT'"
    )
    assert rows and all(row["deleted"] == 1 for row in rows), rows
    saved_context = last_context(runtime.store, runtime.session)
    assert saved_context and saved_context["messages"] is None and saved_context["preview"] == ""
    # Revocation must not poison subsequent ordinary text chat.
    runtime.pool.get = Mock(side_effect=lambda role: Runner(role, seen))
    runtime.submit(question)
    deadline = time.monotonic() + 30
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runtime.idle() and runtime.last_answer()["status"] == "FINAL"
    text_context = last_context(runtime.store, runtime.session)
    assert text_context and text_context["messages"] is not None
    assert "RAW_EAR_ACOUSTIC" not in json.dumps(text_context["messages"], ensure_ascii=False)
except AssertionError as exc:
    failures.append("two-phase provider revocation: " + str(exc))
finally:
    release.set()
    runtime.close()
    if revoker is not None:
        revoker.join(timeout=5)

# Scenario 6: without a revocation subscription the audio side-channel is
# dropped, while the ordinary text request still completes normally.
home = Path(sys.argv[1]) / "missing-revocation-subscription"
runtime = Runtime(home)
provider = Provider()
seen = {}
try:
    configure(runtime)
    runners = {
        role: Runner(role, seen)
        for role in ("B1_DETAIL", "B2_GIST", "C3_LANGUAGE")
    }
    runtime.pool.get = Mock(side_effect=lambda role: runners[role])
    window = make_window(provider)
    window.pop("consent_revocation_subscribe")
    runtime.submit(question, audio_window=window)
    deadline = time.monotonic() + 30
    while not runtime.idle() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert runtime.idle() and runtime.last_answer()["status"] == "FINAL"
    assert "audio_context" not in json.dumps(seen["B1_DETAIL"], ensure_ascii=False), "audio context was admitted without a revocation subscription"
    assert "audio_context" not in json.dumps(seen["B2_GIST"], ensure_ascii=False), "GIST received audio without a revocation subscription"
    assert "RAW_EAR_ACOUSTIC" not in json.dumps(seen["C3_LANGUAGE"], ensure_ascii=False), "C3 received audio without a revocation subscription"
    assert runtime.store.rows(
        "SELECT id FROM sources WHERE id='mic-test-1' OR kind='AUDIO_ACOUSTIC_CONTEXT'"
    ) == []
except AssertionError as exc:
    failures.append("missing subscription fail-closed: " + str(exc))
finally:
    runtime.close()

# Scenario 7: Runtime.close must cancel and wait for the active C3 iterator
# before tombstoning any derived acoustic source or closing the Store.
home = Path(sys.argv[1]) / "close-cleanup-order"
runtime = Runtime(home)
provider = Provider()
entered = threading.Event()
first_chunk = threading.Event()
finished = threading.Event()
cancel_observed = threading.Event()
release = threading.Event()
seen = {}
from v13 import audio_context_store
original_revoke = audio_context_store._revoke
cleanup_observations = []


def observed_revoke(rt, event_id, context):
    cleanup_observations.append((rt.cancel_event.is_set(), finished.is_set()))
    return original_revoke(rt, event_id, context)


audio_context_store._revoke = observed_revoke
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
    assert entered.wait(30), "close-order test did not reach C3"
    assert first_chunk.wait(5), "close-order test did not stream first chunk"
    closer = threading.Thread(target=runtime.close, daemon=True)
    closer.start()
    assert cancel_observed.wait(5), "Runtime.close did not cancel the active C3 iterator"
    assert finished.wait(5), "C3 iterator did not exit before close cleanup"
    closer.join(timeout=10)
    assert not closer.is_alive(), "Runtime.close hung while waiting for C3"
    assert cleanup_observations and all(
        cancelled and iterator_finished for cancelled, iterator_finished in cleanup_observations
    ), cleanup_observations
    assert runtime.closed is True
except AssertionError as exc:
    failures.append("close cleanup ordering: " + str(exc))
finally:
    release.set()
    runtime.close()
    audio_context_store._revoke = original_revoke

# Scenario 8: revocation removes the derived acoustic packet and any
# unshared context blob, not merely a source tombstone/cache entry.
home = Path(sys.argv[1]) / "revoked-packet-and-blob"
runtime = Runtime(home)
provider = TwoPhaseProvider()
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
    assert runtime.idle() and runtime.last_answer()["status"] == "FINAL"
    packets_before = runtime.store.rows("SELECT id,payload FROM packets")
    audio_packets = [row for row in packets_before if "mic-test-1" in row["payload"]]
    assert audio_packets, "synthetic audio PerceptPacket was not persisted under the lease"
    source_rows = runtime.store.rows(
        "SELECT id,hash,deleted FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT'"
    )
    assert len(source_rows) == 1 and source_rows[0]["deleted"] == 0, source_rows
    blob_path = Path(runtime.store.home) / "data/blobs" / source_rows[0]["hash"]
    assert blob_path.is_file(), "derived acoustic context blob was not present before revocation"
    provider.revoke()
    source_after = runtime.store.one(
        "SELECT hash,deleted FROM sources WHERE id=?",
        (source_rows[0]["id"],),
    )
    assert source_after and source_after["deleted"] == 1
    packets_after = runtime.store.rows("SELECT id,payload FROM packets")
    cleanup_failures = []
    if any("mic-test-1" in row["payload"] for row in packets_after):
        cleanup_failures.append("revocation left a source-bound acoustic PerceptPacket in SQLite")
    active_refs = runtime.store.one(
        "SELECT COUNT(*) AS n FROM sources WHERE hash=? AND deleted=0",
        (source_after["hash"],),
    )["n"]
    if active_refs == 0 and blob_path.exists():
        cleanup_failures.append("revocation left an unshared acoustic-context blob on disk")
    if cleanup_failures:
        raise AssertionError("; ".join(cleanup_failures))
except AssertionError as exc:
    failures.append("packet/blob revocation: " + str(exc))
finally:
    runtime.close()

# Scenario 9: a blob shared by another live source must survive revocation
# of this one audio context; packet cleanup is independent of blob sharing.
home = Path(sys.argv[1]) / "shared-context-blob"
runtime = Runtime(home)
provider = TwoPhaseProvider()
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
    assert runtime.idle() and runtime.last_answer()["status"] == "FINAL"
    context_row = runtime.store.one(
        "SELECT id,hash,deleted FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT'"
    )
    assert context_row and context_row["deleted"] == 0
    blob_path = Path(runtime.store.home) / "data/blobs" / context_row["hash"]
    content = blob_path.read_text(encoding="utf-8")
    shared_ref = runtime.store.source(content, "SHARED_CONTROL")
    assert shared_ref["sha256"] == context_row["hash"]
    assert runtime.store.one(
        "SELECT COUNT(*) AS n FROM sources WHERE hash=? AND deleted=0",
        (context_row["hash"],),
    )["n"] == 2
    provider.revoke()
    assert runtime.store.one(
        "SELECT deleted FROM sources WHERE id=?",
        (context_row["id"],),
    )["deleted"] == 1
    assert runtime.store.one(
        "SELECT deleted FROM sources WHERE id=?",
        (shared_ref["source_id"],),
    )["deleted"] == 0
    assert runtime.store.one(
        "SELECT COUNT(*) AS n FROM sources WHERE hash=? AND deleted=0",
        (context_row["hash"],),
    )["n"] == 1
    assert blob_path.is_file(), "revocation removed a blob still referenced by a live source"
except AssertionError as exc:
    failures.append("shared-blob retention: " + str(exc))
finally:
    runtime.close()

# Scenario 10: a new Store.source reference must not slip between audio
# revocation's refcount transaction and its final blob unlink.
home = Path(sys.argv[1]) / "concurrent-shared-audio-blob"
runtime = Runtime(home)
provider = TwoPhaseProvider()
seen = {}
errors = []
published = []
revoker = None
publisher = None
allow_unlink = threading.Event()
original_mutex = runtime.store.mutex
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
    assert runtime.idle() and runtime.last_answer()["status"] == "FINAL"

    context_row = runtime.store.one(
        "SELECT id,hash,deleted FROM sources WHERE kind='AUDIO_ACOUSTIC_CONTEXT'"
    )
    assert context_row and context_row["deleted"] == 0
    blob_path = Path(runtime.store.home) / "data/blobs" / context_row["hash"]
    content = blob_path.read_text(encoding="utf-8")
    entered_unlink = threading.Event()
    publisher_lock_attempted = threading.Event()
    publisher_blob_check = threading.Event()
    import v13.source_lifecycle_candidate as source_lifecycle
    original_unlink = Path.unlink
    original_exists = Path.exists
    original_verify = source_lifecycle.verify_or_create_blob

    class TrackingRLock:
        """Expose the generic publisher's attempt to enter the shared Store lock."""

        def acquire(self, *args, **kwargs):
            if threading.current_thread().name == "audio-source-publisher":
                publisher_lock_attempted.set()
            return original_mutex.acquire(*args, **kwargs)

        def release(self):
            return original_mutex.release()

        def __enter__(self):
            self.acquire()
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.release()
            return False

    def gated_unlink(path, *args, **kwargs):
        if path == blob_path:
            entered_unlink.set()
            if not allow_unlink.wait(5):
                raise TimeoutError("test did not release audio blob unlink")
        return original_unlink(path, *args, **kwargs)

    def observed_exists(path, *args, **kwargs):
        if path == blob_path and threading.current_thread().name == "audio-source-publisher":
            publisher_blob_check.set()
        return original_exists(path, *args, **kwargs)

    def observed_verify(path, data, expected_hash):
        if Path(path) == blob_path and threading.current_thread().name == "audio-source-publisher":
            publisher_blob_check.set()
        return original_verify(path, data, expected_hash)

    def revoke_audio():
        try:
            provider.revoke()
        except BaseException as exc:
            errors.append(("revoke", exc))

    def publish_shared_source():
        try:
            published.append(runtime.store.source(content, "SHARED_CONCURRENT_CONTROL"))
        except BaseException as exc:
            errors.append(("publish", exc))

    runtime.store.mutex = TrackingRLock()
    with patch.object(Path, "exists", observed_exists), \
         patch.object(source_lifecycle, "verify_or_create_blob", observed_verify), \
         patch.object(Path, "unlink", gated_unlink):
        revoker = threading.Thread(target=revoke_audio, name="audio-source-revoker")
        revoker.start()
        assert entered_unlink.wait(2), "audio revocation did not reach final blob unlink"
        publisher = threading.Thread(target=publish_shared_source, name="audio-source-publisher")
        publisher.start()

        # The publisher must request the same Store lock before it checks
        # the digest path. While revocation is paused at unlink, it cannot
        # observe the soon-to-be-removed blob or commit a new source row.
        assert publisher_lock_attempted.wait(2), "generic publisher did not request the Store lock"
        assert not publisher_blob_check.is_set(), (
            "Store.source checked the blob before acquiring the shared Store lock"
        )
        assert not published, "generic source publication completed inside the revocation critical section"

        allow_unlink.set()
        assert publisher_blob_check.wait(2), "generic publisher did not resume after revocation"
        revoker.join(2)
        publisher.join(2)
        assert not revoker.is_alive(), "audio revocation worker did not finish"
        assert not publisher.is_alive(), "shared-source publisher did not finish"


    assert not errors, f"concurrent audio source operations raised: {errors!r}"
    assert len(published) == 1
    assert runtime.store.one(
        "SELECT deleted FROM sources WHERE id=?", (published[0]["source_id"],)
    )["deleted"] == 0
    try:
        assert runtime.store.read_source(published[0]) == content
    except FileNotFoundError as exc:
        raise AssertionError(
            "Store.source committed a live shared source after audio revocation unlinked its blob"
        ) from exc
except AssertionError as exc:
    failures.append("audio shared-source publication/revocation race: " + str(exc))
finally:
    allow_unlink.set()
    if revoker is not None and revoker.is_alive():
        revoker.join(2)
    if publisher is not None and publisher.is_alive():
        publisher.join(2)
    runtime.store.mutex = original_mutex
    runtime.close()

assert not failures, "; ".join(failures)
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

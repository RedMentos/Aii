import contextlib
import hashlib
import json
import os
import struct
import sys
import time
import threading
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13 import native_receiver_matrix_runtime as matrix_runtime
from v13.native_receiver_utility import CONDITIONS


def _source(text, source_id):
    return {
        "source_id": source_id,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "modality": "text",
        "char_start": 0,
        "char_end": len(text),
    }


def _event(event_id, generation, source_ref):
    return {
        "event_id": event_id,
        "brain_generation_id": generation,
        "authority": "AUTHORITATIVE",
        "kind": "USER_TEXT",
        "source_ref": dict(source_ref),
    }


class FakeStore:
    def __init__(self, events, sources):
        self.events = {
            event_id: {"packet": json.dumps(packet), "session_id": "session-1"}
            for event_id, packet in events.items()
        }
        self.sources = dict(sources)
        self.states = {}

    def one(self, sql, params=()):
        event_id = params[0]
        return self.events.get(event_id)

    def read_source(self, source_ref):
        return self.sources[source_ref["source_id"]]

    def state(self, key, default=None):
        item = self.states.get(key)
        if item is None:
            return default, 0
        return json.loads(json.dumps(item[0])), item[1]

    def set_state(self, key, payload, expected=None):
        current = self.states.get(key)
        version = current[1] if current else 0
        if expected is not None and expected != version:
            raise ValueError("stale state write")
        self.states[key] = (json.loads(json.dumps(payload)), version + 1)
        return version + 1


class FakeMatrix:
    def __init__(self, receipt):
        self._receipt = json.loads(json.dumps(receipt))
        self._consumed = False
        self._closed = False
        self._build_one = lambda condition: {"condition": condition}

    @property
    def receipt(self):
        return json.loads(json.dumps(self._receipt))

    def iter_inputs(self, *, approval=None, approval_validator=None):
        if self._closed or self._consumed:
            raise ValueError("closed/consumed")
        if approval_validator(approval, self._receipt["approval_binding_sha256"]) is not True:
            raise ValueError("approval rejected")
        self._consumed = True
        return iter(())

    def close(self):
        self._closed = True
        self._consumed = True
        self._build_one = None


class FakeRuntime:
    def __init__(self, store, home):
        self.store = store
        self.home = str(home)
        self.session = "session-1"
        self.cancel_event = threading.Event()
        self.current = None
        self.paused = False

    def require_idle(self):
        if self.current is not None:
            raise ValueError("runtime busy")

    def last_answer(self):
        return {"status": "FINAL", "event_id": "event-main"}


def _fixture(tmp_path):
    texts = {
        "src-main": "What is 2+2?",
        "src-ood": "Explain photosynthesis.",
        "src-entity": "What is 3+4?",
    }
    refs = {key: _source(value, key) for key, value in texts.items()}
    events = {
        "event-main": _event("event-main", "generation-1", refs["src-main"]),
        "event-ood": _event("event-ood", "generation-1", refs["src-ood"]),
        "event-entity": _event("event-entity", "generation-1", refs["src-entity"]),
    }
    store = FakeStore(events, texts)
    runtime = FakeRuntime(store, tmp_path)
    receiver = {
        "role": "C3_LANGUAGE",
        "tap_id": "tap-c3",
        "model_revision": "c3-rev-1",
        "tokenizer_revision": "tokenizer-rev-1",
        "model_sha256": "1" * 64,
    }
    sender = {
        "role": "B1_DETAIL",
        "tap_id": "tap-b1",
        "model_revision": "b1-rev-1",
        "tokenizer_revision": "tokenizer-rev-1",
        "model_sha256": "2" * 64,
    }
    source_refs = [
        {key: refs["src-main"][key] for key in ("source_id", "sha256")},
        {key: refs["src-ood"][key] for key in ("source_id", "sha256")},
        {key: refs["src-entity"][key] for key in ("source_id", "sha256")},
    ]
    conditions = []
    for name in CONDITIONS:
        if name == "OOD":
            event_id, generation, source = "event-ood", "generation-1", source_refs[1]
        elif name == "ENTITY_SUBSTITUTION":
            event_id, generation, source = "event-entity", "generation-1", source_refs[2]
        else:
            event_id, generation, source = "event-main", "generation-1", source_refs[0]
        conditions.append({
            "condition": name,
            "message_event_id": event_id,
            "message_generation_id": generation,
            "message_source_ref": source,
        })
    target_ids = [7, 8]
    target_sha = hashlib.sha256(struct.pack("<ii", *target_ids)).hexdigest()
    receipt = {
        "schema": "v14.native-receiver-condition-matrix/1",
        "status": "MATRIX_READY_NOT_SCORED",
        "task_group_id": "task-main",
        "task_family": "ARITHMETIC",
        "session_id": "session-1",
        "source_ref": source_refs[0],
        "source_bindings": sorted(source_refs, key=lambda item: (item["source_id"], item["sha256"])),
        "receiver": receiver,
        "task_event_id": "event-main",
        "task_generation_id": "generation-1",
        "target_token_ids_sha256": target_sha,
        "target_token_count": len(target_ids),
        "context_sha256": "3" * 64,
        "adapter_sha256": "4" * 64,
        "conditions": conditions,
        "condition_count": len(CONDITIONS),
        "required_approval_kind": "NATIVE_RECEIVER_MATRIX",
        "approval_binding_kind": "UNSIGNED_DIGEST_ONLY",
        "approval_granted": False,
        "persisted": False,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "approval_binding_sha256": "5" * 64,
        "matrix_sha256": "6" * 64,
    }
    pair_record = {
        "status": "PAIRED_DIAGNOSTIC",
        "persisted": False,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "record_sha256": "7" * 64,
        "session_id": "session-1",
        "event_id": "event-main",
        "brain_generation_id": "generation-1",
        "source_ref": refs["src-main"],
        "sender": sender,
        "receiver": receiver,
    }
    return runtime, FakeMatrix(receipt), target_ids, pair_record, events, texts, sender, receiver


def _patch_core(monkeypatch, runtime, sender, receiver):
    from v13 import native_probe_approval as approval

    monkeypatch.setattr(approval, "_require_local_tty", lambda: None)
    monkeypatch.setattr(
        approval,
        "_current_event",
        lambda r: (r.store_event_main, r.source_ref_main),
        raising=False,
    )
    runtime.store_event_main = _event(
        "event-main", "generation-1",
        _source(runtime.store.sources["src-main"], "src-main"),
    )
    runtime.source_ref_main = runtime.store_event_main["source_ref"]

    models_root = Path(runtime.home) / "models"
    models_root.mkdir(parents=True, exist_ok=True)
    model_paths = {}
    model_identities = {}
    expected_by_role = {sender["role"]: sender, receiver["role"]: receiver}
    for role in expected_by_role:
        path = models_root / (role + ".gguf")
        path.write_bytes(b"x" * 4096)
        st = os.stat(path, follow_symlinks=False)
        model_paths[role] = path
        model_identities[role] = [
            st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns,
        ]
    runtime.models = SimpleNamespace(
        revision=lambda role: expected_by_role[role]["model_revision"],
        path_for=lambda role: model_paths[role],
    )

    def model_binding(_runtime, role):
        expected = expected_by_role[role]
        path = model_paths[role]
        return {
            "revision": expected["model_revision"],
            "sha256": expected["model_sha256"],
            "canonical_path": str(path.resolve()),
            "file_identity": model_identities[role],
        }

    monkeypatch.setattr(approval, "_model_binding", model_binding)
    runtime._native_probe_approval_runtime_nonce = "f" * 32
    monkeypatch.setattr(
        approval, "_runtime_nonce",
        lambda current: getattr(current, "_native_probe_approval_runtime_nonce", "f" * 32),
    )
    monkeypatch.setattr(approval, "_resource_preflight", lambda *_: {"status": "PASS"})
    monkeypatch.setattr(approval, "_require_runtime_probe_lease", lambda *_: None)

    @contextlib.contextmanager
    def lease(_runtime):
        yield "lease-token"

    monkeypatch.setattr(approval, "runtime_probe_lease", lease)
    monkeypatch.setattr(matrix_runtime, "platform_tag", lambda: "linux-x86_64")


def _stage(monkeypatch, tmp_path):
    runtime, matrix, target_ids, pair, events, texts, sender, receiver = _fixture(tmp_path)
    _patch_core(monkeypatch, runtime, sender, receiver)
    from v13 import native_tokenwise_pairing
    monkeypatch.setattr(native_tokenwise_pairing, "_validate_native_pair_record", lambda value: dict(value))
    staged = matrix_runtime.stage_native_receiver_matrix(runtime, matrix, target_ids, pair)
    return runtime, matrix, target_ids, pair, events, texts, sender, receiver, staged


def test_stage_binds_three_sources_target_tokens_and_pair_record_without_persisting_vectors(monkeypatch, tmp_path):
    runtime, matrix, target_ids, pair, _events, _texts, _sender, _receiver, staged = _stage(monkeypatch, tmp_path)
    assert staged["status"] == "STAGED_NOT_APPROVED"
    assert staged["condition_count"] == 8
    assert staged["source_count"] == 3
    assert runtime._native_receiver_matrix_target_token_ids == tuple(target_ids)
    assert runtime.store.states == {}
    assert runtime._native_receiver_condition_matrix is matrix


def test_stage_rejects_target_token_digest_mismatch(monkeypatch, tmp_path):
    runtime, matrix, _ids, pair, _events, _texts, sender, receiver = _fixture(tmp_path)
    _patch_core(monkeypatch, runtime, sender, receiver)
    from v13 import native_tokenwise_pairing
    monkeypatch.setattr(native_tokenwise_pairing, "_validate_native_pair_record", lambda value: dict(value))
    with pytest.raises(ValueError, match="target token IDs"):
        matrix_runtime.stage_native_receiver_matrix(runtime, matrix, [99], pair)


def test_stage_rejects_pair_record_from_another_event(monkeypatch, tmp_path):
    runtime, matrix, target_ids, pair, _events, _texts, sender, receiver = _fixture(tmp_path)
    _patch_core(monkeypatch, runtime, sender, receiver)
    from v13 import native_tokenwise_pairing
    monkeypatch.setattr(native_tokenwise_pairing, "_validate_native_pair_record", lambda value: dict(value))
    pair["event_id"] = "event-ood"
    with pytest.raises(ValueError, match="pair record"):
        matrix_runtime.stage_native_receiver_matrix(runtime, matrix, target_ids, pair)


def test_matrix_run_requires_one_shot_local_approval_and_uses_real_bridge_contract(monkeypatch, tmp_path):
    runtime, matrix, _ids, _pair, _events, _texts, _sender, _receiver, _staged = _stage(monkeypatch, tmp_path)
    with pytest.raises(PermissionError, match="no local one-shot approval"):
        matrix_runtime._run(runtime)

    armed = matrix_runtime._arm(runtime)
    assert armed["status"] == "ARMED_ONE_SHOT"
    calls = []

    def fake_bridge(runtime_arg, matrix_arg, **kwargs):
        receipt = matrix_arg.receipt
        yielded = list(matrix_arg.iter_inputs(
            approval=kwargs["approval"],
            approval_validator=kwargs["approval_validator"],
        ))
        assert yielded == []
        assert kwargs["source_validator"](receipt, "BEFORE_NATIVE") is True
        assert kwargs["source_validator"](receipt, "AFTER_NATIVE") is True
        calls.append(kwargs)
        return {
            "status": "SCORED_DIAGNOSTIC",
            "condition_count": 8,
            "environment": kwargs["target_environment"],
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        }

    module = types.ModuleType("v13.native_receiver_task_matrix_bridge")
    module.score_and_record_native_receiver_condition_matrix = fake_bridge
    monkeypatch.setitem(sys.modules, "v13.native_receiver_task_matrix_bridge", module)

    result = matrix_runtime._run(runtime)
    assert result["status"] == "SCORED_DIAGNOSTIC"
    assert result["environment"] == "LOCAL_LINUX"
    assert len(calls) == 1
    assert calls[0]["threads"] == 1
    assert calls[0]["target_environment"] == "LOCAL_LINUX"
    assert calls[0]["include_hybrid_state_roundtrip"] is False
    state, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert state["status"] == "COMPLETED"
    assert runtime._native_receiver_condition_matrix is None
    assert matrix._closed is True



def test_hybrid_state_roundtrip_requires_explicit_arm_and_is_bound_to_native_run(monkeypatch, tmp_path):
    runtime, matrix, _ids, _pair, _events, _texts, _sender, _receiver, _staged = _stage(monkeypatch, tmp_path)
    armed = matrix_runtime._arm(runtime, include_hybrid_state_roundtrip=True)
    assert armed["include_hybrid_state_roundtrip"] is True
    calls = []

    def fake_bridge(runtime_arg, matrix_arg, **kwargs):
        receipt = matrix_arg.receipt
        assert kwargs["include_hybrid_state_roundtrip"] is True
        assert kwargs["approval_validator"](kwargs["approval"], receipt["approval_binding_sha256"]) is True
        assert kwargs["source_validator"](receipt, "BEFORE_NATIVE") is True
        assert kwargs["source_validator"](receipt, "AFTER_NATIVE") is True
        calls.append(kwargs)
        return {
            "status": "SCORED_DIAGNOSTIC",
            "condition_count": 8,
            "environment": kwargs["target_environment"],
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        }

    module = types.ModuleType("v13.native_receiver_task_matrix_bridge")
    module.score_and_record_native_receiver_condition_matrix = fake_bridge
    monkeypatch.setitem(sys.modules, "v13.native_receiver_task_matrix_bridge", module)
    result = matrix_runtime._run(runtime)
    assert result["status"] == "SCORED_DIAGNOSTIC"
    assert calls[0]["include_hybrid_state_roundtrip"] is True
    assert matrix._closed is True


def test_hybrid_state_roundtrip_model_gate_uses_actual_selected_model_key():
    runtime = types.SimpleNamespace(models=types.SimpleNamespace(b2_control="two_body"))
    assert matrix_runtime._hybrid_state_receiver_supported(runtime, "B1_DETAIL")
    assert matrix_runtime._hybrid_state_receiver_supported(runtime, "C3_LANGUAGE")
    assert not matrix_runtime._hybrid_state_receiver_supported(runtime, "B2_GIST")
    runtime.models.b2_control = "same_model"
    assert matrix_runtime._hybrid_state_receiver_supported(runtime, "B2_GIST")

def test_source_drift_between_arming_and_native_run_revokes_the_attempt(monkeypatch, tmp_path):
    runtime, matrix, _ids, _pair, _events, texts, _sender, _receiver, _staged = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    texts["src-ood"] = "changed after staging"
    runtime.store.sources["src-ood"] = texts["src-ood"]

    called = []
    module = types.ModuleType("v13.native_receiver_task_matrix_bridge")

    def fake_bridge(runtime_arg, matrix_arg, **kwargs):
        called.append(True)
        kwargs["source_validator"](matrix_arg.receipt, "BEFORE_NATIVE")
        return {}

    module.score_and_record_native_receiver_condition_matrix = fake_bridge
    monkeypatch.setitem(sys.modules, "v13.native_receiver_task_matrix_bridge", module)
    with pytest.raises(PermissionError, match="source bytes changed"):
        matrix_runtime._run(runtime)
    assert called == []
    state, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert state["status"] == "FAILED_REVOKED"
    assert runtime._native_receiver_condition_matrix is None
    assert matrix._closed is True


def test_android_native_run_is_blocked_without_a_verified_device_receipt(monkeypatch, tmp_path):
    runtime, matrix, _ids, _pair, _events, _texts, _sender, _receiver, _staged = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    monkeypatch.setattr(matrix_runtime, "platform_tag", lambda: "android-aarch64")
    with pytest.raises(PermissionError, match="verified private device-execution receipt"):
        matrix_runtime._run(runtime)
    state, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert state["status"] == "PENDING"
    assert runtime._native_receiver_condition_matrix is matrix


def test_revoke_and_clear_are_separate_explicit_operations(monkeypatch, tmp_path):
    runtime, matrix, _ids, _pair, _events, _texts, _sender, _receiver, _staged = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    revoked = matrix_runtime._revoke(runtime)
    assert revoked["status"] == "REVOKED"
    cleared = matrix_runtime._clear(runtime)
    assert cleared["status"] == "CLEARED"
    assert cleared["matrix_was_staged"] is True
    assert runtime._native_receiver_condition_matrix is None


def test_live_pending_matrix_approval_still_requires_explicit_revoke_before_clear(monkeypatch, tmp_path):
    runtime, matrix, *_rest = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    with pytest.raises(PermissionError, match="live pending matrix approval"):
        matrix_runtime._clear(runtime)
    state, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert state["status"] == "PENDING"
    assert matrix._closed is False


def test_matrix_status_reports_restart_staleness_without_mutating_the_pending_record(monkeypatch, tmp_path):
    runtime, _matrix, *_rest = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    before, version = runtime.store.state(matrix_runtime.KEY, None)
    runtime._native_probe_approval_runtime_nonce = "e" * 32

    status = matrix_runtime._status(runtime)
    assert status["approval_status"] == "PENDING"
    assert status["approval_liveness"] == "STALE_RUNTIME"
    after, after_version = runtime.store.state(matrix_runtime.KEY, None)
    assert after == before
    assert after_version == version
    with pytest.raises(PermissionError, match="fresh matching"):
        matrix_runtime._run(runtime)


def test_matrix_clear_invalidates_restart_stale_approval_and_closes_matrix(monkeypatch, tmp_path):
    runtime, matrix, *_rest = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    runtime._native_probe_approval_runtime_nonce = "e" * 32

    cleared = matrix_runtime._clear(runtime)
    assert cleared["status"] == "CLEARED"
    state, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert state["status"] == "STALE_RUNTIME"
    assert state["invalidated_reason"] == "STALE_RUNTIME"
    assert matrix._closed is True
    assert runtime._native_receiver_condition_matrix is None


def test_matrix_clear_invalidates_expired_approval(monkeypatch, tmp_path):
    runtime, matrix, *_rest = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    state, version = runtime.store.state(matrix_runtime.KEY, None)
    now = time.time()
    state["issued_at"] = now - matrix_runtime.TTL_SECONDS - 1
    state["expires_at"] = now - 1
    runtime.store.set_state(matrix_runtime.KEY, state, expected=version)

    status = matrix_runtime._status(runtime)
    assert status["approval_liveness"] == "EXPIRED"
    with pytest.raises(PermissionError, match="fresh matching"):
        matrix_runtime._run(runtime)
    matrix_runtime._clear(runtime)
    final, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert final["status"] == "EXPIRED"
    assert matrix._closed is True


def test_matrix_approval_cannot_extend_beyond_its_issued_ttl(monkeypatch, tmp_path):
    runtime, matrix, *_rest = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    state, version = runtime.store.state(matrix_runtime.KEY, None)
    now = time.time()
    state["issued_at"] = now - 10
    state["expires_at"] = now + matrix_runtime.TTL_SECONDS * 10
    runtime.store.set_state(matrix_runtime.KEY, state, expected=version)

    status = matrix_runtime._status(runtime)
    assert status["approval_liveness"] == "INVALID_EXPIRY"
    with pytest.raises(PermissionError, match="fresh matching"):
        matrix_runtime._run(runtime)
    matrix_runtime._clear(runtime)
    final, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert final["status"] == "INVALID_EXPIRY"
    assert matrix._closed is True


@pytest.mark.parametrize("bad_expiry", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_matrix_approval_expiry_fails_closed(monkeypatch, tmp_path, bad_expiry):
    runtime, matrix, *_rest = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    state, version = runtime.store.state(matrix_runtime.KEY, None)
    state["expires_at"] = bad_expiry
    runtime.store.set_state(matrix_runtime.KEY, state, expected=version)

    status = matrix_runtime._status(runtime)
    assert status["approval_liveness"] == "INVALID_EXPIRY"
    assert status["approval_expires_at"] is None
    with pytest.raises(PermissionError, match="fresh matching"):
        matrix_runtime._run(runtime)
    matrix_runtime._clear(runtime)
    final, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert final["status"] == "INVALID_EXPIRY"
    assert matrix._closed is True


def test_matrix_status_reports_model_route_staleness_without_mutating_pending_record(monkeypatch, tmp_path):
    runtime, _matrix, _ids, _pair, _events, _texts, sender, _receiver, _staged = _stage(
        monkeypatch, tmp_path
    )
    matrix_runtime._arm(runtime)
    from v13 import native_probe_approval as approval

    original_revision = runtime.models.revision
    runtime.models.revision = lambda role: (
        "changed-revision" if role == sender["role"] else original_revision(role)
    )
    monkeypatch.setattr(
        approval, "_model_binding",
        lambda *_args: (_ for _ in ()).throw(AssertionError("status must not rehash a GGUF")),
    )
    before, version = runtime.store.state(matrix_runtime.KEY, None)

    status = matrix_runtime._status(runtime)

    assert status["approval_status"] == "PENDING"
    assert status["approval_liveness"] == "STALE_MODEL"
    after, after_version = runtime.store.state(matrix_runtime.KEY, None)
    assert after == before
    assert after_version == version


def test_matrix_clear_invalidates_changed_model_file_identity(monkeypatch, tmp_path):
    runtime, matrix, _ids, _pair, _events, _texts, sender, _receiver, _staged = _stage(
        monkeypatch, tmp_path
    )
    matrix_runtime._arm(runtime)
    model_path = runtime.models.path_for(sender["role"])
    with model_path.open("r+b") as stream:
        stream.seek(0)
        stream.write(b"y")

    cleared = matrix_runtime._clear(runtime)

    assert cleared["status"] == "CLEARED"
    state, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert state["status"] == "STALE_MODEL"
    assert state["invalidated_reason"] == "STALE_MODEL"
    assert matrix._closed is True
    assert runtime._native_receiver_condition_matrix is None


def test_stage_replaces_restart_stale_pending_approval_without_reusing_it(monkeypatch, tmp_path):
    runtime, matrix, target_ids, pair, *_rest = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    receipt = matrix.receipt
    matrix.close()
    runtime._native_receiver_condition_matrix = None
    runtime._native_receiver_matrix_target_token_ids = None
    runtime._native_receiver_matrix_pair_record = None
    runtime._native_receiver_matrix_staged_at = None
    runtime._native_probe_approval_runtime_nonce = "e" * 32

    replacement = type(matrix)(receipt)
    staged = matrix_runtime.stage_native_receiver_matrix(runtime, replacement, target_ids, pair)
    assert staged["status"] == "STAGED_NOT_APPROVED"
    state, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert state["status"] == "STALE_RUNTIME"
    assert runtime._native_receiver_condition_matrix is replacement


def test_operator_dispatch_is_local_command_scoped(monkeypatch, tmp_path):
    runtime, _matrix, _ids, _pair, _events, _texts, _sender, _receiver, _staged = _stage(monkeypatch, tmp_path)
    status = json.loads(matrix_runtime.operator_command(runtime, ["matrix-status"]))
    assert status["status"] == "READY"
    with pytest.raises(ValueError, match="matrix-status"):
        matrix_runtime.operator_command(runtime, ["matrix-run"])

def test_callosum_routes_matrix_status_through_the_real_operator_consumer(monkeypatch, tmp_path):
    runtime, matrix, _ids, _pair, _events, _texts, _sender, _receiver, _staged = _stage(
        monkeypatch, tmp_path
    )
    # Matrix commands are a local diagnostic path and must not need the unrelated
    # numerical B3 calibration dependency merely to import Callosum.
    monkeypatch.setitem(sys.modules, "v13.b3degrade", types.ModuleType("v13.b3degrade"))
    monkeypatch.delitem(sys.modules, "v13.callosum", raising=False)
    from v13 import callosum

    with open(callosum.__file__, encoding="utf-8") as source_file:
        source = source_file.read()
    assert "matrix-status" in source
    assert "native-tokenwise-probe" in source

    status = json.loads(callosum.operator_command(runtime, ["matrix-status"]))
    assert status["status"] == "READY"
    assert runtime.store.states == {}

    with pytest.raises(PermissionError, match="no local one-shot approval"):
        callosum.operator_command(runtime, ["matrix-run", "--confirm"])
    assert matrix._closed is False


def _load_perception_matrix_test_helpers():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).with_name("test_native_receiver_condition_matrix.py")
    spec = importlib.util.spec_from_file_location("v14_perception_matrix_test_helpers", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Perception matrix test helpers are not loadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_callosum_runtime_producer_builds_real_perception_matrix_and_scores_through_bridge(
    monkeypatch, tmp_path
):
    """Exercise Perception builder -> Callosum -> Runtime -> one-shot bridge.

    The native probe is deliberately stubbed as SYNTHETIC; this test proves
    producer/consumer wiring and source/approval contracts, not GGUF execution.
    """
    perception = _load_perception_matrix_test_helpers()
    task, _main, baseline, _candidate, old_ood, old_entity = perception.inputs()

    main = perception.record(
        "src-main", task["source_text"], [11, 22, 33],
        [[0.11, 0.22], [0.37, 0.44], [0.55, 0.66]],
    )
    ood_text = "Birds can fly."
    ood = perception.record(
        "src-ood", ood_text, [41, 42, 43],
        [[0.2, 0.1], [0.4, 0.3], [0.6, 0.5]],
    )
    entity_text = "The dog sat."
    entity = perception.record(
        "src-entity", entity_text, [11, 44, 33],
        [[0.11, 0.22], [0.77, 0.88], [0.55, 0.66]],
    )
    for record, event_id in (
        (main, "event-main"), (ood, "event-ood"), (entity, "event-entity")
    ):
        record["event_id"] = event_id
        record["brain_generation_id"] = "generation-1"
        record["source_ref"]["modality"] = "text"

    candidate = perception.packet(
        main, [[0.11, 0.22], [0.37, 0.44], [0.55, 0.66]]
    )
    ood_control = dict(old_ood)
    ood_control["record"] = ood
    ood_control["candidate_packet"] = perception.packet(
        ood, [[0.2, 0.1], [0.4, 0.3], [0.6, 0.5]]
    )
    entity_control = dict(old_entity)
    entity_control["record"] = entity
    entity_control["source_text"] = entity_text
    entity_control["entity_byte_spans"] = [[4, 7]]
    entity_control["candidate_packet"] = perception.packet(
        entity, [[0.11, 0.22], [0.77, 0.88], [0.55, 0.66]]
    )

    texts = {
        "src-main": task["source_text"],
        "src-ood": ood_text,
        "src-entity": entity_text,
    }
    events = {
        "event-main": _event("event-main", "generation-1", main["source_ref"]),
        "event-ood": _event("event-ood", "generation-1", ood["source_ref"]),
        "event-entity": _event("event-entity", "generation-1", entity["source_ref"]),
    }
    runtime = FakeRuntime(FakeStore(events, texts), tmp_path)
    _patch_core(monkeypatch, runtime, main["sender"], main["receiver"])

    from v13 import native_tokenwise_pairing
    monkeypatch.setattr(
        native_tokenwise_pairing, "_validate_native_pair_record", lambda value: dict(value)
    )
    monkeypatch.setitem(sys.modules, "v13.b3degrade", types.ModuleType("v13.b3degrade"))
    monkeypatch.delitem(sys.modules, "v13.callosum", raising=False)
    from v13 import callosum

    staged = callosum.controller(runtime).stage_native_receiver_matrix(
        task=task,
        pair_record=main,
        baseline_packet=baseline,
        candidate_packet=candidate,
        ood_control=ood_control,
        entity_control=entity_control,
    )
    assert staged["status"] == "STAGED_NOT_APPROVED"
    assert staged["condition_count"] == 8
    assert staged["source_count"] == 3

    calls = perception._fake_matrix_probe(monkeypatch)
    import v13.native_receiver_task_matrix_bridge as bridge
    real_bridge = bridge.score_and_record_native_receiver_condition_matrix

    def synthetic_bridge(runtime_arg, matrix_arg, **kwargs):
        kwargs["target_environment"] = "SYNTHETIC"
        kwargs["binary_path"] = None
        return real_bridge(runtime_arg, matrix_arg, **kwargs)

    monkeypatch.setattr(
        bridge, "score_and_record_native_receiver_condition_matrix", synthetic_bridge
    )
    armed = json.loads(callosum.operator_command(runtime, ["matrix-arm", "--confirm"]))
    assert armed["status"] == "ARMED_ONE_SHOT"
    result = json.loads(callosum.operator_command(runtime, ["matrix-run", "--confirm"]))

    assert result["status"] == "TASK_GROUP_SCORED"
    assert result["execution_kind"] == "SYNTHETIC_FIXTURE"
    assert result["environment"] == "SYNTHETIC"
    assert result["generated_answer_correctness_proven"] is False
    assert result["kv_snapshot_count"] == 8
    assert result["kv_snapshot_scope"] == "ONE_ATTENTION_LAYER_ONE_SEQUENCE"
    assert result["kv_snapshot_stable"] is True
    assert result["training_authority"] == result["native_receiver_authority"] == 0
    assert len(calls) == 1
    assert [item["condition"] for item in calls[0]["condition_inputs"]] == list(CONDITIONS)
    assert calls[0]["condition_inputs"][0]["vectors"] == []
    assert calls[0]["condition_inputs"][0]["position_ids"] == []
    assert runtime._native_receiver_condition_matrix is None


def _tamper_matrix_approval_record(record, field, sender_role):
    if field == "task_group_id":
        record[field] = "tampered-task-group"
    elif field == "source_bindings":
        record[field] = []
    elif field == "sender_role":
        record[field] = "B2_GIST" if sender_role != "B2_GIST" else "B1_DETAIL"
    elif field == "receiver_role":
        record[field] = "INVALID_RECEIVER"
    elif field == "models":
        record[field][sender_role]["revision"] = "tampered-model-revision"
    else:
        raise AssertionError("unknown tamper field")


@pytest.mark.parametrize(
    "field",
    ["task_group_id", "source_bindings", "sender_role", "receiver_role", "models"],
)
def test_matrix_run_rejects_persisted_approval_binding_tampering(
    monkeypatch, tmp_path, field
):
    runtime, matrix, *_rest, sender, _receiver, _staged = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    state, version = runtime.store.state(matrix_runtime.KEY, None)
    _tamper_matrix_approval_record(state, field, sender["role"])
    runtime.store.set_state(matrix_runtime.KEY, state, expected=version)

    native_calls = []
    module = types.ModuleType("v13.native_receiver_task_matrix_bridge")
    module.score_and_record_native_receiver_condition_matrix = (
        lambda *_args, **_kwargs: native_calls.append(True)
    )
    monkeypatch.setitem(sys.modules, "v13.native_receiver_task_matrix_bridge", module)

    with pytest.raises(PermissionError, match="fresh matching"):
        matrix_runtime._run(runtime)

    assert native_calls == []
    persisted, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert persisted["status"] == "FAILED_REVOKED"
    assert matrix._closed is True
    assert runtime._native_receiver_condition_matrix is None


@pytest.mark.parametrize(
    "field",
    ["task_group_id", "source_bindings", "sender_role", "receiver_role", "models"],
)
def test_matrix_consume_rejects_persisted_approval_binding_tampering(
    monkeypatch, tmp_path, field
):
    runtime, matrix, *_rest, sender, _receiver, _staged = _stage(monkeypatch, tmp_path)
    matrix_runtime._arm(runtime)
    state, version = runtime.store.state(matrix_runtime.KEY, None)
    _tamper_matrix_approval_record(state, field, sender["role"])
    runtime.store.set_state(matrix_runtime.KEY, state, expected=version)

    from v13 import native_probe_approval as approval
    monkeypatch.setattr(approval, "_require_runtime_probe_lease", lambda *_args: None)
    persisted, _ = runtime.store.state(matrix_runtime.KEY, None)

    with pytest.raises(PermissionError, match="approval is not live"):
        matrix_runtime._consume_approval(
            runtime,
            persisted["nonce"],
            matrix.receipt["approval_binding_sha256"],
            matrix.receipt,
            object(),
        )

    after, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert after["status"] == "PENDING"


@pytest.mark.parametrize(
    "expires_at",
    [float("nan"), float("inf"), float("-inf"), None, True, "invalid", 0],
)
def test_matrix_arm_requires_explicit_revoke_of_any_pending_single_probe_approval(
    monkeypatch, tmp_path, expires_at
):
    runtime, _matrix, *_rest = _stage(monkeypatch, tmp_path)
    from v13 import native_probe_approval as approval

    state, version = runtime.store.state(approval.KEY, None)
    runtime.store.set_state(
        approval.KEY,
        {"schema": approval.SCHEMA, "status": "PENDING", "expires_at": expires_at},
        expected=version,
    )

    with pytest.raises(PermissionError, match="separate native probe approval"):
        matrix_runtime._arm(runtime)

    existing, _ = runtime.store.state(approval.KEY, None)
    assert existing["status"] == "PENDING"
    matrix_approval, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert matrix_approval is None

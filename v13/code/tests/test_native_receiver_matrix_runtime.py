import contextlib
import hashlib
import json
import struct
import sys
import threading
import types

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

    def model_binding(_runtime, role):
        expected = sender if role == sender["role"] else receiver
        return {
            "revision": expected["model_revision"],
            "sha256": expected["model_sha256"],
            "canonical_path": str(_runtime.home) + "/models/" + role + ".gguf",
            "file_identity": [1, 2, 4096, 3, 4],
        }

    monkeypatch.setattr(approval, "_model_binding", model_binding)
    monkeypatch.setattr(approval, "_runtime_nonce", lambda _runtime: "f" * 32)
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
    state, _ = runtime.store.state(matrix_runtime.KEY, None)
    assert state["status"] == "COMPLETED"
    assert runtime._native_receiver_condition_matrix is None
    assert matrix._closed is True


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
    assert status["native_receiver_effects"]["status"] == "EMPTY"
    assert runtime.store.states == {}

    with pytest.raises(PermissionError, match="no local one-shot approval"):
        callosum.operator_command(runtime, ["matrix-run", "--confirm"])
    assert matrix._closed is False



def _native_effect_cohort(*, semantic_use_proven=False, duplicate_input_groups_checked=1, evidence_class="LOCAL_LINUX"):
    kv = {
        "status": "READ_ONLY_SAMPLE_ONLY",
        "task_group_count": 1,
        "snapshot_count": 8,
        "candidate_differs_from_no_message_count": 1,
        "candidate_differs_from_exact_message_count": 1,
        "distinct_from_no_message_task_groups_by_condition": {
            condition: 1 for condition in CONDITIONS
        },
        "duplicate_input_groups_checked": duplicate_input_groups_checked,
        "same_input_consistency_passed": True,
        "scope": "ONE_ATTENTION_LAYER_ONE_SEQUENCE",
        "semantic_use_proven": semantic_use_proven,
        "generated_answer_correctness_proven": False,
        "production_route": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "persisted": False,
    }
    information = {
        "schema": "v14.native-receiver-information-use-audit/1",
        "status": "INSUFFICIENT_HOLDOUT",
        "semantic_use_proven": False,
        "generated_answer_correctness_proven": False,
        "production_route": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "persisted": False,
    }
    return {
        "status": "INSUFFICIENT_HOLDOUT",
        "evidence_class": evidence_class,
        "task_group_count": 1,
        "kv_snapshot_effect": kv,
        "information_use_audit": information,
    }


def test_core_consumer_surfaces_read_only_kv_and_information_use_effects(monkeypatch):
    from v13 import native_receiver_task_score as task_score

    cohort = _native_effect_cohort()
    monkeypatch.setattr(task_score, "task_score_status", lambda runtime: {
        "status": "COHORT_READY",
        "task_group_count": 1,
        "complete_task_group_count": 1,
        "incomplete_task_group_count": 0,
    })
    monkeypatch.setattr(task_score, "evaluate_task_score_cohort", lambda runtime: cohort)

    effects = matrix_runtime._native_receiver_effects(object(), strict=True)
    assert effects["evidence_class"] == "LOCAL_LINUX"
    assert effects["kv_snapshot_effect"]["status"] == "READ_ONLY_SAMPLE_ONLY"
    assert effects["kv_snapshot_effect"]["snapshot_count"] == 8
    assert effects["kv_snapshot_effect"]["same_input_consistency_observed"] is True
    assert effects["kv_snapshot_effect"]["same_input_consistency_status"] == "CHECKED_PASS"
    assert effects["kv_snapshot_effect"]["distinct_from_no_message_task_groups_by_condition"] == {
        condition: 1 for condition in CONDITIONS
    }
    assert effects["information_use_audit"]["status"] == "INSUFFICIENT_HOLDOUT"
    assert effects["semantic_use_proven"] is False
    assert effects["generated_answer_correctness_proven"] is False
    assert effects["production_route"] is False
    assert effects["training_authority"] == effects["native_receiver_authority"] == 0
    assert effects["persisted"] is False


def test_core_consumer_does_not_claim_duplicate_consistency_when_no_inputs_repeat(monkeypatch):
    from v13 import native_receiver_task_score as task_score

    cohort = _native_effect_cohort(duplicate_input_groups_checked=0)
    monkeypatch.setattr(task_score, "task_score_status", lambda runtime: {
        "status": "COHORT_READY",
        "task_group_count": 1,
        "complete_task_group_count": 1,
        "incomplete_task_group_count": 0,
    })
    monkeypatch.setattr(task_score, "evaluate_task_score_cohort", lambda runtime: cohort)

    effects = matrix_runtime._native_receiver_effects(object(), strict=True)
    kv = effects["kv_snapshot_effect"]
    assert kv["duplicate_input_groups_checked"] == 0
    assert kv["same_input_consistency_passed"] is None
    assert kv["same_input_consistency_observed"] is False
    assert kv["same_input_consistency_status"] == "NOT_TESTED_NO_DUPLICATE_INPUTS"


def test_core_consumer_rejects_negative_duplicate_input_count(monkeypatch):
    from v13 import native_receiver_task_score as task_score

    cohort = _native_effect_cohort(duplicate_input_groups_checked=-1)
    monkeypatch.setattr(task_score, "task_score_status", lambda runtime: {
        "status": "COHORT_READY",
        "task_group_count": 1,
        "complete_task_group_count": 1,
        "incomplete_task_group_count": 0,
    })
    monkeypatch.setattr(task_score, "evaluate_task_score_cohort", lambda runtime: cohort)

    with pytest.raises(matrix_runtime.NativeReceiverMatrixRuntimeError, match="structural contract"):
        matrix_runtime._native_receiver_effects(object(), strict=True)


def test_core_consumer_downgrades_synthetic_kv_snapshots_to_unavailable(monkeypatch):
    from v13 import native_receiver_task_score as task_score

    cohort = _native_effect_cohort(evidence_class="SYNTHETIC")
    monkeypatch.setattr(task_score, "task_score_status", lambda runtime: {
        "status": "COHORT_READY",
        "task_group_count": 1,
        "complete_task_group_count": 1,
        "incomplete_task_group_count": 0,
    })
    monkeypatch.setattr(task_score, "evaluate_task_score_cohort", lambda runtime: cohort)

    effects = matrix_runtime._native_receiver_effects(object(), strict=True)
    kv = effects["kv_snapshot_effect"]
    assert effects["evidence_class"] == "SYNTHETIC"
    assert kv["status"] == "UNAVAILABLE"
    assert kv["reason"] == "SYNTHETIC_FIXTURE_ONLY"
    assert kv["source_status"] == "READ_ONLY_SAMPLE_ONLY"
    assert kv["persisted"] is False
    assert kv["native_receiver_authority"] == 0


def test_core_consumer_rejects_kv_summary_that_claims_semantic_use(monkeypatch):
    from v13 import native_receiver_task_score as task_score

    cohort = _native_effect_cohort(semantic_use_proven=True)
    monkeypatch.setattr(task_score, "task_score_status", lambda runtime: {
        "status": "COHORT_READY",
        "task_group_count": 1,
        "complete_task_group_count": 1,
        "incomplete_task_group_count": 0,
    })
    monkeypatch.setattr(task_score, "evaluate_task_score_cohort", lambda runtime: cohort)

    with pytest.raises(matrix_runtime.NativeReceiverMatrixRuntimeError, match="forbidden authority or proof"):
        matrix_runtime._native_receiver_effects(object(), strict=True)


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
    assert result["training_authority"] == result["native_receiver_authority"] == 0
    effects = result["native_receiver_effects"]
    assert effects["evidence_class"] == "SYNTHETIC"
    assert effects["kv_snapshot_effect"]["status"] == "UNAVAILABLE"
    assert effects["information_use_audit"]["semantic_use_proven"] is False
    assert effects["production_route"] is False
    assert len(calls) == 1
    assert [item["condition"] for item in calls[0]["condition_inputs"]] == list(CONDITIONS)
    assert calls[0]["condition_inputs"][0]["vectors"] == []
    assert calls[0]["condition_inputs"][0]["position_ids"] == []
    assert runtime._native_receiver_condition_matrix is None

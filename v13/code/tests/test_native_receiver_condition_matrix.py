import hashlib
import struct

import pytest

from v13.native_receiver_condition_matrix import (
    NativeReceiverConditionMatrixError,
    build_native_receiver_condition_matrix,
)
from v13.native_receiver_utility import (
    CONDITIONS,
    SCORE_METHOD,
    NativeReceiverUtilityError,
    validate_native_receiver_kv_snapshot,
)
from v13.native_latent_receiver import PINNED_LLAMA_REVISION
from v13.native_receiver_task_matrix_bridge import (
    NativeReceiverTaskMatrixBridgeError,
    score_and_record_native_receiver_condition_matrix,
)
from v13.native_receiver_task_score import task_score_status


def sha(value):
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def f32sha(rows):
    flat = [float(x) for row in rows for x in row]
    return sha(struct.pack("<" + "f" * len(flat), *flat))


def record(source_id, text, token_ids, candidate_rows, receiver_rows=None):
    receiver_rows = receiver_rows or [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    spans = [[0, 3], [4, 7], [8, 12]]
    src = {"source_id": source_id, "sha256": sha(text), "char_start": 0, "char_end": len(text)}
    sender = {"role": "B1_DETAIL", "tap_id": "lfm2.result_norm.final.v1",
              "activation_space": "FINAL_RMSNORM_PREFILL_F32",
              "capture_method": "LLAMA_SERVER_EMBEDDINGS_FINAL_RMSNORM_ONLY",
              "embedding_dim": 2, "runner_revision": "b10964",
              "model_revision": "b1-r1", "model_sha256": "c" * 64, "tokenizer_revision": "b1-tok-r1"}
    receiver = {"role": "C3_LANGUAGE", "tap_id": "C3_NATIVE_INPUT_EMBEDDING",
                "model_revision": "c3-r1", "model_sha256": "b" * 64,
                "tokenizer_revision": "c3-tok-r1", "embedding_dim": 2,
                "token_ids": list(token_ids), "token_spans": spans}
    pairs = [{"pair_id": f"{source_id}-{i}", "token_position": i,
              "receiver_vector": list(row), "sender_vector": [0.01, 0.02],
              "source_id": source_id, "source_sha256": src["sha256"], "session_id": "session-1",
              "alignment_method": "UTF8_BYTE_PIECE_OVERLAP_V1", "alignment_coverage": 1.0}
             for i, row in enumerate(receiver_rows)]
    return {"schema": "v14.native-tokenwise-pairing/2", "status": "PAIRED_DIAGNOSTIC",
            "source_ref": src, "session_id": "session-1", "event_id": "event-" + source_id,
            "brain_generation_id": "generation-" + source_id, "sender": sender, "receiver": receiver,
            "pairs": pairs, "record_sha256": sha("record-" + source_id),
            "persisted": False, "production_route": False, "semantic_use_proven": False,
            "training_authority": 0, "native_receiver_authority": 0}


def packet(rec, rows, adapter_sha="a" * 64):
    return {"schema": "v14.native-tokenwise-anchor-residual-input/1", "source_ref": rec["source_ref"],
            "session_id": rec["session_id"], "record_sha256": rec["record_sha256"],
            "adapter_sha256": adapter_sha, "sender_role": rec["sender"]["role"],
            "sender_tap_id": rec["sender"]["tap_id"], "sender_model_revision": rec["sender"]["model_revision"],
            "sender_model_sha256": rec["sender"]["model_sha256"], "sender_tokenizer_revision": rec["sender"]["tokenizer_revision"],
            "receiver_role": rec["receiver"]["role"], "receiver_tap_id": rec["receiver"]["tap_id"],
            "receiver_model_revision": rec["receiver"]["model_revision"], "receiver_model_sha256": rec["receiver"]["model_sha256"],
            "receiver_tokenizer_revision": rec["receiver"]["tokenizer_revision"],
            "input_strategy": "ANCHOR_PLUS_CAPPED_RESIDUAL_V1", "anchor_rows_preserved_as_base": True,
            "input_rows": len(rows), "input_dim": len(rows[0]), "position_ids": list(range(len(rows))),
            "position_mode": "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL", "input_sha256": f32sha(rows),
            "vectors": [list(row) for row in rows], "persisted": False, "production_route": False,
            "semantic_use_proven": False, "training_authority": 0, "native_receiver_authority": 0}


def inputs():
    main = record("source-main", "The cat sat.", [11, 22, 33], [[0.11, 0.22], [0.37, 0.44], [0.55, 0.66]])
    ood = record("source-ood", "Birds can fly.", [41, 42, 43], [[0.2, 0.1], [0.4, 0.3], [0.6, 0.5]])
    entity = record("source-entity", "The dog sat.", [11, 44, 33], [[0.11, 0.22], [0.77, 0.88], [0.55, 0.66]])
    baseline_rows = [[0.91, 0.82]]
    baseline = {"token_kind": "BOS", "token_id": 1, "rows": baseline_rows,
                "receiver_model_sha256": "b" * 64, "receiver_tap_id": "C3_NATIVE_INPUT_EMBEDDING",
                "tokenizer_revision": "c3-tok-r1", "extractor_receipt_sha256": "e" * 64,
                "input_sha256": f32sha(baseline_rows)}
    task = {"task_group_id": "task-main", "task_family": "ARITHMETIC", "session_id": "session-1",
            "source_text": "The cat sat.", "target_token_ids": [101, 102]}
    ood_control = {"task_group_id": "task-ood", "task_family": "RELATION", "session_id": "session-1",
                  "record": ood, "candidate_packet": packet(ood, [[0.2, 0.1], [0.4, 0.3], [0.6, 0.5]])}
    entity_control = {"task_group_id": "task-entity", "task_family": "ARITHMETIC", "session_id": "session-1",
                      "record": entity, "source_text": "The dog sat.", "entity_byte_spans": [[4, 7]],
                      "candidate_packet": packet(entity, [[0.11, 0.22], [0.77, 0.88], [0.55, 0.66]])}
    return task, main, baseline, packet(main, [[0.11, 0.22], [0.37, 0.44], [0.55, 0.66]]), ood_control, entity_control


def build_with_task(monkeypatch, **overrides):
    import v13.native_tokenwise_pairing as pairing
    monkeypatch.setattr(pairing, "_validate_native_pair_record", lambda value: dict(value))
    task, main, baseline, candidate, ood, entity = inputs()
    args = {"task": task, "pair_record": main, "baseline_packet": baseline,
            "candidate_packet": candidate, "ood_control": ood, "entity_control": entity}
    args.update(overrides)
    return task, build_native_receiver_condition_matrix(**args)


def build(monkeypatch, **overrides):
    return build_with_task(monkeypatch, **overrides)[1]


def approved(matrix):
    digest = matrix.receipt["approval_binding_sha256"]
    return list(matrix.iter_inputs(approval=digest, approval_validator=lambda token, expected: token == expected))


def test_builds_eight_bound_conditions_and_streams_after_one_shot_approval(monkeypatch):
    matrix = build(monkeypatch)
    receipt = matrix.receipt
    assert receipt["status"] == "MATRIX_READY_NOT_SCORED"
    assert receipt["condition_count"] == 8
    assert tuple(x["condition"] for x in receipt["conditions"]) == CONDITIONS
    assert receipt["required_approval_kind"] == "NATIVE_RECEIVER_MATRIX"
    assert receipt["approval_binding_kind"] == "UNSIGNED_DIGEST_ONLY"
    assert receipt["approval_granted"] is False and receipt["native_receiver_authority"] == 0
    assert receipt["training_authority"] == 0 and receipt["persisted"] is False
    assert len(receipt["source_bindings"]) == 3
    assert "target_token_ids" not in receipt and "The cat sat." not in repr(receipt)
    result = approved(matrix)
    assert [x["condition"] for x in result] == list(CONDITIONS)
    assert result[0]["message_source_ref"] is None
    assert result[0]["input_rows"] == 0
    assert result[0]["input_dim"] == 2
    assert result[0]["vectors"] == [] and result[0]["position_ids"] == []
    assert result[0]["input_sha256"] == sha(b"")
    assert result[0]["control_recipe"] == "NO_MESSAGE_NO_INJECTED_ROWS_V1"
    assert result[1]["adapter_sha256"] is None
    assert result[2]["adapter_sha256"] == "a" * 64
    assert result[6]["message_source_ref"]["source_id"] == "source-ood"
    assert result[7]["message_source_ref"]["source_id"] == "source-entity"
    assert all(x["position_ids"] == list(range(x["input_rows"])) for x in result)
    with pytest.raises(NativeReceiverConditionMatrixError, match="already consumed"):
        approved(matrix)


def test_entity_control_changes_only_declared_token_row(monkeypatch):
    result = {x["condition"]: x for x in approved(build(monkeypatch))}
    base, entity = result["LATENT_CANDIDATE"]["vectors"], result["ENTITY_SUBSTITUTION"]["vectors"]
    assert base[0] == entity[0] and base[1] == entity[1] and base[2] != entity[2] and base[3] == entity[3]


def test_requires_matching_matrix_approval_before_yield(monkeypatch):
    matrix = build(monkeypatch)
    with pytest.raises(NativeReceiverConditionMatrixError, match="validator is required"):
        list(matrix.iter_inputs())
    with pytest.raises(NativeReceiverConditionMatrixError, match="does not bind"):
        list(matrix.iter_inputs(approval="wrong", approval_validator=lambda token, digest: token == digest))
    assert len(approved(matrix)) == 8


def test_rejects_wrong_ood_family_and_cross_session_control(monkeypatch):
    import v13.native_tokenwise_pairing as pairing
    monkeypatch.setattr(pairing, "_validate_native_pair_record", lambda value: dict(value))
    task, main, baseline, candidate, ood, entity = inputs()
    ood["task_family"] = "ARITHMETIC"
    with pytest.raises(NativeReceiverConditionMatrixError, match="different task family"):
        build_native_receiver_condition_matrix(task=task, pair_record=main, baseline_packet=baseline,
            candidate_packet=candidate, ood_control=ood, entity_control=entity)
    task, main, baseline, candidate, ood, entity = inputs()
    ood["session_id"] = "other-session"
    with pytest.raises(NativeReceiverConditionMatrixError, match="same session"):
        build_native_receiver_condition_matrix(task=task, pair_record=main, baseline_packet=baseline,
            candidate_packet=candidate, ood_control=ood, entity_control=entity)


def test_rejects_entity_text_changes_outside_declared_span_and_bad_bos_binding(monkeypatch):
    import v13.native_tokenwise_pairing as pairing
    monkeypatch.setattr(pairing, "_validate_native_pair_record", lambda value: dict(value))
    task, main, baseline, candidate, ood, entity = inputs()
    bad_record = record("source-entity", "The dog sat?", [11, 44, 33], [[0.11, 0.22], [0.77, 0.88], [0.55, 0.66]])
    entity["record"] = bad_record
    entity["source_text"] = "The dog sat?"
    entity["candidate_packet"] = packet(bad_record, [[0.11, 0.22], [0.77, 0.88], [0.55, 0.66]])
    with pytest.raises(NativeReceiverConditionMatrixError, match="outside declared spans"):
        build_native_receiver_condition_matrix(task=task, pair_record=main, baseline_packet=baseline,
            candidate_packet=candidate, ood_control=ood, entity_control=entity)
    task, main, baseline, candidate, ood, entity = inputs()
    baseline["receiver_model_sha256"] = "f" * 64
    with pytest.raises(NativeReceiverConditionMatrixError, match="BOS baseline"):
        build_native_receiver_condition_matrix(task=task, pair_record=main, baseline_packet=baseline,
            candidate_packet=candidate, ood_control=ood, entity_control=entity)


def test_public_receipt_is_copy_and_close_blocks_later_vector_access(monkeypatch):
    matrix = build(monkeypatch)
    receipt = matrix.receipt
    receipt["conditions"][0]["input_sha256"] = "f" * 64
    assert matrix.receipt["conditions"][0]["input_sha256"] != "f" * 64
    assert len(approved(matrix)) == 8
    matrix.close()
    with pytest.raises(NativeReceiverConditionMatrixError, match="closed"):
        approved(matrix)


def test_identical_native_input_digests_are_valid_only_with_identical_token_scores():
    from v13.native_receiver_utility import NativeReceiverUtilityError, _validate_duplicate_input_digests
    group = {}
    for condition in CONDITIONS:
        digest = sha("input-" + condition)
        if condition == "LATENT_CANDIDATE":
            digest = sha("input-EXACT_MESSAGE")
        group[condition] = {"input_sha256": digest, "native": {"token_logprobs": [-0.7, -1.1]}}
    _validate_duplicate_input_digests(group)
    group["LATENT_CANDIDATE"]["native"]["token_logprobs"] = [-0.8, -1.1]
    with pytest.raises(NativeReceiverUtilityError, match="identical input digest"):
        _validate_duplicate_input_digests(group)


# The following bridge tests use a stubbed native CLI. They prove the Python
# approval/provenance/collector contract only, not native model execution.
def _fake_matrix_probe(monkeypatch, *, wrong_condition=None, bad_kv_condition=None, missing_kv_condition=None):
    import v13.native_receiver_task_matrix_bridge as bridge

    calls = []
    def fake_probe(**kwargs):
        calls.append({**kwargs, "condition_inputs": [dict(item) for item in kwargs["condition_inputs"]]})
        ids = kwargs["target_token_ids"]
        target_sha = sha(struct.pack("<" + "i" * len(ids), *ids))
        receiver_sha = kwargs["expected_model_sha256"]
        scores = {}
        for item in kwargs["condition_inputs"]:
            digest = item["input_sha256"]
            if item["condition"] == wrong_condition:
                digest = "f" * 64
            context_rows = item["input_rows"] if item["input_rows"] > 0 else 1
            positions = list(range(context_rows))
            position_sha = sha(struct.pack("<" + "i" * context_rows, *positions))
            combined_sha = sha("kv-combined-" + item["condition"])
            kv_snapshot = {
                "schema": "v14.native-receiver-kv-snapshot/1",
                "status": "READ_ONLY_SNAPSHOT",
                "cache_kind": "LLAMA_MEMORY_HYBRID_ATTENTION",
                "snapshot_scope": "ONE_ATTENTION_LAYER_ONE_SEQUENCE",
                "sequence_id": 0,
                "layer_id": 0,
                "attention_layer_count": 12,
                "active_cell_count": context_rows,
                "position_count": context_rows,
                "position_sha256": position_sha,
                "k_shape": [64, 8, 128, 1],
                "v_shape": [128, 8, 64, 1],
                "k_type": "f16",
                "v_type": "f16",
                "k_sha256": sha("kv-k-" + item["condition"]),
                "v_sha256": sha("kv-v-" + item["condition"]),
                "combined_sha256": combined_sha,
                "stable_read_sha256": combined_sha,
                "bytes_read_per_snapshot": 4096,
                "double_read_bytes_read": 8192,
                "duration_us": 100,
                "read_only": True,
                "double_read_stable": True,
                "raw_data_exported": False,
                "recurrent_state_included": False,
                "condition": item["condition"],
                "receiver_model_sha256": receiver_sha,
                "input_sha256": item["input_sha256"],
            }
            if item["condition"] == bad_kv_condition:
                kv_snapshot["stable_read_sha256"] = "f" * 64
            scores[item["condition"]] = {
                "schema": "v14.native-receiver-target-score/1",
                "execution_kind": "SYNTHETIC_FIXTURE",
                "environment": "SYNTHETIC",
                "llama_cpp_revision": PINNED_LLAMA_REVISION,
                "binary_sha256": "d" * 64,
                "receiver_model_sha256": receiver_sha,
                "input_sha256": digest,
                "target_token_ids_sha256": target_sha,
                "target_token_count": len(ids),
                "score_method": SCORE_METHOD,
                "token_logprobs": [-0.7 for _ in ids],
                "decode_status": 0,
                "native_input_consumed": True,
                "llama_version": "synthetic-fixture",
                "kv_snapshot": kv_snapshot,
            }
            if item["condition"] == missing_kv_condition:
                scores[item["condition"]].pop("kv_snapshot")
        return {
            "schema": "v14.native-receiver-task-matrix/1",
            "status": "SCORED",
            "sender_role": kwargs["sender_role"],
            "receiver_role": kwargs["receiver_role"],
            "sender_tap_id": kwargs["sender_tap_id"],
            "sender_model_revision": kwargs["sender_model_revision"],
            "sender_model_sha256": kwargs["sender_model_sha256"],
            "tokenizer_revision": kwargs["tokenizer_revision"],
            "receiver_model_revision": kwargs["receiver_model_revision"],
            "receiver_model_sha256": receiver_sha,
            "runner_revision": PINNED_LLAMA_REVISION,
            "llama_version": "synthetic-fixture",
            "input_dim": kwargs["condition_inputs"][1]["input_dim"],
            "output_dim": 2,
            "target_token_count": len(ids),
            "target_token_ids_sha256": target_sha,
            "duration_s": 0.01,
            "condition_scores": scores,
            "native_input_consumed": True,
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        }
    monkeypatch.setattr(bridge, "probe_matrix", fake_probe)
    return calls


def _run_bridge(monkeypatch, matrix, task, *, source_validator=None, approval=None):
    receipt = matrix.receipt
    phases = []
    runtime = type("Runtime", (), {"session": task["session_id"]})()
    def validate_source(value, phase):
        phases.append(phase)
        return True if source_validator is None else source_validator(value, phase)
    result = score_and_record_native_receiver_condition_matrix(
        runtime,
        matrix,
        approval=receipt["approval_binding_sha256"] if approval is None else approval,
        approval_validator=lambda token, expected: token == expected,
        source_validator=validate_source,
        target_token_ids=task["target_token_ids"],
        home="/tmp/v14-home",
        model_path="/tmp/v14-home/models/receiver.gguf",
        deadline=1.0e12,
        target_environment="SYNTHETIC",
    )
    return result, phases, runtime


def test_matrix_bridge_scores_all_conditions_and_records_one_atomic_group(monkeypatch):
    task, matrix = build_with_task(monkeypatch)
    calls = _fake_matrix_probe(monkeypatch)
    result, phases, runtime = _run_bridge(monkeypatch, matrix, task)

    assert result["status"] == "TASK_GROUP_SCORED"
    assert result["cohort_status"] == "FIXTURE_ONLY"
    assert result["holdout_status"] == "INSUFFICIENT_HOLDOUT"
    assert result["enough_holdout"] is False
    assert result["condition_count"] == 8
    assert result["kv_snapshot_count"] == 8
    assert result["kv_snapshot_layer_id"] == 0
    assert result["kv_snapshot_scope"] == "ONE_ATTENTION_LAYER_ONE_SEQUENCE"
    assert result["kv_snapshot_stable"] is True
    assert result["execution_kind"] == "SYNTHETIC_FIXTURE"
    assert result["environment"] == "SYNTHETIC"
    assert result["persisted"] is False
    assert result["semantic_use_proven"] is False
    assert result["generated_answer_correctness_proven"] is False
    assert result["training_authority"] == result["native_receiver_authority"] == 0
    assert phases == ["before", "after"]
    assert len(calls) == 1
    assert [x["condition"] for x in calls[0]["condition_inputs"]] == list(CONDITIONS)
    assert calls[0]["condition_inputs"][0]["vectors"] == []
    assert calls[0]["condition_inputs"][0]["position_ids"] == []
    assert calls[0]["target_token_ids"] == task["target_token_ids"]
    assert "token_logprobs" not in repr(result)
    assert "target_token_ids" not in result and "source_text" not in result
    status = task_score_status(runtime)
    assert status["receipt_count"] == 8
    stored = runtime._native_receiver_task_score_receipts
    assert len(stored) == 8
    for receipt in stored:
        snapshot = receipt["native"]["kv_snapshot"]
        assert snapshot["condition"] == receipt["condition"]
        assert snapshot["receiver_model_sha256"] == receipt["receiver"]["model_sha256"]
        assert snapshot["input_sha256"] == receipt["input_sha256"]
        assert snapshot["double_read_stable"] is True
        assert "position_ids" not in snapshot
    assert status["complete_task_group_count"] == 1
    assert status["incomplete_task_group_count"] == 0


def test_native_kv_snapshot_validator_sanitizes_and_rejects_untrusted_payloads():
    positions = [0, 1]
    combined = sha("combined")
    raw = {
        "schema": "v14.native-receiver-kv-snapshot/1",
        "status": "READ_ONLY_SNAPSHOT",
        "cache_kind": "LLAMA_MEMORY_HYBRID_ATTENTION",
        "snapshot_scope": "ONE_ATTENTION_LAYER_ONE_SEQUENCE",
        "sequence_id": 0,
        "layer_id": 2,
        "attention_layer_count": 8,
        "active_cell_count": 2,
        "position_ids": positions,
        "position_sha256": sha(struct.pack("<ii", *positions)),
        "k_shape": [64, 8, 128, 1],
        "v_shape": [128, 8, 64, 1],
        "k_type": "f16",
        "v_type": "f16",
        "k_sha256": sha("k"),
        "v_sha256": sha("v"),
        "combined_sha256": combined,
        "stable_read_sha256": combined,
        "bytes_read_per_snapshot": 4096,
        "double_read_bytes_read": 8192,
        "duration_us": 25,
        "read_only": True,
        "double_read_stable": True,
        "raw_data_exported": False,
        "recurrent_state_included": False,
    }
    checked = validate_native_receiver_kv_snapshot(
        raw, expected_rows=2, expected_condition="LATENT_CANDIDATE",
        expected_model_sha256="b" * 64, expected_input_sha256="c" * 64,
    )
    assert checked["position_count"] == 2
    assert checked["condition"] == "LATENT_CANDIDATE"
    assert checked["receiver_model_sha256"] == "b" * 64
    assert checked["input_sha256"] == "c" * 64
    assert "position_ids" not in checked
    assert validate_native_receiver_kv_snapshot(
        checked, expected_rows=2, expected_condition="LATENT_CANDIDATE",
        expected_model_sha256="b" * 64, expected_input_sha256="c" * 64,
        allow_sanitized=True,
    ) == checked

    bad_position = dict(raw, position_sha256="0" * 64)
    with pytest.raises(NativeReceiverUtilityError, match="position digest"):
        validate_native_receiver_kv_snapshot(bad_position, expected_rows=2)
    raw_export = dict(raw, raw_data_exported=True)
    with pytest.raises(NativeReceiverUtilityError, match="raw/recurrent"):
        validate_native_receiver_kv_snapshot(raw_export, expected_rows=2)


def test_matrix_bridge_rejects_unstable_kv_snapshot_atomically(monkeypatch):
    task, matrix = build_with_task(monkeypatch)
    calls = _fake_matrix_probe(monkeypatch, bad_kv_condition="LATENT_CANDIDATE")
    runtime = type("Runtime", (), {"session": task["session_id"]})()
    with pytest.raises(NativeReceiverTaskMatrixBridgeError, match="K/V snapshot rejected.*stable read"):
        score_and_record_native_receiver_condition_matrix(
            runtime, matrix, approval=matrix.receipt["approval_binding_sha256"],
            approval_validator=lambda token, expected: token == expected,
            source_validator=lambda receipt, phase: True,
            target_token_ids=task["target_token_ids"],
            home="/tmp/v14-home", model_path="/tmp/v14-home/models/receiver.gguf",
            deadline=1.0e12, target_environment="SYNTHETIC")
    assert len(calls) == 1
    assert task_score_status(runtime)["receipt_count"] == 0


def test_matrix_bridge_rejects_missing_kv_snapshot_atomically(monkeypatch):
    task, matrix = build_with_task(monkeypatch)
    _fake_matrix_probe(monkeypatch, missing_kv_condition="ZERO")
    runtime = type("Runtime", (), {"session": task["session_id"]})()
    with pytest.raises(NativeReceiverTaskMatrixBridgeError, match="K/V snapshot rejected.*schema"):
        score_and_record_native_receiver_condition_matrix(
            runtime, matrix, approval=matrix.receipt["approval_binding_sha256"],
            approval_validator=lambda token, expected: token == expected,
            source_validator=lambda receipt, phase: True,
            target_token_ids=task["target_token_ids"],
            home="/tmp/v14-home", model_path="/tmp/v14-home/models/receiver.gguf",
            deadline=1.0e12, target_environment="SYNTHETIC")
    assert task_score_status(runtime)["receipt_count"] == 0


def test_matrix_bridge_rejects_wrong_approval_before_native_probe(monkeypatch):
    task, matrix = build_with_task(monkeypatch)
    calls = _fake_matrix_probe(monkeypatch)
    runtime = type("Runtime", (), {"session": task["session_id"]})()
    with pytest.raises(NativeReceiverTaskMatrixBridgeError, match="approval/input validation"):
        score_and_record_native_receiver_condition_matrix(
            runtime, matrix, approval="wrong",
            approval_validator=lambda token, expected: token == expected,
            source_validator=lambda receipt, phase: True,
            target_token_ids=task["target_token_ids"],
            home="/tmp/v14-home", model_path="/tmp/v14-home/models/receiver.gguf",
            deadline=1.0e12, target_environment="SYNTHETIC")
    assert calls == []
    assert task_score_status(runtime)["receipt_count"] == 0


def test_matrix_bridge_discards_scores_when_source_changes_during_native_probe(monkeypatch):
    task, matrix = build_with_task(monkeypatch)
    calls = _fake_matrix_probe(monkeypatch)
    runtime = type("Runtime", (), {"session": task["session_id"]})()
    phases = []
    def validate(receipt, phase):
        phases.append(phase)
        return phase == "before"
    with pytest.raises(NativeReceiverTaskMatrixBridgeError, match="no longer current"):
        score_and_record_native_receiver_condition_matrix(
            runtime, matrix, approval=matrix.receipt["approval_binding_sha256"],
            approval_validator=lambda token, expected: token == expected,
            source_validator=validate, target_token_ids=task["target_token_ids"],
            home="/tmp/v14-home", model_path="/tmp/v14-home/models/receiver.gguf",
            deadline=1.0e12, target_environment="SYNTHETIC")
    assert phases == ["before", "after"]
    assert len(calls) == 1
    assert task_score_status(runtime)["receipt_count"] == 0


def test_matrix_bridge_rejects_misbound_condition_score_atomically(monkeypatch):
    task, matrix = build_with_task(monkeypatch)
    calls = _fake_matrix_probe(monkeypatch, wrong_condition="LATENT_CANDIDATE")
    runtime = type("Runtime", (), {"session": task["session_id"]})()
    with pytest.raises(NativeReceiverTaskMatrixBridgeError, match="not bound to condition"):
        score_and_record_native_receiver_condition_matrix(
            runtime, matrix, approval=matrix.receipt["approval_binding_sha256"],
            approval_validator=lambda token, expected: token == expected,
            source_validator=lambda receipt, phase: True,
            target_token_ids=task["target_token_ids"],
            home="/tmp/v14-home", model_path="/tmp/v14-home/models/receiver.gguf",
            deadline=1.0e12, target_environment="SYNTHETIC")
    assert len(calls) == 1
    assert task_score_status(runtime)["receipt_count"] == 0


def test_matrix_bridge_rejects_session_mismatch_before_native_probe(monkeypatch):
    task, matrix = build_with_task(monkeypatch)
    calls = _fake_matrix_probe(monkeypatch)
    runtime = type("Runtime", (), {"session": "other-session"})()
    with pytest.raises(NativeReceiverTaskMatrixBridgeError, match="active Runtime"):
        score_and_record_native_receiver_condition_matrix(
            runtime, matrix, approval=matrix.receipt["approval_binding_sha256"],
            approval_validator=lambda token, expected: token == expected,
            source_validator=lambda receipt, phase: True,
            target_token_ids=task["target_token_ids"],
            home="/tmp/v14-home", model_path="/tmp/v14-home/models/receiver.gguf",
            deadline=1.0e12, target_environment="SYNTHETIC")
    assert calls == []

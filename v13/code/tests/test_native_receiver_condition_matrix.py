import hashlib
import json
import struct

import pytest

from v13.native_receiver_condition_matrix import (
    NativeReceiverConditionMatrixError,
    build_native_receiver_condition_matrix,
)
from v13.native_receiver_utility import CONDITIONS


def sha(value):
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def f32sha(rows):
    flat = [float(x) for row in rows for x in row]
    return sha(struct.pack("<" + "f" * len(flat), *flat))


def jsonsha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def record(source_id, text, token_ids, candidate_rows, receiver_rows=None):
    receiver_rows = receiver_rows or [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    spans = [[0, 3], [4, 7], [8, 12]]
    src = {"source_id": source_id, "sha256": sha(text), "char_start": 0, "char_end": len(text)}
    sender = {"role": "B1_DETAIL", "tap_id": "B1_HIDDEN_PREFILL_FINAL_RMSNORM",
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
    return {"schema": "v14.native-tokenwise-pairing/1", "status": "PAIRED_DIAGNOSTIC",
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
    proof = {"schema": "v14.entity-substitution-proof/1", "original_source_sha256": main["source_ref"]["sha256"],
             "alternate_source_sha256": entity["source_ref"]["sha256"],
             "original_template_sha256": sha("The <ENTITY> sat."),
             "alternate_template_sha256": sha("The <ENTITY> sat."),
             "changed_token_positions": [1], "token_spans_sha256": jsonsha(main["receiver"]["token_spans"])}
    task = {"task_group_id": "task-main", "task_family": "ARITHMETIC", "session_id": "session-1",
            "target_token_ids": [101, 102]}
    ood_control = {"task_group_id": "task-ood", "task_family": "RELATION", "session_id": "session-1",
                  "record": ood, "candidate_packet": packet(ood, [[0.2, 0.1], [0.4, 0.3], [0.6, 0.5]])}
    entity_control = {"task_group_id": "task-entity", "task_family": "ARITHMETIC", "session_id": "session-1",
                      "record": entity, "candidate_packet": packet(entity, [[0.11, 0.22], [0.77, 0.88], [0.55, 0.66]]),
                      "proof": proof}
    return task, main, baseline, packet(main, [[0.11, 0.22], [0.37, 0.44], [0.55, 0.66]]), ood_control, entity_control


def build(monkeypatch, **overrides):
    import v13.native_tokenwise_pairing as pairing
    monkeypatch.setattr(pairing, "_validate_native_pair_record", lambda value: dict(value))
    task, main, baseline, candidate, ood, entity = inputs()
    args = {"task": task, "pair_record": main, "baseline_packet": baseline,
            "candidate_packet": candidate, "ood_control": ood, "entity_control": entity}
    args.update(overrides)
    return build_native_receiver_condition_matrix(**args)


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
    assert result[0]["message_source_ref"] is None and result[0]["input_rows"] == 1
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


def test_rejects_bad_entity_proof_and_bad_bos_binding(monkeypatch):
    import v13.native_tokenwise_pairing as pairing
    monkeypatch.setattr(pairing, "_validate_native_pair_record", lambda value: dict(value))
    task, main, baseline, candidate, ood, entity = inputs()
    entity["proof"]["alternate_template_sha256"] = "f" * 64
    with pytest.raises(NativeReceiverConditionMatrixError, match="one template"):
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

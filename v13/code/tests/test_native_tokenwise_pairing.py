import copy
import hashlib
import math
import pytest

from v13.native_tokenwise_pairing import (
    _RECORD_MATERIAL_FIELDS,
    _record_digest,
    build_anchor_preserving_native_receiver_input,
    build_native_tokenwise_pair_record,
    fit_adapter_from_native_pair_records,
)
from v13.latent_adapter import (
    LatentAdapterError,
    _activation_vector_sha256,
    _token_pair_id,
    align_token_rows_by_byte_pieces,
)

LLAMA_REV = "2851b3bcbf8d993a2243ae751c0a7dfa8e944a40"


def token(token_id, piece):
    return {"id": token_id, "piece": piece}


def fixture():
    source_text = "alpha beta"
    source_ref = {
        "source_id": "source-1",
        "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "char_start": 0,
        "char_end": len(source_text),
    }
    sender_prefill_ids = [1, 11, 12, 13, 2]
    sender_rows = [
        [0.0, 0.0],
        [1.0, 0.0],
        [0.0, 1.0],
        [1.0, 1.0],
        [0.0, 0.0],
    ]
    sender_packet = {
        "role": "B1_DETAIL",
        "event_id": "event-1",
        "brain_generation_id": "generation-1",
        "source_ref": source_ref,
        "tap_id": "b1.final-rmsnorm.v1",
        "model_revision": "sender-r1",
        "token_ids": sender_prefill_ids,
        "role_state": "INDEPENDENT_READ_ONLY_PREFILL",
        "receiver_read_authority": 0,
        "receiver_injection_authority": 0,
        "body_learning_authority": 0,
        "shape": [5, 2],
        "feature_path": "data/blobs/tap-fixture.json",
        "feature_sha256": "f" * 64,
        "metrics": {
            "whole_sequence_prefill": True,
            "pooling": "none",
            "prompt_tokens": 5,
        },
    }
    extractor_sha = "c" * 64
    receiver_model_sha = "b" * 64
    receiver_ids = [21, 22, 23, 24]
    extractor_output = {
        "status": "COMPLETE",
        "receipt": {
            "schema": "v14.llama-token-embedding-rows-receipt/1",
            "api_symbol": "llama_model_get_tok_embd_rows",
            "api_header": "src/llama-ext.h",
            "api_stability": "STAGING_WIP",
            "llama_cpp_revision": LLAMA_REV,
            "extractor_binary_sha256": extractor_sha,
            "model_revision": "receiver-r1",
            "model_sha256": receiver_model_sha,
            "source_tensor_type": "q4_0",
            "output_dtype": "f32",
            "vocab_size": 128,
            "embedding_dim": 2,
            "requested_token_ids": receiver_ids,
            "elements_written": len(receiver_ids) * 2,
        },
        "rows": [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0]],
        "model_sha256": receiver_model_sha,
        "extractor_binary_sha256": extractor_sha,
    }
    return {
        "source_text": source_text,
        "source_ref": source_ref,
        "sender_content_token_ids": [11, 12, 13],
        "sender_content_token_pieces": [token(11, "alpha"), token(12, " "), token(13, "beta")],
        "sender_tap_packet": sender_packet,
        "sender_tap_data": {"token_ids": sender_prefill_ids, "vectors": sender_rows},
        "receiver_content_token_ids": receiver_ids,
        "receiver_content_token_pieces": [token(21, "al"), token(22, "pha "), token(23, "be"), token(24, "ta")],
        "receiver_extractor_output": extractor_output,
        "source_id": "source-1",
        "session_id": "session-1",
        "event_id": "event-1",
        "brain_generation_id": "generation-1",
        "sender_role": "B1_DETAIL",
        "receiver_role": "C3_LANGUAGE",
        "sender_tap_id": "b1.final-rmsnorm.v1",
        "receiver_tap_id": "c3.input-embedding.v1",
        "sender_model_revision": "sender-r1",
        "receiver_model_revision": "receiver-r1",
        "sender_model_sha256": "a" * 64,
        "receiver_model_sha256": receiver_model_sha,
        "sender_tokenizer_revision": "sender-tokenizer-r1",
        "receiver_tokenizer_revision": "receiver-tokenizer-r1",
    }


def test_pairs_sender_final_rmsnorm_to_receiver_input_rows_across_tokenizers():
    record = build_native_tokenwise_pair_record(**fixture())
    assert record["schema"] == "v14.native-tokenwise-pairing/1"
    assert record["status"] == "PAIRED_DIAGNOSTIC"
    assert record["pair_count"] == 4
    assert record["minimum_coverage"] == pytest.approx(1.0)
    assert record["mean_coverage"] == pytest.approx(1.0)
    assert record["sender"]["prefill_positions"] == [1, 2, 3]
    assert record["receiver"]["tap_id"] == "c3.input-embedding.v1"
    assert record["alignment_method"] == "UTF8_BYTE_PIECE_OVERLAP_V1"
    assert record["production_route"] is False
    assert record["semantic_use_proven"] is False
    assert record["training_authority"] == 0
    assert record["native_receiver_authority"] == 0
    assert record["persisted"] is False
    assert len(record["record_sha256"]) == 64
    assert "source_text" not in record
    assert "sender_content_token_pieces" not in record
    assert all(pair["source_id"] == "source-1" for pair in record["pairs"])


def test_sender_packet_event_generation_source_and_model_are_bound():
    for field, value in (
        ("event_id", "other-event"),
        ("brain_generation_id", "other-generation"),
        ("model_revision", "other-model"),
        ("tap_id", "other-tap"),
        ("receiver_injection_authority", 1),
    ):
        args = fixture()
        args["sender_tap_packet"] = dict(args["sender_tap_packet"], **{field: value})
        with pytest.raises(LatentAdapterError, match="sender LatentTapPacket"):
            build_native_tokenwise_pair_record(**args)


def test_source_ref_must_cover_exact_full_text_and_match_both_taps():
    args = fixture()
    args["source_ref"] = dict(args["source_ref"], char_start=1)
    args["sender_tap_packet"] = dict(args["sender_tap_packet"], source_ref=args["source_ref"])
    with pytest.raises(LatentAdapterError, match="full tapped text"):
        build_native_tokenwise_pair_record(**args)

    args = fixture()
    args["source_ref"] = dict(args["source_ref"], sha256="0" * 64)
    args["sender_tap_packet"] = dict(args["sender_tap_packet"], source_ref=args["source_ref"])
    with pytest.raises(LatentAdapterError, match="same exact source bytes"):
        build_native_tokenwise_pair_record(**args)


def test_receiver_role_tap_and_extractor_hash_are_not_interchangeable():
    args = fixture()
    args["receiver_tap_id"] = "c3.final-rmsnorm.v1"
    with pytest.raises(LatentAdapterError, match="input-embedding"):
        build_native_tokenwise_pair_record(**args)

    args = fixture()
    args["receiver_extractor_output"] = dict(args["receiver_extractor_output"], model_sha256="f" * 64)
    with pytest.raises(LatentAdapterError):
        build_native_tokenwise_pair_record(**args)


def test_content_token_ids_must_match_native_tokenizer_piece_ids():
    args = fixture()
    args["receiver_content_token_pieces"] = [token(99, "al"), *args["receiver_content_token_pieces"][1:]]
    with pytest.raises(LatentAdapterError, match="token-piece ID"):
        build_native_tokenwise_pair_record(**args)


def test_sender_content_sequence_must_map_to_one_prefill_span():
    args = fixture()
    source_text = "aa"
    source_ref = {
        "source_id": "source-1",
        "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "char_start": 0,
        "char_end": len(source_text),
    }
    args["source_text"] = source_text
    args["source_ref"] = source_ref
    args["sender_content_token_ids"] = [11, 11]
    args["sender_content_token_pieces"] = [token(11, "a"), token(11, "a")]
    args["sender_tap_data"] = {
        "token_ids": [11, 11, 11],
        "vectors": [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
    }
    args["sender_tap_packet"] = dict(
        args["sender_tap_packet"],
        source_ref=source_ref,
        token_ids=args["sender_tap_data"]["token_ids"],
        shape=[3, 2],
        metrics=dict(args["sender_tap_packet"]["metrics"], prompt_tokens=3),
    )
    with pytest.raises(LatentAdapterError, match="exactly one contiguous"):
        build_native_tokenwise_pair_record(**args)


def test_tokenwise_path_rejects_same_role_and_malformed_runtime_ids():
    args = fixture()
    args["receiver_role"] = "B1_DETAIL"
    args["receiver_tap_id"] = "b1.input-embedding.v1"
    with pytest.raises(LatentAdapterError, match="distinct"):
        build_native_tokenwise_pair_record(**args)

    args = fixture()
    args["session_id"] = "session id with spaces"
    with pytest.raises(LatentAdapterError, match="opaque identifier"):
        build_native_tokenwise_pair_record(**args)



def native_record(index, session_id):
    args = fixture()
    source_text = f"alpha{index} beta"
    source_ref = {
        "source_id": f"source-{index}",
        "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "char_start": 0,
        "char_end": len(source_text),
    }
    sender_pieces = [
        token(11, f"alpha{index}"),
        token(12, " "),
        token(13, "beta"),
    ]
    receiver_pieces = [
        token(21, "al"),
        token(22, f"pha{index} "),
        token(23, "be"),
        token(24, "ta"),
    ]
    sender_rows = [
        [float(index + 1), float(index + 2)],
        [float(index + 2), float(index + 1)],
        [float(index + 3), float(index + 1)],
    ]
    aligned = align_token_rows_by_byte_pieces(
        sender_rows, sender_pieces, [[1.0, 0.0, 1.0]] * 4, receiver_pieces,
        source_id=source_ref["source_id"], source_text=source_text,
    )
    receiver_rows = [
        [pair["sender_vector"][0], pair["sender_vector"][1],
         pair["sender_vector"][0] + pair["sender_vector"][1]]
        for pair in aligned
    ]
    sender_prefill_ids = [1, 11, 12, 13, 2]
    sender_prefill_rows = [[0.0, 0.0], *sender_rows, [0.0, 0.0]]
    args.update({
        "source_text": source_text,
        "source_ref": source_ref,
        "sender_content_token_ids": [11, 12, 13],
        "sender_content_token_pieces": sender_pieces,
        "sender_tap_packet": dict(
            args["sender_tap_packet"],
            event_id=f"event-{index}",
            source_ref=source_ref,
            token_ids=sender_prefill_ids,
            shape=[5, 2],
            feature_sha256=hashlib.sha256(f"feature-{index}".encode()).hexdigest(),
        ),
        "sender_tap_data": {"token_ids": sender_prefill_ids, "vectors": sender_prefill_rows},
        "receiver_content_token_ids": [21, 22, 23, 24],
        "receiver_content_token_pieces": receiver_pieces,
        "receiver_extractor_output": {
            **args["receiver_extractor_output"],
            "rows": receiver_rows,
            "receipt": {
                **args["receiver_extractor_output"]["receipt"],
                "requested_token_ids": [21, 22, 23, 24],
                "embedding_dim": 3,
                "elements_written": 12,
            },
        },
        "source_id": source_ref["source_id"],
        "session_id": session_id,
        "event_id": f"event-{index}",
    })
    return build_native_tokenwise_pair_record(**args)


def test_native_pair_records_fit_session_disjoint_tokenwise_candidate():
    records = [
        native_record(i, f"train-session-{i // 2}") for i in range(8)
    ] + [
        native_record(i, f"hold-session-{(i - 8) // 2}") for i in range(8, 12)
    ]
    result = fit_adapter_from_native_pair_records(
        records,
        train_session_ids=[
            "train-session-0", "train-session-1",
            "train-session-2", "train-session-3",
        ],
        holdout_session_ids=["hold-session-0", "hold-session-1"],
        rank=2,
        ridge=1e-5,
        min_relative_improvement=0.0,
    )
    assert result["adapter"]["schema"] == "v14.cross-organ-latent-adapter/4"
    assert result["adapter"]["status"] == "ALIGNMENT_CANDIDATE"
    assert result["adapter"]["holdout_policy"] == "SOURCE_AND_SESSION_DISJOINT"
    assert result["adapter"]["metrics"]["session_disjoint"] is True
    assert result["adapter"]["metrics"]["train_session_count"] == 4
    assert result["adapter"]["metrics"]["holdout_session_count"] == 2
    assert result["fit_manifest"]["session_disjoint"] is True
    assert result["fit_manifest"]["train_source_count"] == 8
    assert result["fit_manifest"]["holdout_source_count"] == 4
    assert result["fit_manifest"]["train_pair_count"] == 32
    assert result["fit_manifest"]["holdout_pair_count"] == 16
    assert result["adapter"]["production_route"] is False
    assert result["adapter"]["training_authority"] == 0


def test_native_pair_record_fit_rejects_session_overlap_and_tampering():
    records = [
        native_record(i, f"train-session-{i // 2}") for i in range(8)
    ] + [
        native_record(i, f"hold-session-{(i - 8) // 2}") for i in range(8, 12)
    ]
    with pytest.raises(LatentAdapterError, match="session leakage"):
        fit_adapter_from_native_pair_records(
            records,
            train_session_ids=["train-session-0", "train-session-1"],
            holdout_session_ids=["train-session-1", "hold-session-0"],
            rank=2,
        )
    tampered = [dict(record) for record in records]
    tampered[0] = dict(tampered[0], session_id="forged-session")
    with pytest.raises(LatentAdapterError, match="session"):
        fit_adapter_from_native_pair_records(
            tampered,
            train_session_ids=[
                "train-session-0", "train-session-1",
                "train-session-2", "train-session-3",
            ],
            holdout_session_ids=["hold-session-0", "hold-session-1"],
            rank=2,
        )

def _session_fit_cohort():
    records = [
        native_record(i, f"train-session-{i // 2}") for i in range(8)
    ] + [
        native_record(i, f"hold-session-{(i - 8) // 2}") for i in range(8, 12)
    ]
    result = fit_adapter_from_native_pair_records(
        records,
        train_session_ids=[
            "train-session-0", "train-session-1",
            "train-session-2", "train-session-3",
        ],
        holdout_session_ids=["hold-session-0", "hold-session-1"],
        rank=2,
        ridge=1e-5,
        min_relative_improvement=0.0,
    )
    return records, result


def test_native_pair_fit_rejects_receiver_rows_detached_from_extractor_manifest():
    records, _result = _session_fit_cohort()
    tampered = copy.deepcopy(records[8])
    pair = tampered["pairs"][0]
    pair["receiver_vector"][0] += 0.5
    pair["receiver_vector_sha256"] = _activation_vector_sha256(pair["receiver_vector"])
    pair["pair_id"] = _token_pair_id(
        source_id=pair["source_id"],
        source_sha256=pair["source_sha256"],
        token_position=pair["token_position"],
        source_span=pair["source_span"],
        alignment_id=pair["alignment_id"],
        alignment_coverage=pair["alignment_coverage"],
        sender_vector_sha256=pair["sender_vector_sha256"],
        receiver_vector_sha256=pair["receiver_vector_sha256"],
    )
    tampered["pair_ids"] = [item["pair_id"] for item in tampered["pairs"]]
    material = {key: tampered[key] for key in _RECORD_MATERIAL_FIELDS}
    tampered["record_sha256"] = _record_digest(material)
    records[8] = tampered
    with pytest.raises(LatentAdapterError, match="native manifest row"):
        fit_adapter_from_native_pair_records(
            records,
            train_session_ids=[
                "train-session-0", "train-session-1",
                "train-session-2", "train-session-3",
            ],
            holdout_session_ids=["hold-session-0", "hold-session-1"],
            rank=2,
            ridge=1e-5,
            min_relative_improvement=0.0,
        )


def test_anchor_preserving_native_receiver_input_keeps_exact_anchors_at_zero_gain():
    from v13 import native_latent_receiver

    records, fitted = _session_fit_cohort()
    record = records[8]
    packet = build_anchor_preserving_native_receiver_input(
        fitted["adapter"], record, residual_gain=0.0,
    )
    expected = [
        pair["receiver_vector"]
        for pair in sorted(record["pairs"], key=lambda item: item["token_position"])
    ]
    assert packet["schema"] == "v14.native-tokenwise-anchor-residual-input/1"
    assert packet["input_strategy"] == "ANCHOR_PLUS_CAPPED_RESIDUAL_V1"
    assert packet["vectors"] == expected
    assert packet["input_sha256"] == packet["anchor_sha256"]
    assert packet["anchor_rows_preserved_as_base"] is True
    assert packet["production_route"] is False
    assert packet["semantic_use_proven"] is False
    assert packet["training_authority"] == packet["native_receiver_authority"] == 0
    assert packet["persisted"] is False
    assert "token_ids" not in packet
    rows, dimension, _payload, digest = native_latent_receiver._vector_payload(packet["vectors"])
    positions = native_latent_receiver._validate_positions(
        packet["position_ids"], rows, packet["position_mode"],
    )
    assert rows == packet["input_rows"] == 4
    assert dimension == packet["input_dim"] == fitted["adapter"]["receiver_dim"]
    assert digest == packet["input_sha256"]
    assert positions == [0, 1, 2, 3]


def test_anchor_preserving_native_receiver_input_bounds_residual_and_model_binding():
    records, fitted = _session_fit_cohort()
    packet = build_anchor_preserving_native_receiver_input(
        fitted["adapter"], records[8],
        residual_gain=0.5,
        max_relative_residual=0.2,
    )
    assert packet["max_applied_relative_residual"] <= 0.1 + 1e-6
    assert packet["mean_applied_relative_residual"] <= 0.1 + 1e-6
    assert packet["input_sha256"] != "" and len(packet["input_sha256"]) == 64
    with pytest.raises(LatentAdapterError, match="gain"):
        build_anchor_preserving_native_receiver_input(
            fitted["adapter"], records[8], residual_gain=0.5001,
        )
    with pytest.raises(LatentAdapterError, match="maximum relative residual"):
        build_anchor_preserving_native_receiver_input(
            fitted["adapter"], records[8], max_relative_residual=1.0001,
        )

    wrong_records = copy.deepcopy(records)
    for item in wrong_records:
        item["sender"]["model_sha256"] = "d" * 64
        item["record_sha256"] = _record_digest({
            key: item[key] for key in _RECORD_MATERIAL_FIELDS
        })
    wrong_fit = fit_adapter_from_native_pair_records(
        wrong_records,
        train_session_ids=[
            "train-session-0", "train-session-1",
            "train-session-2", "train-session-3",
        ],
        holdout_session_ids=["hold-session-0", "hold-session-1"],
        rank=2,
        ridge=1e-5,
        min_relative_improvement=0.0,
    )
    with pytest.raises(LatentAdapterError, match="model/tap/tokenizer binding mismatch"):
        build_anchor_preserving_native_receiver_input(
            wrong_fit["adapter"], records[8],
        )



# Native receiver task-score contract: target log-probability is a proxy, not answer proof.
from v13.native_receiver_utility import (
    CONDITIONS as _TASK_SCORE_CONDITIONS,
    NativeReceiverUtilityError,
    build_native_receiver_task_score_receipt,
    evaluate_native_receiver_task_utility,
)


def _task_score_sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _task_score_native(target_hash, input_hash, score):
    return {
        "schema": "v14.native-receiver-target-score/1",
        "execution_kind": "SYNTHETIC_FIXTURE",
        "environment": "SYNTHETIC",
        "llama_cpp_revision": "2851b3bcbf8d993a2243ae751c0a7dfa8e944a40",
        "binary_sha256": "a" * 64,
        "receiver_model_sha256": "b" * 64,
        "input_sha256": input_hash,
        "target_token_ids_sha256": target_hash,
        "target_token_count": 2,
        "score_method": "TEACHER_FORCED_TARGET_LOGPROB_V1",
        "token_logprobs": [score, score - 0.01],
        "decode_status": 0,
        "native_input_consumed": True,
        "llama_version": "synthetic fixture only",
    }


def _task_score_cohort(candidate_delta=0.12):
    result = []
    for index in range(20):
        task_id = f"task-{index}"
        source = {"source_id": f"source-{index}", "sha256": _task_score_sha(f"source-{index}")}
        target_hash = _task_score_sha(f"target-{index}")
        context_hash = _task_score_sha(f"context-{index}")
        family = "ARITHMETIC" if index % 2 == 0 else "ENTITY_RECALL"
        scores = {
            "NO_MESSAGE": -0.42, "EXACT_MESSAGE": -0.38,
            "LATENT_CANDIDATE": -0.38 + candidate_delta,
            "ZERO": -0.50, "SHUFFLE": -0.52, "REPEAT": -0.49,
            "OOD": -0.55, "ENTITY_SUBSTITUTION": -0.58,
        }
        for condition in _TASK_SCORE_CONDITIONS:
            message_source = None if condition == "NO_MESSAGE" else source
            if condition in {"OOD", "ENTITY_SUBSTITUTION"}:
                message_source = {
                    "source_id": f"wrong-{condition}-{index}",
                    "sha256": _task_score_sha(f"wrong-{condition}-{index}"),
                }
            adapter_sha = None if condition in {"NO_MESSAGE", "EXACT_MESSAGE"} else "d" * 64
            input_hash = _task_score_sha(f"{task_id}:{condition}")
            result.append(build_native_receiver_task_score_receipt(
                condition=condition, task_group_id=task_id, task_family=family,
                session_id=f"session-{index // 10}", source_ref=source,
                message_source_ref=message_source,
                receiver={"role": "C3_LANGUAGE", "model_revision": "r1",
                          "model_sha256": "b" * 64, "tokenizer_revision": "tok1"},
                target_token_ids_sha256=target_hash, target_token_count=2,
                context_sha256=context_hash, input_sha256=input_hash,
                native_receipt=_task_score_native(target_hash, input_hash, scores[condition]),
                adapter_sha256=adapter_sha,
            ))
    return result


def test_task_score_complete_synthetic_cohort_is_never_promoted_to_native():
    result = evaluate_native_receiver_task_utility(_task_score_cohort())
    assert result["status"] == "FIXTURE_ONLY"
    assert result["evidence_class"] == "SYNTHETIC"
    assert result["task_group_count"] == 20 and result["session_count"] == 2
    assert result["enough_holdout"] is True and result["candidate_beats_all_controls"] is True
    assert result["semantic_use_proven"] is False
    assert result["generated_answer_correctness_proven"] is False
    assert result["production_route"] is False
    assert result["training_authority"] == result["native_receiver_authority"] == 0


def test_task_score_receipt_digest_rejects_post_wrap_score_mutation():
    rows = _task_score_cohort()
    tampered = copy.deepcopy(rows[0])
    tampered["token_logprobs"][0] += 0.2
    with pytest.raises(NativeReceiverUtilityError, match="digest mismatch"):
        evaluate_native_receiver_task_utility([tampered] + rows[1:])


def test_task_score_evaluator_requires_every_negative_control():
    rows = [item for item in _task_score_cohort()
            if not (item["task_group_id"] == "task-0" and item["condition"] == "SHUFFLE")]
    with pytest.raises(NativeReceiverUtilityError, match="missing or extra"):
        evaluate_native_receiver_task_utility(rows)


def test_task_score_evaluator_rejects_target_mismatch_across_paired_conditions():
    rows = _task_score_cohort()
    item = next(x for x in rows if x["task_group_id"] == "task-0" and x["condition"] == "SHUFFLE")
    new_target = _task_score_sha("different-target")
    changed = build_native_receiver_task_score_receipt(
        condition=item["condition"], task_group_id=item["task_group_id"],
        task_family=item["task_family"], session_id=item["session_id"],
        source_ref=item["source_ref"], message_source_ref=item["message_source_ref"],
        receiver=item["receiver"], target_token_ids_sha256=new_target, target_token_count=2,
        context_sha256=item["context_sha256"], input_sha256=item["input_sha256"],
        native_receipt=_task_score_native(new_target, item["input_sha256"], -0.5),
        adapter_sha256=item["adapter_sha256"],
    )
    rows[rows.index(item)] = changed
    with pytest.raises(NativeReceiverUtilityError, match="source/target/context/model"):
        evaluate_native_receiver_task_utility(rows)


def test_task_score_ood_and_entity_substitution_require_different_sender_source():
    with pytest.raises(NativeReceiverUtilityError, match="must differ"):
        build_native_receiver_task_score_receipt(
            condition="OOD", task_group_id="t", task_family="OTHER", session_id="s",
            source_ref={"source_id": "x", "sha256": "1" * 64},
            message_source_ref={"source_id": "x", "sha256": "1" * 64},
            receiver={"role": "C3_LANGUAGE", "model_revision": "r",
                      "model_sha256": "b" * 64, "tokenizer_revision": "t"},
            target_token_ids_sha256="d" * 64, target_token_count=2,
            context_sha256="e" * 64, input_sha256="f" * 64,
            native_receipt=_task_score_native("d" * 64, "f" * 64, -0.5),
            adapter_sha256="c" * 64,
        )


def test_task_score_candidate_must_beat_exact_and_no_message_controls():
    result = evaluate_native_receiver_task_utility(_task_score_cohort(candidate_delta=0.005))
    assert result["status"] == "FIXTURE_ONLY"
    assert result["candidate_beats_all_controls"] is False
    assert result["paired_candidate_deltas"]["EXACT_MESSAGE"]["pass"] is False


def test_task_score_native_receipt_requires_successful_decode_and_consumption():
    bad = _task_score_native("d" * 64, "f" * 64, -0.5)
    bad["decode_status"] = -1
    with pytest.raises(NativeReceiverUtilityError, match="successfully consume"):
        build_native_receiver_task_score_receipt(
            condition="LATENT_CANDIDATE", task_group_id="t", task_family="OTHER",
            session_id="s", source_ref={"source_id": "x", "sha256": "1" * 64},
            message_source_ref={"source_id": "x", "sha256": "1" * 64},
            receiver={"role": "C3_LANGUAGE", "model_revision": "r",
                      "model_sha256": "b" * 64, "tokenizer_revision": "t"},
            target_token_ids_sha256="d" * 64, target_token_count=2,
            context_sha256="e" * 64, input_sha256="f" * 64,
            native_receipt=bad, adapter_sha256="c" * 64,
        )


def test_task_score_no_message_cannot_claim_sender_source_or_adapter():
    with pytest.raises(NativeReceiverUtilityError, match="NO_MESSAGE"):
        build_native_receiver_task_score_receipt(
            condition="NO_MESSAGE", task_group_id="t", task_family="OTHER", session_id="s",
            source_ref={"source_id": "x", "sha256": "1" * 64}, message_source_ref=None,
            receiver={"role": "C3_LANGUAGE", "model_revision": "r",
                      "model_sha256": "b" * 64, "tokenizer_revision": "t"},
            target_token_ids_sha256="d" * 64, target_token_count=2,
            context_sha256="e" * 64, input_sha256="f" * 64,
            native_receipt=_task_score_native("d" * 64, "f" * 64, -0.5),
            adapter_sha256="c" * 64,
        )


def test_task_score_redmi_receipt_requires_private_execution_digest_and_build_id():
    target_hash = _task_score_sha("target")
    input_hash = _task_score_sha("input")
    native_receipt = _task_score_native(target_hash, input_hash, -0.5)
    native_receipt["execution_kind"] = "NATIVE_LLAMA_CPP_GGUF"
    native_receipt["environment"] = "REDMI"
    kwargs = dict(
        condition="LATENT_CANDIDATE", task_group_id="device-task", task_family="OTHER",
        session_id="device-session",
        source_ref={"source_id": "source", "sha256": "1" * 64},
        message_source_ref={"source_id": "source", "sha256": "1" * 64},
        receiver={"role": "C3_LANGUAGE", "model_revision": "r1",
                  "model_sha256": "b" * 64, "tokenizer_revision": "tok1"},
        target_token_ids_sha256=target_hash, target_token_count=2,
        context_sha256=_task_score_sha("context"), input_sha256=input_hash,
        native_receipt=native_receipt, adapter_sha256="d" * 64,
    )
    with pytest.raises(NativeReceiverUtilityError, match="device_execution_receipt_sha256"):
        build_native_receiver_task_score_receipt(**kwargs)
    native_receipt["device_execution_receipt_sha256"] = _task_score_sha("private-device-receipt")
    native_receipt["device_runtime_build_id"] = "redmi-runtime-build"
    receipt = build_native_receiver_task_score_receipt(**kwargs)
    assert receipt["native"]["environment"] == "REDMI"
    assert receipt["native"]["device_execution_receipt_sha256"] == _task_score_sha("private-device-receipt")


def test_task_score_holdout_gate_requires_minimum_per_session_and_family():
    result = evaluate_native_receiver_task_utility(
        _task_score_cohort(), min_tasks_per_session=11, min_tasks_per_family=11,
    )
    assert result["status"] == "FIXTURE_ONLY"
    assert result["enough_holdout"] is False
    assert result["tasks_per_session"] == {"session-0": 10, "session-1": 10}
    assert result["tasks_per_family"] == {"ARITHMETIC": 10, "ENTITY_RECALL": 10}


def test_task_score_adapter_revision_must_be_stable_across_task_cohort():
    rows = _task_score_cohort()
    for index, item in enumerate(rows):
        if item["task_group_id"] != "task-0" or item["condition"] not in {
            "LATENT_CANDIDATE", "ZERO", "SHUFFLE", "REPEAT", "OOD", "ENTITY_SUBSTITUTION"
        }:
            continue
        native_receipt = dict(item["native"])
        rows[index] = build_native_receiver_task_score_receipt(
            condition=item["condition"], task_group_id=item["task_group_id"],
            task_family=item["task_family"], session_id=item["session_id"],
            source_ref=item["source_ref"], message_source_ref=item["message_source_ref"],
            receiver=item["receiver"], target_token_ids_sha256=item["target_token_ids_sha256"],
            target_token_count=item["target_token_count"], context_sha256=item["context_sha256"],
            input_sha256=item["input_sha256"], native_receipt=native_receipt,
            adapter_sha256="e" * 64,
        )
    with pytest.raises(NativeReceiverUtilityError, match="adapter revision changed"):
        evaluate_native_receiver_task_utility(rows)

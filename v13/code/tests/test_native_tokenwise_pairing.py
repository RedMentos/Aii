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
        "tap_id": "lfm2.result_norm.final.v1",
        "activation_space": "FINAL_RMSNORM_PREFILL_F32",
        "capture_method": "LLAMA_SERVER_EMBEDDINGS_FINAL_RMSNORM_ONLY",
        "runner_revision": "b10964",
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
            "operation": "PREFILL_TAP",
            "normalization": "native_final_RMSNorm_only",
            "whole_sequence_prefill": True,
            "pooling": "none",
            "CAN_LATENT_TAP": True,
            "CAN_LATENT_INJECT": False,
            "CAN_TRAIN_BODY": False,
            "role": "B1_DETAIL",
            "tap_id": "lfm2.result_norm.final.v1",
            "runner_revision": "b10964",
            "embedding_dim": 2,
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
        "sender_tap_id": "lfm2.result_norm.final.v1",
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
    assert record["schema"] == "v14.native-tokenwise-pairing/2"
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



def test_rejects_static_input_embedding_rows_as_sender_context():
    args = fixture()
    args["sender_tap_packet"] = dict(
        args["sender_tap_packet"], activation_space="INPUT_EMBEDDING_F32",
    )
    with pytest.raises(LatentAdapterError, match="final-RMSNorm prefill"):
        build_native_tokenwise_pair_record(**args)


def test_rejects_pooled_sender_tap_even_with_matching_dimensions():
    args = fixture()
    args["sender_tap_packet"] = dict(
        args["sender_tap_packet"],
        metrics=dict(args["sender_tap_packet"]["metrics"], pooling="mean"),
    )
    with pytest.raises(LatentAdapterError, match="final-RMSNorm prefill"):
        build_native_tokenwise_pair_record(**args)

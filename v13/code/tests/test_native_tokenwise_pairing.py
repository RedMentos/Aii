import hashlib
import pytest

from v13.native_tokenwise_pairing import build_native_tokenwise_pair_record
from v13.latent_adapter import LatentAdapterError

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

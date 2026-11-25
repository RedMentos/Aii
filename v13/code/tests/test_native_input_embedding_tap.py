import copy

import pytest

from v13.latent_adapter import LatentAdapterError
from v13.native_input_embedding_tap import (
    build_native_input_embedding_tap_manifest as build,
    validate_native_input_embedding_tap_manifest as validate,
)

SOURCE = "A\u00e1\U0001f9e0e\u0301"
PIECES = [
    {"id": 10, "piece": "A"}, {"id": 11, "piece": [0xC3]},
    {"id": 12, "piece": [0xA1, 0xF0]}, {"id": 13, "piece": [0x9F, 0xA7]},
    {"id": 14, "piece": [0xA0]}, {"id": 15, "piece": "e"},
    {"id": 16, "piece": [0xCC]}, {"id": 17, "piece": [0x81]},
]
IDS = list(range(10, 18))
ROWS = [[float(i + 1), float(i + 2), float(i + 3)] for i in range(8)]
MODEL_SHA = "a" * 64


def receipt(
    *,
    token_ids=None,
    elements_written=None,
    embedding_dim=3,
    vocab_size=32000,
    source_tensor_type="q4_0",
    output_dtype="f32",
    api_symbol="llama_model_get_tok_embd_rows",
    llama_cpp_revision="2851b3bcbf8d993a2243ae751c0a7dfa8e944a40",
    extractor_binary_sha256="b" * 64,
    model_revision="model-r1",
    model_sha256=MODEL_SHA,
):
    return {
        "schema": "v14.llama-token-embedding-rows-receipt/1",
        "api_symbol": api_symbol,
        "api_header": "src/llama-ext.h",
        "api_stability": "STAGING_WIP",
        "llama_cpp_revision": llama_cpp_revision,
        "extractor_binary_sha256": extractor_binary_sha256,
        "model_revision": model_revision,
        "model_sha256": model_sha256,
        "source_tensor_type": source_tensor_type,
        "output_dtype": output_dtype,
        "vocab_size": vocab_size,
        "embedding_dim": embedding_dim,
        "requested_token_ids": list(IDS if token_ids is None else token_ids),
        "elements_written": len(IDS) * embedding_dim if elements_written is None else elements_written,
    }


def make(role="C3_LANGUAGE", **receipt_overrides):
    return build(
        role, SOURCE, IDS, PIECES, ROWS, source_id="s1", event_id="e1",
        brain_generation_id="g1", model_revision="model-r1",
        model_sha256=MODEL_SHA, tokenizer_revision="tokenizer-r1",
        extractor_receipt=receipt(**receipt_overrides),
    )


def test_native_input_tap_binds_exact_role_source_rows_model_and_extractor():
    result = make()
    m = result["manifest"]
    assert m["tap_id"] == "c3.input-embedding.v1"
    assert m["activation_space"] == "INPUT_EMBEDDING_F32"
    assert m["source_span_unit"] == "UTF8_BYTE"
    assert m["row_positions"] == list(range(8))
    assert m["embedding_dim"] == 3
    assert m["model_sha256"] == MODEL_SHA
    assert m["extractor_receipt"]["api_symbol"] == "llama_model_get_tok_embd_rows"
    assert m["extractor_receipt"]["llama_cpp_revision"] == "2851b3bcbf8d993a2243ae751c0a7dfa8e944a40"
    assert len(m["manifest_sha256"]) == 64
    assert validate(m, SOURCE, PIECES, ROWS) == result


@pytest.mark.parametrize("role,tap", [
    ("B1_DETAIL", "b1.input-embedding.v1"),
    ("B2_GIST", "b2.input-embedding.v1"),
    ("C3_LANGUAGE", "c3.input-embedding.v1"),
])
def test_native_input_tap_id_is_role_derived(role, tap):
    assert make(role)["manifest"]["tap_id"] == tap


def test_native_input_tap_rejects_wrong_space_mutated_rows_and_source():
    result = make()
    m = copy.deepcopy(result["manifest"])
    m["tap_id"] = "c3.result_norm.final.v1"
    with pytest.raises(LatentAdapterError):
        validate(m, SOURCE, PIECES, ROWS)
    changed = [list(row) for row in ROWS]
    changed[2][1] += 0.25
    with pytest.raises(LatentAdapterError, match="digest|binding"):
        validate(result["manifest"], SOURCE, PIECES, changed)
    with pytest.raises(LatentAdapterError, match="do not reconstruct"):
        validate(result["manifest"], SOURCE + "x", PIECES, ROWS)


def test_native_input_tap_rejects_token_id_and_row_count_mismatch():
    wrong = [dict(piece) for piece in PIECES]
    wrong[0]["id"] = 999
    with pytest.raises(LatentAdapterError, match="piece ID differs"):
        validate(make()["manifest"], SOURCE, wrong, ROWS)
    with pytest.raises(LatentAdapterError, match="rows do not match"):
        build(
            "C3_LANGUAGE", SOURCE, IDS, PIECES, ROWS[:-1], source_id="s1",
            event_id="e1", brain_generation_id="g1",
            model_revision="model-r1", model_sha256=MODEL_SHA,
            tokenizer_revision="tokenizer-r1", extractor_receipt=receipt(),
        )


@pytest.mark.parametrize("overrides,match", [
    ({"token_ids": list(reversed(IDS))}, "requested token IDs/order"),
    ({"elements_written": len(IDS) * 3 - 1}, "element count"),
    ({"embedding_dim": 4}, "dimension"),
    ({"vocab_size": 17}, "outside the receiver vocabulary"),
    ({"output_dtype": "f16"}, "must be F32"),
    ({"api_symbol": "llama_model_get_tok_embd"}, "API identity"),
    ({"llama_cpp_revision": "not-a-commit"}, "revision is invalid"),
    ({"extractor_binary_sha256": "z" * 64}, "binary SHA-256"),
    ({"model_sha256": "c" * 64}, "model binding"),
    ({"model_revision": "other-model"}, "model binding"),
    ({"source_tensor_type": "Q4/0"}, "tensor type"),
])
def test_native_input_tap_rejects_unbound_or_incomplete_extractor_receipts(overrides, match):
    with pytest.raises(LatentAdapterError, match=match):
        make(**overrides)


def test_native_input_tap_manifest_rejects_receipt_tampering_even_if_rows_match():
    manifest = copy.deepcopy(make()["manifest"])
    manifest["extractor_receipt"]["requested_token_ids"][0] = 999
    with pytest.raises(LatentAdapterError, match="requested token IDs/order"):
        validate(manifest, SOURCE, PIECES, ROWS)


def test_native_input_tap_preserves_repeated_token_ids_without_deduplication():
    source = "ababcd"
    token_ids = [10, 10, 11]
    pieces = [
        {"id": 10, "piece": "ab"},
        {"id": 10, "piece": "ab"},
        {"id": 11, "piece": "cd"},
    ]
    rows = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
    result = build(
        "C3_LANGUAGE", source, token_ids, pieces, rows,
        source_id="repeat-source", event_id="repeat-event",
        brain_generation_id="repeat-generation", model_revision="model-r1",
        model_sha256=MODEL_SHA, tokenizer_revision="tokenizer-r1",
        extractor_receipt=receipt(
            token_ids=token_ids, elements_written=9, embedding_dim=3,
        ),
    )
    assert result["manifest"]["token_ids"] == token_ids
    assert result["manifest"]["extractor_receipt"]["requested_token_ids"] == token_ids
    assert result["manifest"]["row_positions"] == [0, 1, 2]
    assert validate(result["manifest"], source, pieces, rows) == result


def extractor_output(**overrides):
    value = receipt()
    output = {
        "status": "COMPLETE",
        "receipt": value,
        "rows": ROWS,
        "model_sha256": MODEL_SHA,
        "extractor_binary_sha256": value["extractor_binary_sha256"],
    }
    output.update(overrides)
    return output


def build_from_extractor_output(output):
    from v13.native_input_embedding_tap import (
        build_native_input_embedding_tap_manifest_from_extractor_output,
    )
    return build_native_input_embedding_tap_manifest_from_extractor_output(
        "C3_LANGUAGE", SOURCE, IDS, PIECES, output,
        source_id="s1", event_id="e1", brain_generation_id="g1",
        model_revision="model-r1", model_sha256=MODEL_SHA,
        tokenizer_revision="tokenizer-r1",
    )


def test_extractor_output_bridge_builds_and_validates_one_bound_manifest():
    output = extractor_output()
    result = build_from_extractor_output(output)
    assert result["vectors"] == ROWS
    assert result["manifest"]["extractor_receipt"] == output["receipt"]
    assert validate(result["manifest"], SOURCE, PIECES, ROWS) == result


@pytest.mark.parametrize("overrides,match", [
    ({"status": "FAILED"}, "not complete"),
    ({"model_sha256": "c" * 64}, "model SHA differs"),
    ({"extractor_binary_sha256": "c" * 64}, "hashes differ from its receipt"),
    ({"extra": "untrusted"}, "fields are not canonical"),
    ({"rows": None}, "rows do not match"),
])
def test_extractor_output_bridge_rejects_partial_or_mixed_results(overrides, match):
    with pytest.raises(LatentAdapterError, match=match):
        build_from_extractor_output(extractor_output(**overrides))


def test_extractor_output_bridge_rejects_receipt_hash_drift():
    output = extractor_output()
    output["receipt"] = dict(output["receipt"])
    output["receipt"]["model_sha256"] = "c" * 64
    with pytest.raises(LatentAdapterError, match="hashes differ from its receipt"):
        build_from_extractor_output(output)

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


def make(role="C3_LANGUAGE"):
    return build(
        role, SOURCE, IDS, PIECES, ROWS, source_id="s1", event_id="e1",
        brain_generation_id="g1", model_revision="model-r1",
        tokenizer_revision="tokenizer-r1",
    )


def test_native_input_tap_binds_exact_role_source_rows_and_model():
    result = make()
    m = result["manifest"]
    assert m["tap_id"] == "c3.input-embedding.v1"
    assert m["activation_space"] == "INPUT_EMBEDDING_F32"
    assert m["source_span_unit"] == "UTF8_BYTE"
    assert m["row_positions"] == list(range(8))
    assert m["embedding_dim"] == 3
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
    m = dict(result["manifest"])
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
            model_revision="model-r1", tokenizer_revision="tokenizer-r1",
        )

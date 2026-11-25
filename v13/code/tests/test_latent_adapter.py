import hashlib
import json

import numpy as np
import pytest

from v13.latent_adapter import (
    LatentAdapterError, _activation_vector_sha256, _alignment_manifest_sha256, _token_pair_id,
    align_token_rows_by_byte_pieces, align_token_rows_by_char_span, build_native_receiver_input,
    fit_adapter, token_piece_byte_spans, project_event, project_rows, project_vector,
    save_adapter, load_adapter,
)

SENDER_HASH = "a" * 64
RECEIVER_HASH = "b" * 64


def make_pairs(prefix, groups, *, seed, shuffled=False):
    rng = np.random.default_rng(seed)
    basis = np.asarray([[1.0, 0.0], [0.0, 1.0], [0.5, 0.3], [-0.2, 0.4], [0.1, -0.3], [0.2, 0.1]])
    target = np.asarray([[1.2, -0.4, 0.7, 0.2], [0.3, 0.8, -0.6, 1.0]])
    spans = [[sample * 2, sample * 2 + 2] for sample in range(4)]
    source_groups = []
    for group in range(groups):
        source_id = f"{prefix}-source-{group}"
        source_sha256 = hashlib.sha256(source_id.encode("utf-8")).hexdigest()
        sender_rows = []
        receiver_rows = []
        for _sample in range(4):
            z = rng.normal(size=2)
            x = z @ basis.T + rng.normal(scale=0.001, size=6)
            y = z @ target + np.asarray([0.2, -0.1, 0.3, 0.05]) + rng.normal(scale=0.001, size=4)
            sender_rows.append(x.tolist())
            receiver_rows.append(y.tolist())
        source_groups.append((source_id, source_sha256, sender_rows, receiver_rows))
    if shuffled:
        receiver_rows = [row for _source_id, _source_hash, _senders, rows in source_groups for row in rows]
        rng.shuffle(receiver_rows)
        cursor = 0
        rebuilt = []
        for source_id, source_sha256, sender_rows, rows in source_groups:
            count = len(rows)
            rebuilt.append((source_id, source_sha256, sender_rows, receiver_rows[cursor:cursor + count]))
            cursor += count
        source_groups = rebuilt
    result = []
    for source_id, source_sha256, sender_rows, receiver_rows in source_groups:
        result.extend(align_token_rows_by_char_span(
            sender_rows, spans, receiver_rows, spans,
            source_id=source_id, source_sha256=source_sha256,
        ))
    return result

def make_aligned_tokenwise_pairs(prefix, groups, *, seed):
    rng = np.random.default_rng(seed)
    target = np.asarray([[1.2, -0.4, 0.7], [0.3, 0.8, -0.6]])
    rows = []
    sender_spans = [[0, 2], [2, 4], [4, 6]]
    receiver_spans = [[0, 3], [3, 6]]
    for group in range(groups):
        source_id = f"{prefix}-aligned-source-{group}"
        source_sha256 = hashlib.sha256(source_id.encode("utf-8")).hexdigest()
        z = rng.normal(size=(2, 2))
        middle = (z[0] + z[1]) / 2.0
        sender_rows = [
            (3.0 * z[0] - middle) / 2.0,
            middle,
            (3.0 * z[1] - middle) / 2.0,
        ]
        receiver_rows = z @ target + np.asarray([0.2, -0.1, 0.3])
        receiver_rows += rng.normal(scale=0.001, size=(2, 3))
        rows.extend(align_token_rows_by_char_span(
            [row.tolist() for row in sender_rows], sender_spans, receiver_rows.tolist(), receiver_spans,
            source_id=source_id, source_sha256=source_sha256,
        ))
    return rows


def fit(train=None, holdout=None, **overrides):
    args = dict(
        sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
        sender_tap_id="b2.gist.layer-final.v1", receiver_tap_id="c3.input-embedding.v1",
        sender_model_revision="b2-test-r1", receiver_model_revision="c3-test-r1",
        sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
        rank=2, ridge=1e-5,
    )
    args.update(overrides)
    if args.get("projection_scope") == "TOKENWISE":
        args["sender_tokenizer_revision"] = "sender-tokenizer-r1"
        args["receiver_tokenizer_revision"] = "tokenizer-r1"
    return fit_adapter(train or make_pairs("train", 10, seed=1), holdout or make_pairs("hold", 5, seed=2), **args)


def test_low_rank_adapter_generalizes_across_disjoint_sources():
    adapter = fit()
    assert adapter["status"] == "ALIGNMENT_CANDIDATE"
    assert adapter["sender_dim"] == 6 and adapter["receiver_dim"] == 4
    assert adapter["rank"] == 2
    assert adapter["metrics"]["relative_improvement"] > 0.95
    assert adapter["metrics"]["holdout_mse"] < adapter["metrics"]["shuffled_train_mse"]
    assert adapter["production_route"] is False
    assert adapter["semantic_use_proven"] is False
    assert adapter["training_authority"] == adapter["native_receiver_authority"] == 0


def test_source_group_leakage_is_rejected():
    train = make_pairs("train", 8, seed=1)
    holdout = make_pairs("hold", 4, seed=2)
    holdout[0]["source_id"] = train[0]["source_id"]
    with pytest.raises(LatentAdapterError, match="source leakage"):
        fit_adapter(train, holdout, sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
                    sender_tap_id="s", receiver_tap_id="r", sender_model_revision="s1",
                    receiver_model_revision="r1", sender_model_sha256=SENDER_HASH,
                    receiver_model_sha256=RECEIVER_HASH, rank=2)


def test_shuffled_pairing_does_not_open_alignment_candidate_gate():
    adapter = fit(train=make_pairs("train", 10, seed=1, shuffled=True), holdout=make_pairs("hold", 5, seed=2))
    assert adapter["status"] == "REJECTED"


def test_projection_rejects_wrong_model_or_tap_binding():
    adapter = fit()
    vector = make_pairs("probe", 1, seed=99)[0]["sender_vector"]
    with pytest.raises(LatentAdapterError, match="binding mismatch"):
        project_vector(adapter, vector, sender_model_sha256="c"*64,
                       receiver_model_sha256=RECEIVER_HASH,
                       sender_tap_id=adapter["sender_tap_id"], receiver_tap_id=adapter["receiver_tap_id"])


def test_checkpoint_roundtrip_and_tamper_detection(tmp_path):
    adapter = fit()
    path = tmp_path / "adapter.v14lat"
    saved_hash = save_adapter(adapter, path)
    restored = load_adapter(path)
    assert restored["adapter_sha256"] == saved_hash
    assert restored["projection_scope"] == "PAIRED_VECTOR"
    vector = make_pairs("probe", 1, seed=99)[0]["sender_vector"]
    kwargs = dict(sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
                  sender_tap_id=adapter["sender_tap_id"], receiver_tap_id=adapter["receiver_tap_id"])
    assert np.allclose(project_vector(adapter, vector, **kwargs), project_vector(restored, vector, **kwargs), atol=1e-6)
    damaged = bytearray(path.read_bytes())
    damaged[-1] ^= 0x01
    path.write_bytes(damaged)
    with pytest.raises(LatentAdapterError, match="weight digest"):
        load_adapter(path)


def test_projection_scope_prevents_event_vector_broadcast_to_token_rows():
    event_adapter = fit()
    vector = make_pairs("probe", 1, seed=99)[0]["sender_vector"]
    bindings = dict(sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
                    sender_tap_id=event_adapter["sender_tap_id"], receiver_tap_id=event_adapter["receiver_tap_id"])
    with pytest.raises(LatentAdapterError, match="event-level adapter"):
        project_rows(event_adapter, [vector, vector], **bindings)

    token_adapter = fit(projection_scope="TOKENWISE")
    token_bindings = dict(sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
                          sender_tap_id=token_adapter["sender_tap_id"], receiver_tap_id=token_adapter["receiver_tap_id"])
    projected = project_rows(token_adapter, [vector, vector], **token_bindings)
    assert len(projected) == 2 and all(len(row) == token_adapter["receiver_dim"] for row in projected)
    with pytest.raises(LatentAdapterError, match="tokenwise adapter"):
        project_event(token_adapter, vector, **token_bindings)



def test_tokenwise_adapter_builds_exact_native_receiver_input_contract():
    from v13 import native_latent_receiver

    adapter = fit(projection_scope="TOKENWISE")
    vectors = [
        make_pairs("probe", 1, seed=99)[0]["sender_vector"],
        make_pairs("probe", 1, seed=100)[1]["sender_vector"],
    ]
    bindings = dict(sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
                    sender_tap_id=adapter["sender_tap_id"], receiver_tap_id=adapter["receiver_tap_id"])
    packet = build_native_receiver_input(
        adapter, vectors, token_ids=[101, 102], tokenizer_revision="tokenizer-r1", **bindings,
    )
    rows, dim, payload, digest = native_latent_receiver._vector_payload(packet["vectors"])
    positions = native_latent_receiver._validate_positions(
        packet["position_ids"], rows, packet["position_mode"],
    )
    assert rows == packet["input_rows"] == 2
    assert dim == packet["input_dim"] == adapter["receiver_dim"]
    assert packet["position_mode"] == native_latent_receiver.POSITION_MODE
    assert positions == [0, 1]
    assert packet["input_sha256"] == digest
    assert len(payload) == rows * dim * 4
    assert packet["production_route"] is False
    assert packet["semantic_use_proven"] is False
    assert packet["training_authority"] == packet["native_receiver_authority"] == 0


def test_native_receiver_builder_rejects_pooled_or_non_input_space_adapters():
    vectors = [make_pairs("probe", 1, seed=99)[0]["sender_vector"]]
    event_adapter = fit()
    event_bindings = dict(sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
                          sender_tap_id=event_adapter["sender_tap_id"], receiver_tap_id=event_adapter["receiver_tap_id"])
    with pytest.raises(LatentAdapterError, match="tokenwise adapter"):
        build_native_receiver_input(
            event_adapter, vectors, token_ids=[101], tokenizer_revision="tokenizer-r1", **event_bindings,
        )

    wrong_tap_adapter = fit(receiver_tap_id="c3.final-rmsnorm.v1", projection_scope="TOKENWISE")
    wrong_bindings = dict(sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
                          sender_tap_id=wrong_tap_adapter["sender_tap_id"], receiver_tap_id=wrong_tap_adapter["receiver_tap_id"])
    with pytest.raises(LatentAdapterError, match="input-embedding tap"):
        build_native_receiver_input(
            wrong_tap_adapter, vectors, token_ids=[101], tokenizer_revision="tokenizer-r1", **wrong_bindings,
        )


def test_native_receiver_builder_rejects_tokenizer_row_mismatch():
    adapter = fit(projection_scope="TOKENWISE")
    vectors = [make_pairs("probe", 1, seed=99)[0]["sender_vector"]]
    bindings = dict(sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
                    sender_tap_id=adapter["sender_tap_id"], receiver_tap_id=adapter["receiver_tap_id"])
    with pytest.raises(LatentAdapterError, match="token ID count"):
        build_native_receiver_input(
            adapter, vectors, token_ids=[101, 102], tokenizer_revision="tokenizer-r1", **bindings,
        )
    with pytest.raises(LatentAdapterError, match="receiver tokenizer revision mismatch"):
        build_native_receiver_input(
            adapter, vectors, token_ids=[101], tokenizer_revision="other-tokenizer-r1", **bindings,
        )



def test_char_span_alignment_handles_different_tokenizer_segmentations():
    aligned = align_token_rows_by_char_span(
        sender_vectors=[[1.0, 0.0], [3.0, 0.0], [5.0, 0.0]],
        sender_spans=[[0, 2], [2, 4], [4, 6]],
        receiver_vectors=[[0.0, 1.0], [0.0, 3.0]],
        receiver_spans=[[0, 3], [3, 6]],
        source_id="source-different-tokenizers",
        source_sha256="c" * 64,
    )
    assert [row["token_position"] for row in aligned] == [0, 1]
    assert [row["source_span"] for row in aligned] == [[0, 3], [3, 6]]
    assert aligned[0]["sender_vector"] == pytest.approx([5.0 / 3.0, 0.0])
    assert aligned[1]["sender_vector"] == pytest.approx([13.0 / 3.0, 0.0])
    assert [row["alignment_coverage"] for row in aligned] == [1.0, 1.0]
    assert len({row["alignment_id"] for row in aligned}) == 1


def test_tokenwise_fit_rejects_activation_mutation_after_alignment():
    train = make_aligned_tokenwise_pairs("train", 10, seed=11)
    holdout = make_aligned_tokenwise_pairs("hold", 5, seed=12)
    train[0]["sender_vector"][0] += 0.25
    with pytest.raises(LatentAdapterError, match="activation vector digest mismatch"):
        fit_adapter(
            train, holdout,
            sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
            sender_tap_id="b2.gist.layer-final.v1", receiver_tap_id="c3.input-embedding.v1",
            sender_model_revision="b2-test-r1", receiver_model_revision="c3-test-r1",
            sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
            projection_scope="TOKENWISE",
            sender_tokenizer_revision="sender-tokenizer-r1",
            receiver_tokenizer_revision="tokenizer-r1",
            rank=2, ridge=1e-5,
        )


def test_tokenwise_fit_rejects_rehashed_activation_with_stale_pair_id():
    train = make_aligned_tokenwise_pairs("train", 10, seed=11)
    holdout = make_aligned_tokenwise_pairs("hold", 5, seed=12)
    train[0]["sender_vector"][0] += 0.25
    train[0]["sender_vector_sha256"] = _activation_vector_sha256(train[0]["sender_vector"])
    with pytest.raises(LatentAdapterError, match="pair ID does not bind"):
        fit_adapter(
            train, holdout,
            sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
            sender_tap_id="b2.gist.layer-final.v1", receiver_tap_id="c3.input-embedding.v1",
            sender_model_revision="b2-test-r1", receiver_model_revision="c3-test-r1",
            sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
            projection_scope="TOKENWISE",
            sender_tokenizer_revision="sender-tokenizer-r1",
            receiver_tokenizer_revision="tokenizer-r1",
            rank=2, ridge=1e-5,
        )


def test_alignment_digest_changes_when_activation_rows_change():
    train_a = make_aligned_tokenwise_pairs("train", 10, seed=11)
    holdout_a = make_aligned_tokenwise_pairs("hold", 5, seed=12)
    train_b = make_aligned_tokenwise_pairs("train", 10, seed=111)
    holdout_b = make_aligned_tokenwise_pairs("hold", 5, seed=112)
    kwargs = dict(
        sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
        sender_tap_id="b2.gist.layer-final.v1", receiver_tap_id="c3.input-embedding.v1",
        sender_model_revision="b2-test-r1", receiver_model_revision="c3-test-r1",
        sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
        projection_scope="TOKENWISE",
        sender_tokenizer_revision="sender-tokenizer-r1",
        receiver_tokenizer_revision="tokenizer-r1",
        rank=2, ridge=1e-5,
    )
    adapter_a = fit_adapter(train_a, holdout_a, **kwargs)
    adapter_b = fit_adapter(train_b, holdout_b, **kwargs)
    assert adapter_a["alignment_sha256"] != adapter_b["alignment_sha256"]


def test_char_span_alignment_rejects_uncovered_receiver_text():
    with pytest.raises(LatentAdapterError, match="sufficiently cover"):
        align_token_rows_by_char_span(
            sender_vectors=[[1.0, 0.0], [2.0, 0.0]],
            sender_spans=[[0, 1], [4, 6]],
            receiver_vectors=[[0.0, 1.0], [0.0, 2.0]],
            receiver_spans=[[0, 3], [3, 6]],
            source_id="source-gap",
            source_sha256="d" * 64,
        )


def test_char_span_alignment_rejects_overlapping_or_unordered_spans():
    with pytest.raises(LatentAdapterError, match="overlap or are out of order"):
        align_token_rows_by_char_span(
            sender_vectors=[[1.0, 0.0], [2.0, 0.0]],
            sender_spans=[[0, 3], [2, 4]],
            receiver_vectors=[[0.0, 1.0], [0.0, 2.0]],
            receiver_spans=[[0, 2], [2, 4]],
            source_id="source-overlap",
            source_sha256="e" * 64,
        )


def test_char_span_alignment_feeds_source_disjoint_tokenwise_adapter_fit():
    adapter = fit_adapter(
        make_aligned_tokenwise_pairs("train", 10, seed=11),
        make_aligned_tokenwise_pairs("hold", 5, seed=12),
        sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
        sender_tap_id="b2.gist.layer-final.v1", receiver_tap_id="c3.input-embedding.v1",
        sender_model_revision="b2-test-r1", receiver_model_revision="c3-test-r1",
        sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
        sender_tokenizer_revision="sender-tokenizer-r1",
        receiver_tokenizer_revision="tokenizer-r1",
        rank=2, projection_scope="TOKENWISE",
    )
    assert adapter["schema"] == "v14.cross-organ-latent-adapter/3"
    assert adapter["status"] == "ALIGNMENT_CANDIDATE"
    assert adapter["alignment_method"] == "CHAR_SPAN_OVERLAP_V1"
    assert len(adapter["alignment_sha256"]) == 64
    assert adapter["metrics"]["gradient_based_training"] is False
    assert adapter["semantic_use_proven"] is False


def test_tokenwise_fit_rejects_source_hash_leakage_across_holdout():
    train = make_aligned_tokenwise_pairs("train", 10, seed=21)
    holdout = make_aligned_tokenwise_pairs("hold", 5, seed=22)
    leaked_source = holdout[0]["source_id"]
    leaked_hash = train[0]["source_sha256"]
    leaked_alignment = _alignment_manifest_sha256(
        method="CHAR_SPAN_OVERLAP_V1",
        source_id=leaked_source,
        source_sha256=leaked_hash,
        sender_spans=[[0, 2], [2, 4], [4, 6]],
        receiver_spans=[[0, 3], [3, 6]],
        source_span_unit="CHARACTER",
    )
    for row in holdout:
        if row["source_id"] == leaked_source:
            row["source_sha256"] = leaked_hash
            row["alignment_id"] = leaked_alignment
            row["pair_id"] = _token_pair_id(
                source_id=row["source_id"],
                source_sha256=row["source_sha256"],
                token_position=row["token_position"],
                source_span=row["source_span"],
                alignment_id=row["alignment_id"],
                alignment_coverage=row["alignment_coverage"],
                sender_vector_sha256=row["sender_vector_sha256"],
                receiver_vector_sha256=row["receiver_vector_sha256"],
            )
    with pytest.raises(LatentAdapterError, match="source hash leakage"):
        fit(train=train, holdout=holdout, projection_scope="TOKENWISE")


def test_tokenwise_checkpoint_roundtrip_preserves_alignment_contract(tmp_path):
    adapter = fit(projection_scope="TOKENWISE")
    path = tmp_path / "tokenwise-adapter.v14lat"
    saved_hash = save_adapter(adapter, path)
    restored = load_adapter(path)
    assert restored["adapter_sha256"] == saved_hash
    assert restored["schema"] == "v14.cross-organ-latent-adapter/3"
    assert restored["alignment_method"] == "CHAR_SPAN_OVERLAP_V1"
    assert restored["alignment_sha256"] == adapter["alignment_sha256"]
    assert restored["sender_tokenizer_revision"] == "sender-tokenizer-r1"
    assert restored["receiver_tokenizer_revision"] == "tokenizer-r1"


def test_tokenwise_fit_rejects_position_only_pairs_without_span_proof():
    train = make_pairs("train", 10, seed=1)
    holdout = make_pairs("hold", 5, seed=2)
    for row in train + holdout:
        row.pop("source_span")
        row.pop("alignment_method")
        row.pop("alignment_id")
        row.pop("alignment_coverage")
        row.pop("source_span_unit")
        row.pop("source_length")
        row.pop("sender_spans")
    with pytest.raises(LatentAdapterError, match="source_span alignment"):
        fit(train=train, holdout=holdout, projection_scope="TOKENWISE")


@pytest.mark.parametrize("mutation,match", [
    ("missing", "require bounded token_position"),
    ("duplicate", "duplicate token position"),
    ("gap", "contiguous rows"),
])
def test_tokenwise_fit_requires_source_local_contiguous_positions(mutation, match):
    train = make_pairs("train", 10, seed=1)
    holdout = make_pairs("hold", 5, seed=2)
    if mutation == "missing":
        del train[0]["token_position"]
    elif mutation == "duplicate":
        train[1]["token_position"] = train[0]["token_position"]
    else:
        train[0]["token_position"] = 7
    with pytest.raises(LatentAdapterError, match=match):
        fit(train=train, holdout=holdout, projection_scope="TOKENWISE")


def _byte_piece_groups(prefix, groups):
    source_prefix = "A\u00e1\U0001f9e0e\u0301"
    result = []
    for group in range(groups):
        source_text = f"{prefix}-{group}: {source_prefix}"
        source_bytes = source_text.encode("utf-8")
        sender_pieces = [{"id": index + 1, "piece": [byte]} for index, byte in enumerate(source_bytes)]
        receiver_chunks = [source_bytes[:4], source_bytes[4:9], source_bytes[9:]]
        receiver_pieces = [{"id": index + 100, "piece": list(chunk)}
                           for index, chunk in enumerate(receiver_chunks) if chunk]
        sender_vectors = [[float(i), float(i + 1)] for i in range(len(sender_pieces))]
        receiver_vectors = [[float(i + 1), float(i + 2), float(i + 3)]
                            for i in range(len(receiver_pieces))]
        result.extend(align_token_rows_by_byte_pieces(
            sender_vectors, sender_pieces, receiver_vectors, receiver_pieces,
            source_id=f"{prefix}-byte-source-{group}", source_text=source_text,
        ))
    return result


def test_token_piece_byte_spans_accept_llama_cpp_raw_byte_pieces_and_unicode_splits():
    source = "A\u00e1\U0001f9e0e\u0301"
    pieces = [
        {"id": 1, "piece": "A"},
        {"id": 2, "piece": [0xC3]},
        {"id": 3, "piece": [0xA1, 0xF0]},
        {"id": 4, "piece": [0x9F, 0xA7]},
        {"id": 5, "piece": [0xA0]},
        {"id": 6, "piece": "e"},
        {"id": 7, "piece": [0xCC]},
        {"id": 8, "piece": [0x81]},
    ]
    metadata = token_piece_byte_spans(pieces, source)
    assert metadata["source_sha256"] == hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert metadata["source_length"] == len(source.encode("utf-8"))
    assert metadata["token_spans"][1] == [1, 2]
    assert metadata["token_spans"][2] == [2, 4]
    assert metadata["token_spans"][-1][1] == metadata["source_length"]


def test_utf8_byte_piece_alignment_fits_a_tokenwise_adapter_with_distinct_segmentations():
    adapter = fit_adapter(
        _byte_piece_groups("byte-train", 10),
        _byte_piece_groups("byte-hold", 5),
        sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
        sender_tap_id="b2.gist.layer-final.v1", receiver_tap_id="c3.input-embedding.v1",
        sender_model_revision="b2-test-r1", receiver_model_revision="c3-test-r1",
        sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
        sender_tokenizer_revision="sender-tokenizer-r1",
        receiver_tokenizer_revision="tokenizer-r1",
        rank=2, projection_scope="TOKENWISE",
    )
    assert adapter["alignment_method"] == "UTF8_BYTE_PIECE_OVERLAP_V1"
    assert adapter["schema"] == "v14.cross-organ-latent-adapter/3"
    assert adapter["semantic_use_proven"] is False
    assert adapter["training_authority"] == adapter["native_receiver_authority"] == 0


def test_token_piece_byte_spans_reject_non_exact_or_empty_piece_streams():
    with pytest.raises(LatentAdapterError, match="do not reconstruct"):
        token_piece_byte_spans([b"not", b"the source"], "source")
    with pytest.raises(LatentAdapterError, match="empty/special"):
        token_piece_byte_spans([b"source", b""], "source")


def test_tokenwise_manifest_digest_rejects_sender_span_tampering():
    train = make_aligned_tokenwise_pairs("train", 10, seed=31)
    holdout = make_aligned_tokenwise_pairs("hold", 5, seed=32)
    tampered = [dict(row) for row in train]
    for row in tampered:
        row["sender_spans"] = [[0, 1], [1, 4], [4, 6]]
    with pytest.raises(LatentAdapterError, match="manifest digest"):
        fit_adapter(
            tampered, holdout,
            sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
            sender_tap_id="b2.gist.layer-final.v1", receiver_tap_id="c3.input-embedding.v1",
            sender_model_revision="b2-test-r1", receiver_model_revision="c3-test-r1",
            sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
            projection_scope="TOKENWISE",
            sender_tokenizer_revision="sender-tokenizer-r1",
            receiver_tokenizer_revision="tokenizer-r1",
            rank=2, ridge=1e-5,
        )


def test_tokenwise_fit_recomputes_alignment_coverage_instead_of_trusting_metadata():
    train = make_aligned_tokenwise_pairs("train", 10, seed=41)
    holdout = make_aligned_tokenwise_pairs("hold", 5, seed=42)
    item = train[0]
    item["alignment_coverage"] = 0.80
    item["pair_id"] = _token_pair_id(
        source_id=item["source_id"], source_sha256=item["source_sha256"],
        token_position=item["token_position"], source_span=item["source_span"],
        alignment_id=item["alignment_id"], alignment_coverage=item["alignment_coverage"],
        sender_vector_sha256=item["sender_vector_sha256"],
        receiver_vector_sha256=item["receiver_vector_sha256"],
    )
    with pytest.raises(LatentAdapterError, match="coverage mismatch"):
        fit_adapter(
            train, holdout,
            sender_role="B2_GIST", receiver_role="C3_LANGUAGE",
            sender_tap_id="b2.gist.layer-final.v1", receiver_tap_id="c3.input-embedding.v1",
            sender_model_revision="b2-test-r1", receiver_model_revision="c3-test-r1",
            sender_model_sha256=SENDER_HASH, receiver_model_sha256=RECEIVER_HASH,
            projection_scope="TOKENWISE",
            sender_tokenizer_revision="sender-tokenizer-r1",
            receiver_tokenizer_revision="tokenizer-r1",
            rank=2, ridge=1e-5,
        )

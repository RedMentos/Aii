import hashlib
import json
from pathlib import Path

import pytest

from v13.common import atomic_write, dumps, file_hash
from v13.contracts import packet
from v13.models import model_key
from v13.native_latent_pairing import (
    NativeTapPairError,
    pair_taps,
    validate_pair_packet,
)
from v13.runtime import Runtime


TOKEN_IDS = [101, 202]
TAP_ID = "lfm2.result_norm.final.v1"
TOKENIZER_REVISION = "lfm2-tokenizer-r1"
MODEL_REVISIONS = {
    "B1_DETAIL": "lfm2-b1-r1",
    "C3_LANGUAGE": "lfm2-c3-r1",
}


def setup_runtime(tmp_path):
    runtime = Runtime(Path(tmp_path))
    runtime.sleep.cycle.set_policy("enabled", "off")
    event = runtime.store.event(runtime.session, "private native tap source stays local")
    model_dir = runtime.home / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    hashes = {}
    for role, filename in (
        ("B1_DETAIL", "b1-detail.gguf"),
        ("C3_LANGUAGE", "c3-language.gguf"),
    ):
        path = model_dir / filename
        path.write_bytes(("fixture:" + role).encode())
        paths[role] = path
        hashes[role] = hashlib.sha256(path.read_bytes()).hexdigest()
        key = model_key(role, runtime.models.b2_control)
        runtime.models.installed[key] = {
            "download_complete": True,
            "exact_revision": MODEL_REVISIONS[role],
            "main_file": filename,
            "files": {filename: {"sha256": hashes[role]}},
        }
    runtime.models.path_for = lambda role: paths[role]
    runtime.models.revision = lambda role: MODEL_REVISIONS[role]
    return runtime, event, hashes


def add_tap(runtime, event, role, dimension, vectors, token_ids=None, source_ref=None):
    token_ids = list(TOKEN_IDS if token_ids is None else token_ids)
    source_ref = event["source_ref"] if source_ref is None else source_ref
    payload = {"token_ids": token_ids, "vectors": vectors}
    path = runtime.home / "data" / "blobs" / (role.lower() + "-tap.json")
    atomic_write(path, dumps(payload))
    tap_packet = packet(
        "LatentTapPacket",
        role,
        event["event_id"],
        event["brain_generation_id"],
        [source_ref],
        role=role,
        source_ref=source_ref,
        tap_id=TAP_ID,
        model_revision=MODEL_REVISIONS.get(role, "fixture-r1"),
        tokenizer_revision=TOKENIZER_REVISION,
        token_ids=token_ids,
        feature_path=str(path.relative_to(runtime.home)),
        feature_sha256=file_hash(path),
        shape=[len(token_ids), dimension],
        metrics={
            "whole_sequence_prefill": True,
            "pooling": "none",
            "prompt_tokens": len(token_ids),
        },
    )
    runtime.store.add_packet("LatentTapPacket", tap_packet)
    return tap_packet


def test_exact_b1_c3_pair_is_persisted_without_training_authority(tmp_path):
    runtime, event, hashes = setup_runtime(tmp_path)
    try:
        sender = add_tap(
            runtime, event, "B1_DETAIL", 2048,
            [[0.125] * 2048, [-0.25] * 2048],
        )
        receiver = add_tap(
            runtime, event, "C3_LANGUAGE", 1024,
            [[0.5] * 1024, [-0.75] * 1024],
        )
        pair = pair_taps(
            runtime.cognition, sender, receiver,
            hashes["B1_DETAIL"], hashes["C3_LANGUAGE"],
        )
        checked = validate_pair_packet(pair)
        assert checked["sender_role"] == "B1_DETAIL"
        assert checked["receiver_role"] == "C3_LANGUAGE"
        assert checked["sender_shape"] == [2, 2048]
        assert checked["receiver_shape"] == [2, 1024]
        assert checked["token_count"] == 2
        assert checked["alignment"] == "TOKEN_IDS_EXACT"
        assert checked["status"] == "PAIRED_READ_ONLY"
        assert checked["training_authority"] == 0
        assert checked["native_receiver_authority"] == 0
        assert checked["production_route"] is False
        assert checked["source_ref"] == event["source_ref"]
        assert checked["provenance"] == [event["source_ref"]]
        assert checked["sender_tap_packet_id"] == sender["packet_id"]
        assert checked["receiver_tap_packet_id"] == receiver["packet_id"]
        stored = runtime.store.one(
            "SELECT payload FROM packets WHERE kind='LatentTapPairPacket' ORDER BY rowid DESC LIMIT 1"
        )
        assert json.loads(stored["payload"]) == pair
        serialized = json.dumps(pair, sort_keys=True)
        assert "private native tap source" not in serialized
        assert "0.125" not in serialized
    finally:
        runtime.close()


def test_pair_rejects_tokenizer_or_source_misalignment(tmp_path):
    runtime, event, hashes = setup_runtime(tmp_path)
    try:
        sender = add_tap(
            runtime, event, "B1_DETAIL", 2048,
            [[0.1] * 2048, [0.2] * 2048],
        )
        mismatched_tokens = add_tap(
            runtime, event, "C3_LANGUAGE", 1024,
            [[0.3] * 1024, [0.4] * 1024],
            token_ids=[101, 303],
        )
        with pytest.raises(NativeTapPairError, match="tokenizer output differs"):
            pair_taps(runtime.cognition, sender, mismatched_tokens,
                      hashes["B1_DETAIL"], hashes["C3_LANGUAGE"])

        other_event = runtime.store.event(runtime.session, "different source")
        wrong_source = add_tap(
            runtime, other_event, "C3_LANGUAGE", 1024,
            [[0.3] * 1024, [0.4] * 1024],
        )
        with pytest.raises(NativeTapPairError, match="event, generation or SourceRef"):
            pair_taps(runtime.cognition, sender, wrong_source,
                      hashes["B1_DETAIL"], hashes["C3_LANGUAGE"])
    finally:
        runtime.close()


def test_pair_rejects_tampered_features_and_invalid_model_hash(tmp_path):
    runtime, event, hashes = setup_runtime(tmp_path)
    try:
        sender = add_tap(
            runtime, event, "B1_DETAIL", 2048,
            [[0.1] * 2048, [0.2] * 2048],
        )
        receiver = add_tap(
            runtime, event, "C3_LANGUAGE", 1024,
            [[0.3] * 1024, [0.4] * 1024],
        )
        with pytest.raises(NativeTapPairError, match="lowercase SHA-256"):
            pair_taps(runtime.cognition, sender, receiver, "bad", hashes["C3_LANGUAGE"])

        feature = runtime.home / sender["feature_path"]
        atomic_write(feature, "tampered")
        with pytest.raises(ValueError):
            pair_taps(runtime.cognition, sender, receiver,
                      hashes["B1_DETAIL"], hashes["C3_LANGUAGE"])
    finally:
        runtime.close()


def test_pair_packet_rejects_authority_promotion_and_binding_drift(tmp_path):
    runtime, event, hashes = setup_runtime(tmp_path)
    try:
        sender = add_tap(
            runtime, event, "B1_DETAIL", 2048,
            [[0.1] * 2048, [0.2] * 2048],
        )
        receiver = add_tap(
            runtime, event, "C3_LANGUAGE", 1024,
            [[0.3] * 1024, [0.4] * 1024],
        )
        pair = pair_taps(runtime.cognition, sender, receiver,
                         hashes["B1_DETAIL"], hashes["C3_LANGUAGE"])
        with pytest.raises(NativeTapPairError, match="cannot grant"):
            validate_pair_packet(dict(pair, training_authority=1))
        with pytest.raises(NativeTapPairError, match="binding hash mismatch"):
            validate_pair_packet(dict(pair, sender_model_sha256="f" * 64))
    finally:
        runtime.close()

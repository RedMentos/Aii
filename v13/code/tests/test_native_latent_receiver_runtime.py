import hashlib
import json
import tempfile
import time
from pathlib import Path

import pytest

from v13.runtime import Runtime
from v13.models import model_key
from v13.common import atomic_write, dumps, file_hash, uid
from v13.contracts import packet, validate
from v13.callosum import controller, operator_command
from v13 import native_latent_receiver as native


def receipt(model_sha, sender_sha, tokenizer_revision=None):
    return {
        "sender_role": "B2_GIST",
        "receiver_role": "C3_LANGUAGE",
        "sender_tap_id": "qwen35.result_norm.final.v1",
        "sender_model_revision": "qwen35-r1",
        "sender_model_sha256": sender_sha,
        "tokenizer_revision": tokenizer_revision,
        "receiver_model_revision": "lfm2-r1",
        "receiver_model_sha256": model_sha,
        "runner_revision": native.PINNED_LLAMA_REVISION,
        "llama_version": "b10964",
        "input_rows": 2,
        "input_dim": 2,
        "receiver_input_dim": 2,
        "output_dim": 4,
        "input_sha256": "a" * 64,
        "position_ids": [0, 1],
        "position_mode": native.POSITION_MODE,
        "decode_status": 0,
        "output_norm": 1.25,
        "input_effect_rms": 0.5,
        "zero_control_cosine": 0.2,
        "shuffle_control_cosine": 0.1,
        "row_shuffle_control_cosine": 0.05,
        "row_shuffle_control_applicable": True,
        "repeat_cosine": 1.0,
        "receiver_vocab_size": 32000,
        "receiver_next_token_id": 42,
        "zero_control_next_token_id": 0,
        "shuffle_control_next_token_id": 17,
        "row_shuffle_control_next_token_id": 12,
        "repeat_next_token_id": 42,
        "receiver_next_token_margin": 1.25,
        "logit_effect_rms": 0.5,
        "logit_cosine": 0.2,
        "next_token_effect_detected": True,
        "next_token_changed_vs_zero": True,
        "next_token_changed_vs_shuffle": True,
        "next_token_changed_vs_row_shuffle": True,
        "repeat_next_token_stable": True,
        "native_input_consumed": True,
        "input_effect_detected": True,
        "status": "NATIVE_INPUT_EFFECT",
    }


def setup_runtime(tmp_path):
    runtime = Runtime(Path(tmp_path))
    runtime.sleep.cycle.set_policy("enabled", "off")
    event = runtime.store.event(runtime.session, "private source text stays local")
    model_dir = runtime.home / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "receiver.gguf"
    model_path.write_bytes(b"installed-receiver-model")
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    key = model_key("C3_LANGUAGE", runtime.models.b2_control)
    runtime.models.installed[key] = {
        "download_complete": True,
        "exact_revision": "lfm2-r1",
        "main_file": "receiver.gguf",
        "files": {"receiver.gguf": {"sha256": digest}},
    }
    sender_dir = model_dir / "gist"
    sender_dir.mkdir(parents=True, exist_ok=True)
    sender_path = sender_dir / "sender.gguf"
    sender_path.write_bytes(b"installed-sender-model")
    sender_digest = hashlib.sha256(sender_path.read_bytes()).hexdigest()
    sender_key = model_key("B2_GIST", runtime.models.b2_control)
    runtime.models.installed[sender_key] = {
        "download_complete": True,
        "exact_revision": "qwen35-r1",
        "main_file": "sender.gguf",
        "files": {"sender.gguf": {"sha256": sender_digest}},
    }
    runtime.models.path_for = lambda role: sender_path if role == "B2_GIST" else model_path
    runtime.models.revision = lambda role: "qwen35-r1" if role == "B2_GIST" else "lfm2-r1"
    return runtime, event, model_path, digest, sender_path, sender_digest


def test_cognition_native_receive_is_source_bound_and_non_authoritative(tmp_path, monkeypatch):
    runtime, event, model_path, digest, sender_path, sender_digest = setup_runtime(tmp_path)
    order = []
    tap = {
        "packet_id": "tap-packet-1",
        "event_id": event["event_id"],
        "brain_generation_id": event["brain_generation_id"],
        "source_ref": event["source_ref"],
        "role": "B2_GIST",
        "tap_id": "qwen35.result_norm.final.v1",
        "model_revision": "qwen35-r1",
        "tokenizer_revision": None,
        "metrics": {"whole_sequence_prefill": True, "pooling": "none", "prompt_tokens": 2},
    }
    runtime.cognition.tap = lambda role, e, ref, deadline: (order.append("tap") or tap)
    runtime.cognition.read_tap = lambda packet: {
        "token_ids": [101, 202],
        "vectors": [[0.25, -0.5], [1.0, 0.75]],
    }
    runtime.pool.unload = lambda: order.append("unload")

    def fake_probe(**kwargs):
        assert order == ["tap", "unload"]
        assert kwargs["model_path"] == model_path
        assert kwargs["expected_model_sha256"] == digest
        assert kwargs["sender_model_sha256"] == sender_digest
        assert kwargs["tokenizer_revision"] is None
        assert kwargs["position_ids"] == [0, 1]
        assert kwargs["position_mode"] == native.POSITION_MODE
        assert kwargs["source_id"] == event["source_ref"]["source_id"]
        assert kwargs["generation_id"] == event["brain_generation_id"]
        return receipt(digest, sender_digest)

    monkeypatch.setattr(native, "probe", fake_probe)
    before = model_path.read_bytes()
    packet = runtime.cognition.native_receive(
        "B2_GIST", "C3_LANGUAGE", event, event["source_ref"], time.monotonic() + 30
    )
    assert packet["status"] == "NATIVE_INPUT_EFFECT"
    assert packet["sender_tap_packet_id"] == "tap-packet-1"
    assert packet["source_ref"] == event["source_ref"]
    assert packet["provenance"] == [event["source_ref"]]
    assert packet["native_input_consumed"] is True
    assert packet["input_effect_detected"] is True
    assert packet["receiver_next_token_id"] == 42
    assert packet["logit_effect_rms"] == 0.5
    assert packet["next_token_effect_detected"] is True
    assert packet["next_token_changed_vs_zero"] is True
    assert packet["production_route"] is False
    assert packet["semantic_use_proven"] is False
    assert packet["training_authority"] == packet["native_receiver_authority"] == 0
    assert model_path.read_bytes() == before

    stored = json.loads(runtime.store.one(
        "SELECT payload FROM packets WHERE kind='LatentReceiverPacket' ORDER BY rowid DESC LIMIT 1"
    )["payload"])
    assert stored == packet
    status = controller(runtime).report(runtime.cfg)
    assert status["native_receiver_probe"]["status"] == "NATIVE_INPUT_EFFECT"
    assert status["native_receiver_probe"]["sender_tap_packet_id"] == "tap-packet-1"
    assert status["native_receiver_probe"]["input_rows"] == 2
    assert status["native_receiver_probe"]["receiver_next_token_id"] == 42
    assert status["native_receiver_probe"]["logit_effect_rms"] == 0.5
    assert status["native_receiver_probe"]["next_token_effect_detected"] is True
    assert status["native_receiver_probe"]["next_token_changed_vs_zero"] is True
    assert status["native_receiver_probe"]["production_route"] is False
    assert "LATENT blocked" in status["gate"]

    promoted = dict(packet, production_route=True)
    with pytest.raises(native.NativeReceiverError, match="cannot grant"):
        native.validate_packet(promoted)
    bad_token = dict(packet, receiver_next_token_id=packet["receiver_vocab_size"])
    with pytest.raises(native.NativeReceiverError, match="outside receiver vocabulary"):
        native.validate_packet(bad_token)
    bad_effect = dict(packet, next_token_effect_detected=False)
    with pytest.raises(native.NativeReceiverError, match="next-token effect threshold"):
        native.validate_packet(bad_effect)
    runtime.close()




def test_native_receive_persists_b2_to_c3_pair_when_tokenizer_is_pinned(
    tmp_path, monkeypatch
):
    runtime, event, model_path, digest, sender_path, sender_digest = setup_runtime(tmp_path)
    token_ids = [101, 202]
    tokenizer_revision = "shared-lfm2-tokenizer-r1"
    taps = {}

    def stored_tap(role, revision, tap_id, dimension, vectors):
        path = runtime.home / "data" / "blobs" / (uid("tap") + ".json")
        atomic_write(path, dumps({"token_ids": token_ids, "vectors": vectors}))
        tap_packet = packet(
            "LatentTapPacket", role, event["event_id"], event["brain_generation_id"],
            [event["source_ref"]],
            role=role, source_ref=event["source_ref"], tap_id=tap_id,
            model_revision=revision, tokenizer_revision=tokenizer_revision,
            token_ids=token_ids, feature_path=str(path.relative_to(runtime.home)),
            feature_sha256=file_hash(path), shape=[len(token_ids), dimension],
            role_state="INDEPENDENT_READ_ONLY_PREFILL",
            receiver_read_authority=0, receiver_injection_authority=0,
            body_learning_authority=0,
            metrics={"whole_sequence_prefill": True, "pooling": "none",
                     "prompt_tokens": len(token_ids)},
        )
        runtime.store.add_packet("LatentTapPacket", tap_packet)
        return tap_packet

    taps["B2_GIST"] = stored_tap(
        "B2_GIST", "qwen35-r1", "qwen35.layer12.final.v1", 2,
        [[0.25, -0.5], [1.0, 0.75]],
    )
    taps["C3_LANGUAGE"] = stored_tap(
        "C3_LANGUAGE", "lfm2-r1", "lfm2.layer8.final.v1", 3,
        [[0.5, -0.25, 0.75], [-0.5, 0.25, -0.75]],
    )
    runtime.cognition.tap = lambda role, *args: taps[role]
    runtime.pool.unload = lambda: None

    def fake_probe(**kwargs):
        assert kwargs["sender_role"] == "B2_GIST"
        assert kwargs["receiver_role"] == "C3_LANGUAGE"
        assert kwargs["tokenizer_revision"] == tokenizer_revision
        return receipt(digest, sender_digest, tokenizer_revision)

    monkeypatch.setattr(native, "probe", fake_probe)
    packet_result = runtime.cognition.native_receive(
        "B2_GIST", "C3_LANGUAGE", event, event["source_ref"],
        time.monotonic() + 30,
    )
    assert packet_result["status"] == "NATIVE_INPUT_EFFECT"
    pair_row = runtime.store.one(
        "SELECT payload FROM packets WHERE kind='LatentTapPairPacket' "
        "AND event_id=? ORDER BY rowid DESC LIMIT 1",
        (event["event_id"],),
    )
    assert pair_row is not None
    pair = json.loads(pair_row["payload"])
    assert pair["sender_role"] == "B2_GIST"
    assert pair["receiver_role"] == "C3_LANGUAGE"
    assert pair["sender_tap_id"] != pair["receiver_tap_id"]
    assert pair["tokenizer_revision"] == tokenizer_revision
    assert pair["alignment"] == "TOKEN_IDS_EXACT"
    assert pair["status"] == "PAIRED_READ_ONLY"
    assert pair["training_authority"] == 0
    assert pair["native_receiver_authority"] == 0
    assert pair["production_route"] is False
    assert "private source text stays local" not in json.dumps(pair)
    assert "0.25" not in json.dumps(pair)
    status = controller(runtime).report(runtime.cfg)
    assert status["native_receiver_probe"]["tap_pair"]["status"] == "PAIRED_READ_ONLY"
    assert status["native_receiver_probe"]["tap_pair"]["tokenizer_revision"] == tokenizer_revision
    assert status["native_latent_tap_pair"]["sender_role"] == "B2_GIST"
    assert status["native_latent_tap_pair"]["receiver_role"] == "C3_LANGUAGE"
    runtime.close()


def test_native_receive_rejects_unverified_position_mapping(tmp_path, monkeypatch):
    runtime, event, model_path, digest, sender_path, sender_digest = setup_runtime(tmp_path)
    tap = {
        "packet_id": "tap-packet-bad",
        "event_id": event["event_id"],
        "brain_generation_id": event["brain_generation_id"],
        "source_ref": event["source_ref"],
        "role": "B2_GIST",
        "tap_id": "qwen35.result_norm.final.v1",
        "model_revision": "qwen35-r1",
        "tokenizer_revision": None,
        "metrics": {"whole_sequence_prefill": False, "pooling": "mean", "prompt_tokens": 1},
    }
    runtime.cognition.tap = lambda *args: tap
    runtime.cognition.read_tap = lambda packet: {"token_ids": [101], "vectors": [[1.0, 2.0]]}
    runtime.pool.unload = lambda: None
    monkeypatch.setattr(native, "probe", lambda **kwargs: pytest.fail("native receiver must not run"))
    with pytest.raises(ValueError, match="whole-sequence position map"):
        runtime.cognition.native_receive(
            "B2_GIST", "C3_LANGUAGE", event, event["source_ref"], time.monotonic() + 30
        )
    runtime.close()


def test_native_receiver_dimension_mismatch_packet_is_valid_but_not_consumed(tmp_path, monkeypatch):
    runtime, event, model_path, digest, sender_path, sender_digest = setup_runtime(tmp_path)
    tap = {
        "packet_id": "tap-packet-2",
        "event_id": event["event_id"],
        "brain_generation_id": event["brain_generation_id"],
        "source_ref": event["source_ref"],
        "role": "B2_GIST",
        "tap_id": "qwen35.result_norm.final.v1",
        "model_revision": "qwen35-r1",
        "tokenizer_revision": None,
        "metrics": {"whole_sequence_prefill": True, "pooling": "none", "prompt_tokens": 1},
    }
    runtime.cognition.tap = lambda *args: tap
    runtime.cognition.read_tap = lambda packet: {
        "token_ids": [101],
        "vectors": [[1.0, 2.0]],
    }
    runtime.pool.unload = lambda: None
    mismatch = receipt(digest, sender_digest)
    mismatch.update({
        "input_rows": 1,
        "position_ids": [0],
        "receiver_input_dim": 3,
        "decode_status": -100,
        "output_norm": 0.0,
        "input_effect_rms": 0.0,
        "zero_control_cosine": None,
        "shuffle_control_cosine": None,
        "row_shuffle_control_cosine": None,
        "row_shuffle_control_applicable": False,
        "repeat_cosine": None,
        "receiver_next_token_id": None,
        "zero_control_next_token_id": None,
        "shuffle_control_next_token_id": None,
        "row_shuffle_control_next_token_id": None,
        "repeat_next_token_id": None,
        "receiver_next_token_margin": None,
        "logit_effect_rms": None,
        "logit_cosine": None,
        "next_token_effect_detected": False,
        "next_token_changed_vs_zero": False,
        "next_token_changed_vs_shuffle": False,
        "next_token_changed_vs_row_shuffle": False,
        "repeat_next_token_stable": False,
        "native_input_consumed": False,
        "input_effect_detected": False,
        "status": "DIMENSION_MISMATCH",
    })
    monkeypatch.setattr(native, "probe", lambda **kwargs: mismatch)
    packet = runtime.cognition.native_receive(
        "B2_GIST", "C3_LANGUAGE", event, event["source_ref"], time.monotonic() + 30
    )
    assert packet["status"] == "DIMENSION_MISMATCH"
    assert packet["native_input_consumed"] is False
    assert packet["production_route"] is False
    runtime.close()


def test_native_receive_rejects_sender_model_hash_drift(tmp_path, monkeypatch):
    runtime, event, model_path, digest, sender_path, sender_digest = setup_runtime(tmp_path)
    tap = {
        "packet_id": "tap-packet-drift",
        "event_id": event["event_id"],
        "brain_generation_id": event["brain_generation_id"],
        "source_ref": event["source_ref"],
        "role": "B2_GIST",
        "tap_id": "qwen35.result_norm.final.v1",
        "model_revision": "qwen35-r1",
        "tokenizer_revision": None,
        "metrics": {"whole_sequence_prefill": True, "pooling": "none", "prompt_tokens": 1},
    }
    runtime.cognition.tap = lambda *args: tap
    runtime.cognition.read_tap = lambda packet: {"token_ids": [101], "vectors": [[1.0, 2.0]]}
    runtime.pool.unload = lambda: None
    sender_path.write_bytes(b"changed-after-tap")
    monkeypatch.setattr(native, "probe", lambda **kwargs: pytest.fail("native receiver must not run"))
    with pytest.raises(ValueError, match="Sender model hash differs"):
        runtime.cognition.native_receive(
            "B2_GIST", "C3_LANGUAGE", event, event["source_ref"], time.monotonic() + 30
        )
    runtime.close()


def test_native_receive_rejects_sender_model_outside_home_models(tmp_path, monkeypatch):
    runtime, event, model_path, digest, sender_path, sender_digest = setup_runtime(tmp_path)
    outside = Path(tmp_path) / "sender-outside.gguf"
    outside.write_bytes(sender_path.read_bytes())
    runtime.models.path_for = lambda role: outside if role == "B2_GIST" else model_path
    tap = {
        "packet_id": "tap-packet-outside",
        "event_id": event["event_id"],
        "brain_generation_id": event["brain_generation_id"],
        "source_ref": event["source_ref"],
        "role": "B2_GIST",
        "tap_id": "qwen35.result_norm.final.v1",
        "model_revision": "qwen35-r1",
        "tokenizer_revision": None,
        "metrics": {"whole_sequence_prefill": True, "pooling": "none", "prompt_tokens": 1},
    }
    runtime.cognition.tap = lambda *args: tap
    runtime.cognition.read_tap = lambda packet: {"token_ids": [101], "vectors": [[1.0, 2.0]]}
    runtime.pool.unload = lambda: None
    monkeypatch.setattr(native, "probe", lambda **kwargs: pytest.fail("native receiver must not run"))
    try:
        with pytest.raises(ValueError, match="Sender model must be an installed file under home/models"):
            runtime.cognition.native_receive(
                "B2_GIST", "C3_LANGUAGE", event, event["source_ref"], time.monotonic() + 30
            )
    finally:
        runtime.close()


def test_native_receive_rejects_sender_model_symlink(tmp_path, monkeypatch):
    runtime, event, model_path, digest, sender_path, sender_digest = setup_runtime(tmp_path)
    outside = Path(tmp_path) / "sender-symlink-target.gguf"
    outside.write_bytes(sender_path.read_bytes())
    sender_path.unlink()
    sender_path.symlink_to(outside)
    runtime.models.path_for = lambda role: sender_path if role == "B2_GIST" else model_path
    tap = {
        "packet_id": "tap-packet-symlink",
        "event_id": event["event_id"],
        "brain_generation_id": event["brain_generation_id"],
        "source_ref": event["source_ref"],
        "role": "B2_GIST",
        "tap_id": "qwen35.result_norm.final.v1",
        "model_revision": "qwen35-r1",
        "tokenizer_revision": None,
        "metrics": {"whole_sequence_prefill": True, "pooling": "none", "prompt_tokens": 1},
    }
    runtime.cognition.tap = lambda *args: tap
    runtime.cognition.read_tap = lambda packet: {"token_ids": [101], "vectors": [[1.0, 2.0]]}
    runtime.pool.unload = lambda: None
    monkeypatch.setattr(native, "probe", lambda **kwargs: pytest.fail("native receiver must not run"))
    try:
        with pytest.raises(ValueError, match="Sender model symlink refused"):
            runtime.cognition.native_receive(
                "B2_GIST", "C3_LANGUAGE", event, event["source_ref"], time.monotonic() + 30
            )
    finally:
        runtime.close()


def test_callosum_probe_runs_synchronously_only_from_idle_operator_and_uses_last_source(tmp_path):
    runtime, event, model_path, digest, sender_path, sender_digest = setup_runtime(tmp_path)
    runtime.last_answer = lambda: {"event_id": event["event_id"]}
    calls = []
    runtime.require_idle = lambda: calls.append("idle")
    packet = {
        "status": "NATIVE_INPUT_EFFECT",
        "sender_tap_packet_id": "tap-packet-3",
        "source_ref": event["source_ref"],
        "native_input_consumed": True,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }
    runtime.cognition.native_receive = lambda sender, receiver, e, ref, deadline: (
        calls.append((sender, receiver, e["event_id"], ref, deadline)) or packet
    )
    runtime.pool.unload = lambda: calls.append("unload")
    result = json.loads(operator_command(
        runtime, ["native-probe", "B2_GIST", "C3_LANGUAGE", "--last-source", "--confirm"]
    ))
    assert result["completed"] is True
    assert result["queued"] is False
    assert result["production_route"] is False
    assert calls[0] == "idle"
    assert calls[1][:4] == ("B2_GIST", "C3_LANGUAGE", event["event_id"], event["source_ref"])
    assert calls[2] == "unload"
    with pytest.raises(ValueError):
        operator_command(runtime, ["native-probe", "B2_GIST", "C3_LANGUAGE", "--last-source"])
    with pytest.raises(ValueError):
        operator_command(runtime, ["native-probe", "C3_LANGUAGE", "B2_GIST", "--last-source", "--confirm"])
    runtime.close()

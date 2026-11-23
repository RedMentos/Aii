import hashlib
import json
import tempfile
import time
from pathlib import Path

import pytest

from v13.runtime import Runtime
from v13.models import model_key
from v13.contracts import packet, validate
from v13.callosum import controller
from v13.operator import Operator
from v13 import brain_panel
from v13 import native_latent_receiver as native
from v13 import native_probe_approval as approval


def receipt(model_sha, sender_sha):
    return {
        "sender_role": "B2_GIST",
        "receiver_role": "C3_LANGUAGE",
        "sender_tap_id": "qwen35.result_norm.final.v1",
        "sender_model_revision": "qwen35-r1",
        "sender_model_sha256": sender_sha,
        "tokenizer_revision": None,
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
        "files": {"receiver.gguf": {"sha256": digest, "path": "models/receiver.gguf", "size": model_path.stat().st_size}},
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
        "files": {"sender.gguf": {"sha256": sender_digest, "path": "models/gist/sender.gguf", "size": sender_path.stat().st_size}},
    }
    runtime.models.path_for = lambda role: sender_path if role == "B2_GIST" else model_path
    runtime.models.revision = lambda role: "qwen35-r1" if role == "B2_GIST" else "lfm2-r1"
    return runtime, event, model_path, digest, sender_path, sender_digest


def test_cognition_native_receive_is_source_bound_and_non_authoritative(tmp_path, monkeypatch):
    runtime, event, model_path, digest, sender_path, sender_digest = setup_runtime(tmp_path)
    order = []
    class FakeTapRunner:
        tap_id = "qwen35.result_norm.final.v1"
        tap_dim = 2

        def tap(self, text, cancel, deadline):
            order.append("tap")
            assert text == "private source text stays local"
            return {
                "tap_id": self.tap_id,
                "token_ids": [101, 202],
                "vectors": [[0.25, -0.5], [1.0, 0.75]],
                "metrics": {
                    "tap_id": self.tap_id,
                    "whole_sequence_prefill": True,
                    "pooling": "none",
                    "prompt_tokens": 2,
                },
            }

    runtime.pool.get_tap = lambda role: FakeTapRunner()
    runtime.learner.predict_states = lambda role, vectors: None
    runtime.pool.unload = lambda: order.append("unload")

    def fake_probe(**kwargs):
        assert order == ["tap", "unload"]
        assert kwargs["model_path"] == model_path
        assert kwargs["expected_model_sha256"] == digest
        assert kwargs["sender_model_sha256"] == sender_digest
        assert kwargs["tokenizer_revision"] is None
        assert kwargs["position_ids"] == [0, 1]
        assert kwargs["position_mode"] == native.POSITION_MODE
        assert kwargs["vectors"] == [[0.25, -0.5], [1.0, 0.75]]
        assert kwargs["source_id"] == event["source_ref"]["source_id"]
        assert kwargs["generation_id"] == event["brain_generation_id"]
        return receipt(digest, sender_digest)

    monkeypatch.setattr(native, "probe", fake_probe)
    before = model_path.read_bytes()
    packet = runtime.cognition.native_receive(
        "B2_GIST", "C3_LANGUAGE", event, event["source_ref"], time.monotonic() + 30
    )
    assert packet["status"] == "NATIVE_INPUT_EFFECT"
    assert isinstance(packet["sender_tap_packet_id"], str) and packet["sender_tap_packet_id"]
    tap_row = runtime.store.one(
        "SELECT payload FROM packets WHERE id=? AND kind='LatentTapPacket'",
        (packet["sender_tap_packet_id"],),
    )
    assert tap_row is not None
    sender_tap = json.loads(tap_row["payload"])
    assert sender_tap["packet_id"] == packet["sender_tap_packet_id"]
    assert sender_tap["source_ref"] == event["source_ref"]
    assert sender_tap["role"] == "B2_GIST"
    assert packet["source_ref"] == event["source_ref"]
    assert packet["provenance"] == [event["source_ref"]]
    assert packet["native_input_consumed"] is True
    assert packet["input_effect_detected"] is True
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
    assert status["native_receiver_probe"]["production_route"] is False
    assert "LATENT blocked" in status["gate"]

    panel = brain_panel.status(runtime)
    trace = panel["native_latent_receiver"]
    expected_token_digest = hashlib.sha256(
        b"v14.native-latent-sender-token-ids/1:"
        + b"".join(value.to_bytes(4, "big") for value in [101, 202])
    ).hexdigest()
    assert trace["status"] == "NATIVE_INPUT_EFFECT"
    assert trace["sender_role"] == "B2_GIST"
    assert trace["receiver_role"] == "C3_LANGUAGE"
    assert trace["sender_token_count"] == 2
    assert trace["sender_token_ids_sha256"] == expected_token_digest
    assert trace["receiver_input_kind"] == "EMBEDDING_ROWS_NOT_TOKEN_IDS"
    assert trace["receiver_input_rows"] == 2
    assert trace["receiver_input_dim"] == 2
    assert trace["receiver_input_sha256"] == "a" * 64
    assert trace["native_input_consumed"] is True
    assert trace["input_effect_detected"] is True
    assert trace["semantic_use_proven"] is False
    assert trace["production_route"] is False
    assert "token_ids" not in trace

    promoted = dict(packet, production_route=True)
    with pytest.raises(native.NativeReceiverError, match="cannot grant"):
        native.validate_packet(promoted)
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


def test_callosum_probe_runs_synchronously_only_from_idle_operator_and_uses_last_source(tmp_path, monkeypatch):
    monkeypatch.setattr(approval.os, "isatty", lambda fd: fd == 0)
    runtime, event, model_path, digest, sender_path, sender_digest = setup_runtime(tmp_path)
    runtime.last_answer = lambda: {"event_id": event["event_id"], "status": "FINAL"}
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
    def native_receive(sender, receiver, e, ref, deadline):
        assert runtime.current == "probe"
        assert runtime.paused is True
        calls.append((sender, receiver, e["event_id"], ref, deadline))
        return packet

    runtime.cognition.native_receive = native_receive
    runtime.pool.unload = lambda: calls.append("unload")
    operator = Operator(runtime)
    try:
        armed = json.loads(operator.run(
            ":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm"
        ))
        assert armed["status"] == "ARMED"
        assert armed["source_bound"] is True
        assert armed["model_revisions_and_hashes_bound"] is True
        result = json.loads(operator.run(
            ":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm"
        ))
        assert result["completed"] is True
        assert result["queued"] is False
        assert result["production_route"] is False
        assert result["local_approval_consumed"] is True
        assert result["approval_id"] == armed["approval_id"]
        probe_index = next(i for i, value in enumerate(calls) if isinstance(value, tuple))
        # The local arm checks idle before creating the lease; consume now
        # validates the exclusive lease instead of calling require_idle again.
        assert calls[:probe_index].count("idle") == 1
        assert calls[probe_index][:4] == (
            "B2_GIST", "C3_LANGUAGE", event["event_id"], event["source_ref"]
        )
        assert calls[probe_index + 1] == "unload"
        with pytest.raises(ValueError):
            operator.run(":callosum native-probe B2_GIST C3_LANGUAGE --last-source")
        with pytest.raises(ValueError):
            operator.run(":callosum native-probe C3_LANGUAGE B2_GIST --last-source --confirm")
    finally:
        runtime.close()



def test_brain_panel_fails_closed_when_receiver_has_no_linked_sender_tap(tmp_path):
    runtime, event, model_path, digest, sender_path, sender_digest = setup_runtime(tmp_path)
    try:
        assert brain_panel.status(runtime)["native_latent_receiver"]["status"] == "NOT_RUN"
        native.register_packet_contract()
        fields = receipt(digest, sender_digest)
        fields.update({
            "source_ref": event["source_ref"],
            "sender_tap_packet_id": "missing-tap-packet",
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        })
        receiver = packet(
            "LatentReceiverPacket", "B3_NATIVE_RECEIVER_PROBE",
            event["event_id"], event["brain_generation_id"],
            [event["source_ref"]], **fields,
        )
        native.validate_packet(receiver)
        runtime.store.add_packet("LatentReceiverPacket", receiver)
        trace = brain_panel.status(runtime)["native_latent_receiver"]
        assert trace["status"] == "TAP_PACKET_UNAVAILABLE"
        assert "sender_token_ids_sha256" not in trace
        assert "token_ids" not in trace
    finally:
        runtime.close()

import hashlib
import json
from pathlib import Path

import pytest

from v13.models import model_key
from v13.operator import Operator
from v13.runtime import Runtime
from v13 import native_probe_approval as approval
import v13.callosum as callosum


@pytest.fixture(autouse=True)
def _interactive_local_tty(monkeypatch):
    # The stage tests exercise the real TTY gate; pytest supplies this explicit
    # local-console fixture rather than inheriting the runner's non-TTY stdin.
    monkeypatch.setattr(approval, "_is_local_tty", lambda: True)


def setup_runtime(tmp_path):
    runtime = Runtime(Path(tmp_path) / "brain")
    runtime.sleep.cycle.set_policy("enabled", "off")
    event = runtime.store.event(runtime.session, "private source text remains local")
    runtime.store.message(runtime.session, event["event_id"], "assistant", "test answer", "FINAL", {})

    models = runtime.home / "models"
    sender_path = models / "gist" / "sender.gguf"
    receiver_path = models / "language" / "receiver.gguf"
    sender_path.parent.mkdir(parents=True, exist_ok=True)
    receiver_path.parent.mkdir(parents=True, exist_ok=True)
    sender_path.write_bytes(b"installed sender model")
    receiver_path.write_bytes(b"installed receiver model")

    def install(role, path, revision):
        raw = path.read_bytes()
        key = model_key(role, runtime.models.b2_control)
        runtime.models.installed[key] = {
            "download_complete": True,
            "exact_revision": revision,
            "main_file": path.name,
            "files": {
                path.name: {
                    "path": str(path.relative_to(runtime.home)),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "size": len(raw),
                }
            },
        }

    install("B2_GIST", sender_path, "sender-r1")
    install("C3_LANGUAGE", receiver_path, "receiver-r1")
    runtime.pool.unload = lambda: None
    return runtime, event, sender_path, receiver_path



def test_native_probe_requires_actual_interactive_tty(tmp_path, monkeypatch):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    try:
        monkeypatch.setattr(approval, "_is_local_tty", lambda: False)
        with pytest.raises(PermissionError, match="interactive local TTY"):
            approval.arm(runtime, "B2_GIST", "C3_LANGUAGE")
        state, _ = runtime.store.state(approval.KEY, None)
        assert state is None

        monkeypatch.setattr(approval, "_is_local_tty", lambda: True)
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE")
        monkeypatch.setattr(approval, "_is_local_tty", lambda: False)
        with pytest.raises(PermissionError, match="interactive local TTY"):
            approval.consume(runtime, "B2_GIST", "C3_LANGUAGE", event, event["source_ref"])
        with pytest.raises(PermissionError, match="interactive local TTY"):
            approval.revoke(runtime)
        state, _ = runtime.store.state(approval.KEY, None)
        assert state["status"] == "PENDING"
    finally:
        runtime.close()


def test_native_probe_requires_local_arm_and_consumes_it_once(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    calls = []
    runtime.cognition.native_receive = lambda sender, receiver, e, ref, deadline: (
        calls.append((sender, receiver, e["event_id"], ref["source_id"])) or {
            "status": "NATIVE_INPUT_EFFECT",
            "native_input_consumed": True,
            "input_effect_detected": True,
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        }
    )
    operator = Operator(runtime)
    command = ":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm"
    try:
        with pytest.raises(ValueError, match="lokale Operator"):
            operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm", origin="REMOTE_OWNER")
        with pytest.raises(PermissionError, match="local"):
            operator.run(command)
        assert calls == []

        armed = json.loads(operator.run(
            ":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm"
        ))
        assert armed["status"] == "ARMED"
        assert armed["source_bound"] is True
        assert armed["model_revisions_and_hashes_bound"] is True
        assert armed["runtime_instance_scoped"] is True

        result = json.loads(operator.run(command))
        assert result["status"] == "NATIVE_INPUT_EFFECT"
        assert result["local_approval_consumed"] is True
        assert result["approval_id"] == armed["approval_id"]
        assert result["production_route"] is False
        assert result["training_authority"] == 0
        assert calls == [("B2_GIST", "C3_LANGUAGE", event["event_id"], event["source_ref"]["source_id"])]

        with pytest.raises(PermissionError):
            operator.run(command)
        assert len(calls) == 1
    finally:
        runtime.close()


def test_wrong_role_pair_cannot_use_pending_local_approval(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    calls = []
    runtime.cognition.native_receive = lambda *args: (
        calls.append(args) or {
            "status": "NATIVE_INPUT_EFFECT",
            "native_input_consumed": True,
            "input_effect_detected": True,
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        }
    )
    operator = Operator(runtime)
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        with pytest.raises(PermissionError, match="role pair"):
            operator.run(":callosum native-probe B1_DETAIL C3_LANGUAGE --last-source --confirm")
        assert calls == []
        result = json.loads(operator.run(
            ":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm"
        ))
        assert result["local_approval_consumed"] is True
        assert len(calls) == 1
    finally:
        runtime.close()


def test_model_file_content_hash_drift_invalidates_local_approval(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    calls = []
    runtime.cognition.native_receive = lambda *args: calls.append(args)
    operator = Operator(runtime)
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        original = sender_path.read_bytes()
        tampered = bytes([original[0] ^ 1]) + original[1:]
        assert len(tampered) == len(original)
        sender_path.write_bytes(tampered)
        with pytest.raises(PermissionError, match="content hash"):
            operator.run(":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        assert calls == []
    finally:
        runtime.close()


def test_model_revision_drift_invalidates_local_approval(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    calls = []
    runtime.cognition.native_receive = lambda *args: calls.append(args)
    operator = Operator(runtime)
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        key = model_key("C3_LANGUAGE", runtime.models.b2_control)
        runtime.models.installed[key]["exact_revision"] = "receiver-r2"
        with pytest.raises(PermissionError, match="revision"):
            operator.run(":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        assert calls == []
    finally:
        runtime.close()


def test_new_turn_invalidates_local_source_approval(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    calls = []
    runtime.cognition.native_receive = lambda *args: calls.append(args)
    operator = Operator(runtime)
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        next_event = runtime.store.event(runtime.session, "a different source")
        runtime.store.message(runtime.session, next_event["event_id"], "assistant", "next answer", "FINAL", {})
        with pytest.raises(PermissionError, match="source/session/event changed"):
            operator.run(":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        assert calls == []
    finally:
        runtime.close()


def test_runtime_restart_invalidates_pending_local_approval(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    calls = []
    runtime.cognition.native_receive = lambda *args: calls.append(args)
    operator = Operator(runtime)
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        runtime._native_probe_approval_runtime_nonce = "0" * 32
        with pytest.raises(PermissionError, match="Runtime restart"):
            operator.run(":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        assert calls == []
    finally:
        runtime.close()


def test_expired_local_approval_is_rejected(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    try:
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE", now=1000)
        with pytest.raises(PermissionError, match="expired"):
            approval.consume(
                runtime, "B2_GIST", "C3_LANGUAGE", event, event["source_ref"],
                now=1000 + approval.TTL_SECONDS + 1,
            )
    finally:
        runtime.close()


def test_revoke_clears_pending_local_approval_without_probe(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    calls = []
    runtime.cognition.native_receive = lambda *args: calls.append(args)
    operator = Operator(runtime)
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        revoked = json.loads(operator.run(":callosum revoke-probe"))
        assert revoked["status"] == "REVOKED"
        with pytest.raises(PermissionError):
            operator.run(":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        assert calls == []
    finally:
        runtime.close()


def test_native_probe_deadline_is_hard_capped_at_120_seconds(tmp_path, monkeypatch):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    runtime.cfg["observer_seconds"] = 99999
    captured = []
    runtime.cognition.native_receive = lambda sender, receiver, e, ref, deadline: (
        captured.append(deadline) or {
            "status": "NATIVE_INPUT_EFFECT",
            "native_input_consumed": True,
            "input_effect_detected": True,
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        }
    )
    operator = Operator(runtime)
    monkeypatch.setattr(callosum.time, "monotonic", lambda: 1000.0)
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        result = json.loads(operator.run(
            ":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm"
        ))
        assert result["local_approval_consumed"] is True
        assert captured == [1120.0]
    finally:
        runtime.close()

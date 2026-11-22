import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from v13.models import model_key
from v13.operator import Operator
from v13.runtime import Runtime
from v13 import native_probe_approval as approval
import v13.callosum as callosum


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


@pytest.mark.parametrize("model_name", ["sender", "receiver"])
def test_actual_model_bytes_must_match_manifest_before_arm(tmp_path, model_name):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    calls = []
    runtime.cognition.native_receive = lambda *args: calls.append(args)
    operator = Operator(runtime)
    model_path = sender_path if model_name == "sender" else receiver_path
    try:
        original = model_path.read_bytes()
        model_path.write_bytes(b"X" * len(original))
        with pytest.raises(PermissionError, match="hash"):
            operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        assert calls == []
    finally:
        runtime.close()


@pytest.mark.parametrize("model_name", ["sender", "receiver"])
def test_same_size_model_tamper_after_arm_invalidates_approval(tmp_path, model_name):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    calls = []
    runtime.cognition.native_receive = lambda *args: calls.append(args)
    operator = Operator(runtime)
    model_path = sender_path if model_name == "sender" else receiver_path
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        original = model_path.read_bytes()
        model_path.write_bytes(b"Y" * len(original))
        with pytest.raises(PermissionError, match="hash"):
            operator.run(":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        assert calls == []
    finally:
        runtime.close()


@pytest.mark.parametrize(
    ("model_name", "role"),
    [("sender", "B2_GIST"), ("receiver", "C3_LANGUAGE")],
)
def test_selected_model_path_must_match_manifest_path_before_arm(tmp_path, model_name, role):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    manifest_path = sender_path if model_name == "sender" else receiver_path
    alternate = tmp_path / (model_name + "-same-bytes-different-path.gguf")
    alternate.write_bytes(manifest_path.read_bytes())
    runtime.models.router = lambda selected_role: alternate if selected_role == role else None
    try:
        with pytest.raises(PermissionError, match="selected model path"):
            approval.arm(runtime, "B2_GIST", "C3_LANGUAGE", now=1000.0)
    finally:
        runtime.close()


@pytest.mark.parametrize(
    ("model_name", "role"),
    [("sender", "B2_GIST"), ("receiver", "C3_LANGUAGE")],
)
def test_selected_model_route_change_after_arm_invalidates_approval(tmp_path, model_name, role):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    manifest_path = sender_path if model_name == "sender" else receiver_path
    alternate = tmp_path / (model_name + "-same-bytes-rerouted.gguf")
    alternate.write_bytes(manifest_path.read_bytes())
    try:
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE", now=1000.0)
        runtime.models.router = lambda selected_role: alternate if selected_role == role else None
        with pytest.raises(PermissionError, match="selected model path"):
            approval.consume(
                runtime, "B2_GIST", "C3_LANGUAGE", event, event["source_ref"], now=1001.0
            )
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "PENDING"
    finally:
        runtime.close()


@pytest.mark.parametrize(
    ("model_name", "role"),
    [("sender", "B2_GIST"), ("receiver", "C3_LANGUAGE")],
)
def test_joint_manifest_and_router_redirect_after_arm_invalidates_approval(
    tmp_path, model_name, role,
):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    manifest_path = sender_path if model_name == "sender" else receiver_path
    key = model_key(role, runtime.models.b2_control)
    entry = runtime.models.installed[key]["files"][manifest_path.name]
    alternate = runtime.home / "models" / (model_name + "-same-bytes-copy.gguf")
    alternate.write_bytes(manifest_path.read_bytes())
    calls = []
    runtime.cognition.native_receive = lambda *args: calls.append(args)
    operator = Operator(runtime)
    try:
        armed = json.loads(operator.run(
            ":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm"
        ))
        record, _ = runtime.store.state(approval.KEY, None)
        original_binding = record["models"][role]
        assert original_binding["canonical_path"] == str(manifest_path.resolve())
        assert len(original_binding["file_identity"]) == 5

        # Redirect both the installed manifest and the live router after arm.
        # The bytes, size and revision stay identical; only path/inode change.
        entry["path"] = str(alternate.relative_to(runtime.home))
        runtime.models.router = lambda selected_role: alternate if selected_role == role else None
        with pytest.raises(PermissionError, match="model revision/hash changed"):
            operator.run(
                ":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm"
            )
        assert calls == []
        pending, _ = runtime.store.state(approval.KEY, None)
        assert pending["status"] == "PENDING"
        assert pending["models"][role] == original_binding
        assert armed["status"] == "ARMED"
    finally:
        runtime.close()


def test_arm_ttl_starts_after_model_hash_verification(tmp_path, monkeypatch):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    clock = [1000.0]

    def verify_model(runtime_arg, role):
        clock[0] += 50.0
        return {"model_key": role, "revision": role + "-r1", "sha256": "0" * 64}

    monkeypatch.setattr(approval, "_clock", lambda value=None: clock[0])
    monkeypatch.setattr(approval, "_model_binding", verify_model)
    try:
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE")
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["issued_at"] == 1100.0
        assert record["expires_at"] == 1220
    finally:
        runtime.close()


def test_consume_rechecks_expiry_after_model_hash_verification(tmp_path, monkeypatch):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    try:
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE", now=1000.0)
        record, _ = runtime.store.state(approval.KEY, None)
        model_bindings = record["models"]
        monkeypatch.setattr(approval, "_model_binding", lambda runtime_arg, role: model_bindings[role])
        times = iter([1000.0, 1121.0])
        monkeypatch.setattr(approval, "_clock", lambda value=None: next(times))
        with pytest.raises(PermissionError, match="expired"):
            approval.consume(
                runtime, "B2_GIST", "C3_LANGUAGE", event, event["source_ref"]
            )
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


def test_fifo_model_path_is_rejected_without_blocking(tmp_path):
    fifo = tmp_path / "model-fifo.gguf"
    os.mkfifo(fifo)
    script = (
        "from pathlib import Path\n"
        "import sys\n"
        "from v13.native_probe_approval import _verify_model_file\n"
        "try:\n"
        "    _verify_model_file(Path(sys.argv[1]), 1, '0' * 64)\n"
        "except PermissionError:\n"
        "    print('REJECTED')\n"
        "else:\n"
        "    raise SystemExit(1)\n"
    )
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    result = subprocess.run(
        [sys.executable, "-c", script, str(fifo)],
        capture_output=True, text=True, timeout=3, check=False, env=env,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "REJECTED"


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

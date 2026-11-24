import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from v13.models import model_key
from v13.operator import Operator
from v13.runtime import Runtime
from v13 import native_probe_approval as approval


@pytest.fixture(autouse=True)
def _interactive_tty_for_approval_tests(monkeypatch):
    monkeypatch.setattr(approval.os, "isatty", lambda fd: fd == 0)
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
        assert armed["model_paths_and_file_identity_bound"] is True
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


def _set_empty_native_census(runtime):
    runtime.pool.pids = lambda: []
    runtime.needle.pids = lambda: []
    runtime.memory.semantic_keys.encoder.pids = lambda: []


def test_runtime_probe_lease_blocks_new_turns_and_restores_runtime(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    try:
        with approval.runtime_probe_lease(runtime) as token:
            assert runtime.current == "probe"
            assert runtime.paused is True
            assert runtime._native_probe_lease_nonce == token
            with pytest.raises(Exception, match="Probe läuft"):
                runtime.submit("This turn must not enter the queue during a native probe")
            assert runtime.jobs.empty()
        assert runtime.current is None
        assert runtime.paused is False
        assert not hasattr(runtime, "_native_probe_lease_nonce")
    finally:
        runtime.close()


def test_runtime_probe_lease_refuses_existing_work_or_user_pause(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    try:
        runtime.current = "turn"
        with pytest.raises(ValueError, match="idle Runtime"):
            with approval.runtime_probe_lease(runtime):
                pass
        runtime.current = None
        runtime.paused = True
        runtime.store.set_queue_paused(True)
        with pytest.raises(ValueError, match="paused Runtime"):
            with approval.runtime_probe_lease(runtime):
                pass
        runtime.store.set_queue_paused(False)
        runtime.paused = False
    finally:
        runtime.close()


def test_native_probe_resource_preflight_refuses_resident_c2_and_keeps_approval(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    unloads = []
    runtime.pool.unload = lambda: unloads.append("unload")
    runtime.pool.pids = lambda: []
    runtime.needle.pids = lambda: [4321]
    runtime.memory.semantic_keys.encoder.pids = lambda: []
    runtime.resources = lambda: {"mem_available_bytes": 10**12}
    try:
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE")
        with approval.runtime_probe_lease(runtime) as token:
            with pytest.raises(PermissionError, match="C2 still has 1"):
                approval.consume(
                    runtime, "B2_GIST", "C3_LANGUAGE", event, event["source_ref"],
                    lease_token=token,
                )
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "PENDING"
        assert unloads == ["unload"]
        assert runtime.current is None
    finally:
        runtime.close()


def test_native_probe_resource_preflight_refuses_low_mem_and_keeps_approval(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    unloads = []
    runtime.pool.unload = lambda: unloads.append("unload")
    _set_empty_native_census(runtime)
    runtime.resources = lambda: {"mem_available_bytes": 1}
    try:
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE")
        with approval.runtime_probe_lease(runtime) as token:
            with pytest.raises(PermissionError, match="MemAvailable is insufficient"):
                approval.consume(
                    runtime, "B2_GIST", "C3_LANGUAGE", event, event["source_ref"],
                    lease_token=token,
                )
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "PENDING"
        assert unloads == ["unload"]
    finally:
        runtime.close()


def test_native_probe_resource_preflight_passes_with_headroom_and_zero_residency(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    unloads = []
    runtime.pool.unload = lambda: unloads.append("unload")
    _set_empty_native_census(runtime)
    runtime.resources = lambda: {"mem_available_bytes": 10**12}
    try:
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE")
        with approval.runtime_probe_lease(runtime) as token:
            result = approval.consume(
                runtime, "B2_GIST", "C3_LANGUAGE", event, event["source_ref"],
                lease_token=token,
            )
            assert result["resource_preflight"]["status"] == "PASS"
            assert result["resource_preflight"]["known_managed_model_processes"] == 0
            assert result["resource_preflight"]["global_native_process_census"] is False
            assert result["resource_preflight"]["census_scope"] == [
                "runtime.pool (B1/B2/C3)",
                "runtime.needle (C2)",
                "runtime.memory.semantic_keys.encoder",
            ]
            assert result["resource_preflight"]["body_models_unloaded"] is True
            assert result["resource_preflight"]["headroom_margin_bytes"] > 0
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "CONSUMED"
        assert unloads == ["unload"]
    finally:
        runtime.close()


def test_cancelled_exclusive_probe_does_not_consume_local_approval(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    try:
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE")
        with approval.runtime_probe_lease(runtime) as token:
            runtime.cancel_event.set()
            with pytest.raises(InterruptedError, match="cancelled"):
                approval.consume(
                    runtime, "B2_GIST", "C3_LANGUAGE", event, event["source_ref"],
                    lease_token=token,
                )
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "PENDING"
        assert runtime.current is None
    finally:
        runtime.close()


def test_operator_native_probe_holds_exclusive_lease_through_receiver_call(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    calls = []

    def fake_native_receive(sender, receiver, current_event, source_ref, deadline):
        assert runtime.current == "probe"
        assert runtime.paused is True
        with pytest.raises(Exception, match="Probe läuft"):
            runtime.submit("Concurrent user turn must be rejected")
        calls.append((sender, receiver, current_event["event_id"], source_ref["source_id"]))
        return {
            "status": "NATIVE_INPUT_EFFECT",
            "native_input_consumed": True,
            "input_effect_detected": True,
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        }

    runtime.cognition.native_receive = fake_native_receive
    operator = Operator(runtime)
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        result = json.loads(operator.run(
            ":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm"
        ))
        assert result["runtime_exclusive"] is True
        assert result["resource_preflight"]["status"] == "PASS"
        assert result["local_approval_consumed"] is True
        assert len(calls) == 1
        assert runtime.current is None
        assert runtime.paused is False
    finally:
        runtime.close()


def test_operator_keyboard_interrupt_cancels_receiver_before_releasing_lease(tmp_path, monkeypatch):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    _set_empty_native_census(runtime)
    runtime.resources = lambda: {"mem_available_bytes": 10**12}
    started = threading.Event()

    def blocking_native_receive(sender, receiver, current_event, source_ref, deadline):
        assert runtime.current == "probe"
        started.set()
        while not runtime.cancel_event.is_set():
            time.sleep(0.01)
        raise InterruptedError("native receiver probe cancelled")

    runtime.cognition.native_receive = blocking_native_receive
    operator = Operator(runtime)
    original_join = threading.Thread.join
    injected = [False]

    def interrupt_probe_wait(thread, timeout=None):
        if thread.name == "v14-native-probe" and not injected[0]:
            assert started.wait(1.0)
            injected[0] = True
            raise KeyboardInterrupt
        return original_join(thread, timeout)

    monkeypatch.setattr(threading.Thread, "join", interrupt_probe_wait)
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        with pytest.raises(InterruptedError, match="local operator"):
            operator.run(":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        assert injected[0] is True
        assert runtime.cancel_event.is_set()
        assert runtime.current is None
        assert runtime.paused is False
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "CONSUMED"
    finally:
        runtime.close()




def test_runtime_close_cancels_and_joins_probe_before_store_teardown(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    _set_empty_native_census(runtime)
    runtime.resources = lambda: {"mem_available_bytes": 10**12}
    started = threading.Event()
    finished = threading.Event()
    store_closed = threading.Event()
    original_store_close = runtime.store.close

    def checked_store_close():
        assert runtime.current is None
        assert runtime.paused is False
        assert runtime._native_probe_active is False
        assert runtime._native_probe_done.is_set()
        store_closed.set()
        return original_store_close()

    runtime.store.close = checked_store_close

    def blocking_native_receive(sender, receiver, current_event, source_ref, deadline):
        started.set()
        while not runtime.cancel_event.is_set():
            time.sleep(0.01)
        finished.set()
        raise InterruptedError("cancelled by Runtime close")

    runtime.cognition.native_receive = blocking_native_receive
    operator = Operator(runtime)
    errors = []
    probe_thread = None
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")

        def run_probe():
            try:
                operator.run(":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm")
            except BaseException as exc:
                errors.append(exc)

        probe_thread = threading.Thread(target=run_probe, name="test-native-probe-command")
        probe_thread.start()
        assert started.wait(1.0)
        runtime.close()
        probe_thread.join(2.0)

        assert not probe_thread.is_alive()
        assert finished.is_set()
        assert store_closed.is_set()
        assert runtime.closed is True
        assert runtime.current is None
        assert len(errors) == 1 and isinstance(errors[0], InterruptedError)
    finally:
        if probe_thread is not None and probe_thread.is_alive():
            runtime.cancel_event.set()
            probe_thread.join(2.0)
        if not runtime.closed:
            runtime.close()


def test_runtime_close_timeout_keeps_store_open_until_probe_lease_releases(tmp_path, monkeypatch):
    monkeypatch.setattr(approval, "PROBE_CLOSE_WAIT_SECONDS", 0.02)
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    _set_empty_native_census(runtime)
    runtime.resources = lambda: {"mem_available_bytes": 10**12}
    started = threading.Event()
    release = threading.Event()
    store_closed = threading.Event()
    original_store_close = runtime.store.close

    def checked_store_close():
        store_closed.set()
        return original_store_close()

    runtime.store.close = checked_store_close

    def slow_native_receive(sender, receiver, current_event, source_ref, deadline):
        started.set()
        release.wait(2.0)
        return {
            "status": "NATIVE_INPUT_EFFECT",
            "native_input_consumed": True,
            "input_effect_detected": True,
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        }

    runtime.cognition.native_receive = slow_native_receive
    operator = Operator(runtime)
    errors = []
    probe_thread = None
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")

        def run_probe():
            try:
                operator.run(":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm")
            except BaseException as exc:
                errors.append(exc)

        probe_thread = threading.Thread(target=run_probe, name="test-native-probe-command")
        probe_thread.start()
        assert started.wait(1.0)
        with pytest.raises(RuntimeError, match="Store remains open"):
            runtime.close()

        assert runtime.closed is False
        assert not store_closed.is_set()
        assert runtime.store.one("SELECT 1 AS ok")["ok"] == 1

        release.set()
        probe_thread.join(2.0)
        assert not probe_thread.is_alive()
        assert len(errors) == 1 and isinstance(errors[0], InterruptedError)
        assert runtime.current is None
        assert runtime._native_probe_active is False

        runtime.close()
        assert runtime.closed is True
        assert store_closed.is_set()
    finally:
        release.set()
        if probe_thread is not None and probe_thread.is_alive():
            probe_thread.join(2.0)
        if not runtime.closed:
            runtime.close()


def test_runtime_close_from_probe_owner_fails_closed_until_lease_exit(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    try:
        with approval.runtime_probe_lease(runtime):
            with pytest.raises(RuntimeError, match="inside active native probe"):
                runtime.close()
            assert runtime.closed is False
            assert runtime.current == "probe"
            assert runtime._native_probe_active is True
        assert runtime.current is None
        assert runtime._native_probe_done.is_set()
        runtime.close()
        assert runtime.closed is True
    finally:
        if not runtime.closed:
            runtime.close()


def test_operator_rejects_empty_native_receiver_result(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    _set_empty_native_census(runtime)
    runtime.resources = lambda: {"mem_available_bytes": 10**12}
    runtime.cognition.native_receive = lambda *args: None
    operator = Operator(runtime)
    try:
        operator.run(":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        with pytest.raises(RuntimeError, match="returned no result packet"):
            operator.run(":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm")
        assert runtime.current is None
        assert runtime.paused is False
    finally:
        runtime.close()



def test_operator_routes_probe_commands_to_approval_not_raw_callosum(tmp_path, monkeypatch):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    operator = Operator(runtime)
    calls = []

    monkeypatch.setattr(
        approval, "operator_command",
        lambda r, args: calls.append(("approved", list(args))) or "approved",
    )
    monkeypatch.setattr(
        callosum, "operator_command",
        lambda r, args: calls.append(("raw", list(args))) or "raw",
    )
    try:
        command = ":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm"
        assert operator.run(command) == "approved"
        assert calls == [(
            "approved",
            ["arm-probe", "B2_GIST", "C3_LANGUAGE", "--last-source", "--confirm"],
        )]
        with pytest.raises(ValueError, match="lokale Operator"):
            operator.run(command, origin="REMOTE_OWNER")
        assert len(calls) == 1
        assert operator.run(":callosum status") == "raw"
        assert calls[-1] == ("raw", ["status"])
    finally:
        runtime.close()


def test_native_probe_rejects_wrong_exclusive_lease_token_and_keeps_approval(tmp_path):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    try:
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE")
        with approval.runtime_probe_lease(runtime) as token:
            with pytest.raises(PermissionError, match="active exclusive Runtime lease"):
                approval.consume(
                    runtime, "B2_GIST", "C3_LANGUAGE", event, event["source_ref"],
                    lease_token=token + "wrong",
                )
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "PENDING"
        assert runtime.current is None
    finally:
        runtime.close()



def test_consume_requires_local_tty_even_after_a_valid_arm(tmp_path, monkeypatch):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    try:
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE")
        monkeypatch.setattr(approval.os, "isatty", lambda fd: False)
        with approval.runtime_probe_lease(runtime) as token:
            with pytest.raises(PermissionError, match="interactive local TTY"):
                approval.consume(
                    runtime, "B2_GIST", "C3_LANGUAGE", event, event["source_ref"],
                    lease_token=token,
                )
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "PENDING"
        assert runtime.current is None
    finally:
        runtime.close()


def test_remote_chat_allowlist_excludes_native_probe_controls():
    from v13.remote_chat import SAFE_OPERATOR_COMMANDS

    assert not any(command.startswith(":callosum arm-probe") for command in SAFE_OPERATOR_COMMANDS)
    assert not any(command.startswith(":callosum native-probe") for command in SAFE_OPERATOR_COMMANDS)
    assert not any(command.startswith(":callosum revoke-probe") for command in SAFE_OPERATOR_COMMANDS)


def test_arm_rejects_non_interactive_stdin(tmp_path, monkeypatch):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    monkeypatch.setattr(approval.os, "isatty", lambda fd: False)
    try:
        with pytest.raises(PermissionError, match="interactive local TTY"):
            approval.arm(runtime, "B2_GIST", "C3_LANGUAGE")
        record, _ = runtime.store.state(approval.KEY, None)
        assert record is None
    finally:
        runtime.close()


def test_operator_native_probe_runs_staged_receiver_with_source_bound_tap(tmp_path, monkeypatch):
    runtime, event, sender_path, receiver_path = setup_runtime(tmp_path)
    if not callable(getattr(runtime.cognition, "native_receive", None)):
        runtime.close()
        pytest.skip("native_receive is installed by the exact staged Runtime composer")

    from v13 import native_latent_receiver as native

    sender_digest = hashlib.sha256(sender_path.read_bytes()).hexdigest()
    receiver_digest = hashlib.sha256(receiver_path.read_bytes()).hexdigest()
    vectors = [[0.25, -0.5], [1.0, 0.75]]
    tap_packet = {
        "packet_id": "tap-packet-e2e",
        "event_id": event["event_id"],
        "brain_generation_id": event["brain_generation_id"],
        "source_ref": event["source_ref"],
        "role": "B2_GIST",
        "tap_id": "qwen35.result_norm.final.v1",
        "model_revision": "sender-r1",
        "tokenizer_revision": None,
        "metrics": {
            "whole_sequence_prefill": True,
            "pooling": "none",
            "prompt_tokens": 2,
        },
    }
    tap_calls = []
    unload_calls = []
    probe_calls = []

    def fake_tap(role, current_event, source_ref, deadline):
        tap_calls.append((role, current_event["event_id"], source_ref["source_id"]))
        assert role == "B2_GIST"
        assert current_event["event_id"] == event["event_id"]
        assert source_ref == event["source_ref"]
        return tap_packet

    def fake_probe(**kwargs):
        probe_calls.append(kwargs)
        assert Path(kwargs["home"]).resolve() == runtime.home.resolve()
        assert Path(kwargs["model_path"]).resolve() == receiver_path.resolve()
        assert kwargs["expected_model_sha256"] == receiver_digest
        assert kwargs["sender_model_sha256"] == sender_digest
        assert kwargs["sender_tap_id"] == tap_packet["tap_id"]
        assert kwargs["sender_model_revision"] == tap_packet["model_revision"]
        assert kwargs["tokenizer_revision"] is None
        assert kwargs["source_id"] == event["source_ref"]["source_id"]
        assert kwargs["generation_id"] == event["brain_generation_id"]
        assert kwargs["vectors"] == vectors
        assert kwargs["position_ids"] == [0, 1]
        assert kwargs["position_mode"] == native.POSITION_MODE
        assert 1 <= kwargs["threads"] <= 2
        assert kwargs["cancel_event"] is runtime.cancel_event
        return {
            "sender_role": "B2_GIST",
            "receiver_role": "C3_LANGUAGE",
            "sender_tap_id": tap_packet["tap_id"],
            "sender_model_revision": "sender-r1",
            "sender_model_sha256": sender_digest,
            "tokenizer_revision": None,
            "receiver_model_revision": "receiver-r1",
            "receiver_model_sha256": receiver_digest,
            "runner_revision": native.PINNED_LLAMA_REVISION,
            "llama_version": "b10964",
            "input_rows": 2,
            "input_dim": 2,
            "position_ids": [0, 1],
            "position_mode": native.POSITION_MODE,
            "receiver_input_dim": 2,
            "output_dim": 4,
            "input_sha256": "a" * 64,
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

    runtime.cognition.tap = fake_tap
    runtime.cognition.read_tap = lambda packet: {
        "token_ids": [101, 202],
        "vectors": vectors,
    }
    runtime.pool.unload = lambda: unload_calls.append("unload")
    monkeypatch.setattr(native, "probe", fake_probe)
    operator = Operator(runtime)
    command = ":callosum native-probe B2_GIST C3_LANGUAGE --last-source --confirm"
    try:
        armed = json.loads(operator.run(
            ":callosum arm-probe B2_GIST C3_LANGUAGE --last-source --confirm"
        ))
        assert armed["status"] == "ARMED"

        result = json.loads(operator.run(command))
        assert result["status"] == "NATIVE_INPUT_EFFECT"
        assert result["local_approval_consumed"] is True
        assert result["sender_tap_packet_id"] == tap_packet["packet_id"]
        assert result["source_ref"] == event["source_ref"]
        assert result["provenance"] == [event["source_ref"]]
        assert result["input_rows"] == 2
        assert result["input_dim"] == 2
        assert result["receiver_input_dim"] == 2
        assert result["native_input_consumed"] is True
        assert result["input_effect_detected"] is True
        assert result["production_route"] is False
        assert result["semantic_use_proven"] is False
        assert result["training_authority"] == 0
        assert result["native_receiver_authority"] == 0
        assert tap_calls == [("B2_GIST", event["event_id"], event["source_ref"]["source_id"])]
        assert len(probe_calls) == 1
        assert len(unload_calls) >= 2

        stored = json.loads(runtime.store.one(
            "SELECT payload FROM packets WHERE kind='LatentReceiverPacket' ORDER BY rowid DESC LIMIT 1"
        )["payload"])
        assert stored["sender_tap_packet_id"] == tap_packet["packet_id"]
        assert stored["source_ref"] == event["source_ref"]
        assert stored["native_input_consumed"] is True
        assert stored["production_route"] is False

        report = callosum.controller(runtime).report(runtime.cfg)
        assert report["native_receiver_probe"]["status"] == "NATIVE_INPUT_EFFECT"
        assert report["native_receiver_probe"]["production_route"] is False
    finally:
        runtime.close()

import hashlib
import json
from pathlib import Path

import pytest

from v13 import native_probe_approval as approval
from v13 import native_probe_matrix as matrix
from v13.models import model_key
from v13.runtime import Runtime


@pytest.fixture(autouse=True)
def _interactive_tty_for_matrix_tests(monkeypatch):
    monkeypatch.setattr(approval.os, "isatty", lambda fd: fd == 0)


def setup_matrix_runtime(tmp_path):
    runtime = Runtime(Path(tmp_path) / "brain")
    runtime.sleep.cycle.set_policy("enabled", "off")
    event = runtime.store.event(runtime.session, "private source text remains local")
    runtime.store.message(runtime.session, event["event_id"], "assistant", "test answer", "FINAL", {})

    models = (
        ("B1_DETAIL", "body", "b1.gguf", "b1-r1", b"installed detail model"),
        ("B2_GIST", "gist", "b2.gguf", "b2-r1", b"installed gist model"),
        ("C3_LANGUAGE", "language", "c3.gguf", "c3-r1", b"installed language model"),
    )
    paths = {}
    for role, key, filename, revision, raw in models:
        path = runtime.home / "models" / key / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        model_key_value = model_key(role, runtime.models.b2_control)
        runtime.models.installed[model_key_value] = {
            "download_complete": True,
            "exact_revision": revision,
            "main_file": filename,
            "files": {
                filename: {
                    "path": str(path.relative_to(runtime.home)),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "size": len(raw),
                }
            },
        }
        paths[role] = path

    runtime.resources = lambda: {"mem_available_bytes": 2 * 1024 * 1024 * 1024}
    unload_calls = []
    runtime.pool.unload = lambda: unload_calls.append(True)
    return runtime, event, paths, unload_calls


def _install_fake_receiver(monkeypatch, calls):
    def receive(runtime, sender, receiver, event, source_ref, deadline):
        calls.append((sender, receiver, event["event_id"], source_ref["source_id"]))
        return {
            "sender_role": sender,
            "receiver_role": receiver,
            "status": "NATIVE_INPUT_EFFECT",
            "native_input_consumed": True,
            "input_effect_detected": True,
        }

    monkeypatch.setattr(approval, "_native_receive_interruptibly", receive)
    monkeypatch.setattr(
        matrix,
        "_packet_summary",
        lambda packet, sender, receiver: {
            "sender_role": sender,
            "receiver_role": receiver,
            "status": packet["status"],
            "native_input_consumed": packet["native_input_consumed"],
            "input_effect_detected": packet["input_effect_detected"],
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
        },
    )


def test_matrix_is_source_and_three_model_bound_one_shot(tmp_path, monkeypatch):
    runtime, event, paths, unload_calls = setup_matrix_runtime(tmp_path)
    calls = []
    _install_fake_receiver(monkeypatch, calls)
    try:
        armed = json.loads(matrix.operator_command(
            runtime, ["arm-probe-matrix", "--last-source", "--confirm"]
        ))
        assert armed["status"] == "ARMED"
        assert armed["pair_count"] == 4
        assert armed["pairs"] == [list(pair) for pair in matrix.PAIRS]
        assert armed["source_bound"] is True
        assert armed["all_three_model_revisions_hashes_paths_and_file_identities_bound"] is True
        assert armed["production_route"] is False

        result = json.loads(matrix.operator_command(
            runtime, ["native-probe-matrix", "--last-source", "--confirm"]
        ))
        assert result["schema"] == matrix.RESULT_SCHEMA
        assert result["status"] == "COMPLETE"
        assert result["completed_pairs"] == 4
        assert [(p["sender_role"], p["receiver_role"]) for p in result["pairs"]] == list(matrix.PAIRS)
        assert all(p["production_route"] is False for p in result["pairs"])
        assert all(p["training_authority"] == 0 for p in result["pairs"])
        assert len(calls) == 4
        assert all(call[2] == event["event_id"] for call in calls)
        assert all(call[3] == event["source_ref"]["source_id"] for call in calls)
        assert len(unload_calls) >= 7  # three per-model preflights plus one unload per pair

        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "CONSUMED"
        assert record["schema"] == matrix.MATRIX_SCHEMA
        with pytest.raises(PermissionError):
            matrix.operator_command(runtime, ["native-probe-matrix", "--last-source", "--confirm"])
        assert len(calls) == 4
    finally:
        runtime.close()


def test_matrix_rejects_model_tamper_before_any_receiver_call(tmp_path, monkeypatch):
    runtime, event, paths, unload_calls = setup_matrix_runtime(tmp_path)
    calls = []
    _install_fake_receiver(monkeypatch, calls)
    try:
        matrix.arm_matrix(runtime)
        original = paths["B1_DETAIL"].read_bytes()
        paths["B1_DETAIL"].write_bytes(b"X" * len(original))
        with pytest.raises(PermissionError, match="hash"):
            matrix.run_matrix(runtime)
        assert calls == []
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "PENDING"
    finally:
        runtime.close()


def test_matrix_requires_headroom_for_every_installed_role(tmp_path, monkeypatch):
    runtime, event, paths, unload_calls = setup_matrix_runtime(tmp_path)
    calls = []
    _install_fake_receiver(monkeypatch, calls)
    try:
        matrix.arm_matrix(runtime)
        runtime.resources = lambda: {"mem_available_bytes": 1}
        with pytest.raises(PermissionError, match="insufficient"):
            matrix.run_matrix(runtime)
        assert calls == []
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "PENDING"
    finally:
        runtime.close()


def test_matrix_revoke_does_not_revoke_single_pair_approval(tmp_path):
    runtime, event, paths, unload_calls = setup_matrix_runtime(tmp_path)
    try:
        approval.arm(runtime, "B2_GIST", "C3_LANGUAGE")
        result = matrix.revoke_matrix(runtime)
        assert result["status"] == "NO_PENDING_MATRIX_APPROVAL"
        record, _ = runtime.store.state(approval.KEY, None)
        assert record["status"] == "PENDING"
        assert record["schema"] == approval.SCHEMA
    finally:
        runtime.close()

import copy
import hashlib
import json
import struct
import time
import threading
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from v13.native_tokenwise_receiver_probe import (
    APPROVAL_KIND,
    NativeTokenwiseReceiverProbeError,
    probe_native_tokenwise_candidate,
)

POSITION_MODE = "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL"


class Store:
    def __init__(self, source_ref, source_text):
        self.source_ref = source_ref
        self.source_text = source_text
        self.state_value = None
        self.logs = []

    def read_source(self, ref):
        if ref != self.source_ref:
            raise ValueError("source mismatch")
        return self.source_text

    def queue_stats(self):
        return {"count": 0}

    def state(self, key, default=None):
        return copy.deepcopy(self.state_value), 1

    def log(self, kind, event_id, audit):
        self.logs.append((kind, event_id, copy.deepcopy(audit)))


class EmptyManager:
    def pids(self):
        return []


class FakeRuntime:
    def __init__(self, root):
        self.home = Path(root) / "brain"
        models = self.home / "models"
        models.mkdir(parents=True)
        self.session = "session_0123456789abcdef"
        self.source_text = "private diagnostic source"
        self.source_ref = {
            "source_id": "src_0123456789abcdef",
            "sha256": hashlib.sha256(self.source_text.encode()).hexdigest(),
            "char_start": 0,
            "char_end": len(self.source_text),
            "modality": "text",
        }
        self.event = {
            "event_id": "evt_0123456789abcdef",
            "brain_generation_id": "gen_0123456789abcdef",
        }
        self.store = Store(self.source_ref, self.source_text)
        self.cancel_event = threading.Event()
        self.stop = threading.Event()
        self.jobs = SimpleNamespace(empty=lambda: True)
        self.pool = EmptyManager()
        self.needle = EmptyManager()
        self.memory = SimpleNamespace(semantic_keys=SimpleNamespace(encoder=EmptyManager()))
        self.current = None
        self._native_probe_active = False
        self._native_probe_lease_nonce = None
        self.bindings = {}
        for role, revision, digest, filename in (
            ("B1_DETAIL", "sender-r1", "a" * 64, "sender.gguf"),
            ("C3_LANGUAGE", "receiver-r1", "b" * 64, "receiver.gguf"),
        ):
            path = models / filename
            path.write_bytes((role + "-fixture").encode())
            info = path.stat()
            self.bindings[role] = {
                "revision": revision,
                "sha256": digest,
                "canonical_path": str(path.resolve()),
                "file_identity": [
                    info.st_dev, info.st_ino, info.st_size,
                    info.st_mtime_ns, info.st_ctime_ns,
                ],
            }

    def require_idle(self):
        if self.current is not None:
            raise RuntimeError("Runtime is not idle")

    def resources(self):
        return {"mem_available_bytes": 1024 * 1024 * 1024}


class FakeApproval:
    KEY = "v14.native_probe_approval"

    def __init__(self, runtime):
        self.runtime = runtime
        self.consumed_kind = None

    @contextmanager
    def runtime_probe_lease(self, runtime):
        runtime.current = "probe"
        runtime._native_probe_active = True
        runtime._native_probe_lease_nonce = "lease-token"
        yield "lease-token"
        runtime.current = None
        runtime._native_probe_active = False
        runtime._native_probe_lease_nonce = None

    def _roles(self, sender, receiver):
        if sender not in {"B1_DETAIL", "B2_GIST"} or receiver not in {
            "B1_DETAIL", "B2_GIST", "C3_LANGUAGE"
        } or sender == receiver:
            raise ValueError("invalid roles")

    def _current_event(self, runtime):
        return runtime.event, runtime.source_ref

    def _model_binding(self, runtime, role):
        return copy.deepcopy(runtime.bindings[role])

    def consume(self, runtime, sender, receiver, event, source_ref, *,
                lease_token, probe_kind):
        assert lease_token == "lease-token"
        self.consumed_kind = probe_kind
        assert probe_kind == APPROVAL_KIND
        assert event == runtime.event
        assert source_ref == runtime.source_ref
        self.runtime.store.state_value = {
            "status": "CONSUMED",
            "probe_kind": probe_kind,
            "sender_role": sender,
            "receiver_role": receiver,
            "session_id": runtime.session,
            "event_id": event["event_id"],
            "source_ref": source_ref,
        }
        return {
            "approval_id": "approval-123456",
            "probe_kind": probe_kind,
            "consumed": True,
            "resource_preflight": {"status": "PASS"},
        }


def pair_record(runtime):
    return {
        "schema": "v14.native-tokenwise-pairing/1",
        "status": "PAIRED_DIAGNOSTIC",
        "persisted": False,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "source_ref": {
            key: runtime.source_ref[key]
            for key in ("source_id", "sha256", "char_start", "char_end")
        },
        "session_id": runtime.session,
        "event_id": runtime.event["event_id"],
        "brain_generation_id": runtime.event["brain_generation_id"],
        "record_sha256": "d" * 64,
        "sender": {
            "role": "B1_DETAIL",
            "model_revision": runtime.bindings["B1_DETAIL"]["revision"],
            "model_sha256": runtime.bindings["B1_DETAIL"]["sha256"],
            "tap_id": "b1.final-rmsnorm.v1",
            "tokenizer_revision": "llama-server:b10964;gguf:" + runtime.bindings["B1_DETAIL"]["sha256"],
        },
        "receiver": {
            "role": "C3_LANGUAGE",
            "model_revision": runtime.bindings["C3_LANGUAGE"]["revision"],
            "model_sha256": runtime.bindings["C3_LANGUAGE"]["sha256"],
            "tap_id": "c3.input-embedding.v1",
            "tokenizer_revision": "llama-server:b10964;gguf:" + runtime.bindings["C3_LANGUAGE"]["sha256"],
        },
    }


def packet(adapter, record, **kwargs):
    return {
        "schema": "v14.native-tokenwise-anchor-residual-input/1",
        "input_strategy": "ANCHOR_PLUS_CAPPED_RESIDUAL_V1",
        "vectors": [[0.1, 0.2], [0.3, 0.4]],
        "position_ids": [0, 1],
        "position_mode": POSITION_MODE,
        "input_rows": 2,
        "input_dim": 2,
        "input_sha256": hashlib.sha256(
            struct.pack("<ffff", 0.1, 0.2, 0.3, 0.4)
        ).hexdigest(),
        "anchor_sha256": "e" * 64,
        "tokenizer_revision": record["receiver"]["tokenizer_revision"],
        "source_ref": record["source_ref"],
        "event_id": record["event_id"],
        "brain_generation_id": record["brain_generation_id"],
        "session_id": record["session_id"],
        "record_sha256": record["record_sha256"],
        "adapter_sha256": adapter["adapter_sha256"],
        "sender_role": record["sender"]["role"],
        "receiver_role": record["receiver"]["role"],
        "sender_model_revision": record["sender"]["model_revision"],
        "receiver_model_revision": record["receiver"]["model_revision"],
        "sender_model_sha256": record["sender"]["model_sha256"],
        "receiver_model_sha256": record["receiver"]["model_sha256"],
        "residual_gain": kwargs["residual_gain"],
        "max_relative_residual": kwargs["max_relative_residual"],
        "mean_applied_relative_residual": 0.05,
        "anchor_rows_preserved_as_base": True,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "persisted": False,
    }


def native_result(**kwargs):
    input_payload = struct.pack(
        "<" + "f" * (len(kwargs["vectors"]) * len(kwargs["vectors"][0])),
        *(value for row in kwargs["vectors"] for value in row),
    )
    return {
        "status": "NATIVE_INPUT_EFFECT",
        "sender_role": kwargs["sender_role"],
        "receiver_role": kwargs["receiver_role"],
        "sender_tap_id": kwargs["sender_tap_id"],
        "sender_model_revision": kwargs["sender_model_revision"],
        "sender_model_sha256": kwargs["sender_model_sha256"],
        "tokenizer_revision": kwargs["tokenizer_revision"],
        "receiver_model_revision": kwargs["receiver_model_revision"],
        "receiver_model_sha256": kwargs["expected_model_sha256"],
        "runner_revision": "b29c606e28a01b1bc8c1351026a0fa6e616bf6c4",
        "input_sha256": hashlib.sha256(input_payload).hexdigest(),
        "position_ids": kwargs["position_ids"],
        "position_mode": kwargs["position_mode"],
        "input_rows": len(kwargs["vectors"]),
        "input_dim": len(kwargs["vectors"][0]),
        "native_input_consumed": True,
        "input_effect_detected": True,
        "input_effect_rms": 0.5,
        "output_norm": 1.25,
        "decode_status": 0,
        "row_shuffle_control_applicable": True,
        "zero_control_cosine": 0.1,
        "shuffle_control_cosine": 0.2,
        "row_shuffle_control_cosine": 0.3,
        "repeat_cosine": 1.0,
    }


def run_probe(runtime, approval, record, *, receiver_fn=None, packet_fn=packet):
    return probe_native_tokenwise_candidate(
        runtime, {
            "status": "ALIGNMENT_CANDIDATE",
            "projection_scope": "TOKENWISE",
            "production_route": False,
            "semantic_use_proven": False,
            "training_authority": 0,
            "native_receiver_authority": 0,
            "adapter_sha256": "c" * 64,
        }, record,
        approval_module=approval, packet_builder=packet_fn,
        receiver_fn=receiver_fn or native_result,
    )


def test_probe_consumes_separate_native_receiver_approval_and_native_input(tmp_path):
    runtime = FakeRuntime(tmp_path)
    approval = FakeApproval(runtime)
    calls = []

    def receiver_fn(**kwargs):
        calls.append(kwargs)
        return native_result(**kwargs)

    result = run_probe(runtime, approval, pair_record(runtime), receiver_fn=receiver_fn)

    assert approval.consumed_kind == "NATIVE_RECEIVER"
    assert len(calls) == 1
    assert calls[0]["vectors"] == [[0.1, 0.2], [0.3, 0.4]]
    assert calls[0]["position_ids"] == [0, 1]
    assert calls[0]["position_mode"] == POSITION_MODE
    assert calls[0]["model_path"] == Path(runtime.bindings["C3_LANGUAGE"]["canonical_path"])
    assert result["status"] == "NATIVE_RECEIVER_DIAGNOSTIC"
    assert result["native_status"] == "NATIVE_INPUT_EFFECT"
    assert result["native_input_consumed"] is True
    assert result["semantic_utility_proven"] is False
    assert result["training_authority"] == result["native_receiver_authority"] == 0
    assert result["vectors_persisted"] is result["adapter_persisted"] is False
    kind, event_id, audit = runtime.store.logs[0]
    assert kind == "native_tokenwise_receiver_probe"
    assert event_id == runtime.event["event_id"]
    assert "vectors" not in audit and "source_text" not in audit
    assert runtime.source_text not in str(audit)


def test_probe_rejects_pair_record_from_another_event_before_approval(tmp_path):
    runtime = FakeRuntime(tmp_path)
    approval = FakeApproval(runtime)
    record = pair_record(runtime)
    record["event_id"] = "evt_other_0123456789"

    with pytest.raises(PermissionError, match="current source/session/event"):
        run_probe(runtime, approval, record)
    assert approval.consumed_kind is None
    assert runtime.store.logs == []


def test_probe_rejects_nonzero_authority_packet_before_approval(tmp_path):
    runtime = FakeRuntime(tmp_path)
    approval = FakeApproval(runtime)

    def bad_packet(adapter, record, **kwargs):
        value = packet(adapter, record, **kwargs)
        value["production_route"] = True
        return value

    with pytest.raises(NativeTokenwiseReceiverProbeError, match="authority"):
        run_probe(runtime, approval, pair_record(runtime), packet_fn=bad_packet)
    assert approval.consumed_kind is None
    assert runtime.store.logs == []


def test_probe_rejects_model_file_replacement_after_native_call(tmp_path):
    runtime = FakeRuntime(tmp_path)
    approval = FakeApproval(runtime)
    receiver_path = Path(runtime.bindings["C3_LANGUAGE"]["canonical_path"])

    def replace_model(**kwargs):
        receiver_path.write_bytes(b"replaced receiver")
        return native_result(**kwargs)

    with pytest.raises(NativeTokenwiseReceiverProbeError, match="file identity changed"):
        run_probe(runtime, approval, pair_record(runtime), receiver_fn=replace_model)
    assert runtime.store.logs == []


def test_probe_does_not_write_audit_when_native_receiver_fails(tmp_path):
    runtime = FakeRuntime(tmp_path)
    approval = FakeApproval(runtime)

    def fail(**kwargs):
        raise RuntimeError("native receiver unavailable")

    with pytest.raises(RuntimeError, match="native receiver unavailable"):
        run_probe(runtime, approval, pair_record(runtime), receiver_fn=fail)
    assert runtime.store.logs == []


def test_cohort_wrapper_requires_declared_holdout_and_keeps_candidate_in_memory(tmp_path):
    runtime = FakeRuntime(tmp_path)
    record = pair_record(runtime)
    record["session_id"] = "holdout-session"
    adapter = {
        "status": "ALIGNMENT_CANDIDATE",
        "projection_scope": "TOKENWISE",
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "adapter_sha256": "c" * 64,
    }
    calls = []

    def fit_fn(records, train_sessions, holdout_sessions):
        calls.append(("fit", list(train_sessions), list(holdout_sessions)))
        return {
            "adapter": adapter,
            "fit_manifest": {
                "session_disjoint": True,
                "train_session_count": 2,
                "holdout_session_count": 2,
                "train_source_count": 8,
                "holdout_source_count": 4,
                "train_pair_count": 32,
                "holdout_pair_count": 16,
            },
        }

    def probe_fn(runtime_arg, adapter_arg, record_arg, **kwargs):
        calls.append(("probe", adapter_arg, record_arg))
        return {"status": "NATIVE_RECEIVER_DIAGNOSTIC", "semantic_utility_proven": False}

    from v13.native_tokenwise_receiver_probe import fit_and_probe_native_tokenwise_cohort

    result = fit_and_probe_native_tokenwise_cohort(
        runtime, [record], ["train-a", "train-b"],
        ["holdout-session", "holdout-other"], record,
        fit_fn=fit_fn, probe_fn=probe_fn,
    )
    assert calls[0] == ("fit", ["train-a", "train-b"], ["holdout-session", "holdout-other"])
    assert calls[1][0] == "probe"
    assert result["status"] == "ALIGNMENT_CANDIDATE_NATIVE_DIAGNOSTIC"
    assert result["fit_manifest"]["session_disjoint"] is True
    assert result["adapter_sha256"] == "c" * 64
    assert result["adapter_persisted"] is False
    assert result["pair_records_persisted"] is False
    assert result["semantic_utility_proven"] is False


def test_cohort_wrapper_refuses_record_outside_holdout_before_fit(tmp_path):
    runtime = FakeRuntime(tmp_path)
    record = pair_record(runtime)
    calls = []

    with pytest.raises(ValueError, match="declared holdout session"):
        from v13.native_tokenwise_receiver_probe import fit_and_probe_native_tokenwise_cohort
        fit_and_probe_native_tokenwise_cohort(
            runtime, [record], ["train-a", "train-b"], ["hold-a", "hold-b"], record,
            fit_fn=lambda *args: calls.append(args),
            probe_fn=lambda *args, **kwargs: calls.append((args, kwargs)),
        )
    assert calls == []


def test_callosum_native_tokenwise_probe_fails_closed_without_local_approval(tmp_path):
    from v13 import callosum

    runtime = FakeRuntime(tmp_path)
    runtime._native_tokenwise_candidate = {
        "adapter": {"adapter_sha256": "c" * 64},
        "record": pair_record(runtime),
    }
    with patch("v13.native_probe_approval._require_local_tty"):
        with patch("v13.native_tokenwise_receiver_probe.probe_native_tokenwise_candidate") as probe:
            with pytest.raises(PermissionError, match="fresh, matching one-shot"):
                callosum.operator_command(runtime, ["native-tokenwise-probe", "--confirm"])
    probe.assert_not_called()
    assert isinstance(runtime._native_tokenwise_candidate, dict)


def test_callosum_native_tokenwise_probe_consumes_matching_approval_and_clears_candidate(tmp_path):
    from v13 import callosum

    runtime = FakeRuntime(tmp_path)
    record = pair_record(runtime)
    adapter = {"adapter_sha256": "c" * 64}
    runtime._native_tokenwise_candidate = {"adapter": adapter, "record": record}
    runtime.store.state_value = {
        "status": "PENDING",
        "probe_kind": "NATIVE_RECEIVER",
        "sender_role": "B1_DETAIL",
        "receiver_role": "C3_LANGUAGE",
        "session_id": runtime.session,
        "event_id": runtime.event["event_id"],
        "brain_generation_id": runtime.event["brain_generation_id"],
        "source_ref": runtime.source_ref,
        "expires_at": time.time() + 60,
    }

    def fake_probe(runtime_arg, adapter_arg, record_arg):
        assert runtime_arg is runtime
        assert adapter_arg is adapter
        assert record_arg is record
        runtime.store.state_value["status"] = "CONSUMED"
        return {"status": "NATIVE_RECEIVER_DIAGNOSTIC", "semantic_utility_proven": False}

    with patch("v13.native_probe_approval._require_local_tty"):
        with patch("v13.native_tokenwise_receiver_probe.probe_native_tokenwise_candidate", side_effect=fake_probe):
            result = json.loads(callosum.operator_command(runtime, ["native-tokenwise-probe", "--confirm"]))
    assert result["status"] == "NATIVE_RECEIVER_DIAGNOSTIC"
    assert runtime._native_tokenwise_candidate is None
    assert runtime._native_tokenwise_pair_records == []


def test_callosum_fit_tokenwise_cohort_stages_only_current_holdout_record(tmp_path):
    from v13 import callosum
    from v13 import native_probe_approval
    from v13 import native_tokenwise_pair_capture

    runtime = FakeRuntime(tmp_path)
    runtime.session = "holdout-a"
    heldout = pair_record(runtime)
    heldout["session_id"] = "holdout-a"
    heldout["record_sha256"] = "d" * 64
    train_a = copy.deepcopy(heldout)
    train_a.update(session_id="train-a", event_id="event-train-a", record_sha256="a" * 64)
    train_b = copy.deepcopy(heldout)
    train_b.update(session_id="train-b", event_id="event-train-b", record_sha256="b" * 64)
    holdout_b = copy.deepcopy(heldout)
    holdout_b.update(session_id="holdout-b", event_id="event-holdout-b", record_sha256="e" * 64)
    runtime._native_tokenwise_pair_records = [train_a, train_b, heldout, holdout_b]
    adapter = {
        "status": "ALIGNMENT_CANDIDATE",
        "projection_scope": "TOKENWISE",
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "adapter_sha256": "c" * 64,
    }
    fit_manifest = {
        "session_disjoint": True,
        "source_disjoint": True,
        "manifest_sha256": "f" * 64,
        "train_record_count": 2,
        "holdout_record_count": 2,
        "train_pair_count": 32,
        "holdout_pair_count": 32,
    }
    with patch.object(native_probe_approval, "_require_local_tty"):
        with patch.object(native_probe_approval, "_current_event", return_value=(runtime.event, runtime.source_ref)):
            with patch.object(native_tokenwise_pair_capture, "fit_native_tokenwise_pair_cohort",
                              return_value={"adapter": adapter, "fit_manifest": fit_manifest}) as fit:
                result = json.loads(callosum.operator_command(
                    runtime,
                    ["fit-tokenwise-cohort", "train-a,train-b", "holdout-a,holdout-b", "d" * 8, "--confirm"],
                ))
    assert result["status"] == "ALIGNMENT_CANDIDATE_STAGED"
    assert result["adapter_sha256"] == "c" * 64
    assert runtime._native_tokenwise_candidate["record"] is heldout
    assert runtime._native_tokenwise_pair_records == [heldout]
    fit.assert_called_once()


def test_callosum_fit_tokenwise_cohort_refuses_missing_local_tty(tmp_path):
    from v13 import callosum
    from v13 import native_probe_approval

    runtime = FakeRuntime(tmp_path)
    runtime._native_tokenwise_pair_records = [pair_record(runtime)]
    with patch.object(native_probe_approval, "_require_local_tty", side_effect=PermissionError("TTY required")):
        with pytest.raises(PermissionError, match="TTY required"):
            callosum.operator_command(
                runtime,
                ["fit-tokenwise-cohort", "train-a,train-b", "hold-a,hold-b", "d" * 8, "--confirm"],
            )
    assert not hasattr(runtime, "_native_tokenwise_candidate")


def test_top_level_operator_parses_and_routes_callosum_tokenwise_probe():
    from v13.operator import Operator

    runtime = SimpleNamespace(store=object())
    with patch("v13.callosum.operator_command", return_value="native-probe-routed") as routed:
        result = Operator(runtime).run(":callosum native-tokenwise-probe --confirm")
    assert result == "native-probe-routed"
    routed.assert_called_once_with(runtime, ["native-tokenwise-probe", "--confirm"])


def test_top_level_operator_rejects_remote_callosum_probe_origin():
    from v13.operator import Operator

    with pytest.raises(ValueError, match="Nur lokale Operator-Eingaben"):
        Operator(object()).run(
            ":callosum native-tokenwise-probe --confirm",
            origin="REMOTE_RELAY",
        )

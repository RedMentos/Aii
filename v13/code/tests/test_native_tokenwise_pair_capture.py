import copy
import hashlib
import json
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from v13.native_tokenwise_pair_capture import (
    PROBE_KIND,
    capture_native_tokenwise_pair_record,
    fit_native_tokenwise_pair_cohort,
    operator_command,
)

SOURCE = "wxyz"


class FakeStore:
    def __init__(self, source_ref):
        self.source_ref = source_ref
        self.logs = []

    def read_source(self, ref):
        if ref != self.source_ref:
            raise ValueError("wrong source")
        return SOURCE

    def queue_stats(self):
        return {"count": 0}

    def log(self, kind, event_id, metrics):
        self.logs.append((kind, event_id, copy.deepcopy(metrics)))

    def state(self, key, default=None):
        return getattr(self, "_state", default), 1

    def set_state(self, key, value, expected=None):
        self._state = copy.deepcopy(value)
        return 2


class FakeQueue:
    def empty(self):
        return True


class FakeRunner:
    def __init__(self, runtime, role):
        self.runtime = runtime
        self.role = role
        self.loaded = False

    def load(self, cancel, deadline):
        self.loaded = True
        self.runtime.events.append("load:" + self.role)

    def _json(self, method, path, payload, deadline, timeout_cap=None):
        self.runtime.events.append("tokenize:" + self.role)
        if self.role == "B1_DETAIL":
            pieces = [
                {"id": 10, "piece": "w"},
                {"id": 11, "piece": "x"},
                {"id": 12, "piece": "y"},
                {"id": 13, "piece": "z"},
            ]
        else:
            pieces = [
                {"id": 20, "piece": "wx"},
                {"id": 21, "piece": "yz"},
            ]
        return {"tokens": pieces}


class FakePool:
    def __init__(self, runtime):
        self.runtime = runtime
        self.runners = {}
        self.live = []

    def get_tap(self, role):
        self.runtime.events.append("get_tap:" + role)
        if role not in self.runners:
            self.runners[role] = FakeRunner(self.runtime, role)
        return self.runners[role]

    def unload(self):
        self.runtime.events.append("pool_unload")
        self.live.clear()
        for runner in self.runners.values():
            runner.loaded = False
        return {"process_reaped": True}

    def pids(self):
        return list(self.live)


class FakeRuntime:
    def __init__(self, root):
        self.home = Path(root)
        (self.home / "models").mkdir()
        (self.home / "bin").mkdir()
        self.model_paths = {}
        self.model_bindings = {}
        for role, digest in (("B1_DETAIL", "a" * 64), ("C3_LANGUAGE", "b" * 64)):
            path = self.home / "models" / (role + ".gguf")
            path.write_bytes(role.encode("ascii"))
            self.model_paths[role] = path
            self.model_bindings[role] = {
                "revision": role + "-revision-1",
                "sha256": digest,
                "canonical_path": str(path),
                "file_identity": [1, 2, path.stat().st_size, 3, 4],
            }
        self.source_ref = {
            "source_id": "src_0123456789abcdef",
            "sha256": hashlib.sha256(SOURCE.encode("utf-8")).hexdigest(),
            "char_start": 0,
            "char_end": len(SOURCE),
            "modality": "text",
        }
        self.event = {
            "event_id": "evt_0123456789abcdef",
            "brain_generation_id": "gen_0123456789abcdef",
            "source_ref": self.source_ref,
        }
        self.session = "session_0123456789abcdef"
        self.store = FakeStore(self.source_ref)
        self.cancel_event = threading.Event()
        self.stop = threading.Event()
        self.jobs = FakeQueue()
        self.current = None
        self._native_probe_active = False
        self._native_probe_lease_nonce = None
        self.pool = FakePool(self)
        self.needle = SimpleNamespace(pids=lambda: [])
        self.memory = SimpleNamespace(semantic_keys=None)
        self.events = []


class FakeApproval:
    KEY = "v14.native_probe_approval"

    def __init__(self, runtime, *, drift=False):
        self.runtime = runtime
        self.drift = drift
        self.binding_calls = {}

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
        if sender not in {"B1_DETAIL", "B2_GIST"} or receiver not in {"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"} or sender == receiver:
            raise ValueError("invalid role pair")

    def _current_event(self, runtime):
        return runtime.event, runtime.source_ref

    def _model_binding(self, runtime, role):
        self.binding_calls[role] = self.binding_calls.get(role, 0) + 1
        binding = copy.deepcopy(runtime.model_bindings[role])
        if self.drift and role == "C3_LANGUAGE" and self.binding_calls[role] >= 2:
            binding["sha256"] = "c" * 64
        return binding

    def _resource_preflight(self, runtime, binding):
        runtime.events.append("preflight:" + binding["revision"])
        return {"status": "PASS"}

    def consume(self, runtime, sender, receiver, event, source_ref, *, lease_token, probe_kind):
        assert lease_token == "lease-token"
        assert probe_kind == PROBE_KIND
        assert event == runtime.event
        assert source_ref == runtime.source_ref
        runtime.events.append("approval_consumed")
        runtime.store.set_state(self.KEY, {
            "status": "CONSUMED",
            "probe_kind": probe_kind,
            "sender_role": sender,
            "receiver_role": receiver,
            "session_id": runtime.session,
            "event_id": event["event_id"],
            "source_ref": source_ref,
        })
        return {
            "approval_id": "approval-123456",
            "sender_role": sender,
            "receiver_role": receiver,
            "resource_preflight": {"status": "PASS"},
        }


class FakeCognition:
    def __init__(self, runtime):
        self.runtime = runtime
        self.packet = {
            "packet_id": "tap_0123456789abcdef",
            "role": "B1_DETAIL",
            "event_id": runtime.event["event_id"],
            "brain_generation_id": runtime.event["brain_generation_id"],
            "source_ref": runtime.source_ref,
            "tap_id": "b1.result_norm.final.v1",
            "model_revision": runtime.model_bindings["B1_DETAIL"]["revision"],
            "runner_revision": "b10964",
            "token_ids": [1, 10, 11, 12, 13],
            "feature_path": "data/blobs/tap.json",
            "feature_sha256": "d" * 64,
            "shape": [5, 2],
            "role_state": "INDEPENDENT_READ_ONLY_PREFILL",
            "receiver_read_authority": 0,
            "receiver_injection_authority": 0,
            "body_learning_authority": 0,
            "metrics": {
                "whole_sequence_prefill": True,
                "pooling": "none",
                "prompt_tokens": 5,
            },
        }
        self.data = {
            "token_ids": [1, 10, 11, 12, 13],
            "vectors": [
                [0.1, 0.2],
                [1.0, 1.1],
                [2.0, 2.1],
                [3.0, 3.1],
                [4.0, 4.1],
            ],
        }

    def tap(self, role, event, source_ref, deadline):
        self.runtime.events.append("cognition_tap:" + role)
        return self.packet

    def read_tap(self, packet):
        self.runtime.events.append("cognition_read_tap")
        assert packet is self.packet
        return self.data


def make_record(runtime, kwargs):
    assert kwargs["session_id"] == runtime.session
    assert kwargs["sender_role"] == "B1_DETAIL"
    assert kwargs["receiver_role"] == "C3_LANGUAGE"
    assert kwargs["sender_tokenizer_revision"].startswith("llama-server:b10964;gguf:")
    assert kwargs["receiver_tokenizer_revision"].startswith("llama-server:b10964;gguf:")
    assert kwargs["sender_model_sha256"] == runtime.model_bindings["B1_DETAIL"]["sha256"]
    assert kwargs["receiver_model_sha256"] == runtime.model_bindings["C3_LANGUAGE"]["sha256"]
    return {
        "schema": "v14.native-tokenwise-pairing/1",
        "status": "PAIRED_DIAGNOSTIC",
        "source_ref": {
            "source_id": runtime.source_ref["source_id"],
            "sha256": runtime.source_ref["sha256"],
            "char_start": 0,
            "char_end": len(SOURCE),
        },
        "session_id": runtime.session,
        "event_id": runtime.event["event_id"],
        "brain_generation_id": runtime.event["brain_generation_id"],
        "sender": {
            "role": "B1_DETAIL",
            "tap_id": "b1.result_norm.final.v1",
            "model_revision": runtime.model_bindings["B1_DETAIL"]["revision"],
            "model_sha256": runtime.model_bindings["B1_DETAIL"]["sha256"],
            "tokenizer_revision": kwargs["sender_tokenizer_revision"],
            "feature_sha256": "d" * 64,
        },
        "receiver": {
            "role": "C3_LANGUAGE",
            "tap_id": "c3.input-embedding.v1",
            "model_revision": runtime.model_bindings["C3_LANGUAGE"]["revision"],
            "model_sha256": runtime.model_bindings["C3_LANGUAGE"]["sha256"],
            "tokenizer_revision": kwargs["receiver_tokenizer_revision"],
            "manifest_sha256": "e" * 64,
            "embedding_dim": 3,
        },
        "pair_count": 2,
        "minimum_coverage": 1.0,
        "mean_coverage": 1.0,
        "record_sha256": "f" * 64,
        "persisted": False,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
        "pairs": [{"pair_id": "p1"}, {"pair_id": "p2"}],
    }


def test_capture_composes_cognition_tap_exact_piece_streams_and_native_extractor(tmp_path):
    runtime = FakeRuntime(tmp_path)
    approval = FakeApproval(runtime)
    cognition = FakeCognition(runtime)
    extracted = {
        "status": "COMPLETE",
        "receipt": {"schema": "fake-receipt"},
        "rows": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        "model_sha256": runtime.model_bindings["C3_LANGUAGE"]["sha256"],
        "extractor_binary_sha256": "b" * 64,
    }
    extractor_calls = []

    def extractor(binary, model, revision, token_ids, **kwargs):
        extractor_calls.append((binary, model, revision, list(token_ids), kwargs))
        kwargs["prepare_idle"]()
        runtime.events.append("extractor")
        return extracted

    def pair_builder(*args, **kwargs):
        assert args[0] == SOURCE
        assert args[1] == runtime.source_ref
        assert args[2] == [10, 11, 12, 13]
        assert args[3] == [
            {"id": 10, "piece": "w"},
            {"id": 11, "piece": "x"},
            {"id": 12, "piece": "y"},
            {"id": 13, "piece": "z"},
        ]
        assert args[4] is cognition.packet
        assert args[5] is cognition.data
        assert args[6] == [20, 21]
        assert args[8] is extracted
        return make_record(runtime, kwargs)

    result = capture_native_tokenwise_pair_record(
        runtime,
        "B1_DETAIL",
        "C3_LANGUAGE",
        approval_module=approval,
        cognition_factory=lambda r: cognition,
        extractor_fn=extractor,
        pair_builder=pair_builder,
    )

    assert result["status"] == "PAIRED_DIAGNOSTIC"
    assert result["pair_count"] == 2
    assert result["sender_tap_persisted"] is True
    assert result["receiver_rows_persisted"] is False
    assert result["pair_vectors_persisted"] is False
    assert result["pair_record_persisted"] is False
    assert result["training_authority"] == 0
    assert result["native_receiver_authority"] == 0
    assert len(extractor_calls) == 1
    assert extractor_calls[0][3] == [20, 21]
    assert runtime.events.index("cognition_tap:B1_DETAIL") < runtime.events.index("tokenize:B1_DETAIL")
    assert runtime.events.index("pool_unload") < runtime.events.index("tokenize:C3_LANGUAGE")
    assert runtime.events.index("pool_unload", runtime.events.index("tokenize:C3_LANGUAGE")) < runtime.events.index("extractor")
    assert runtime.store.logs[0][0] == "native_tokenwise_pair_capture"
    audit_text = json.dumps(runtime.store.logs[0][2])
    assert SOURCE not in audit_text
    audit = runtime.store.logs[0][2]

    def field_names(value):
        if isinstance(value, dict):
            for key, item in value.items():
                yield key
                yield from field_names(item)
        elif isinstance(value, list):
            for item in value:
                yield from field_names(item)

    assert not {"vectors", "pairs", "sender_vector", "receiver_vector", "receiver_rows"}.intersection(
        field_names(audit)
    )
    assert audit["pair_vectors_persisted"] is False
    assert audit["pair_record_persisted"] is False
    assert "token_ids" not in audit_text


def test_capture_rejects_model_binding_drift_after_extraction(tmp_path):
    runtime = FakeRuntime(tmp_path)
    approval = FakeApproval(runtime, drift=True)
    cognition = FakeCognition(runtime)
    calls = []

    def extractor(binary, model, revision, token_ids, **kwargs):
        kwargs["prepare_idle"]()
        calls.append("extract")
        return {
            "status": "COMPLETE",
            "receipt": {},
            "rows": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
            "model_sha256": runtime.model_bindings["C3_LANGUAGE"]["sha256"],
            "extractor_binary_sha256": "b" * 64,
        }

    with pytest.raises(Exception, match="model binding changed"):
        capture_native_tokenwise_pair_record(
            runtime,
            "B1_DETAIL",
            "C3_LANGUAGE",
            approval_module=approval,
            cognition_factory=lambda r: cognition,
            extractor_fn=extractor,
            pair_builder=lambda *a, **k: make_record(runtime, k),
        )
    assert calls == ["extract"]
    assert runtime.store.logs == []


def test_cancel_after_receiver_tokenization_prevents_native_extractor(tmp_path):
    runtime = FakeRuntime(tmp_path)
    approval = FakeApproval(runtime)
    cognition = FakeCognition(runtime)
    original_get_tap = runtime.pool.get_tap

    def get_tap(role):
        runner = original_get_tap(role)
        if role == "C3_LANGUAGE":
            original_json = runner._json
            def cancel_after(*args, **kwargs):
                result = original_json(*args, **kwargs)
                runtime.cancel_event.set()
                return result
            runner._json = cancel_after
        return runner

    runtime.pool.get_tap = get_tap
    called = []

    with pytest.raises(InterruptedError):
        capture_native_tokenwise_pair_record(
            runtime,
            "B1_DETAIL",
            "C3_LANGUAGE",
            approval_module=approval,
            cognition_factory=lambda r: cognition,
            extractor_fn=lambda *a, **k: called.append("extractor"),
            pair_builder=lambda *a, **k: make_record(runtime, k),
        )
    assert called == []
    assert runtime.store.logs == []


def test_pair_operator_requires_distinct_approval_kind_and_routes_capture():
    class Commands:
        def __init__(self):
            self.calls = []
        def arm(self, runtime, sender, receiver, *, probe_kind):
            self.calls.append(("arm", sender, receiver, probe_kind))
            return {"status": "ARMED", "probe_kind": probe_kind}
        def revoke(self, runtime):
            self.calls.append(("revoke",))
            return {"status": "REVOKED"}

    commands = Commands()
    runtime = object()
    armed = json.loads(operator_command(
        runtime,
        ["arm-tokenwise-pair", "B1_DETAIL", "C3_LANGUAGE", "--last-source", "--confirm"],
        approval_module=commands,
    ))
    assert armed == {"status": "ARMED", "probe_kind": PROBE_KIND}
    revoked = json.loads(operator_command(runtime, ["revoke-tokenwise-pair"], approval_module=commands))
    assert revoked == {"status": "REVOKED"}
    ran = json.loads(operator_command(
        runtime,
        ["native-tokenwise-pair", "B1_DETAIL", "C3_LANGUAGE", "--last-source", "--confirm"],
        approval_module=commands,
        capture_fn=lambda r, s, t: {"status": "PAIRED_DIAGNOSTIC", "sender": s, "receiver": t},
    ))
    assert ran["status"] == "PAIRED_DIAGNOSTIC"
    assert commands.calls == [("arm", "B1_DETAIL", "C3_LANGUAGE", PROBE_KIND), ("revoke",)]


def test_callosum_dispatches_pair_capture_before_production_controller():
    from v13 import callosum

    runtime = object()
    with patch("v13.native_tokenwise_pair_capture.operator_command", return_value="pair-routed") as routed:
        result = callosum.operator_command(
            runtime,
            ["native-tokenwise-pair", "B1_DETAIL", "C3_LANGUAGE", "--last-source", "--confirm"],
        )
    assert result == "pair-routed"
    routed.assert_called_once_with(
        runtime,
        ["native-tokenwise-pair", "B1_DETAIL", "C3_LANGUAGE", "--last-source", "--confirm"],
    )


def test_fit_cohort_forwards_whole_session_split_to_schema_v4_fitter():
    records = [{"status": "PAIRED_DIAGNOSTIC", "persisted": False}]
    train = ["train-a", "train-b"]
    holdout = ["holdout-a", "holdout-b"]
    expected = {"status": "ALIGNMENT_CANDIDATE", "training_authority": 0}
    with patch("v13.native_tokenwise_pairing.fit_adapter_from_native_pair_records", return_value=expected) as fit:
        result = fit_native_tokenwise_pair_cohort(records, train, holdout)
    assert result is expected
    fit.assert_called_once_with(records, train_session_ids=train, holdout_session_ids=holdout)


def test_fit_cohort_rejects_empty_in_memory_records():
    with pytest.raises(ValueError, match="non-empty"):
        fit_native_tokenwise_pair_cohort([], ["train-a", "train-b"], ["holdout-a", "holdout-b"])

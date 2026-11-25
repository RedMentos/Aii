import hashlib
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

from v13.native_input_embedding_capture import (
    NativeInputEmbeddingCaptureError,
    capture_native_input_embedding_tap,
    operator_command,
)

SOURCE = "A\u00e1\U0001f9e0e\u0301"
TOKEN_PIECES = [
    {"id": 10, "piece": "A"},
    {"id": 11, "piece": [0xC3]},
    {"id": 12, "piece": [0xA1, 0xF0]},
    {"id": 13, "piece": [0x9F, 0xA7]},
    {"id": 14, "piece": [0xA0]},
    {"id": 15, "piece": "e"},
    {"id": 16, "piece": [0xCC]},
    {"id": 17, "piece": [0x81]},
]
TOKEN_IDS = [item["id"] for item in TOKEN_PIECES]
ROWS = [[float(i + 1), float(i + 2), float(i + 3)] for i in range(len(TOKEN_IDS))]
LLAMA_REVISION = "2851b3bcbf8d993a2243ae751c0a7dfa8e944a40"


class FakeQueue:
    def empty(self):
        return True


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
        self.logs.append((kind, event_id, metrics))


class FakeRunner:
    def __init__(self, runtime, tokens=None, cancel_after_tokenize=False):
        self.runtime = runtime
        self.tokens = TOKEN_PIECES if tokens is None else tokens
        self.cancel_after_tokenize = cancel_after_tokenize

    def load(self, cancel, deadline):
        self.runtime.events.append("runner_load")

    def _json(self, method, path, payload, deadline, timeout_cap=None):
        self.runtime.events.append("tokenize")
        self.runtime.assertions.append((method, path, payload, timeout_cap))
        if self.cancel_after_tokenize:
            self.runtime.cancel_event.set()
        return {"tokens": self.tokens}


class FakePool:
    def __init__(self, runtime, runner):
        self.runtime = runtime
        self.runner = runner
        self.remaining = []

    def unload(self):
        self.runtime.events.append("pool_unload")
        self.remaining = []
        return {"process_reaped": True, "was_loaded": True}

    def get_tap(self, role):
        self.runtime.events.append("get_tap:" + role)
        return self.runner

    def pids(self):
        return list(self.remaining)


class FakeApproval:
    def __init__(self, runtime, model_path, model_sha):
        self.runtime = runtime
        self.model_path = model_path
        self.model_sha = model_sha

    def _roles(self, sender, receiver):
        if sender not in {"B1_DETAIL", "B2_GIST"} or receiver not in {"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"} or sender == receiver:
            raise ValueError("invalid roles")

    @contextmanager
    def runtime_probe_lease(self, runtime):
        runtime.current = "probe"
        runtime._native_probe_active = True
        runtime._native_probe_lease_nonce = "lease-test"
        runtime.events.append("lease_enter")
        try:
            yield "lease-test"
        finally:
            runtime.current = None
            runtime._native_probe_active = False
            runtime._native_probe_lease_nonce = None
            runtime.events.append("lease_exit")

    def _current_event(self, runtime):
        runtime.events.append("current_event")
        return runtime.event, runtime.store.source_ref

    def consume(self, runtime, sender, receiver, event, source_ref, *, lease_token, probe_kind):
        self.runtime.events.append("approval_consumed")
        if (lease_token != "lease-test" or event != runtime.event
                or source_ref != runtime.store.source_ref
                or probe_kind != "INPUT_EMBEDDING_TAP"):
            raise PermissionError("approval binding mismatch")
        return {"approval_id": "approval-123", "resource_preflight": {"status": "PASS"}}

    def _model_binding(self, runtime, role):
        if role != "C3_LANGUAGE":
            raise AssertionError("unexpected receiver")
        return {
            "revision": "model-r1",
            "sha256": self.model_sha,
            "canonical_path": str(self.model_path),
            "file_identity": [1, 2, self.model_path.stat().st_size, 3, 4],
        }

    def _resource_preflight(self, runtime, model_binding):
        runtime.events.append("resource_preflight")
        if model_binding["sha256"] != self.model_sha:
            raise PermissionError("wrong model")
        return {"status": "PASS"}


class FakeRuntime:
    def __init__(self, home, model_path, *, tokens=None, cancel_after_tokenize=False):
        self.home = Path(home)
        self.events = []
        self.assertions = []
        self.stop = threading.Event()
        self.cancel_event = threading.Event()
        self.jobs = FakeQueue()
        self.current = None
        self._native_probe_active = False
        self._native_probe_lease_nonce = None
        source_ref = {
            "source_id": "src_0123456789abcdef",
            "sha256": hashlib.sha256(SOURCE.encode("utf-8")).hexdigest(),
            "char_start": 0,
            "char_end": len(SOURCE),
            "modality": "text",
        }
        self.event = {
            "event_id": "evt_0123456789abcdef",
            "brain_generation_id": "gen_0123456789abcdef",
            "source_ref": source_ref,
        }
        self.store = FakeStore(source_ref)
        self.runner = FakeRunner(self, tokens=tokens, cancel_after_tokenize=cancel_after_tokenize)
        self.pool = FakePool(self, self.runner)
        self.needle = SimpleNamespace(pids=lambda: [])
        self.memory = SimpleNamespace(semantic_keys=None)
        self.model_path = model_path


class NativeInputEmbeddingCaptureTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        (self.home / "models").mkdir()
        (self.home / "bin").mkdir()
        self.model_path = self.home / "models" / "receiver.gguf"
        self.model_path.write_bytes(b"synthetic receiver model fixture")
        self.binary_path = self.home / "bin" / "native_input_embedding_extractor"
        self.binary_path.write_bytes(b"synthetic executable fixture")
        self.model_sha = hashlib.sha256(self.model_path.read_bytes()).hexdigest()
        self.runtime = FakeRuntime(self.home, self.model_path)
        self.approval = FakeApproval(self.runtime, self.model_path, self.model_sha)

    def tearDown(self):
        self.temp.cleanup()

    def _receipt(self, token_ids):
        return {
            "schema": "v14.llama-token-embedding-rows-receipt/1",
            "api_symbol": "llama_model_get_tok_embd_rows",
            "api_header": "src/llama-ext.h",
            "api_stability": "STAGING_WIP",
            "llama_cpp_revision": LLAMA_REVISION,
            "extractor_binary_sha256": "b" * 64,
            "model_revision": "model-r1",
            "model_sha256": self.model_sha,
            "source_tensor_type": "q4_0",
            "output_dtype": "f32",
            "vocab_size": 32000,
            "embedding_dim": 3,
            "requested_token_ids": list(token_ids),
            "elements_written": len(token_ids) * 3,
        }

    def _extractor(self, binary, model, revision, token_ids, **kwargs):
        self.runtime.events.append("extractor_start")
        self.assertEqual(Path(binary), self.binary_path)
        self.assertEqual(Path(model), self.model_path)
        self.assertEqual(revision, "model-r1")
        self.assertEqual(token_ids, TOKEN_IDS)
        self.assertEqual(self.runtime.pool.pids(), [])
        kwargs["prepare_idle"]()
        self.runtime.events.append("extractor_after_idle")
        return {
            "status": "COMPLETE",
            "receipt": self._receipt(token_ids),
            "rows": ROWS,
            "model_sha256": self.model_sha,
            "extractor_binary_sha256": "b" * 64,
        }

    def _capture(self, **kwargs):
        return capture_native_input_embedding_tap(
            self.runtime,
            "B1_DETAIL",
            "C3_LANGUAGE",
            approval_module=self.approval,
            extractor_fn=self._extractor,
            **kwargs,
        )

    def test_native_tokenizer_and_extractor_are_connected_source_bound_and_ephemeral(self):
        result = self._capture()
        self.assertEqual(result["status"], "DIAGNOSTIC_ONLY")
        self.assertEqual(result["token_count"], len(TOKEN_IDS))
        self.assertEqual(result["embedding_dim"], 3)
        self.assertEqual(result["source_sha256"], self.runtime.store.source_ref["sha256"])
        self.assertEqual(result["model_sha256"], self.model_sha)
        self.assertEqual(result["llama_cpp_revision"], LLAMA_REVISION)
        self.assertEqual(result["sender_role"], "B1_DETAIL")
        self.assertFalse(result["sender_activation_captured"])
        self.assertFalse(result["vectors_persisted"])
        self.assertFalse(result["vectors_returned"])
        self.assertFalse(result["production_route"])
        self.assertFalse(result["semantic_use_proven"])
        self.assertEqual(result["training_authority"], 0)
        self.assertEqual(result["native_receiver_authority"], 0)
        self.assertTrue(result["audit_logged"])
        self.assertEqual(len(self.runtime.store.logs), 1)
        kind, event_id, metrics = self.runtime.store.logs[0]
        self.assertEqual(kind, "native_input_embedding_tap")
        self.assertEqual(event_id, self.runtime.event["event_id"])
        self.assertEqual(metrics["id"], result["manifest_sha256"])
        self.assertNotIn(SOURCE, json.dumps(metrics))
        self.assertNotIn("vectors", metrics)
        self.assertEqual(self.runtime.assertions[0], (
            "POST",
            "/tokenize",
            {
                "content": SOURCE,
                "add_special": False,
                "parse_special": False,
                "with_pieces": True,
            },
            None,
        ))
        self.assertLess(self.runtime.events.index("approval_consumed"), self.runtime.events.index("get_tap:C3_LANGUAGE"))
        self.assertLess(self.runtime.events.index("tokenize"), self.runtime.events.index("extractor_start"))
        self.assertLess(self.runtime.events.index("pool_unload", self.runtime.events.index("tokenize")), self.runtime.events.index("extractor_start"))
        self.assertLess(self.runtime.events.index("resource_preflight"), self.runtime.events.index("extractor_after_idle"))

    def test_malformed_tokenizer_response_fails_closed_and_reaps_runner(self):
        self.runtime.runner.tokens = [{"id": 10, "piece": "A"}]
        with self.assertRaises(NativeInputEmbeddingCaptureError):
            self._capture()
        self.assertEqual(self.runtime.store.logs, [])
        self.assertEqual(self.runtime.pool.pids(), [])
        self.assertIn("pool_unload", self.runtime.events)

    def test_source_piece_mismatch_is_rejected_without_audit_record(self):
        self.runtime.runner.tokens = [
            {"id": item["id"], "piece": ("X" if index == 0 else item["piece"])}
            for index, item in enumerate(TOKEN_PIECES)
        ]
        with self.assertRaises(ValueError):
            self._capture()
        self.assertEqual(self.runtime.store.logs, [])

    def test_remaining_managed_native_process_blocks_extractor(self):
        original = self.runtime.pool.pids
        self.runtime.pool.pids = lambda: [12345]
        with self.assertRaises(NativeInputEmbeddingCaptureError):
            self._capture()
        self.runtime.pool.pids = original
        self.assertFalse(any(item == "extractor_start" for item in self.runtime.events))
        self.assertEqual(self.runtime.store.logs, [])

    def test_cancel_after_tokenization_blocks_native_extractor(self):
        self.runtime.runner.cancel_after_tokenize = True
        with self.assertRaises(InterruptedError):
            self._capture()
        self.assertFalse(any(item == "extractor_start" for item in self.runtime.events))
        self.assertEqual(self.runtime.store.logs, [])

    def test_large_source_is_rejected_before_consuming_approval_or_loading_model(self):
        self.runtime.store.read_source = lambda ref: "x" * 4097
        with self.assertRaisesRegex(NativeInputEmbeddingCaptureError, "4096-byte"):
            self._capture()
        self.assertFalse(any(item == "approval_consumed" for item in self.runtime.events))
        self.assertFalse(any(item.startswith("get_tap:") for item in self.runtime.events))



    def test_probe_kind_is_not_interchangeable_with_native_receiver_approval(self):
        from v13.native_probe_approval import _require_probe_kind
        self.assertEqual(
            _require_probe_kind({"probe_kind": "INPUT_EMBEDDING_TAP"}, "INPUT_EMBEDDING_TAP"),
            "INPUT_EMBEDDING_TAP",
        )
        self.assertEqual(
            _require_probe_kind({"probe_kind": "NATIVE_RECEIVER"}, "NATIVE_RECEIVER"),
            "NATIVE_RECEIVER",
        )
        # Older persisted approvals have no kind and remain native-receiver only.
        self.assertEqual(_require_probe_kind({}, "NATIVE_RECEIVER"), "NATIVE_RECEIVER")
        with self.assertRaises(PermissionError):
            _require_probe_kind({"probe_kind": "INPUT_EMBEDDING_TAP"}, "NATIVE_RECEIVER")
        with self.assertRaises(PermissionError):
            _require_probe_kind({"probe_kind": "NATIVE_RECEIVER"}, "INPUT_EMBEDDING_TAP")

    def test_callosum_dispatches_input_tap_before_production_controller(self):
        from v13 import callosum
        with patch("v13.native_input_embedding_capture.operator_command", return_value="input-tap-routed") as routed:
            result = callosum.operator_command(
                self.runtime,
                ["native-input-tap", "B1_DETAIL", "C3_LANGUAGE", "--last-source", "--confirm"],
            )
        self.assertEqual(result, "input-tap-routed")
        routed.assert_called_once_with(
            self.runtime,
            ["native-input-tap", "B1_DETAIL", "C3_LANGUAGE", "--last-source", "--confirm"],
        )

    def test_operator_command_uses_separate_arm_run_and_revoke_names(self):
        class Commands:
            def __init__(self):
                self.calls = []
            def arm(self, runtime, sender, receiver, *, probe_kind):
                self.calls.append(("arm", sender, receiver, probe_kind))
                return {"status": "ARMED"}
            def revoke(self, runtime):
                self.calls.append(("revoke",))
                return {"status": "REVOKED"}

        commands = Commands()
        armed = operator_command(self.runtime, [
            "arm-input-tap", "B1_DETAIL", "C3_LANGUAGE", "--last-source", "--confirm",
        ], approval_module=commands)
        self.assertEqual(json.loads(armed), {"status": "ARMED"})
        revoked = operator_command(self.runtime, ["revoke-input-tap"], approval_module=commands)
        self.assertEqual(json.loads(revoked), {"status": "REVOKED"})
        ran = operator_command(
            self.runtime,
            ["native-input-tap", "B1_DETAIL", "C3_LANGUAGE", "--last-source", "--confirm"],
            approval_module=commands,
            capture_fn=lambda runtime, sender, receiver: {"status": "DIAGNOSTIC_ONLY", "sender": sender, "receiver": receiver},
        )
        self.assertEqual(json.loads(ran)["status"], "DIAGNOSTIC_ONLY")
        self.assertEqual(commands.calls, [
            ("arm", "B1_DETAIL", "C3_LANGUAGE", "INPUT_EMBEDDING_TAP"),
            ("revoke",),
        ])
        with self.assertRaises(ValueError):
            operator_command(self.runtime, ["native-input-tap", "B1_DETAIL", "C3_LANGUAGE"])

if __name__ == "__main__":
    unittest.main()

"""Software-only V2 QAD base+LoRA collector/scorer tests, no model/heldout execution."""
import copy
from contextlib import contextmanager
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from scripts import bp1_qad_lora_eval as E
from scripts import bp1_paired_score as S


def binding():
    return {
        "schema": E.SCHEMA, "dataset_sha256": S.HELDOUT_SHA,
        "base_master_sha256": E.N.MASTER_SHA,
        "base_gguf_sha256": E.N.GGUF_SHA,
        "adapter_gguf_sha256": "a" * 64,
        "runner_sha256": E.RUNNER_SHA,
        "seed": 13, "temperature": 0,
        "decoding": E.C.DECODING,
        "lora_id": 0, "scales": dict(E.SCALES),
        "train_sha256": E.T.TRAIN_SHA,
        "train_proof_sha256": "b" * 64,
        "production_weight_authority": 0,
        "gates": dict(E.GATES),
    }


def train_proof():
    return {
        "schema": E.T.SCHEMA, "mode": "train",
        "status": "TRAINED_SHADOW_ADAPTER_NOT_DEPLOYED",
        "train_sha256": E.T.TRAIN_SHA,
        "master": {"master_sha256": E.N.MASTER_SHA},
        "config": dict(E.T.CFG),
        "train_rows": 25,
        "heldout_files_opened": False,
        "native_training_executed": True,
        "production_weight_authority": 0,
        "redmi_measured": False,
        "model_utility_proven": False,
        "gates": dict(E.T.GATES),
        "adapter": {"gguf_sha256": "a" * 64, "lora_b_nonzero": 3},
        "metrics": {"steps": 2, "trainable_parameter_count": 100, "jepa_weight": 0},
    }


def index():
    rows = {}
    for i in range(11):
        rid = f"RUN181-{i:02d}"
        for arm in S.ARMS:
            rows[(rid, arm)] = {
                "row_id": rid, "arm": arm, "source_sha256": "c" * 64,
                "prompt": f"Question {i} {arm}. Original source: source KEY",
                "source": "source KEY", "answer_keys": ["KEY"],
            }
    return rows


class QADLoraEvalTests(unittest.TestCase):
    def test_binding_accepts_explicit_base_plus_adapter(self):
        self.assertTrue(E.validate_binding(binding(), S.HELDOUT_SHA))

    def test_adapter_is_never_mislabeled_full_model(self):
        b = binding()
        b["adapter_gguf_sha256"] = E.N.GGUF_SHA
        with self.assertRaisesRegex(ValueError, "confused with base"):
            E.validate_binding(b, S.HELDOUT_SHA)

    def test_binding_rejects_source_runner_training_and_gate_drift(self):
        for field, value in (
            ("base_master_sha256", "a" * 64), ("runner_sha256", "a" * 64),
            ("train_sha256", "a" * 64), ("train_proof_sha256", "missing"),
            ("seed", 14), ("temperature", 0.5), ("lora_id", 1),
            ("scales", {"base": 1.0, "candidate": 0.0}),
            ("gates", {"jepa_weight": 1}),
            ("production_weight_authority", 1),
        ):
            with self.subTest(field=field):
                b = binding()
                b[field] = value
                with self.assertRaises(ValueError):
                    E.validate_binding(b, S.HELDOUT_SHA)

    def test_request_contains_only_prompt_and_explicit_scale(self):
        seen = []
        def fake_http(port, method, path, payload):
            seen.append((port, method, path, payload))
            return {"choices": [{"message": {"content": '{"answer":"KEY"}'}}]}
        with patch.object(E, "_http_json", side_effect=fake_http):
            for scale in (0.0, 1.0):
                E.request(8832, "safe prompt", 13, scale)
        self.assertEqual([x[3]["lora"] for x in seen],
                         [[{"id": 0, "scale": 0.0}], [{"id": 0, "scale": 1.0}]])
        self.assertEqual([x[3]["messages"][1]["content"] for x in seen], ["safe prompt", "safe prompt"])
        self.assertTrue(all(x[2] == "/v1/chat/completions" for x in seen))
        self.assertTrue(all(x[3]["temperature"] == 0 for x in seen))
        self.assertTrue(all("target" not in str(x[3]) for x in seen))

    def test_unregistered_scale_rejected(self):
        with self.assertRaisesRegex(ValueError, "scale"):
            E.request(8832, "prompt", 13, 0.5)

    def test_owned_server_requires_loaded_matching_adapter(self):
        class FakeProc:
            def poll(self): return None
        with tempfile.TemporaryDirectory() as d:
            binary = Path(d) / "llama-server"
            base = Path(d) / "base.gguf"
            adapter = Path(d) / "adapter.gguf"
            binary.write_bytes(b"binary")
            base.write_bytes(b"base")
            adapter.write_bytes(b"adapter")
            with patch.object(E.N, "assert_loopback_port_available"), \
                 patch.object(E.subprocess, "Popen", return_value=FakeProc()), \
                 patch.object(E.C, "stop") as stop, \
                 patch.object(E, "_http_json", side_effect=[
                     {"status": "ok"}, [{"id": 0, "path": str(adapter), "scale": 0.0}]
                 ]):
                with E.serve(binary, base, adapter, 8832, Path(d) / "server.log"):
                    pass
                stop.assert_called_once()
            with patch.object(E.N, "assert_loopback_port_available"), \
                 patch.object(E.subprocess, "Popen", return_value=FakeProc()), \
                 patch.object(E.C, "stop"), \
                 patch.object(E, "_http_json", side_effect=[
                     {"status": "ok"}, [{"id": 0, "path": "wrong.gguf", "scale": 0.0}]
                 ]):
                with self.assertRaisesRegex(RuntimeError, "adapter ID/path"):
                    with E.serve(binary, base, adapter, 8832, Path(d) / "bad.log"):
                        pass

    def test_train_proof_bytes_and_optimizer_are_required(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "proof.json"
            p.write_text(json.dumps(train_proof(), sort_keys=True))
            b = binding()
            b["train_proof_sha256"] = E.S.sha(p.read_bytes())
            self.assertTrue(E.verify_train_proof(b, p))
            bad = train_proof()
            bad["native_training_executed"] = False
            p.write_text(json.dumps(bad, sort_keys=True))
            with self.assertRaises(ValueError):
                E.verify_train_proof(b, p)
            bad = train_proof()
            bad["adapter"]["lora_b_nonzero"] = 0
            p.write_text(json.dumps(bad, sort_keys=True))
            with self.assertRaises(ValueError):
                E.verify_train_proof(b, p)

    def test_resume_only_missing_records_and_preserves_exact_binding(self):
        rows = index()
        @contextmanager
        def fake_serve(*args):
            yield
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bind = root / "binding.json"
            bind.write_text(json.dumps(binding()))
            proof = root / "proof.json"
            proof.write_text(json.dumps(train_proof()))
            out = root / "out"
            seen = []
            def interrupt(port, prompt, seed, scale):
                seen.append((prompt, scale))
                if len(seen) == 6:
                    raise RuntimeError("injected interruption")
                return json.dumps({"answer": "KEY", "evidence_quote": "source KEY", "uncertainty": ""})
            with patch.object(E.S, "load_dataset", return_value=(rows, S.HELDOUT_SHA)), \
                 patch.object(E, "validate_native_files", return_value={"verified": True}), \
                 patch.object(E, "validate_train_proof", return_value=True):
                with self.assertRaisesRegex(RuntimeError, "injected interruption"):
                    E.collect("unused", bind, "server", "base", "adapter", out,
                        train_proof_path=proof, owner_confirmed=True, ask=interrupt,
                        server_context=fake_serve)
                self.assertEqual(len(S.read_jsonl(out / "predictions.jsonl")[0]), 5)
                completed = E.collect("unused", bind, "server", "base", "adapter", out,
                    train_proof_path=proof, resume=True, owner_confirmed=True,
                    ask=lambda *args: json.dumps({"answer": "KEY", "evidence_quote": "source KEY", "uncertainty": ""}),
                    server_context=fake_serve)
                self.assertEqual(completed["rows"], 44)
                with self.assertRaises(ValueError):
                    E.collect("unused", bind, "server", "base", "adapter", out,
                        train_proof_path=proof, resume=True, owner_confirmed=True,
                        ask=lambda *args: "x", server_context=fake_serve)

    def test_owner_confirmation_is_required(self):
        with self.assertRaises(PermissionError):
            E.collect("none", "none", "none", "none", "none", "none")

    def test_mocked_serial_collection_is_44_source_bound_rows(self):
        rows = index()
        @contextmanager
        def fake_serve(*args):
            yield
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bind = root / "binding.json"
            bind.write_text(json.dumps(binding()))
            with patch.object(E.S, "load_dataset", return_value=(rows, S.HELDOUT_SHA)), \
                 patch.object(E, "validate_native_files", return_value={"verified": True}):
                result = E.collect("unused", bind, "server", "base", "adapter", root / "out",
                    train_proof_path="mock-proof", owner_confirmed=True, ask=lambda port, prompt, seed, scale: json.dumps({
                        "answer": "KEY", "evidence_quote": "source KEY", "uncertainty": ""}),
                    server_context=fake_serve)
            self.assertEqual(result["rows"], 44)
            self.assertFalse(result["heldout_targets_sent_to_model"])
            self.assertEqual(result["lora_scales"], E.SCALES)
            preds, _ = S.read_jsonl(root / "out" / "predictions.jsonl")
            self.assertEqual(len(preds), 44)
            with patch.object(E.S, "load_dataset", return_value=(rows, S.HELDOUT_SHA)):
                score = E.score("unused", bind, root / "out" / "predictions.jsonl", root / "scores")
            self.assertEqual(score["schema"], E.SCORE_SCHEMA)
            self.assertEqual(score["candidate_semantics"], "SAME_QAD_BASE_GGUF_PLUS_VERIFIED_LORA_ADAPTER")
            self.assertFalse(score["model_utility_proven"])
            self.assertEqual(score["counts"]["base"]["offer"]["supported"], 11)

    def test_missing_native_predictions_fail_closed(self):
        rows = index()
        with self.assertRaisesRegex(ValueError, "incomplete predictions"):
            S.evaluate(rows, S.HELDOUT_SHA, binding(), [], binding_validator=E.validate_binding)


if __name__ == "__main__":
    unittest.main()

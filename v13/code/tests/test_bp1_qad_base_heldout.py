"""Software-only BP1 QAD base Q4 heldout collection/scoring tests."""
import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from scripts import bp1_qad_base_heldout as B
from scripts import bp1_paired_score as S
from tests.test_bp1_qad_lora_eval import index


def binding():
    return {"schema": B.SCHEMA, "dataset_sha256": S.HELDOUT_SHA,
            "model_sha256": B.N.GGUF_SHA, "runner_sha256": B.V2.RUNNER_SHA,
            "seed": 13, "temperature": 0, "decoding": B.C.DECODING,
            "production_weight_authority": 0, "gates": dict(B.GATES)}


@contextmanager
def fake_serve(*args):
    yield


class BaseOnlyTests(unittest.TestCase):
    def test_binding_requires_exact_original_source_runner_seed_gates(self):
        self.assertTrue(B.validate_binding(binding(), S.HELDOUT_SHA))
        for field, value in (
            ("dataset_sha256", "f"*64), ("model_sha256", "a"*64),
            ("runner_sha256", "b"*64), ("seed", 14), ("temperature", 0.2),
            ("decoding", "not greedy"), ("production_weight_authority", 1),
            ("gates", {"jepa_weight": 1}),
        ):
            with self.subTest(field=field):
                b = binding()
                b[field] = value
                with self.assertRaises(ValueError):
                    B.validate_binding(b, S.HELDOUT_SHA)

    def test_owner_required_before_any_dataset_or_file_open(self):
        with self.assertRaises(PermissionError):
            B.collect("missing", "missing", "missing", "missing", "missing")

    def test_22_source_bound_base_only_records_and_scoring(self):
        rows = index()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bpath = root / "binding.json"
            bpath.write_text(json.dumps(binding()))
            sent = []
            def ask(port, prompt, seed):
                sent.append((port, prompt, seed))
                return json.dumps({"answer": "KEY", "evidence_quote": "source KEY", "uncertainty": ""})
            with patch.object(B.S, "load_dataset", return_value=(rows, S.HELDOUT_SHA)), \
                 patch.object(B, "validate_files", return_value={"model_sha256": B.N.GGUF_SHA}):
                result = B.collect("unused", bpath, "server", "model", root / "run",
                                   owner_confirmed=True, ask=ask, server_context=fake_serve)
                score = B.score("unused", bpath, root / "run" / "predictions.jsonl", root / "score")
            self.assertEqual(result["rows"], 22)
            self.assertEqual(len(sent), 22)
            self.assertTrue(all(seed == 13 for _, _, seed in sent))
            self.assertEqual({p for _, p, _ in sent}, {row["prompt"] for row in rows.values()})
            self.assertTrue(result["base_only"])
            self.assertFalse(result["heldout_targets_sent_to_model"])
            self.assertEqual(score["counts"]["offer"]["supported"], 11)
            self.assertEqual(score["counts"]["no_offer"]["supported"], 11)
            self.assertEqual(score["offer_vs_no_offer"], {"wins": 0, "losses": 0, "ties": 11})
            self.assertFalse(score["native_execution_verified_by_scorer"])
            self.assertFalse(score["model_utility_proven"])
            preds, _ = S.read_jsonl(root / "run" / "predictions.jsonl")
            self.assertEqual({r["model"] for r in preds}, {"base"})
            self.assertEqual(len(preds), 22)

    def test_resume_partial_and_changed_binding_fail_closed(self):
        rows = index()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bpath = root / "binding.json"
            bpath.write_text(json.dumps(binding()))
            calls = []
            def interrupt(port, prompt, seed):
                calls.append(prompt)
                if len(calls) == 4:
                    raise RuntimeError("interrupted")
                return "{}"
            with patch.object(B.S, "load_dataset", return_value=(rows, S.HELDOUT_SHA)), \
                 patch.object(B, "validate_files", return_value={}):
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    B.collect("unused", bpath, "server", "model", root / "run",
                              owner_confirmed=True, ask=interrupt, server_context=fake_serve)
                pred = root / "run" / "predictions.jsonl"
                original = pred.read_bytes()
                self.assertEqual(len(S.read_jsonl(pred)[0]), 3)
                bpath.write_bytes(bpath.read_bytes() + b" ")
                with self.assertRaisesRegex(ValueError, "binding bytes changed"):
                    B.collect("unused", bpath, "server", "model", root / "run",
                              owner_confirmed=True, resume=True, server_context=fake_serve)
                bpath.write_bytes(bpath.read_bytes()[:-1])
                pred.write_bytes(original + b'{"partial":')
                with self.assertRaisesRegex(ValueError, "partial trailing"):
                    B.collect("unused", bpath, "server", "model", root / "run",
                              owner_confirmed=True, resume=True, server_context=fake_serve)
                pred.write_bytes(original)
                result = B.collect("unused", bpath, "server", "model", root / "run",
                                   owner_confirmed=True, resume=True, ask=lambda *args: "{}",
                                   server_context=fake_serve)
                self.assertEqual(result["rows"], 22)
                with self.assertRaises(ValueError):
                    B.collect("unused", bpath, "server", "model", root / "run",
                              owner_confirmed=True, resume=True, server_context=fake_serve)

    def test_candidate_and_duplicate_prediction_rejected(self):
        rows = index()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bpath = root / "binding.json"
            bpath.write_text(json.dumps(binding()))
            with patch.object(B.S, "load_dataset", return_value=(rows, S.HELDOUT_SHA)), \
                 patch.object(B, "validate_files", return_value={}):
                B.collect("unused", bpath, "server", "model", root / "run",
                          owner_confirmed=True, ask=lambda *args: "{}", server_context=fake_serve)
                pred = root / "run" / "predictions.jsonl"
                original = pred.read_bytes()
                first = json.loads(original.splitlines()[0])
                first["model"] = "candidate"
                lines = original.splitlines()
                lines[0] = json.dumps(first).encode()
                pred.write_bytes(b"\n".join(lines) + b"\n")
                with self.assertRaisesRegex(ValueError, "candidate"):
                    B.score("unused", bpath, pred, root / "badscore")
                pred.write_bytes(original)
                lines = original.splitlines()
                lines[-1] = lines[0]
                pred.write_bytes(b"\n".join(lines) + b"\n")
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    B.score("unused", bpath, pred, root / "dupscore")


if __name__ == "__main__":
    unittest.main()

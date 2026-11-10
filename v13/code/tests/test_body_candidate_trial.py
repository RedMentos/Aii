import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from v13.agi.body_dataset import compile_dataset
from v13.agi.body_candidate_trial import run_body_candidate_trial


class CandidateTrialTests(unittest.TestCase):
    def dataset(self, root):
        source = root / "reviewed.jsonl"
        rows = []
        for role in ("B1_DETAIL", "B2_GIST"):
            for i in range(120):
                digest = hashlib.sha256(f"{role}-{i}".encode()).hexdigest()
                rows.append({"role": role, "source_id": f"{role}-{i}",
                             "source_sha256": digest, "prompt": f"input-{i}",
                             "target": "answer", "reviewed": True,
                             "permission": "TRAINING_APPROVED"})
        source.write_text("".join(json.dumps(row) + "\n" for row in rows))
        dest = root / "dataset"
        compile_dataset(source, dest)
        pin = hashlib.sha256((dest / "manifest.json").read_bytes()).hexdigest()
        return dest, pin

    def test_candidate_trains_and_reports_holdout_without_activation(self):
        with tempfile.TemporaryDirectory() as temp:
            dest, pin = self.dataset(Path(temp))
            calls = []
            def train(model, items):
                calls.append(len(items))
                model["loss"] = 0.1
            metrics, candidate = run_body_candidate_trial(
                dest, "B1_DETAIL", manifest_sha256=pin,
                authorize=lambda role, digest: role == "B1_DETAIL" and digest == pin,
                make_candidate=lambda role: {"loss": 0.9},
                train_candidate=train,
                evaluate=lambda model, prompt, target: model["loss"])
            self.assertTrue(metrics["retention_pass"])
            self.assertEqual(metrics["deployment"], "NOT_AUTHORIZED")
            self.assertLess(metrics["heldout_after"], metrics["heldout_before"])
            self.assertEqual(candidate["loss"], 0.1)
            self.assertEqual(calls, [metrics["train_rows"]])

    def test_denial_precedes_candidate_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            dest, pin = self.dataset(Path(temp))
            with self.assertRaises(PermissionError):
                run_body_candidate_trial(
                    dest, "B2_GIST", manifest_sha256=pin,
                    authorize=lambda *_: False,
                    make_candidate=lambda *_: self.fail("candidate constructed"),
                    train_candidate=lambda *_: None,
                    evaluate=lambda *_: 0.1)

    def test_wrong_pin_and_regression_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            dest, pin = self.dataset(Path(temp))
            args = dict(authorize=lambda *_: True,
                        make_candidate=lambda *_: {"loss": 0.1},
                        train_candidate=lambda model, items: model.update(loss=0.8),
                        evaluate=lambda model, *_: model["loss"])
            with self.assertRaises(ValueError):
                run_body_candidate_trial(dest, "B1_DETAIL",
                                         manifest_sha256="0"*64, **args)
            result, _ = run_body_candidate_trial(dest, "B1_DETAIL",
                                                  manifest_sha256=pin, **args)
            self.assertFalse(result["retention_pass"])
            self.assertEqual(result["deployment"], "NOT_AUTHORIZED")

    def test_invalid_losses_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            dest, pin = self.dataset(Path(temp))
            with self.assertRaises(ValueError):
                run_body_candidate_trial(
                    dest, "B1_DETAIL", manifest_sha256=pin,
                    authorize=lambda *_: True, make_candidate=lambda *_: {},
                    train_candidate=lambda *_: None,
                    evaluate=lambda *_: float("nan"))


if __name__ == "__main__":
    unittest.main()

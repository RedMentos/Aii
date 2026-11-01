"""Run117CO real Store + pinned CPU Torch grouped Body-JEPA synthetic two-step."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from v13.config import initialize
from v13.store import Store, audit_closed
from v13 import body_jepa_store_grouped_twostep_candidate as C


def row(ref, view, *, path="B1_DETAIL", weight=1.0):
    return {
        "path": path, "source_id": ref["source_id"],
        "source_sha256": ref["sha256"],
        "context_source_sha256": ref["sha256"],
        "target_source_sha256": ref["sha256"],
        "view_id": view, "eligibility": weight,
    }


class StoreGroupedTwoStep(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        initialize(self.home)
        self.store = Store(self.home)
        self.a = self.store.source("Run117CO human source A repeated views")
        self.b = self.store.source("Run117CO human source B genuine negative")
        self.c = self.store.source("Run117CO human source C heldout")
        self.rows = [row(self.a, "a1"), row(self.a, "a2"), row(self.b, "b1")]
        self.heldout = [row(self.c, "c1")]
        self.refs = {"a1": self.a, "a2": self.a,
                     "b1": self.b, "c1": self.c}
        self.target = torch.tensor(
            [[1., 0., 0.], [1., 0., 0.], [0., 1., 0.]],
            dtype=torch.float32, requires_grad=True)
        self.student = torch.tensor(
            [[1., 0.1, 0.], [1., -0.1, 0.], [0.1, 1., 0.]],
            dtype=torch.float32, requires_grad=True)

    def tearDown(self):
        self.store.close()
        self.assertTrue(audit_closed(self.home)["ok"])
        self.tmp.cleanup()

    def run_candidate(self, **kwargs):
        args = {"heldout_rows": self.heldout, "operator_opt_in": True}
        args.update(kwargs)
        return C.run(torch, self.store, self.student, self.target,
                     self.rows, self.refs, **args)

    def test_two_real_store_authenticated_synthetic_updates_only(self):
        before = self.target.detach().clone()
        result = self.run_candidate()
        self.assertEqual(result["status"], "STORE_GROUPED_TWO_STEP_SHADOW", result)
        self.assertEqual(result["synthetic_tensor_updates"], 2)
        self.assertEqual(result["model_weight_updates"], 0)
        self.assertEqual(result["source_authentication"], "STORE_FULLSPAN_PRE_POST")
        self.assertEqual(result["source_group_count"], 2)
        self.assertEqual(result["repeated_view_count"], 1)
        self.assertEqual(result["masked_false_negatives"], [2, 2])
        self.assertTrue(all(x > 0 for x in result["step_student_grad_abs_sum"]))
        self.assertTrue(all(torch.isfinite(torch.tensor(x)) for x in result["step_losses"]))
        self.assertTrue(torch.equal(before, self.target.detach()))
        self.assertIsNone(self.target.grad)
        self.assertIsNone(self.student.grad)
        self.assertEqual(result["learning_authority"], 0)
        self.assertEqual(result["jepa_weight"], 0)
        self.assertEqual(result["native_calls"], 0)
        self.assertFalse(result["model_exported"])
        self.assertFalse(result["body_jepa"] != "UNAVAILABLE")
        serialized = json.dumps(result)
        self.assertNotIn(self.a["source_id"], serialized)
        self.assertNotIn(self.b["source_id"], serialized)
        self.assertNotIn("human source A", serialized)

    def test_default_off_nonboolean_and_invalid_lr(self):
        self.assertEqual(self.run_candidate(operator_opt_in=False)["status"], "OFF")
        self.assertEqual(self.run_candidate(operator_opt_in=1)["status"], "OFF")
        for lr in (True, 0, -0.1, 1.0, float("nan")):
            with self.subTest(lr=lr):
                self.assertEqual(self.run_candidate(lr=lr)["status"],
                                 "LEARNING_RATE_RED")

    def test_tampered_ref_revoked_source_and_heldout_overlap_fail(self):
        wrong = dict(self.refs, a1=self.b)
        self.assertNotEqual(self.run_candidate()["status"], "SOURCE_OR_TRAINING_INTEGRITY_RED")
        self.assertEqual(C.run(torch, self.store, self.student, self.target,
                               self.rows, wrong, heldout_rows=self.heldout,
                               operator_opt_in=True)["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")
        leak = [row(self.a, "c1")]
        self.assertEqual(self.run_candidate(heldout_rows=leak)["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")
        with self.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.b["source_id"],))
        self.assertEqual(self.run_candidate()["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")

    def test_revocation_after_first_loss_fails_after_one_ephemeral_update(self):
        original = C.research_loss
        calls = [0]

        def injected(*args, **kwargs):
            result = original(*args, **kwargs)
            calls[0] += 1
            if calls[0] == 1:
                with self.store.tx() as db:
                    db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                               (self.b["source_id"],))
            return result

        with patch.object(C, "research_loss", side_effect=injected):
            report = self.run_candidate()
        self.assertEqual(report["status"], "SOURCE_OR_TRAINING_INTEGRITY_RED")
        self.assertEqual(report["synthetic_tensor_updates"], 1)
        self.assertEqual(report["model_weight_updates"], 0)
        self.assertEqual(report["learning_authority"], 0)

    def test_mixed_body_path_and_source_rebind_refused(self):
        mixed = [dict(self.rows[0]), dict(self.rows[1]),
                 dict(self.rows[2], path="B2_GIST")]
        self.assertEqual(C.run(torch, self.store, self.student, self.target,
                               mixed, self.refs, heldout_rows=self.heldout,
                               operator_opt_in=True)["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")
        rebound = [dict(self.rows[0]), dict(self.rows[1]),
                   dict(self.rows[2], source_id=self.a["source_id"])]
        self.assertEqual(C.run(torch, self.store, self.student, self.target,
                               rebound, self.refs, heldout_rows=self.heldout,
                               operator_opt_in=True)["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")


if __name__ == "__main__":
    unittest.main()

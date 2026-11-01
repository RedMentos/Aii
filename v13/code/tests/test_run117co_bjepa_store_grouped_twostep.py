"""Run117CP independent repair: real USER event span fixtures for Run117CO.

No native model, adapter, learning authority or production Runtime integration.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from v13.common import dumps
from v13.store import Store, audit_closed
from v13 import body_jepa_store_grouped_twostep_candidate as C


def make_row(event, source, question, answer, view, path="B1_DETAIL"):
    full = event["source_ref"]
    qstart = source.index(question)
    astart = source.index(answer, qstart + len(question))
    return {
        "event_id": event["event_id"],
        "source_ref": full,
        "context_ref": dict(full, char_start=qstart, char_end=qstart + len(question)),
        "target_ref": dict(full, char_start=astart, char_end=astart + len(answer)),
        "path": path,
        "source_id": full["source_id"],
        "source_sha256": full["sha256"],
        "context_source_sha256": full["sha256"],
        "target_source_sha256": full["sha256"],
        "view_id": view,
        "eligibility": 1.0,
        "prompt": question,
        "target": answer,
    }


class StoreGroupedTwoStep(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / "data/db").mkdir(parents=True)
        (self.home / "data/blobs").mkdir(parents=True)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.a_text = "Question: Avelorn copper key?\nAnswer: Kestrel."
        self.b_text = "Question: Brimora jade key?\nAnswer: Nimbus."
        self.c_text = "Question: Caelith indigo key?\nAnswer: Saffron."
        self.a = self.store.event(self.session, self.a_text)
        self.b = self.store.event(self.session, self.b_text)
        self.c = self.store.event(self.session, self.c_text)
        self.rows = [
            make_row(self.a, self.a_text, "Avelorn copper key?", "Kestrel", "a1"),
            make_row(self.a, self.a_text, "Avelorn copper key?", "Kestrel", "a2"),
            make_row(self.b, self.b_text, "Brimora jade key?", "Nimbus", "b1"),
        ]
        self.heldout = [make_row(self.c, self.c_text, "Caelith indigo key?",
                                 "Saffron", "c1")]
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
        return C.run(torch, self.store, self.session, self.student, self.target,
                     self.rows, **args)

    def test_real_event_spans_two_ephemeral_steps_no_authority(self):
        before_target = self.target.detach().clone()
        before_student = self.student.detach().clone()
        result = self.run_candidate()
        self.assertEqual(result["status"], "STORE_GROUPED_TWO_STEP_SHADOW", result)
        self.assertEqual(result["synthetic_tensor_updates"], 2)
        self.assertEqual(result["model_weight_updates"], 0)
        self.assertEqual(result["source_authentication"],
                         "EXACT_STORE_USER_EVENT_SPANS_PRE_POST")
        self.assertEqual((result["source_group_count"], result["repeated_view_count"]),
                         (2, 1))
        self.assertEqual(result["masked_false_negatives"], [2, 2])
        self.assertEqual(len(result["step_losses"]), 2)
        self.assertTrue(all(x > 0 for x in result["step_student_grad_abs_sum"]))
        self.assertTrue(all(torch.isfinite(torch.tensor(x)) for x in result["step_losses"]))
        self.assertEqual(len(result["event_provenance_sha256"]), 64)
        self.assertTrue(torch.equal(before_target, self.target.detach()))
        self.assertTrue(torch.equal(before_student, self.student.detach()))
        self.assertIsNone(self.target.grad)
        self.assertIsNone(self.student.grad)
        self.assertEqual((result["learning_authority"], result["jepa_weight"],
                          result["native_calls"], result["delivery_authority"]), (0, 0, 0, 0))
        self.assertFalse(result["model_exported"])
        self.assertEqual(result["body_jepa"], "UNAVAILABLE")
        serialized = json.dumps(result)
        for private in (self.a["source_ref"]["source_id"],
                        self.b["source_ref"]["source_id"],
                        "Avelorn", "Kestrel", "Brimora", "Nimbus"):
            self.assertNotIn(private, serialized)

    def test_raw_binding_and_grouped_loss_are_separately_differentiable(self):
        receipt = C.bind_store_rows(
            self.store, self.session, self.rows,
            heldout_rows=self.heldout, operator_opt_in=True)
        self.assertEqual(receipt["status"], "SHADOW_STORE_SOURCE_BOUND")
        student = torch.nn.Parameter(self.student.detach().clone())
        frozen = self.target.detach().clone()
        loss, metrics = C.research_loss(
            torch, student, frozen, self.rows, heldout_rows=self.heldout)
        self.assertTrue(bool(torch.isfinite(loss)))
        self.assertEqual(metrics["masked_false_negatives"], 2)
        loss.backward()
        self.assertIsNotNone(student.grad)
        self.assertGreater(float(student.grad.detach().abs().sum()), 0)
        self.assertIsNone(frozen.grad)
        self.assertEqual(C.recheck_store_rows(
            self.store, self.session, self.rows, receipt,
            heldout_rows=self.heldout, operator_opt_in=True), receipt)

    def test_default_off_requires_explicit_boolean_and_valid_lr(self):
        self.assertEqual(self.run_candidate(operator_opt_in=False)["status"], "OFF")
        self.assertEqual(self.run_candidate(operator_opt_in=1)["status"], "OFF")
        for lr in (True, 0, -0.1, 1.0, float("nan"), float("inf")):
            with self.subTest(lr=lr):
                self.assertEqual(self.run_candidate(lr=lr)["status"],
                                 "LEARNING_RATE_RED")

    def test_forged_event_ref_heldout_overlap_and_revocation_red(self):
        wrong = [dict(r) for r in self.rows]
        wrong[0]["source_ref"] = self.b["source_ref"]
        self.assertEqual(C.run(torch, self.store, self.session, self.student,
                               self.target, wrong, heldout_rows=self.heldout,
                               operator_opt_in=True)["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")
        leak = [dict(self.rows[0], view_id="c1")]
        self.assertEqual(self.run_candidate(heldout_rows=leak)["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")
        with self.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.b["source_ref"]["source_id"],))
        self.assertEqual(self.run_candidate()["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")

    def test_revocation_after_first_loss_refuses_poststep(self):
        original = C.research_loss
        calls = [0]

        def injected(*args, **kwargs):
            result = original(*args, **kwargs)
            calls[0] += 1
            if calls[0] == 1:
                with self.store.tx() as db:
                    db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                               (self.b["source_ref"]["source_id"],))
            return result

        with patch.object(C, "research_loss", side_effect=injected):
            report = self.run_candidate()
        self.assertEqual(report["status"], "SOURCE_OR_TRAINING_INTEGRITY_RED")
        self.assertEqual(report["synthetic_tensor_updates"], 1)
        self.assertEqual(report["model_weight_updates"], 0)
        self.assertEqual(report["learning_authority"], 0)

    def test_mixed_body_path_and_source_rebind_red(self):
        mixed = [dict(self.rows[0]), dict(self.rows[1]),
                 dict(self.rows[2], path="B2_GIST")]
        self.assertEqual(C.run(torch, self.store, self.session, self.student,
                               self.target, mixed, heldout_rows=self.heldout,
                               operator_opt_in=True)["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")
        rebound = [dict(self.rows[0]), dict(self.rows[1]),
                   dict(self.rows[2], source_id=self.a["source_ref"]["source_id"])]
        self.assertEqual(C.run(torch, self.store, self.session, self.student,
                               self.target, rebound, heldout_rows=self.heldout,
                               operator_opt_in=True)["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")

    def test_foreign_session_and_nonhuman_event_red(self):
        foreign = self.store.new_session()
        self.assertEqual(C.run(torch, self.store, foreign, self.student,
                               self.target, self.rows, heldout_rows=self.heldout,
                               operator_opt_in=True)["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")
        with self.store.tx() as db:
            db.execute("UPDATE sources SET kind='MODEL' WHERE id=?",
                       (self.a["source_ref"]["source_id"],))
        self.assertEqual(self.run_candidate()["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")

    def test_event_packet_authority_tamper_red(self):
        packet = json.loads(self.store.one(
            "SELECT packet FROM events WHERE id=?", (self.a["event_id"],))["packet"])
        packet["authority"] = "MODEL_GENERATED"
        with self.store.tx() as db:
            db.execute("UPDATE events SET packet=? WHERE id=?",
                       (dumps(packet), self.a["event_id"]))
        self.assertEqual(self.run_candidate()["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")

    def test_restart_preserves_source_authentication_not_weights(self):
        first = self.run_candidate()
        self.assertEqual(first["status"], "STORE_GROUPED_TWO_STEP_SHADOW")
        self.store.close()
        self.store = Store(self.home)
        again = self.run_candidate()
        self.assertEqual(again["status"], "STORE_GROUPED_TWO_STEP_SHADOW")
        self.assertEqual(again["cohort_sha256"], first["cohort_sha256"])
        self.assertEqual(again["event_provenance_sha256"],
                         first["event_provenance_sha256"])
        self.assertEqual(again["step_losses"], first["step_losses"])
        self.assertEqual(again["model_weight_updates"], 0)

    def test_tensor_shape_nonfinite_and_missing_torch_red(self):
        self.assertEqual(C.run(None, self.store, self.session, self.student,
                               self.target, self.rows, operator_opt_in=True)["status"],
                         "TORCH_REQUIRED_RED")
        self.assertEqual(C.run(torch, self.store, self.session,
                               self.student[:2], self.target, self.rows,
                               operator_opt_in=True)["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")
        bad = self.student.detach().clone()
        bad[0, 0] = float("nan")
        self.assertEqual(C.run(torch, self.store, self.session,
                               bad, self.target, self.rows,
                               operator_opt_in=True)["status"],
                         "SOURCE_OR_TRAINING_INTEGRITY_RED")


if __name__ == "__main__":
    unittest.main()

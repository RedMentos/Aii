"""Run328 source-only adversarial tests; these are not native weight evidence."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_native_weight_delta_run328 as A


def record(sha, finite=True, shape=None, kind=0, size=4):
    return {"sha256": sha, "shape": [1] if shape is None else shape,
            "type": kind, "bytes": size, "finite": finite}


def triplet():
    base = {k: record("a") for k in A.SELECTED}
    base["blk.1.attn_q.weight"] = record("static")
    e1 = {k: dict(v) for k, v in base.items()}
    e2 = {k: dict(v) for k, v in base.items()}
    e1[A.SELECTED[0]]["sha256"] = "b"
    e2[A.SELECTED[0]]["sha256"] = "c"
    return base, e1, e2


class Run328SourceOnly(unittest.TestCase):
    def test_selected_only_two_epoch_change_passes_structurally(self):
        b, e1, e2 = triplet()
        result = A.assess(b, e1, e2)
        self.assertEqual(result["changed_epoch1"], [A.SELECTED[0]])
        self.assertEqual(result["changed_epoch2"], [A.SELECTED[0]])
        self.assertEqual(result["unchanged_nonselected"], 1)

    def test_missing_selected_tensor_rejected(self):
        b, e1, e2 = triplet()
        for row in (b, e1, e2):
            del row[A.SELECTED[1]]
        with self.assertRaisesRegex(ValueError, "selected"):
            A.assess(b, e1, e2)

    def test_unselected_weight_change_rejected(self):
        b, e1, e2 = triplet()
        e1["blk.1.attn_q.weight"]["sha256"] = "mutated"
        with self.assertRaisesRegex(ValueError, "unselected"):
            A.assess(b, e1, e2)

    def test_no_epoch1_update_rejected(self):
        b, e1, e2 = triplet()
        e1[A.SELECTED[0]]["sha256"] = "a"
        with self.assertRaisesRegex(ValueError, "epoch1"):
            A.assess(b, e1, e2)

    def test_no_epoch2_update_rejected(self):
        b, e1, e2 = triplet()
        e2[A.SELECTED[0]]["sha256"] = "b"
        with self.assertRaisesRegex(ValueError, "epoch2"):
            A.assess(b, e1, e2)

    def test_missing_tensor_inventory_rejected(self):
        b, e1, e2 = triplet()
        del e1["blk.1.attn_q.weight"]
        with self.assertRaisesRegex(ValueError, "inventory"):
            A.assess(b, e1, e2)

    def test_shape_type_and_byte_size_changes_rejected(self):
        for key, value in (("shape", [2]), ("type", 2), ("bytes", 8)):
            b, e1, e2 = triplet()
            e1[A.SELECTED[0]][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "drift"):
                A.assess(b, e1, e2)

    def test_nonfinite_selected_rejected(self):
        b, e1, e2 = triplet()
        e2[A.SELECTED[0]]["finite"] = False
        with self.assertRaisesRegex(ValueError, "non-finite"):
            A.assess(b, e1, e2)

    def test_negative_gates_immutable(self):
        self.assertEqual(A.GATES["STEP2"], "UTILITY_FAIL")
        self.assertEqual(A.GATES["B3_L1"], "FAIL")
        self.assertEqual(A.GATES["Body_JEPA"], "UNAVAILABLE")
        self.assertEqual(A.GATES["jepa_weight"], 0)

    def test_full_master_and_epoch_receipts_bound_to_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            files = [Path(td) / name for name in ("master.gguf", "epoch1.gguf", "epoch2.gguf")]
            for i, p in enumerate(files):
                p.write_bytes(("weight" + str(i)).encode())
            hashes = [hashlib.sha256(p.read_bytes()).hexdigest() for p in files]
            report = {"status": "COMPLETE_NATIVE_EVALUATION", "native_training_executed": True,
                      "gates": dict(A.GATES), "weights_published": False,
                      "master_sha256": hashes[0], "final_master_sha256": hashes[2],
                      "checkpoint_receipts": [{"epoch": 1, "sha256": hashes[1]},
                                              {"epoch": 2, "sha256": hashes[2]}]}
            with patch.object(A, "MASTER_SHA", hashes[0]):
                self.assertEqual(A.verify_report_and_paths(report, *files), hashes)
                report["checkpoint_receipts"][1]["sha256"] = "forged"
                with self.assertRaisesRegex(ValueError, "checkpoint SHA"):
                    A.verify_report_and_paths(report, *files)

    def test_missing_native_receipt_rejected_even_with_files(self):
        with tempfile.TemporaryDirectory() as td:
            files = [Path(td) / name for name in ("a", "b", "c")]
            for p in files: p.write_bytes(b"data")
            with self.assertRaisesRegex(ValueError, "incomplete"):
                A.verify_report_and_paths({"status": "ERROR"}, *files)

    def test_source_only_cannot_claim_optimizer_evidence(self):
        b, e1, e2 = triplet()
        self.assertIn("changed_epoch1", A.assess(b, e1, e2))
        self.assertNotIn("evidence_level", A.assess(b, e1, e2))


if __name__ == "__main__":
    unittest.main()

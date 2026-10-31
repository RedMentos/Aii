"""Run34 negative controls against the actual original Run32 ZIP (read-only)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from scripts.run34_world_jepa_disjoint_raw_audit import audit, ZIP_SHA


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rewritten(original, output, changes=None, drop=(), bad_manifest=False, duplicate=False):
    changes = changes or {}
    with zipfile.ZipFile(original) as z:
        members = {n: z.read(n) for n in z.namelist() if n not in set(drop) | {"SHA256SUMS"}}
    members.update(changes)
    lines = [hashlib.sha256(data).hexdigest() + "  " + name
             for name, data in sorted(members.items())]
    if bad_manifest:
        lines[0] = "0" * 64 + lines[0][64:]
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
        z.writestr("SHA256SUMS", "\n".join(lines) + "\n")
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr("RESULT.json", members["RESULT.json"])


@unittest.skipUnless(os.environ.get("RUN34_ORIGINAL_ZIP"),
                     "Run34 original native ZIP must be supplied explicitly")
class Run34OriginalRawAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = Path(os.environ["RUN34_ORIGINAL_ZIP"])
        if not cls.original.is_file():
            raise FileNotFoundError(cls.original)

    def test_original_closed_raw_and_negative_gates(self):
        self.assertEqual(sha(self.original), ZIP_SHA)
        r = audit(self.original)
        self.assertEqual(r["manifest_members_verified"], 130)
        self.assertEqual(r["stage_exit_zero"], 9)
        self.assertEqual(r["status"], "SHADOW_CANDIDATE_FAIL")
        self.assertEqual(list(r["w7_gates"].values()), [True, False, False])
        self.assertEqual(r["jepa_weight"], 0)
        self.assertFalse(r["redmi_measured"])
        self.assertFalse(r["whole_system_complete"])

    def assert_mutation_rejected(self, reason, changes=None, drop=(),
                                 bad_manifest=False, duplicate=False):
        with tempfile.TemporaryDirectory(prefix="run34-negative-") as tmp:
            p = Path(tmp) / "changed.zip"
            rewritten(self.original, p, changes, drop, bad_manifest, duplicate)
            with self.assertRaisesRegex(ValueError, "RUN34_" + reason):
                audit(p, expected_sha=sha(p))

    def json_change(self, mutate):
        with zipfile.ZipFile(self.original) as z:
            r = json.loads(z.read("RESULT.json"))
        mutate(r)
        return {"RESULT.json": json.dumps(r, allow_nan=True).encode()}

    def test_outer_zip_mutation_rejected_before_inner(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.zip"
            p.write_bytes(self.original.read_bytes() + b"extra")
            with self.assertRaisesRegex(ValueError, "RUN34_OUTER_SHA_RED"):
                audit(p)

    def test_inner_hash_mutation_rejected(self):
        self.assert_mutation_rejected("INNER_SHA_RED", bad_manifest=True)

    def test_duplicate_zip_member_rejected(self):
        self.assert_mutation_rejected("ZIP_MEMBERS_RED", duplicate=True)

    def test_missing_seed_checkpoint_rejected(self):
        self.assert_mutation_rejected("ZIP_MEMBERS_RED",
                                      drop=("work/slot-203-RESULT.json",))

    def test_stage_exit_failure_rejected(self):
        self.assert_mutation_rejected("STAGE_REALFILE_RED",
                                      changes={"REALFILE_EXIT.txt": b"1\n"})

    def test_posthoc_w7_promotion_rejected(self):
        def mutate(r):
            r["w7_gates"]["W7b_none_self_action_gain"] = True
            r["w7_gates"]["W7c_four_class_macro_action_gain"] = True
        self.assert_mutation_rejected("W7_GATE_RECOMPUTATION_RED",
                                      changes=self.json_change(mutate))

    def test_seed_swap_rejected(self):
        self.assert_mutation_rejected("REGISTRATION_RED",
                                      changes=self.json_change(
                                          lambda r: r["seeds"].__setitem__(2, 204)))

    def test_nonfinite_metric_rejected(self):
        def mutate(r):
            r["slot_arm"][0]["errors"]["covered_mean"] = float("nan")
        self.assert_mutation_rejected("NONFINITE_JSON_NaN_RED",
                                      changes=self.json_change(mutate))

    def test_per_seed_checkpoint_mismatch_rejected(self):
        with zipfile.ZipFile(self.original) as z:
            r = json.loads(z.read("work/original-201-RESULT.json"))
        r["n_train"] += 1
        self.assert_mutation_rejected("PER_SEED_CHECKPOINT_BINDING_RED",
            changes={"work/original-201-RESULT.json": json.dumps(r).encode()})

    def test_negative_gate_mutation_rejected(self):
        self.assert_mutation_rejected("NEGATIVE_GATE_RED",
                                      changes=self.json_change(
                                          lambda r: r.__setitem__("jepa_weight", 1)))


if __name__ == "__main__":
    unittest.main()

import copy
import json
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import b3pair_integrity_candidate as C


KEY = bytes(range(32))
GOOD = {"NO_MESSAGE": .69, "SCALAR": .90, "L1": .94, "L2": .82}


def batch(prefix, seed, n=3000):
    ids = [f"private source {prefix} {i}" for i in range(n)]
    return {"sender": np.arange(n * 2, dtype=np.float32).reshape(n, 2),
            "receiver": np.arange(n * 3, dtype=np.float32).reshape(n, 3),
            "labels": (np.arange(n) % 2).astype(np.int64),
            "sender_source_ids": ids, "receiver_source_ids": list(ids),
            "sender_revision": "sender-r1", "receiver_revision": "receiver-r1",
            "task": "private/escalate", "seed": seed}


class TestPairIntegrityCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a = batch("A", 1)
        cls.b = batch("B", 2)
        cls.ma = C.build_manifest(**cls.a, key=KEY)
        cls.mb = C.build_manifest(**cls.b, key=KEY)

    def check(self, ma=None, a=None, aa=None, mb=None, b=None, ab=None, key=KEY):
        return C.precheck(self.ma if ma is None else ma, self.a if a is None else a,
                          GOOD if aa is None else aa, self.mb if mb is None else mb,
                          self.b if b is None else b, GOOD if ab is None else ab, key=key)

    def test_valid_pair_and_manifest_do_not_include_private_ids(self):
        self.assertEqual(C.verify(self.ma, **self.a, key=KEY), (True, []))
        self.assertEqual(self.check()["verdict"], "GO")
        serialized = json.dumps(self.ma)
        self.assertNotIn("private source A 0", serialized)
        self.assertNotIn(KEY.hex(), serialized)
        self.assertEqual(len(self.ma["row_sha256"]), 3000)
        self.assertTrue(all(len(h) == 64 for h in self.ma["row_sha256"]))

    def test_manifest_all_fields_and_each_row_are_checked(self):
        for field, value in (("schema", "different"), ("sender_revision", "other"),
                             ("receiver_revision", "other"), ("task", "other"),
                             ("seed", 9), ("rows", 3001), ("sender_sha256", "0" * 64),
                             ("receiver_sha256", "0" * 64), ("labels_sha256", "0" * 64),
                             ("source_key_check", "0" * 64), ("row_sha256", []),
                             ("source_hmac_sha256", []), ("extra", "bad")):
            with self.subTest(field=field):
                forged = copy.deepcopy(self.ma)
                forged[field] = value
                self.assertFalse(C.verify(forged, **self.a, key=KEY)[0])
        forged = copy.deepcopy(self.ma)
        forged["row_sha256"][100] = "0" * 64
        self.assertFalse(C.verify(forged, **self.a, key=KEY)[0])
        forged = copy.deepcopy(self.ma)
        forged["source_hmac_sha256"][100] = "0" * 64
        self.assertFalse(C.verify(forged, **self.a, key=KEY)[0])
        forged = copy.deepcopy(self.ma)
        del forged["task"]
        self.assertFalse(C.verify(forged, **self.a, key=KEY)[0])

    def test_pinned_revision_task_seed_and_key(self):
        for name, value in (("sender_revision", "new"), ("receiver_revision", "new"),
                            ("task", "different"), ("seed", 55)):
            inputs = dict(self.a, **{name: value})
            with self.subTest(name=name):
                self.assertFalse(C.verify(self.ma, **inputs, key=KEY)[0])
        self.assertFalse(C.verify(self.ma, **self.a, key=b"x" * 32)[0])
        self.assertEqual(self.check(key=b"short")["verdict"], "NO_GO")

    def test_source_identity_and_row_pairing_are_pinned(self):
        altered = list(self.a["receiver_source_ids"])
        altered[0], altered[1] = altered[1], altered[0]
        inputs = dict(self.a, receiver_source_ids=altered)
        self.assertFalse(C.verify(self.ma, **inputs, key=KEY)[0])
        changed = list(self.a["sender_source_ids"])
        changed[0] = "a different private source"
        inputs = dict(self.a, sender_source_ids=changed, receiver_source_ids=list(changed))
        self.assertFalse(C.verify(self.ma, **inputs, key=KEY)[0])
        with self.assertRaises(ValueError):
            C.build_manifest(**dict(self.a, receiver_source_ids=altered), key=KEY)

    def test_content_and_labels_exact_not_lossily_cast(self):
        sender = self.a["sender"].astype(np.float64)
        sender[0, 0] += 1e-10
        self.assertFalse(C.verify(self.ma, **dict(self.a, sender=sender), key=KEY)[0])
        labels = self.a["labels"].copy()
        labels[0] = 1
        self.assertFalse(C.verify(self.ma, **dict(self.a, labels=labels), key=KEY)[0])
        labels = self.a["labels"].astype(np.float32) + .1
        self.assertFalse(C.verify(self.ma, **dict(self.a, labels=labels), key=KEY)[0])
        with self.assertRaises(ValueError):
            C.build_manifest(**dict(self.a, labels=labels), key=KEY)
        self.assertFalse(C.verify(self.ma, **dict(self.a, labels=self.a["labels"].astype(np.int32)), key=KEY)[0])

    def test_overlap_detects_same_source_even_when_activations_change(self):
        ids = list(self.b["sender_source_ids"])
        ids[10] = self.a["sender_source_ids"][10]
        b = dict(self.b, receiver=self.b["receiver"] + 5,
                 sender_source_ids=ids, receiver_source_ids=list(ids))
        mb = C.build_manifest(**b, key=KEY)
        result = self.check(b=b, mb=mb)
        self.assertEqual(result["verdict"], "NO_GO")
        self.assertIn("source identities overlap across cohorts", result["reasons"])

    def test_manifest_mutation_cannot_bypass_overlap(self):
        forged = copy.deepcopy(self.ma)
        forged["source_hmac_sha256"] = []
        forged["row_sha256"] = []
        self.assertEqual(self.check(ma=forged)["verdict"], "NO_GO")
        self.assertEqual(self.check(ma={"rows": 3000})["verdict"], "NO_GO")

    def test_nan_inf_missing_boolean_and_impossible_accuracies_fail_closed(self):
        for field in GOOD:
            for invalid in (float("nan"), float("inf"), -0.01, 1.01, True, None, "0.9"):
                with self.subTest(field=field, invalid=invalid):
                    self.assertEqual(self.check(aa=dict(GOOD, **{field: invalid}))["verdict"], "NO_GO")
            missing = dict(GOOD)
            del missing[field]
            self.assertEqual(self.check(aa=missing)["verdict"], "NO_GO")

    def test_scalar_and_other_controls_apply_to_both_cohorts(self):
        for bad in (dict(GOOD, SCALAR=.94), dict(GOOD, SCALAR=.99),
                    dict(GOOD, NO_MESSAGE=.93), dict(GOOD, L2=.93)):
            with self.subTest(bad=bad):
                self.assertEqual(self.check(aa=bad)["verdict"], "NO_GO")
                self.assertEqual(self.check(ab=bad)["verdict"], "NO_GO")

    def test_insufficient_rows_seed_and_metadata_fail(self):
        small = batch("small", 3, 4)
        msmall = C.build_manifest(**small, key=KEY)
        self.assertEqual(self.check(b=small, mb=msmall)["verdict"], "NO_GO")
        same_seed = dict(self.b, seed=self.a["seed"])
        ms = C.build_manifest(**same_seed, key=KEY)
        self.assertEqual(self.check(b=same_seed, mb=ms)["verdict"], "NO_GO")
        other_task = dict(self.b, task="different")
        mt = C.build_manifest(**other_task, key=KEY)
        self.assertEqual(self.check(b=other_task, mb=mt)["verdict"], "NO_GO")

    def test_repeated_sources_cannot_fake_the_required_sample_size(self):
        # 3000 rows created by repeating one group are not 3000 examples.
        ids = ["one repeated source"] * 3000
        duplicated = dict(self.a, sender_source_ids=ids, receiver_source_ids=list(ids))
        manifest = C.build_manifest(**duplicated, key=KEY)
        result = self.check(ma=manifest, a=duplicated)
        self.assertEqual(result["verdict"], "NO_GO")
        self.assertIn("cohort A: insufficient distinct source groups", result["reasons"])

    def test_malformed_shapes_and_states_fail(self):
        for field, value in (("sender", np.array([1.])),
                             ("sender", np.full((3000, 2), np.nan)),
                             ("sender", np.ones((3000, 0))),
                             ("receiver", np.ones((2999, 3))),
                             ("labels", np.zeros((3000, 1), dtype=int)),
                             ("labels", np.ones(3000, dtype=bool))):
            with self.subTest(field=field):
                self.assertFalse(C.verify(self.ma, **dict(self.a, **{field: value}), key=KEY)[0])


if __name__ == "__main__":
    unittest.main()

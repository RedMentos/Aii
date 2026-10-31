"""Run103 preregistered C3 prior-rule fixture/source envelope tests; NO native."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run103_c3_prior_fixture as f
from v13.config import initialize
from v13.store import Store
from v13.models import catalog


class Run103C3PriorFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        home = Path(self.temp.name)
        initialize(home)
        self.store = Store(home)
        self.addCleanup(self.store.close)
        self.rows = f.fixtures()

    def refs(self, row):
        return self.store.source(row["prior"]), self.store.source(row["current"])

    def test_table_hash_disjoint_balanced_oracles(self):
        digest = hashlib.sha256(json.dumps(f.TABLE, sort_keys=True,
                          separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest, f.TABLE_SHA256)
        self.assertEqual(f.SEED, 1031)
        self.assertEqual(len(self.rows), 6)
        self.assertEqual([r["expected"] for r in self.rows],
                         ["A", "B", "NONE", "A", "B", "NONE"])
        self.assertEqual(len({r["project"] for r in self.rows}), 6)
        self.assertFalse({r["project"] for r in self.rows} &
                         {"Quartz", "Rowan", "Sable", "Tundra", "Umber", "Vesper",
                          "Alder", "Birch", "Cedar", "Dune", "Elm", "Fir"})
        self.assertEqual(len(f.ARMS) * len(self.rows), 24)
        self.assertEqual({a for r in self.rows for a in r["arm_order"]}, set(f.ARMS))

    def test_pinned_catalog_model_and_runner(self):
        entry = catalog()["models"]["language"]
        self.assertEqual(entry["files"][0]["sha256"], f.MODEL_SHA256)
        self.assertEqual(len(f.RUNNER_SHA256), 64)
        int(f.RUNNER_SHA256, 16)

    def test_four_arms_have_exact_expected_source_visibility(self):
        row = self.rows[0]
        prior, current = self.refs(row)
        payloads = {}
        for arm in f.ARMS:
            result = f.build_messages(self.store, row, arm, prior, current)
            self.assertEqual(result["messages"][0]["content"], f.SYSTEM)
            self.assertEqual(len(result["input_sha256"]), 64)
            payloads[arm] = json.loads(result["messages"][1]["content"])
            self.assertEqual(payloads[arm]["current_source"], row["current"])
        self.assertEqual(set(payloads["CURRENT_ONLY"]), {"current_source"})
        self.assertEqual(payloads["DIRECT_FULL"]["archived_policy_exact_source"],
                         row["prior"])
        wide = payloads["B2_WIDE_VERIFIED_SYNTHETIC"]["b2_hypothesis"]
        narrow = payloads["B2_NARROW_SYNTHETIC"]["b2_hypothesis"]
        self.assertEqual(wide["verified_quotes"][0]["text"], row["prior"])
        self.assertFalse(wide["verified_quotes"][0]["semantic_truth_authority"])
        self.assertIn("Maximum budget:", narrow["verified_quotes"][0]["text"])
        self.assertNotIn("Maximum deadline:", narrow["verified_quotes"][0]["text"])
        self.assertEqual(self.store.read_source(
            narrow["verified_quotes"][0]["source_ref"]),
            narrow["verified_quotes"][0]["text"])
        self.assertNotIn("archived_policy_exact_source", payloads["CURRENT_ONLY"])
        self.assertNotIn("expected", json.dumps(payloads))

    def test_deleted_and_tampered_prior_fail_closed(self):
        row = self.rows[0]
        prior, current = self.refs(row)
        wrong = self.store.source(row["prior"] + " changed")
        with self.assertRaisesRegex(ValueError, "RUN103_PRIOR_SOURCE_CHANGED"):
            f.build_messages(self.store, row, "DIRECT_FULL", wrong, current)
        with self.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (prior["source_id"],))
        with self.assertRaises(ValueError):
            f.build_messages(self.store, row, "B2_WIDE_VERIFIED_SYNTHETIC",
                             prior, current)

    def test_registered_table_tamper_rejected(self):
        changed = list(f.TABLE)
        row = list(changed[0])
        row[1] += 1
        changed[0] = tuple(row)
        with patch.object(f, "TABLE", tuple(changed)):
            with self.assertRaisesRegex(ValueError, "TABLE_CHANGED"):
                f.fixtures()

    def test_strict_positive_and_negative_scoring(self):
        for row in self.rows:
            expected = {"choice": row["expected"],
                        "remaining": str(row["remaining"])
                        if row["remaining"] is not None else "NA"}
            for arm in ("DIRECT_FULL", "B2_WIDE_VERIFIED_SYNTHETIC"):
                self.assertEqual(f.score(json.dumps(expected), row, arm), 1)
                self.assertEqual(f.score('{"choice":"UNKNOWN","remaining":"NA"}',
                                         row, arm), 0)
            for arm in ("CURRENT_ONLY", "B2_NARROW_SYNTHETIC"):
                self.assertEqual(f.score('{"choice":"UNKNOWN","remaining":"NA"}',
                                         row, arm), 1)
                self.assertEqual(f.score(json.dumps(expected), row, arm), 0)
        self.assertEqual(f.score('{"choice":"A","remaining":12}', self.rows[0],
                                 "DIRECT_FULL"), 0)
        self.assertEqual(f.score('{"choice":"A","remaining":"12","extra":0}',
                                 self.rows[0], "DIRECT_FULL"), 0)
        self.assertEqual(f.score('not json', self.rows[0], "DIRECT_FULL"), 0)

    def test_preregistered_verdict_and_invalid_shapes(self):
        scores = dict.fromkeys(f.ARMS, 4)
        self.assertEqual(f.verdict(scores), "C3_SOURCE_RULE_SMALL_SIGNAL_SHADOW")
        scores["B2_WIDE_VERIFIED_SYNTHETIC"] = 2
        self.assertEqual(f.verdict(scores), "C3_SOURCE_RULE_UTILITY_RED")
        scores["B2_WIDE_VERIFIED_SYNTHETIC"] = 4
        scores["CURRENT_ONLY"] = 1
        self.assertEqual(f.verdict(scores), "C3_SOURCE_RULE_UTILITY_RED")
        with self.assertRaisesRegex(ValueError, "SCORE_SHAPE"):
            f.verdict({})
        with self.assertRaisesRegex(ValueError, "SCORE_VALUE"):
            f.verdict(dict.fromkeys(f.ARMS, True))


if __name__ == "__main__":
    unittest.main()

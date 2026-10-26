"""Run511 frozen 5×12 B2 offer collector source-only and fake-source tests."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run509_b2_rule_quote_prereg as frozen
import run511_b2_offer_collector as collector


class FakeStore:
    def __init__(self, text):
        self.text = text
    def read_source(self, ref):
        return self.text


class B2OfferCollectorSource(unittest.TestCase):
    def test_five_disjoint_twelve_row_stage_plans(self):
        stages = [collector.plan(i) for i in range(5)]
        self.assertEqual([s["stage_id"] for s in stages],
                         ["p00", "p01", "p02", "p03", "p04"])
        self.assertEqual([s["expected_observations"] for s in stages], [12] * 5)
        keys = [tuple(key) for stage in stages for key in stage["row_keys"]]
        self.assertEqual(len(keys), 60)
        self.assertEqual(len(set(keys)), 60)
        self.assertEqual({k[1] for k in keys}, {"BASE", "RULE_FOCUS"})
        self.assertEqual({k[2] for k in keys}, {41, 42, 43})
        self.assertEqual([f for stage in stages for f in stage["fixture_ids"]],
                         [f["id"] for f in frozen.fixtures()])
        self.assertTrue(all(stage["native_executed"] is False and
                            stage["canonical_gate_pass"] is False and
                            stage["step2_exit"] == "UTILITY_FAIL"
                            for stage in stages))

    def test_frozen_fixture_hash_and_invalid_index(self):
        self.assertEqual(collector.plan(0)["run509_fixture_sha256"],
                         frozen.EXPECTED_FIXTURE_SHA256)
        for index in (-1, 5, True, 1.5):
            with self.assertRaisesRegex(ValueError, "PAIR_INDEX_OUT_OF_RANGE"):
                collector.plan(index)
        with patch.object(collector, "PAIRS", (("Arbor", "Arbor"),) +
                          collector.PAIRS[1:]):
            with self.assertRaisesRegex(ValueError, "FROZEN_FIVE_PAIR_PARTITION_DRIFT"):
                collector.plan(0)

    def test_exact_source_id_mapping_and_verified_quote(self):
        fixture = frozen.fixtures()[0]
        prior = [{"source_ref": {"source_id": f"src{i}"}} for i in range(3)]
        event = {"source_ref": {"source_id": "current"}}
        mapping = collector.source_slot_map({"prior_events": prior}, event)
        self.assertEqual(mapping["src0"], "history0")
        text = collector.sha(fixture["history"][0].encode())
        ref = {"source_id": "src0", "sha256": text}
        offer = {"role": "B2_GIST", "native_metrics": {"status": "FINAL"},
                 "evidence_refs": [ref]}
        quotes = collector.collect_verified_quote_records(
            offer, FakeStore("Budget 117 euros."), fixture, mapping)
        self.assertEqual(quotes, [{"source_slot": "history0",
                                   "source_sha256": text,
                                   "text": "Budget 117 euros."}])

    def test_unknown_source_fabrication_and_nonfinal_rejected(self):
        fixture = frozen.fixtures()[0]
        mapping = {"src0": "history0"}
        source_sha = collector.sha(fixture["history"][0].encode())
        offer = {"role": "B2_GIST", "native_metrics": {"status": "FINAL"},
                 "evidence_refs": [{"source_id": "src0",
                                    "sha256": source_sha}]}
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_SOURCE_EXCERPT"):
            collector.collect_verified_quote_records(
                offer, FakeStore("Budget 999 euros."), fixture, mapping)
        bad = copy.deepcopy(offer)
        bad["evidence_refs"][0]["source_id"] = "not_registered"
        with self.assertRaisesRegex(ValueError, "UNREGISTERED_EVIDENCE_SOURCE"):
            collector.collect_verified_quote_records(
                bad, FakeStore("Budget 117 euros."), fixture, mapping)
        bad = copy.deepcopy(offer)
        bad["evidence_refs"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "EVIDENCE_SOURCE_HASH_DRIFT"):
            collector.collect_verified_quote_records(
                bad, FakeStore("Budget 117 euros."), fixture, mapping)
        bad = copy.deepcopy(offer)
        bad["native_metrics"]["status"] = "ERROR"
        with self.assertRaisesRegex(ValueError, "B2_NATIVE_OFFER_NOT_FINAL"):
            collector.collect_verified_quote_records(
                bad, FakeStore("Budget 117 euros."), fixture, mapping)

    def test_source_only_cli_refuses_overwrite_and_native_without_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            cmd = [sys.executable, str(ROOT / "scripts" /
                   "run511_b2_offer_collector.py"), "--work", str(work),
                   "--pair-index", "0", "--plan"]
            first = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            path = work / "RUN511_STAGE_PLAN.json"
            self.assertEqual(json.loads(path.read_text()), collector.plan(0))
            second = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("FileExistsError", second.stderr)
            native = subprocess.run(cmd[:-1] + ["--execute"],
                                    capture_output=True, text=True, timeout=60)
            self.assertNotEqual(native.returncode, 0)
            self.assertIn("NATIVE_REQUIRES_INSTALLED_HOME", native.stderr)


if __name__ == "__main__":
    unittest.main()

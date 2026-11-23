"""Run117W disjoint seed1063 model-free C3 diagnostic contracts."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run117w_c3_arithmetic_native as pilot
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/RUN117W_C3_ARITHMETIC_SEED1063.json")


def fake_report():
    rows = []
    for row in pilot.fixture(FIXTURE):
        rows.append({
            "id": row["id"], "closed_store_ok": True,
            "no_live_output": True,
            "arms": [{"arm": arm, "status": "RECORDED",
                      "native_final": True, "process_reaped": True,
                      "score": {"correct": 1}}
                     for arm in pilot.ARMS]})
    return {"rows": rows, "native_c3_calls": 18,
            "exploratory_arithmetic_signal": False}


class Run117WContracts(unittest.TestCase):
    def test_new_disjoint_cohort_oracles_and_hash(self):
        rows = pilot.fixture(FIXTURE)
        self.assertEqual(pilot.SEED, 1063)
        self.assertEqual(len(rows), 6)
        self.assertEqual([r["id"] for r in rows], list(pilot.IDS))
        self.assertEqual([(r["oracle"]["choice"], r["oracle"]["remaining"])
                          for r in rows],
                         [("A", 50), ("B", 60), ("NONE", None),
                          ("B", 70), ("B", 85), ("NONE", None)])

    def test_frozen_fixture_byte_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "changed.json"
            p.write_bytes(FIXTURE.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "FIXTURE_SHA_RED"):
                pilot.fixture(p)

    def test_source_roles_and_typed_jef_only_in_formatter(self):
        row = pilot.fixture(FIXTURE)[0]
        with tempfile.TemporaryDirectory() as d:
            runtime = QuoteRuntime(Path(d) / "home", row)
            try:
                prior = runtime.store.event(runtime.session, row["prior"])
                current = runtime.store.event(runtime.session, row["current"])
                prompts = pilot._prompts(runtime, prior, current, row)
                self.assertEqual(set(prompts), set(pilot.ARMS))
                for arm, messages in prompts.items():
                    self.assertEqual([m["role"] for m in messages],
                                     ["system", "user"])
                    self.assertEqual(messages[0]["content"], pilot.SYSTEMS[arm])
                    self.assertNotIn(row["policy_span"], messages[0]["content"])
                    self.assertNotIn(row["option_span"], messages[0]["content"])
                    self.assertNotIn('"oracle"', messages[1]["content"])
                    payload = json.loads(messages[1]["content"])
                    self.assertEqual(payload["policy"]["text"], row["policy_span"])
                    self.assertEqual(payload["options"]["text"], row["option_span"])
                    if arm == pilot.ARMS[2]:
                        self.assertEqual(payload["typed_jef_candidate"],
                                         row["oracle"])
                        self.assertEqual(payload["candidate_authority"], 0)
                    else:
                        self.assertNotIn("typed_jef_candidate", payload)
                self.assertEqual(
                    runtime.store.one("SELECT COUNT(*) AS n FROM actions")["n"], 0)
            finally:
                runtime.close()

    def test_complete_without_gain_stays_no_gain(self):
        report = fake_report()
        self.assertEqual(pilot._summarize(report), pilot.GOOD[1])
        self.assertFalse(report["exploratory_arithmetic_signal"])

    def test_predeclared_signal_requires_explicit_gain_and_typed_control(self):
        report = fake_report()
        for i, row in enumerate(report["rows"]):
            row["arms"][0]["score"]["correct"] = int(i == 0)
            row["arms"][1]["score"]["correct"] = int(i < 4)
            row["arms"][2]["score"]["correct"] = int(i < 5)
        self.assertEqual(pilot._summarize(report), pilot.GOOD[0])
        self.assertTrue(report["exploratory_arithmetic_signal"])

    def test_missing_native_reap_is_structural_red(self):
        report = fake_report()
        report["rows"][0]["arms"][0]["process_reaped"] = False
        self.assertEqual(pilot._summarize(report), pilot.RED)

    def test_wrong_native_call_count_is_structural_red(self):
        report = fake_report()
        report["native_c3_calls"] = 17
        self.assertEqual(pilot._summarize(report), pilot.RED)


if __name__ == "__main__":
    unittest.main()

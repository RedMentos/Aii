"""Explicit local F1/F5 source-exact explanation SHADOW, test-first real Store."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import p2x_disjoint_receiver_trainset as cohort
from v13 import jef_f1f5_source_admission as admission
from v13.operator import Operator
from v13.runtime import Runtime


class JefSourceExplainOptinTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        self.row = next(x for x in cohort.fixtures()
                        if x["partition"] == "calibration")

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def record(self, key, value):
        event = self.r.store.event(self.r.session, "Record: " + key)
        mid = self.r.memory.feedback(
            event["event_id"], "fact", value, permission="record",
            key=key, scope="session")
        self.r.memory.candidate(mid, self.r.session)
        return mid

    def sources(self):
        row = self.row
        policy = self.record(
            f'Project {row["id"]} archived {row["domain"]} policy',
            row["b2_source"])
        sheet = self.record(
            f'Project {row["id"]} latest {row["domain"]} option sheet',
            row["b1_source"])
        event = self.r.store.event(self.r.session, row["current"])
        return event["event_id"], policy, sheet

    def cmd(self, ids, explain=True):
        return ":jefsource " + ("explain " if explain else "") + " ".join(ids)

    def counts(self):
        return tuple(self.r.store.one(
            f"SELECT count(*) AS n FROM {table}")["n"]
            for table in ("sources", "events", "feedback", "packets", "memories"))

    def test_exact_two_source_explanation_no_mutation_or_model(self):
        ids = self.sources()
        before = self.counts()
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_MODEL_CALLED")):
            result = json.loads(self.op.run(self.cmd(ids)))
        self.assertEqual(self.counts(), before)
        self.assertEqual(result["explanation_status"],
                         "F1F5_SOURCE_EXACT_SHADOW_ONLY")
        self.assertTrue(result["human_source_lineage_verified"])
        self.assertEqual(result["suggested_action"], self.row["oracle_action"])
        self.assertEqual(result["status"], "SHADOW_NO_AUTHORITY")
        self.assertEqual(result["authority"], 0)
        self.assertTrue(result["operator_diagnostic"])
        self.assertTrue(result["no_live_answer"])
        self.assertFalse(result["model_called"])
        self.assertEqual(result["native_calls"], 0)
        self.assertEqual(result["jepa_weight"], 0)
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertFalse(result["whole_system_complete"])
        explanation = result["source_exact_explanation"]
        arithmetic = result["source_exact_arithmetic"]
        self.assertIn(self.row["id"], explanation)
        self.assertIn("Suggested action: " + self.row["oracle_action"],
                      explanation)
        for name in ("A", "B"):
            option = arithmetic["options"][name]
            self.assertIn("Option " + name + ":", explanation)
            for i, field in enumerate(arithmetic["fields"]):
                expected = (f'{field["limit"]} {field["unit"]} - '
                            f'{option["used"][i]} {field["unit"]} = '
                            f'{option["remaining"][i]} {field["unit"]}')
                self.assertIn(expected, explanation)
        self.assertIn(":jefsource explain", self.op.run(":help"))

    def test_default_diagnostic_still_same_after_explain(self):
        ids = self.sources()
        before = self.op.run(self.cmd(ids, explain=False))
        self.op.run(self.cmd(ids, explain=True))
        after = self.op.run(self.cmd(ids, explain=False))
        self.assertEqual(before, after)
        self.assertNotIn("source_exact_explanation", json.loads(after))

    def test_forget_and_tamper_suppress_explanation(self):
        ids = self.sources()
        self.r.memory.forget(ids[2])
        result = json.loads(self.op.run(self.cmd(ids)))
        self.assertIsNone(result["source_exact_explanation"])
        self.assertEqual(result["explanation_status"], "SOURCE_NOT_ADMITTED")
        self.assertEqual(result["suggested_action"], "UNKNOWN")

    def test_revocation_during_first_check_is_vetoed_by_second(self):
        ids = self.sources()
        original = admission.decide
        calls = []
        def revoke_after_first(*args, **kwargs):
            result = original(*args, **kwargs)
            calls.append(result)
            if len(calls) == 1:
                self.r.memory.forget(ids[2])
            return result
        with patch.object(admission, "decide", side_effect=revoke_after_first):
            result = json.loads(self.op.run(self.cmd(ids)))
        self.assertEqual(len(calls), 2)
        self.assertIsNone(result["source_exact_explanation"])
        self.assertEqual(result["explanation_status"], "SOURCE_NOT_ADMITTED")
        self.assertFalse(result["human_source_lineage_verified"])

    def test_non_tty_busy_invalid_ids_and_age0_rejected(self):
        ids = self.sources()
        with self.assertRaisesRegex(ValueError, "Nur lokale Operator"):
            self.op.run(self.cmd(ids), origin="MODEL")
        with patch.object(self.r, "require_idle",
                          side_effect=ValueError("BUSY")):
            with self.assertRaisesRegex(ValueError, "BUSY"):
                self.op.run(self.cmd(ids))
        for bad in (":jefsource explain", ":jefsource explain " + ids[0],
                    self.cmd(ids) + " extra",
                    ":jefsource explain " + ids[0] + " wrong " + ids[2]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.op.run(bad)
        old = dict(self.r.cfg)
        try:
            for field, value in (("system_stage", 1),
                                 ("learning_mode", "SHADOW_UPDATE"),
                                 ("latents_enabled", True),
                                 ("jepa_weight", 1)):
                self.r.cfg[field] = value
                with self.assertRaisesRegex(ValueError, "AGE0_RECORD_ONLY_REQUIRED"):
                    self.op.run(self.cmd(ids))
                self.r.cfg.clear()
                self.r.cfg.update(old)
        finally:
            self.r.cfg.clear()
            self.r.cfg.update(old)

    def test_restart_same_explanation(self):
        ids = self.sources()
        before = json.loads(self.op.run(self.cmd(ids)))
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.op = Operator(self.r)
        after = json.loads(self.op.run(self.cmd(ids)))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

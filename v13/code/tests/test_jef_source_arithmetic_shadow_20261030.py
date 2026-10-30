"""Preregistered F1/F5 signed source arithmetic SHADOW regression, software only."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import p2x_disjoint_receiver_trainset as cohort
from v13 import jef_typed_source_shadow as typed
from v13 import jef_f1f5_source_admission as human
from v13.runtime import Runtime


class SourceExactArithmeticShadowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.rows = cohort.fixtures()
        cohort.validate(self.rows)
        self.calibration = sorted(
            (x for x in self.rows if x["partition"] == "calibration"),
            key=lambda x: x["id"])

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def refs(self, row):
        return (
            self.r.store.source(row["current"], "USER"),
            self.r.store.source(row["b2_source"], "USER"),
            self.r.store.source(row["b1_source"], "USER"),
            self.r.store.source(cohort.foreign_sheet(row, self.rows), "USER"))

    def assert_arithmetic(self, result, row):
        payload = result["source_exact_arithmetic"]
        self.assertEqual(payload["evidence_level"], "STORE_INTEGRITY_ONLY")
        self.assertEqual(payload["mode"], "SHADOW_NO_AUTHORITY")
        self.assertEqual(payload["project"], row["id"])
        self.assertEqual(payload["domain"], row["domain"])
        self.assertEqual(len(payload["fields"]), 2)
        self.assertEqual([f["limit"] for f in payload["fields"]],
                         [row["rule"]["max_first"], row["rule"]["max_second"]])
        for name in ("A", "B"):
            option = payload["options"][name]
            expected = row["options"][name]
            self.assertEqual(option["used"],
                             [expected["first"], expected["second"]])
            self.assertEqual(option["remaining"], [
                row["rule"]["max_first"] - expected["first"],
                row["rule"]["max_second"] - expected["second"]])
            self.assertEqual(option["flag"], expected["flag"])
            self.assertEqual(option["eligible"], (
                all(v >= 0 for v in option["remaining"]) and
                (not row["rule"]["require_flag"] or expected["flag"])))
        self.assertEqual(result["suggested_action"], row["oracle_action"])
        self.assertEqual(result["authority"], 0)
        self.assertFalse(result["weight_updates"])
        self.assertEqual(result["native_calls"], 0)
        self.assertEqual(result["jepa_weight"], 0)
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertFalse(result["whole_system_complete"])

    def test_36_exact_and_144_negative_calibration_rows(self):
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("native model called")):
            for row in self.calibration:
                current, policy, sheet, foreign = self.refs(row)
                before = self.r.store.one("SELECT count(*) AS n FROM sources")["n"]
                full = typed.decide(self.r.store, current, [policy, sheet])
                self.assert_arithmetic(full, row)
                for refs in ([], [policy], [sheet], [policy, foreign]):
                    result = typed.decide(self.r.store, current, refs)
                    self.assertEqual(result["suggested_action"], "UNKNOWN")
                    self.assertNotIn("source_exact_arithmetic", result)
                self.assertEqual(
                    self.r.store.one("SELECT count(*) AS n FROM sources")["n"],
                    before)

    def test_overlimit_signed_negative_not_clamped(self):
        row = next(x for x in self.calibration if
                   any(x["options"][name]["first"] > x["rule"]["max_first"]
                       for name in "AB"))
        current, policy, sheet, _ = self.refs(row)
        result = typed.decide(self.r.store, current, [policy, sheet])
        self.assert_arithmetic(result, row)
        self.assertTrue(any(
            x < 0 for opt in result["source_exact_arithmetic"]["options"].values()
            for x in opt["remaining"]))

    def record(self, key, value):
        event = self.r.store.event(self.r.session, "Record: " + key)
        mid = self.r.memory.feedback(
            event["event_id"], "fact", value, permission="record", key=key)
        self.r.memory.candidate(mid, self.r.session)
        return mid

    def human_sources(self, row):
        policy = self.record(
            f'Project {row["id"]} archived {row["domain"]} policy',
            row["b2_source"])
        sheet = self.record(
            f'Project {row["id"]} latest {row["domain"]} option sheet',
            row["b1_source"])
        event = self.r.store.event(self.r.session, row["current"])
        return event["event_id"], event["source_ref"], policy, sheet

    def test_human_f1f5_restart_and_forget(self):
        row = self.calibration[0]
        event, current, policy, sheet = self.human_sources(row)
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("native model called")):
            first = human.decide(
                self.r.memory, self.r.session, event, current, [policy, sheet])
        self.assertTrue(first["human_source_lineage_verified"])
        self.assert_arithmetic(first, row)
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        again = human.decide(
            self.r.memory, self.r.session, event, current, [policy, sheet])
        self.assertEqual(first, again)
        self.r.memory.forget(sheet)
        revoked = human.decide(
            self.r.memory, self.r.session, event, current, [policy, sheet])
        self.assertEqual(revoked["suggested_action"], "UNKNOWN")
        self.assertFalse(revoked["human_source_lineage_verified"])
        self.assertNotIn("source_exact_arithmetic", revoked)

    def test_tampered_human_sheet_refuses_all_arithmetic(self):
        row = self.calibration[1]
        event, current, policy, sheet = self.human_sources(row)
        candidate = self.r.memory.candidate(sheet, self.r.session)
        blob = self.home / "data/blobs" / candidate["source_ref"]["sha256"]
        blob.write_text("forged", encoding="utf-8")
        result = human.decide(
            self.r.memory, self.r.session, event, current, [policy, sheet])
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assertNotIn("source_exact_arithmetic", result)
        self.assertFalse(result["human_source_lineage_verified"])


if __name__ == "__main__":
    unittest.main()

"""Run113 Atlas CQP20: fail-closed software guards; never start native models."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run113_step2_atlas_cqp_native_pilot as pilot
from v13.common import digest, dumps


class Run113NativePilotGuards(unittest.TestCase):
    def test_registered_atlas_cqp20_and_no_native_preflight(self):
        dry = pilot.prereg()
        self.assertFalse(dry["native_execution"])
        self.assertEqual(dry["native_calls"], 0)
        self.assertEqual(pilot.ARM, "CQP")
        self.assertEqual(pilot.SEED, 20)
        self.assertEqual(pilot.FIXTURE_ID, "Atlas")
        self.assertEqual(pilot.FIXTURE_SHA256,
                         dry["registration"]["fixture_sha256"])
        self.assertEqual(len(pilot.VARIANTS), 7)
        self.assertIs(pilot.z2, pilot.z2b.z2)
        old = pilot.z2.FIXTURES
        with pilot.pre.configured():
            self.assertEqual(len(pilot.z2.harness().FIXTURES), 6)
            self.assertEqual(pilot.z2.FIXTURES[0]["id"], "Atlas")
            self.assertEqual(pilot.pre.settings("CQP", 20)["b2_quote_select"],
                             "pointer")
        self.assertIs(pilot.z2.FIXTURES, old)

    def test_missing_installed_home_refuses_without_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "new-evidence"
            with self.assertRaises(ValueError):
                pilot.run(root / "missing", target)
            self.assertFalse(target.exists())

    def synthetic(self):
        hashes = {"B1_DETAIL": "a" * 64, "B2_GIST": "b" * 64,
                  "C3_LANGUAGE": "c" * 64}
        rows = []
        for variant in pilot.VARIANTS:
            rows.append({"fixture": "Atlas", "variant": variant,
                         "status": "RECORDED", "processes_reaped": True,
                         "oracle_visible_to_native": False,
                         "consumer_messages": [{"role": "user", "content": "{}"}],
                         "native_consumer_metrics": {"status": "FINAL"}})
        report = {
            "status": "DIAGNOSTIC_INCOMPLETE",
            "wire_arm": {"arm": "w1"},
            "canonical_gate_pass": False,
            "phone_measured": False,
            "all_structural_checks_passed": True,
            "source_unchanged": True,
            "installed_artifacts_unchanged": True,
            "distinct_bodies": True,
            "fixture_sha256": pilot.FIXTURE_SHA256,
            "fixtures": pilot.pre.corpus.fixtures(),
            "preparations": [{"fixture": "Atlas", "status": "RECORDED",
                              "model_sha256": hashes}],
            "rows": rows,
            "row_sha256": {r["fixture"] + ":" + r["variant"]: digest(dumps(r))
                           for r in rows},
        }
        return report, hashes

    def test_seven_source_rows_and_negative_gates_fail_closed(self):
        report, hashes = self.synthetic()
        ok = pilot.verify_source(report, {"offers": 12, "with_question": 12},
                                 hashes)
        self.assertEqual(ok["rows"], 7)
        for change in (
            lambda r: r["rows"].pop(),
            lambda r: r["rows"][0].update(status="ERROR"),
            lambda r: r["rows"][0].update(processes_reaped=False),
            lambda r: r["rows"][0].update(oracle_visible_to_native=True),
            lambda r: r["rows"][0]["native_consumer_metrics"].update(status="ERROR"),
            lambda r: r["fixtures"][0]["rules"].update(budget=-1),
            lambda r: r.update(canonical_gate_pass=True),
            lambda r: r.update(distinct_bodies=False),
            lambda r: r.update(status="UTILITY_PASS_SCOPED"),
        ):
            bad = copy.deepcopy(report)
            change(bad)
            with self.subTest(change=repr(change)), self.assertRaises(ValueError):
                pilot.verify_source(bad, {"offers": 12, "with_question": 12},
                                    hashes)
        with self.assertRaises(ValueError):
            pilot.verify_source(report, {"offers": 12, "with_question": 11},
                                hashes)

    def test_private_replay_accepts_only_sealed_atlas_diagnostic(self):
        private = pilot.private_tool_replay()
        report, _ = self.synthetic()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.json"
            path.write_text(json.dumps(report))
            self.assertEqual(len(private.recorded(path)["rows"]), 7)
            tampered = copy.deepcopy(report)
            tampered["rows"][0]["variant"] = "wrong"
            path.write_text(json.dumps(tampered))
            with self.assertRaises(ValueError):
                private.recorded(path)
            tampered = copy.deepcopy(report)
            tampered["status"] = "UTILITY_PASS_SCOPED"
            path.write_text(json.dumps(tampered))
            with self.assertRaises(ValueError):
                private.recorded(path)

    def test_tool_seven_rows_binding_and_wrong_commit_refusal(self):
        source, _ = self.synthetic()
        rows = []
        for src in source["rows"]:
            rows.append({"fixture": "Atlas", "variant": src["variant"],
                         "status": "RECORDED", "oracle_visible_to_native": False,
                         "consumer_metrics": {"status": "FINAL"},
                         "consumer_messages_sha256":
                             digest(dumps(src["consumer_messages"]))})
        tool = {
            "status": "TOOL_UTILITY_FAIL", "canonical_gate_pass": False,
            "phone_measured": False, "installed_artifacts_unchanged": True,
            "paired_tool": {"complete": False},
            "rows": rows,
            "row_sha256": {r["fixture"] + ":" + r["variant"]: digest(dumps(r))
                           for r in rows},
            "summary": {"tool": {v: {"wrong_committed": 0}
                                 for v in pilot.VARIANTS}},
        }
        self.assertEqual(pilot.verify_tool(source, tool)["rows"], 7)
        for change in (
            lambda t: t["rows"].pop(),
            lambda t: t["rows"][0].update(consumer_messages_sha256="wrong"),
            lambda t: t["rows"][0].update(oracle_visible_to_native=True),
            lambda t: t["rows"][0]["consumer_metrics"].update(status="ERROR"),
            lambda t: t["summary"]["tool"]["both_exact"].update(wrong_committed=1),
            lambda t: t.update(canonical_gate_pass=True),
            lambda t: t.update(status="TOOL_UTILITY_PASS_SCOPED"),
        ):
            bad = copy.deepcopy(tool)
            change(bad)
            with self.subTest(change=repr(change)), self.assertRaises(ValueError):
                pilot.verify_tool(source, bad)


if __name__ == "__main__":
    unittest.main()

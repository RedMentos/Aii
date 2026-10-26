"""Run396 independent raw audit adversarial synthetic fixtures; no native/model execution."""
import copy
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run394_step2_fresh as r394
import run396_step2_pilot_audit as audit
from v13.common import digest, dumps


def write(path, obj):
    Path(path).write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n")


def rowhashes(rows):
    return {x["fixture"] + ":" + x["variant"]: digest(dumps(x)) for x in rows}


def make_synthetic(folder):
    """Generate complete fake reports ONLY to test audit logic, never native evidence."""
    folder = Path(folder)
    fixtures = [copy.deepcopy(f) for f in r394.FIXTURES if f["id"] in r394.PILOT_IDS]
    manifest = r394.manifest(fixtures, True, list(audit.ARMS), [20])
    write(folder / "RUN394_PREREGISTERED_FIXTURES.json", manifest)
    result = {"run": "Run394", "status": "PILOT_DIAGNOSTIC",
              "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
              "preregistration_sha256": audit.sha(folder / "RUN394_PREREGISTERED_FIXTURES.json"),
              "results": {}}
    for arm in audit.ARMS:
        rid = arm + "_s20"
        src_rows = []
        tool_rows = []
        for fixture in fixtures:
            old = fixture["old_rules"]
            old_rule = r394.rule_text((old["budget"], old["deadline"], old["local_only"]))
            for variant in audit.VARIANTS:
                msg = [{"role": "system", "content": "Synthetic audit fixture"},
                       {"role": "user", "content": json.dumps({
                           "current_source": fixture["current"],
                           "analysts": [{"role": "B2_GIST", "verified_quotes": [old_rule]}]
                       })}]
                src = {"fixture": fixture["id"], "variant": variant,
                       "status": "RECORDED", "consumer_messages": msg}
                src_rows.append(src)
                value = {"O": 0.25, "P": 0.75, "S": 0.5}[arm]
                tool_rows.append({"fixture": fixture["id"], "variant": variant,
                                  "status": "RECORDED", "score": {"utility": value},
                                  "elapsed_s": 1.0, "oracle_visible_to_native": False,
                                  "consumer_messages_sha256": digest(dumps(msg))})
        source = {"fixtures": fixtures, "status": "UTILITY_FAIL",
                  "all_structural_checks_passed": True, "wire_arm": {"arm": "w1"},
                  "rows": src_rows, "row_sha256": rowhashes(src_rows)}
        source_path = folder / ("step2_" + rid + ".json")
        write(source_path, source)
        prereg = {"source_report": {"sha256": audit.sha(source_path)}}
        prereg_path = folder / ("tool_" + rid + ".preregistration.json")
        write(prereg_path, prereg)
        mean = {v: {"O": 0.25, "P": 0.75, "S": 0.5}[arm] for v in audit.VARIANTS}
        tool = {"rows": tool_rows, "row_sha256": rowhashes(tool_rows),
                "installed_artifacts_unchanged": True, "status": "TOOL_UTILITY_FAIL",
                "canonical_gate_pass": False, "phone_measured": False,
                "preregistration_sha256": audit.sha(prereg_path),
                "paired_tool": {"mean_utility": mean},
                "summary": {"tool": {v: {"wrong_committed": 0} for v in audit.VARIANTS}}}
        tool_path = folder / ("tool_" + rid + ".json")
        write(tool_path, tool)
        summary = {"run": rid, "arm": arm, "seed": 20,
                   "z2c": {"b2_quote_select": r394.ARMS[arm]["pointer"],
                           "wrong_committed_tool": 0},
                   "paired_tool": {"mean_utility": mean}}
        summary_path = folder / ("summary_" + rid + ".json")
        write(summary_path, summary)
        result["results"][rid] = {"rows": 14, "summary_sha256": audit.sha(summary_path),
                                  "tool_sha256": audit.sha(tool_path)}
    write(folder / "RUN394_RESULT.json", result)
    return folder


class Run396AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = make_synthetic(self.temp.name)

    def test_valid_synthetic_audit_nonpromoting_and_paired(self):
        report = audit.audit(self.folder)
        self.assertEqual(report["rows_verified"], 42)
        self.assertEqual(report["status"], "PILOT_POSTFLIGHT_VERIFIED")
        self.assertFalse(report["canonical_gate_pass"])
        self.assertEqual(report["step2_exit"], "UTILITY_FAIL")
        self.assertFalse(report["redmi_measured"])
        self.assertAlmostEqual(report["paired_differences"]["pointer_minus_off"]["both_exact"]["mean"], .5)
        self.assertAlmostEqual(report["paired_differences"]["pointer_minus_shared_body"]["both_exact"]["mean"], .25)
        self.assertTrue(report["historical_quote_provenance"]["P"]["Delta"]["revision_overrides_historical_rule"])
        self.assertEqual(report["historical_quote_provenance"]["P"]["Delta"]["historical_exact_rule_quotes"], 4)

    def test_reject_missing_arm_not_silently_zero(self):
        (self.folder / "tool_S_s20.json").unlink()
        with self.assertRaises(FileNotFoundError):
            audit.audit(self.folder)

    def test_reject_modified_row_even_if_summary_unchanged(self):
        path = self.folder / "tool_P_s20.json"
        j = audit.load(path)
        j["rows"][0]["score"]["utility"] = .001
        write(path, j)
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            audit.audit(self.folder)

    def test_reject_nonnumeric_even_with_forged_updated_digests(self):
        path = self.folder / "tool_P_s20.json"
        j = audit.load(path)
        j["rows"][0]["score"]["utility"] = "NaN"
        j["row_sha256"] = rowhashes(j["rows"])
        write(path, j)
        result_path = self.folder / "RUN394_RESULT.json"
        result = audit.load(result_path)
        result["results"]["P_s20"]["tool_sha256"] = audit.sha(path)
        write(result_path, result)
        with self.assertRaisesRegex(ValueError, "invalid utility"):
            audit.audit(self.folder)

    def test_reject_wrong_committed_tool_even_if_rows_are_complete(self):
        path = self.folder / "summary_O_s20.json"
        j = audit.load(path)
        j["z2c"]["wrong_committed_tool"] = 1
        write(path, j)
        with self.assertRaisesRegex(ValueError, "wrong committed tool"):
            audit.audit(self.folder)

    def test_reject_false_model_identity(self):
        path = self.folder / "tool_O_s20.json"
        j = audit.load(path)
        j["installed_artifacts_unchanged"] = False
        write(path, j)
        with self.assertRaisesRegex(ValueError, "installed model changed"):
            audit.audit(self.folder)

    def test_reject_forged_oracle_visibility(self):
        path = self.folder / "tool_S_s20.json"
        j = audit.load(path)
        j["rows"][0]["oracle_visible_to_native"] = True
        j["row_sha256"] = rowhashes(j["rows"])
        write(path, j)
        result_path = self.folder / "RUN394_RESULT.json"
        result = audit.load(result_path)
        result["results"]["S_s20"]["tool_sha256"] = audit.sha(path)
        write(result_path, result)
        with self.assertRaisesRegex(ValueError, "oracle leaked"):
            audit.audit(self.folder)

    def test_reject_wrong_fixture_manifest(self):
        path = self.folder / "RUN394_PREREGISTERED_FIXTURES.json"
        j = audit.load(path)
        j["fixtures"][0]["rules"]["budget"] += 1
        write(path, j)
        with self.assertRaisesRegex(ValueError, "fixture hash mismatch"):
            audit.audit(self.folder)

    def test_historical_quote_not_a_current_rule_claim(self):
        f = next(x for x in r394.FIXTURES if x["id"] == "Delta")
        old = f["old_rules"]
        rule = r394.rule_text((old["budget"], old["deadline"], old["local_only"]))
        rows = {}
        for v in audit.B2_VARIANTS:
            rows[(f["id"], v)] = {"consumer_messages": [{"role": "user", "content": json.dumps({
                "analysts": [{"role": "B2_GIST", "verified_quotes": [rule]}]})}]}
        result = audit.quote_provenance(rows, f)
        self.assertEqual(result["historical_exact_rule_quotes"], 4)
        self.assertTrue(result["revision_overrides_historical_rule"])
        self.assertTrue(result["historical_quote_is_not_by_itself_hallucination"])


if __name__ == "__main__":
    unittest.main()

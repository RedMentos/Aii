"""Run13A read-only posthoc ZIP audit: synthetic tamper controls only."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import run13a_raw_route_readonly_audit_20261030 as audit


def synthetic():
    fixtures = [{"project": f"PrivateFixture{i}", "budget": 1000,
                 "a_cost": 200, "b_cost": 300} for i in range(8)]
    rows, witnesses = [], {}
    for i in range(32):
        arm = audit.ARM_ORDER[i // 4][i % 4]
        f = fixtures[i // 4]
        output = "800 and 700" if arm == "F_NATIVE_AUTO" else "No answer"
        row = {
            "index": i, "fixture": f["project"], "arm": arm,
            "event_id": f"event{i}", "final_output": output,
            "flags": {"valid_native": True, "route": "both" if arm == "F_NATIVE_AUTO" else "gist",
                      "runner_role": "B1_DETAIL" if arm == "F_NATIVE_AUTO" else "B2_GIST",
                      "route_source": "NATIVE_C2_ADVISORY"},
            "score": {"correct": 0},
            "full_task": {"strict_full": False},
        }
        rows.append(row)
        if arm == "F_NATIVE_AUTO":
            witnesses[i] = {
                "event_id": row["event_id"], "arm": arm,
                "fixture": f["project"], "final_output": output,
                "source_exact_before_close": True,
                "observer_mode": "off", "raw_audit": {"output": output},
                "route_info": {
                    "native_control": {"function_calls": [
                        {"name": "select_processing", "arguments": {"route": "both"}}]},
                    "source": "NATIVE_C2_ADVISORY"},
            }
    report = {
        "schema": "v13.c2_c3_body.fulltask.run13a.v1",
        "seed": 211, "fixture_sha256": "synthetic-only",
        "arms": list(audit.ARMS), "arm_order": [list(x) for x in audit.ARM_ORDER],
        "fixtures": fixtures, "rows": rows,
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
    }
    report.update({k: False for k in audit.NEGATIVE})
    return report, witnesses


def archive(report, witnesses, *, corrupt_manifest=False):
    members = {"HEAD.txt": b"synthetic-head\n",
               "pilot/report.json": json.dumps(report).encode("utf-8")}
    for i, witness in witnesses.items():
        members[f"pilot/preclose/{i:02d}_F_NATIVE_AUTO.json"] = json.dumps(
            witness).encode("utf-8")
    lines = []
    for name, value in sorted(members.items()):
        digest = hashlib.sha256(value).hexdigest()
        if corrupt_manifest and name == "pilot/report.json":
            digest = "0" * 64
        lines.append(f"{digest}  ./{name}")
    members["SHA256SUMS"] = ("\n".join(lines) + "\n").encode("utf-8")
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, value in members.items():
            z.writestr(name, value)
    return b.getvalue()


class OriginalZipReadOnlyTests(unittest.TestCase):
    def test_presence_does_not_change_frozen_scores(self):
        report, witnesses = synthetic()
        out = audit.analyze(report, witnesses, expected_fixture="synthetic-only")
        self.assertEqual(out["original_f_numeric_total"], 0)
        self.assertEqual(out["original_b2_numeric_total"], 0)
        self.assertEqual(out["f_numeric_value_presence_both_rows"], 8)
        self.assertEqual(out["f_role_counts"], {"B1_DETAIL": 8})
        self.assertFalse(out["gate_promotion"])
        self.assertIn("NOT CORRECTNESS OR RESCORING", out["claim_limit"])
        self.assertNotIn("final_output", json.dumps(out))
        self.assertNotIn("PrivateFixture0", out["rows"][0]["f_output_sha256"])

    def test_original_bytes_manifest_head_and_tamper_are_bound(self):
        report, witnesses = synthetic()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "synthetic.zip"
            raw = archive(report, witnesses)
            p.write_bytes(raw)
            parsed, found = audit.verify_zip(
                p, expected_sha=hashlib.sha256(raw).hexdigest(),
                expected_head="synthetic-head")
            self.assertEqual(parsed["seed"], 211)
            self.assertEqual(len(found), 8)
            with self.assertRaisesRegex(ValueError, "OUTER_ZIP_SHA_MISMATCH"):
                audit.verify_zip(p)
            broken = archive(report, witnesses, corrupt_manifest=True)
            p.write_bytes(broken)
            with self.assertRaisesRegex(ValueError, "MANIFEST_HASH_MISMATCH"):
                audit.verify_zip(p, expected_sha=hashlib.sha256(broken).hexdigest(),
                                 expected_head="synthetic-head")

    def test_changed_cohort_and_negative_gate_are_rejected(self):
        report, witnesses = synthetic()
        report["step2_gate_promoted"] = True
        with self.assertRaisesRegex(ValueError, "NEGATIVE_GATE_CHANGED"):
            audit.analyze(report, witnesses, expected_fixture="synthetic-only")
        report["step2_gate_promoted"] = False
        report["arm_order"][0][0] = "F_NATIVE_AUTO"
        with self.assertRaisesRegex(ValueError, "FROZEN_COHORT_CHANGED"):
            audit.analyze(report, witnesses, expected_fixture="synthetic-only")


if __name__ == "__main__":
    unittest.main()

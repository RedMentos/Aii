"""Run45A: deterministic synthetic witnesses and adversarial original-raw mutations."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run45a_run44_raw_audit as audit

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run44_source_handoff_seed307.json"


def h(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def make_ref(text, source_id):
    return {"source_id": source_id, "sha256": h(text), "modality": "text",
            "char_start": 0, "char_end": len(text)}


def make_report():
    fixture = json.loads(FIXTURE.read_text())
    rows = []
    for f, order in zip(fixture["fixtures"], audit.ORDER):
        prior = make_ref(f["prior"], "prior-" + f["id"])
        current = make_ref(f["current"], "current-" + f["id"])
        for arm in order:
            payload = {"current_source": f["current"]}
            row = {"fixture": f["id"], "arm": arm, "status": "RECORDED",
                   "prior_sha256": h(f["prior"]), "current_sha256": h(f["current"]),
                   "oracle_visible_to_native": False,
                   "prior_source_ref": prior, "current_source_ref": current,
                   "native_b2_finals": [True, True] if arm == audit.ARMS[1] else [],
                   "native_c3_final": True, "native_c3_metrics": {"status": "FINAL"},
                   "process_releases": [{"process_reaped": True}],
                   "processes_reaped": True}
            if arm == audit.ARMS[1]:
                quote = (f["prior"].split(". ")[1] + ".")
                a = f["prior"].index(quote)
                qref = dict(prior, char_start=a, char_end=a + len(quote))
                quote_obj = {"text": quote, "source_ref": qref,
                             "verification": "EXACT_SOURCE_SUBSTRING_ONLY",
                             "semantic_truth_authority": False}
                payload["analysts"] = [{"role": "B2_GIST", "offer_packet_id": "pkt",
                                         "hypothesis": {"summary": "Source quote only"},
                                         "hypothesis_authority": "MODEL_HYPOTHESIS_NOT_FACT",
                                         "verified_quotes": [quote_obj]}]
                row["prior_quote_verified"] = True
                row["verified_quote_refs"] = [qref]
                row["verified_quote_texts"] = [quote]
            elif arm == audit.ARMS[2]:
                payload["prior_source"] = f["prior"]
            row["native_prompt"] = [{"role": "system", "content": audit.SYS},
                                    {"role": "user", "content": json.dumps(
                                        payload, sort_keys=True, ensure_ascii=False,
                                        separators=(",", ":"))}]
            row["native_prompt_sha256"] = audit.digest(row["native_prompt"])
            answer = ({"choice": "UNKNOWN", "remaining": None}
                      if arm == audit.ARMS[0] else f["oracle"])
            row["native_answer"] = json.dumps(answer)
            row["score"] = {"correct": audit.strict_score(row["native_answer"], f["oracle"])}
            rows.append(row)
    report = {"schema": "v13.run44.current_source_handoff_native_result.v1",
              "registered": True, "seed": 307, "fixture_sha256": audit.FIXTURE_SHA256,
              "negative_gates": audit.NEGATIVE, "binding": {"model_sha256": audit.MODELS},
              "rows": rows, "installed_binding_unchanged": True}
    seal(report)
    return report


def seal(report):
    report["row_sha256"] = {r["fixture"] + "/" + r["arm"]: audit.digest(r)
                            for r in report["rows"]}
    counts = {a: {"rows": 0, "correct": 0, "structural": 0} for a in audit.ARMS}
    for row in report["rows"]:
        c = counts[row["arm"]]
        c["rows"] += 1
        c["correct"] += row["score"]["correct"]
        c["structural"] += int(row["status"] == "RECORDED")
    report["summary"] = counts
    a, b, c = (counts[x]["correct"] for x in audit.ARMS)
    report["pilot_signal"] = (len(report["rows"]) == 12 and
                              all(counts[x]["structural"] == 4 for x in audit.ARMS)
                              and b >= a + 2 and b >= c - 1 and b >= 2)
    report["status"] = ("PILOT_SIGNAL_ONLY_NO_PROMOTION" if report["pilot_signal"]
                        else "UTILITY_FAIL" if len(report["rows"]) == 12
                        and all(r["status"] == "RECORDED" for r in report["rows"])
                        else "STRUCTURAL_RED")


class OriginalRawAuditTests(unittest.TestCase):
    def check(self, report):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "original.json"
            p.write_text(json.dumps(report))
            return audit.audit(p, FIXTURE)

    def test_12row_strict_green_no_promotion(self):
        result = self.check(make_report())
        self.assertEqual(result["status"], "AUDIT_GREEN_STRUCTURAL")
        self.assertTrue(result["strict_pilot_signal"])
        self.assertEqual(result["negative_gates"]["step2"], "UTILITY_FAIL")

    def test_duplicate_json_key_detects_original_scorer_disagreement(self):
        r = make_report()
        row = next(x for x in r["rows"] if x["fixture"] == "Quartz"
                   and x["arm"] == audit.ARMS[1])
        row["native_answer"] = '{"choice":"B","choice":"A","remaining":12}'
        seal(r)
        result = self.check(r)
        self.assertEqual(result["status"], "AUDIT_RED")
        self.assertTrue(any("ORIGINAL_SCORE_DISAGREEMENT" in x for x in result["reasons"]))

    def test_wrong_source_id_rejected_even_if_text_matches(self):
        r = make_report()
        row = next(x for x in r["rows"] if x["arm"] == audit.ARMS[1])
        q = row["native_prompt"][1]["content"]
        obj = json.loads(q)
        obj["analysts"][0]["verified_quotes"][0]["source_ref"]["source_id"] = "foreign"
        row["native_prompt"][1]["content"] = json.dumps(obj)
        row["verified_quote_refs"][0]["source_id"] = "foreign"
        row["native_prompt_sha256"] = audit.digest(row["native_prompt"])
        seal(r)
        with self.assertRaisesRegex(audit.AuditError, "QUOTE_FOREIGN_SOURCE"):
            self.check(r)

    def test_changed_offset_rejected_even_with_rehashed_receipts(self):
        r = make_report()
        row = next(x for x in r["rows"] if x["arm"] == audit.ARMS[1])
        obj = json.loads(row["native_prompt"][1]["content"])
        obj["analysts"][0]["verified_quotes"][0]["source_ref"]["char_start"] += 1
        row["native_prompt"][1]["content"] = json.dumps(obj)
        row["verified_quote_refs"][0]["char_start"] += 1
        row["native_prompt_sha256"] = audit.digest(row["native_prompt"])
        seal(r)
        with self.assertRaisesRegex(audit.AuditError, "QUOTE_SPAN"):
            self.check(r)

    def test_analyst_semantic_truth_forgery_rejected(self):
        r = make_report()
        row = next(x for x in r["rows"] if x["arm"] == audit.ARMS[1])
        obj = json.loads(row["native_prompt"][1]["content"])
        obj["analysts"][0]["verified_quotes"][0]["semantic_truth_authority"] = True
        row["native_prompt"][1]["content"] = json.dumps(obj)
        row["native_prompt_sha256"] = audit.digest(row["native_prompt"])
        seal(r)
        with self.assertRaisesRegex(audit.AuditError, "QUOTE_AUTHORITY"):
            self.check(r)

    def test_missing_prior_quote_rejected(self):
        r = make_report()
        row = next(x for x in r["rows"] if x["arm"] == audit.ARMS[1])
        obj = json.loads(row["native_prompt"][1]["content"])
        obj["analysts"][0]["verified_quotes"] = []
        row["native_prompt"][1]["content"] = json.dumps(obj)
        row["verified_quote_refs"] = []
        row["verified_quote_texts"] = []
        row["native_prompt_sha256"] = audit.digest(row["native_prompt"])
        seal(r)
        with self.assertRaisesRegex(audit.AuditError, "B_QUOTE_RECEIPTS"):
            self.check(r)

    def test_row_digest_tamper_rejected(self):
        r = make_report()
        r["rows"][0]["native_answer"] = "tampered"
        with self.assertRaisesRegex(audit.AuditError, "ROW_DIGEST"):
            self.check(r)

    def test_negative_gate_tamper_rejected(self):
        r = make_report()
        r["negative_gates"] = dict(r["negative_gates"], step2="PASS")
        with self.assertRaisesRegex(audit.AuditError, "REGISTRATION"):
            self.check(r)

    def test_structural_red_preserved_not_promoted(self):
        r = make_report()
        r["rows"][0]["status"] = "ERROR"
        r["rows"][0]["score"]["correct"] = 0
        seal(r)
        result = self.check(r)
        self.assertEqual(result["status"], "ORIGINAL_INCOMPLETE")
        self.assertFalse(result["strict_pilot_signal"])

    def test_partial_checkpoint_is_incomplete(self):
        r = make_report()
        r["rows"] = r["rows"][:5]
        seal(r)
        result = self.check(r)
        self.assertEqual(result["status"], "ORIGINAL_INCOMPLETE")
        self.assertIn("ORIGINAL_INCOMPLETE_ROWS", result["reasons"])

    def test_nonfinite_and_boolean_are_not_integer(self):
        self.assertEqual(audit.strict_score('{"choice":"A","remaining":NaN}',
                                            {"choice": "A", "remaining": 12}), 0)
        self.assertEqual(audit.strict_score('{"choice":"A","remaining":true}',
                                            {"choice": "A", "remaining": 1}), 0)


if __name__ == "__main__":
    unittest.main()

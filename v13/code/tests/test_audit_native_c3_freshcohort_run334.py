"""Run334 independent raw-score audit negative fixtures (source-only)."""
import unittest
from scripts import audit_native_c3_freshcohort_run334 as A
from scripts import native_c3_freshcohort_run334 as E


def synthetic_row():
    data=E.cohort()
    def group(items,key):
        return [{"q":x.get("q",x.get("prompt")),"a":"unknown",key:False,"strict":False}
                for x in items]
    return {"facts":group(data["facts"],"ok"),
            "paraphrases":group(data["paraphrases"],"ok"),
            "near_miss":group(data["near_miss"],"leak"),
            "probes":group(E.PROBES,"ok"),
            "invalid_outputs":0,
            "summary":{"facts_strict":0,"paraphrases_strict":0,
                       "near_miss_leak_strict":0.0,"probes_ok":0,
                       "invalid_outputs":0,"facts_n":8,
                       "paraphrases_n":6,"near_miss_n":5,"probes_n":12}}


class Run334IndependentSourceOnly(unittest.TestCase):
    def test_synthetic_raw_scores_recompute(self):
        row=synthetic_row()
        self.assertEqual(A.recompute(row,E.cohort()),row["summary"])

    def test_forged_positive_label_rejected(self):
        row=synthetic_row()
        row["facts"][0]["ok"]=True
        with self.assertRaisesRegex(ValueError,"label drift"):
            A.recompute(row,E.cohort())

    def test_answer_changed_without_label_update_rejected(self):
        row=synthetic_row()
        row["facts"][0]["a"]="cobalt"
        with self.assertRaisesRegex(ValueError,"label drift"):
            A.recompute(row,E.cohort())

    def test_wrong_question_or_order_rejected(self):
        row=synthetic_row()
        row["facts"][0]["q"]="other"
        with self.assertRaisesRegex(ValueError,"order/question"):
            A.recompute(row,E.cohort())

    def test_missing_denominator_rejected(self):
        row=synthetic_row()
        row["near_miss"].pop()
        with self.assertRaisesRegex(ValueError,"denominator"):
            A.recompute(row,E.cohort())

    def test_summary_tamper_rejected(self):
        row=synthetic_row()
        row["summary"]["facts_strict"]=1
        with self.assertRaisesRegex(ValueError,"summary"):
            A.recompute(row,E.cohort())

    def test_incomplete_native_run_rejected(self):
        with self.assertRaisesRegex(ValueError,"incomplete"):
            A.audit({"schema":E.SCHEMA,"status":"INCOMPLETE"},"unused")

    def test_negative_gate_drift_rejected(self):
        report={"schema":E.SCHEMA,"status":"COMPLETE_NATIVE_THREE_ARM_DIAGNOSTIC",
                "evidence_level":"LINUX_NATIVE_C3_FRESH_COHORT_TRAIN_EVAL",
                "cohort_sha256":E.COHORT_SHA,"master_sha256":E.MASTER_SHA,
                "train":E.TRAIN,"criteria":E.CRITERIA,
                "gates":dict(E.GATES,STEP2="PASS"),"weights_published":False,
                "model_activated":False}
        with self.assertRaisesRegex(ValueError,"negative gates"):
            A.audit(report,"unused")

    def test_sha_validator(self):
        self.assertTrue(A.valid_sha("a"*64))
        self.assertFalse(A.valid_sha("g"*64))
        self.assertFalse(A.valid_sha("a"*63))

    def test_no_model_activation_from_source_only(self):
        self.assertEqual(A.SCHEMA,"V13_RUN334_INDEPENDENT_RAW_SCORE_AUDIT_V1")
        self.assertEqual(E.GATES["Body_JEPA"],"UNAVAILABLE")
        self.assertEqual(E.GATES["jepa_weight"],0)


if __name__=="__main__":
    unittest.main()

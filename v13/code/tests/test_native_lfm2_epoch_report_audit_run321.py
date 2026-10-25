"""Run321 adversarial JSON-only audit tests; never native optimizer evidence."""
import copy
import unittest

from scripts import audit_native_lfm2_epoch_eval_run321 as A
from scripts import native_lfm2_epoch_eval_run320 as R


def fake_eval(facts=0, para=0, probes=0):
    def rows(pairs, positive, field="ok"):
        result = []
        for i, (q, keys) in enumerate(pairs):
            ans = str(keys[0]) if i < positive else ""
            result.append({"q": q, "a": ans, field: R.hit(ans, keys),
                           "strict": R.hit(R.first_sentence(ans), keys)})
        return result
    f = rows([(q, keys) for q, _, keys in R.FACTS], facts)
    p = rows(list(R.PARAPHRASES), para)
    n = rows(list(R.NEAR_MISS), 0, "leak")
    h = rows([(x["prompt"], x["expect"]) for x in R.PROBES], probes)
    return {
        "facts": f, "paraphrases": p, "near_miss": n, "probes": h,
        "invalid_outputs": 0,
        "summary": {
            "facts_ok": sum(x["ok"] for x in f), "facts_n": 8,
            "para_ok": sum(x["ok"] for x in p), "para_n": 6,
            "near_miss_leak": 0.0, "probes_ok": sum(x["ok"] for x in h),
            "probes_n": 12, "facts_strict": sum(x["strict"] for x in f),
            "para_strict": sum(x["strict"] for x in p),
            "near_miss_leak_strict": 0.0,
        },
    }


def fake_report():
    base = fake_eval(probes=2)
    e1 = fake_eval(facts=3, para=2, probes=2)
    e2 = fake_eval(facts=4, para=2, probes=2)
    selection = R.select(base, [e1, e2])
    sha = lambda ch: ch * 64
    return {
        "schema": R.SCHEMA, "status": "COMPLETE_NATIVE_EVALUATION",
        "evidence_level": "LINUX_NATIVE_C3_TRAIN_AND_EVAL",
        "hf_repo": R.HF_REPO, "hf_revision": R.HF_REVISION,
        "gates": dict(R.GATES), "weights_published": False,
        "native_training_executed": True, "train": {"epochs": 2},
        "final_matches_last_epoch_sha256": True,
        "master_sha256": sha("a"), "source_manifest_sha256": sha("a"),
        "native_binary_sha256": sha("a"), "quantizer_sha256": sha("a"),
        "server_sha256": sha("a"), "train_stream_sha256": sha("a"),
        "final_master_sha256": sha("c"), "baseline_q4_sha256": sha("a"),
        "checkpoint_receipts": [
            {"epoch": 1, "bytes": 1024, "sha256": sha("b")},
            {"epoch": 2, "bytes": 1024, "sha256": sha("c")},
        ],
        "baseline": base,
        "epochs": [
            {"epoch": 1, "source_sha256": sha("b"), "q4_sha256": sha("d"), "evaluation": e1},
            {"epoch": 2, "source_sha256": sha("c"), "q4_sha256": sha("e"), "evaluation": e2},
        ],
        "selection_report": selection, "selection": selection["selection"],
    }


class Run321IndependentReportAudit(unittest.TestCase):
    def setUp(self):
        self.report = fake_report()

    def fail_case(self, mutate, message):
        report = copy.deepcopy(self.report)
        mutate(report)
        with self.assertRaisesRegex(A.AuditError, message):
            A.audit(report)

    def test_valid_report_passes_without_authority_promotion(self):
        result = A.audit(self.report)
        self.assertEqual(result["status"], "PASS_SOURCE_ONLY")
        self.assertEqual(result["selection"], "CANDIDATE_ONLY_NO_ACTIVATION")
        self.assertEqual(result["selected_epoch"], 1)
        self.assertEqual(result["gates"], R.GATES)

    def test_swapped_retention_probe_is_not_hidden_by_same_denominator(self):
        def mutate(r):
            p = r["epochs"][0]["evaluation"]["probes"]
            p[0], p[2] = p[2], p[0]
        self.fail_case(mutate, "question/order mismatch")

    def test_forged_summary_score_rejected(self):
        self.fail_case(lambda r: r["epochs"][0]["evaluation"]["summary"].__setitem__(
            "facts_strict", 8), "summary differs")

    def test_forged_raw_strict_bit_rejected(self):
        self.fail_case(lambda r: r["epochs"][0]["evaluation"]["facts"][0].__setitem__(
            "strict", False), "forged strict")

    def test_forged_raw_ok_bit_rejected(self):
        self.fail_case(lambda r: r["epochs"][0]["evaluation"]["facts"][0].__setitem__(
            "ok", False), "forged ok")

    def test_duplicate_question_rejected(self):
        self.fail_case(lambda r: r["epochs"][0]["evaluation"]["facts"][1].__setitem__(
            "q", r["epochs"][0]["evaluation"]["facts"][0]["q"]), "question/order mismatch")

    def test_missing_epoch_rejected(self):
        self.fail_case(lambda r: r["epochs"].pop(), "missing epoch evaluations")

    def test_receipt_sha_mismatch_rejected(self):
        self.fail_case(lambda r: r["checkpoint_receipts"][0].__setitem__(
            "sha256", "f" * 64), "checkpoint source SHA mismatch")

    def test_forged_selection_rejected(self):
        self.fail_case(lambda r: r.__setitem__("selection", "NONE"), "selection flag mismatch")

    def test_wrong_evidence_level_or_negative_gate_rejected(self):
        self.fail_case(lambda r: r.__setitem__("evidence_level", "REDMI_NATIVE"), "evidence level")
        self.fail_case(lambda r: r["gates"].__setitem__("Body_JEPA", "PASS"), "negative gates")

    def test_partial_native_report_fails_closed(self):
        self.fail_case(lambda r: r.__setitem__("status", "TRAIN_FAILED"), "native evaluation incomplete")

    def test_missing_raw_answer_fails_closed(self):
        self.fail_case(lambda r: r["epochs"][0]["evaluation"]["facts"][0].pop("a"),
                       "missing raw answer")


if __name__ == "__main__":
    unittest.main()

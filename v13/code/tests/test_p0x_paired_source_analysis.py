"""Synthetic-only tests for preregistered P0X matched-pair analysis."""
from copy import deepcopy
import hashlib
import unittest

from scripts import p0x_independent_source_holdout as p0x
from scripts import p0x_paired_source_analysis as paired


def summary(details, arm):
    subset = [d for d in details if d.get("arm") == arm] if arm != "c3_only" else details
    counts = {"exact": 0, "wrong_committed": 0, "unknown": 0, "unparseable": 0}
    labels = {"A": 0, "B": 0, "NONE": 0, "UNKNOWN": 0, "UNPARSEABLE": 0}
    for row in subset:
        label, truth = row["parsed"], row["oracle"]
        labels[label] += 1
        key = ("exact" if label == truth else
               "wrong_committed" if label in ("A", "B", "NONE") else
               "unknown" if label == "UNKNOWN" else "unparseable")
        counts[key] += 1
    return counts, labels


def scores(exact_both=True):
    rows = [r for r in p0x.fixtures() if r["partition"] == "holdout"]
    base_details = []
    arms_details = []
    for row in rows:
        digest = hashlib.sha256(row["id"].encode()).hexdigest()
        base_details.append({"id_sha256": digest, "parsed": "NONE",
                             "oracle": row["oracle_action"]})
        for arm in ("b1_only", "b2_only", "both_exact", "shuffled"):
            label = row["oracle_action"] if arm == "both_exact" and exact_both else "NONE"
            arms_details.append({"id_sha256": digest, "arm": arm,
                                 "parsed": label, "oracle": row["oracle_action"]})
    gates = {"canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
             "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
             "lp3_status": "FAIL", "jepa_weight": 0,
             "redmi_measured": False, "whole_system_complete": False}
    base_count, base_labels = summary(base_details, "c3_only")
    base = dict(gates, schema="v13.p0x.c3_150_baseline.v1.score.v1",
                status="P0X_NATIVE_C3_ONLY_HEADROOM_DIAGNOSTIC_NO_GATE",
                rows=150, c3_native_calls=150, details=base_details,
                per_arm={"c3_only": base_count}, output_labels=base_labels)
    arms = dict(gates, schema="v13.p0x.c3_source_arms.v1.score.v1",
                status="P0X_NATIVE_SOURCE_ABLATION_DIAGNOSTIC_NO_GATE",
                rows=600, c3_native_calls=600, details=arms_details,
                per_arm={}, output_labels={})
    for arm in paired.ARMS:
        arms["per_arm"][arm], arms["output_labels"][arm] = summary(arms_details, arm)
    return base, arms


class PairedSoftware(unittest.TestCase):
    def test_perfect_both_vs_none_prior(self):
        base, arms = scores()
        result = paired.analyze(base, arms)
        self.assertEqual(result["both_exact_count"], 150)
        self.assertEqual(result["c3_only_count"], 50)
        self.assertEqual(result["comparisons"]["c3_only"]["wins"], 100)
        self.assertEqual(result["comparisons"]["c3_only"]["losses"], 0)
        self.assertGreater(result["comparisons"]["c3_only"]["bootstrap_ci_95"][0], 0)
        self.assertGreater(result["comparisons"]["c3_only"]["family_cluster_ci_95"][0], 0)
        self.assertEqual(len(set(paired.frozen_family_map().values())), 30)
        self.assertLess(result["comparisons"]["c3_only"]["holm_adjusted_p"], .001)
        self.assertFalse(result["canonical_gate_pass"])
        self.assertEqual(result, paired.analyze(base, arms))

    def test_no_effect_stays_null_not_gate(self):
        base, arms = scores(False)
        result = paired.analyze(base, arms)
        for arm in paired.CONTRASTS:
            contrast = result["comparisons"][arm]
            self.assertEqual(contrast["wins"], 0)
            self.assertEqual(contrast["losses"], 0)
            self.assertEqual(contrast["mcnemar_exact_p_two_sided"], 1.0)
            self.assertEqual(contrast["bootstrap_ci_95"], [0, 0])
            self.assertEqual(contrast["family_cluster_ci_95"], [0, 0])

    def test_duplicate_oracle_and_summary_tamper(self):
        base, arms = scores()
        corrupt = deepcopy(arms)
        corrupt["details"][4]["id_sha256"] = corrupt["details"][0]["id_sha256"]
        with self.assertRaisesRegex(ValueError, "ROW_SHAPE"):
            paired.analyze(base, corrupt)
        corrupt = deepcopy(arms)
        corrupt["details"][0]["oracle"] = "B" if corrupt["details"][0]["oracle"] != "B" else "A"
        with self.assertRaisesRegex(ValueError, "SCORE_SUMMARY|ARM_ORACLE_MATCH"):
            paired.analyze(base, corrupt)
        corrupt = deepcopy(arms)
        corrupt["per_arm"]["both_exact"]["exact"] = 149
        with self.assertRaisesRegex(ValueError, "SCORE_SUMMARY"):
            paired.analyze(base, corrupt)

    def test_negative_gate_and_missing_arm_rejected(self):
        base, arms = scores()
        base["canonical_gate_pass"] = True
        with self.assertRaisesRegex(ValueError, "NEGATIVE_GATES"):
            paired.analyze(base, arms)
        base, arms = scores()
        arms["details"] = [d for d in arms["details"] if d["arm"] != "shuffled"]
        with self.assertRaisesRegex(ValueError, "ARMS_COUNT"):
            paired.analyze(base, arms)

    def test_family_cluster_map_must_cover_all_rows(self):
        base, arms = scores()
        bad = paired.frozen_family_map()
        bad.pop(next(iter(bad)))
        with self.assertRaisesRegex(ValueError, "FAMILY_MATCH"):
            paired.analyze(base, arms, family_map=bad)

    def test_exact_mcnemar_and_holm(self):
        self.assertEqual(paired.mcnemar_exact(0, 0), 1.0)
        self.assertAlmostEqual(paired.mcnemar_exact(10, 0), 2 / 1024)
        result = paired.holm({"a": .01, "b": .02, "c": .5, "d": .9})
        self.assertAlmostEqual(result["a"], .04)
        self.assertAlmostEqual(result["b"], .06)
        self.assertEqual(result["d"], 1.0)


if __name__ == "__main__":
    unittest.main()

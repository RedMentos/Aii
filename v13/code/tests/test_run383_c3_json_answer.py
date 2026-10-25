"""Run383 source-only controls; native evidence requires separate pinned Actions."""
import copy
import unittest

from scripts import run382_c3_prompt_ablation_native as PRIOR
from scripts import run383_c3_json_answer_native as R
from v13.agi.solver import SYS, SCHEMA


RUN373_PROMPTS = {
    "Compute: 7 + 5 = ?", "Compute: 9 + 1 = ?",
    "Write backwards: dog", "Continue: 2, 4, 6, ?",
}


class Run383JSONAnswerControls(unittest.TestCase):
    def rows(self):
        result = []
        for index, (cat, prompt, expected) in enumerate(R.CASES):
            local = sum(c == cat for c, _, _ in R.CASES[:index])
            for arm in R.ARMS:
                cutoff = {
                    "baseline": {"arithmetic": 2, "backwards": 1, "sequence": 1},
                    "combined": {"arithmetic": 3, "backwards": 2, "sequence": 1},
                    "min_length": {"arithmetic": 2, "backwards": 1, "sequence": 1},
                    "explicit_json": {"arithmetic": 2, "backwards": 1, "sequence": 1},
                }[arm][cat]
                correct = local < cutoff
                result.append({
                    "index": index, "category": cat, "prompt": prompt,
                    "arm": arm, "correct_exact": correct, "empty": False,
                    "wrong_nonempty": not correct, "field_supported": True,
                    "status": "FINAL", "can_train_body": False,
                    "duration_s": 1.0 if arm == "baseline" else 1.2,
                })
        # Baseline: 4 correct, 4 empty, 4 wrong nonempty.
        # Combined: 6 correct, 2 empty, 4 wrong nonempty.
        for arm, target in (("baseline", 4), ("combined", 2)):
            changed = 0
            for row in result:
                if row["arm"] == arm and not row["correct_exact"] and changed < target:
                    row["empty"] = True
                    row["wrong_nonempty"] = False
                    row["field_supported"] = False
                    changed += 1
        return result

    def test_fresh_cases_and_unmodified_production_schema(self):
        old = RUN373_PROMPTS | {p for _, p, _ in PRIOR.CASES}
        self.assertEqual(len(R.CASES), 12)
        self.assertEqual(len({p for _, p, _ in R.CASES}), 12)
        self.assertFalse(old & {p for _, p, _ in R.CASES})
        self.assertEqual(SCHEMA, R.arm_config("baseline")[1])
        self.assertEqual(SYS, R.arm_config("min_length")[0])
        self.assertNotIn("minLength", SCHEMA["properties"]["answer"])
        self.assertEqual(R.arm_config("combined")[1]["properties"]["answer"]["minLength"], 1)
        copy_schema = copy.deepcopy(R.arm_config("combined")[1])
        copy_schema["properties"]["answer"]["minLength"] = 20
        self.assertEqual(R.arm_config("combined")[1]["properties"]["answer"]["minLength"], 1)

    def test_verdict_requires_correctness_not_just_nonempty(self):
        rows = self.rows()
        summary = R.summarize(rows)
        self.assertEqual(summary["exact_gain"], 2)
        self.assertEqual(summary["empty_reduction"], 2)
        self.assertTrue(R.supported(summary, rows, True, []))
        self.assertFalse(R.supported(summary, rows, False, []))
        self.assertFalse(R.supported(summary, rows, True, [123]))
        bad = [dict(x) for x in rows]
        next(x for x in bad if x["arm"] == "combined" and x["correct_exact"])["correct_exact"] = False
        self.assertFalse(R.supported(R.summarize(bad), bad, True, []))
        empty = [dict(x) for x in rows]
        for x in empty:
            if x["arm"] == "combined" and not x["correct_exact"] and not x["empty"]:
                x["empty"] = True
                x["wrong_nonempty"] = False
        self.assertFalse(R.supported(R.summarize(empty), empty, True, []))
        slow = [dict(x) for x in rows]
        for x in slow:
            if x["arm"] == "combined":
                x["duration_s"] = 1.6
        self.assertFalse(R.supported(R.summarize(slow), slow, True, []))


if __name__ == "__main__":
    unittest.main()

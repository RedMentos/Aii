"""Run382 source-only controls. Native evidence requires separate pinned Actions run."""
import unittest

from scripts import run382_c3_prompt_ablation_native as R
RUN373_PROMPTS = {"Compute: 7 + 5 = ?", "Compute: 9 + 1 = ?", "Write backwards: dog", "Continue: 2, 4, 6, ?"}


class Run382NativePromptControls(unittest.TestCase):
    def rows(self):
        out = []
        for index, (category, prompt, expected) in enumerate(R.CASES):
            for arm in R.ARMS:
                # Baseline: arithmetic 2, backwards 1, sequence 1 = 4.
                # Candidate: arithmetic 4, backwards 2, sequence 1 = 7.
                cutoff = {
                    "baseline": {"arithmetic": 2, "backwards": 1, "sequence": 1},
                    "candidate": {"arithmetic": 4, "backwards": 2, "sequence": 1},
                }[arm][category]
                local_index = sum(1 for cat, _, _ in R.CASES[:index] if cat == category)
                correct = local_index < cutoff
                out.append({
                    "index": index, "category": category, "prompt": prompt,
                    "expected": expected, "arm": arm,
                    "correct_exact": correct, "status": "FINAL",
                    "can_train_body": False, "field_supported": True,
                    "duration_s": 1.0 if arm == "baseline" else 1.2,
                })
        return out

    def test_fresh_registered_cases_do_not_repeat_run373(self):
        old = RUN373_PROMPTS
        self.assertEqual(len(R.CASES), 12)
        self.assertEqual(len({p for _, p, _ in R.CASES}), 12)
        self.assertFalse(old & {p for _, p, _ in R.CASES})
        self.assertEqual(
            {cat: sum(c == cat for c, _, _ in R.CASES)
             for cat in ("arithmetic", "backwards", "sequence")},
            {"arithmetic": 4, "backwards": 4, "sequence": 4},
        )

    def test_verdict_needs_gain_categories_confidence_latency_and_reaping(self):
        rows = self.rows()
        summary = R.summarize(rows)
        self.assertEqual(summary["gain"], 3)
        self.assertTrue(summary["category_no_regress"])
        self.assertTrue(R.supported(summary, rows, True, []))
        self.assertFalse(R.supported(summary, rows, False, []))
        self.assertFalse(R.supported(summary, rows, True, [123]))
        missing_field = [dict(r) for r in rows]
        missing_field[0]["field_supported"] = False
        self.assertFalse(R.supported(R.summarize(missing_field), missing_field, True, []))
        slow = [dict(r) for r in rows]
        for row in slow:
            if row["arm"] == "candidate":
                row["duration_s"] = 1.6
        self.assertFalse(R.supported(R.summarize(slow), slow, True, []))
        weak = [dict(r) for r in rows]
        next(r for r in weak if r["arm"] == "candidate" and r["correct_exact"])["correct_exact"] = False
        self.assertFalse(R.supported(R.summarize(weak), weak, True, []))


if __name__ == "__main__":
    unittest.main()

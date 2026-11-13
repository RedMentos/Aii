"""Whole-turn recovery policy using genuine-shaped, content-free Redmi metrics."""
import json
import unittest
from v13 import native_turn_budget as budget


def turn(status="DEADLINE", *, generated=0, phase="prefill", role="C3_LANGUAGE"):
    return {"status":status,"metadata":json.dumps({
        "runner":{"role":role,"generated_tokens":generated,
                  "last_phase":phase,"duration_s":29.1},
        "raw_user_prompt":"PRIVATE NEVER SELECT OR RETURN",
    })}


class DummyStore:
    def __init__(self, rows):
        self.proof = rows
        self.query = None
        self.args = None
    def rows(self, query, args):
        self.query = query
        self.args = args
        return self.proof


class NativeTurnBudgetTests(unittest.TestCase):
    def test_two_observed_c3_zero_token_deadlines_reserve_c3_time(self):
        rows=[turn(),turn(),turn("FINAL",generated=21,phase="stream")]
        d=budget.plan(100,130,104.2,recent=rows,background_enabled=True)
        self.assertTrue(d["recovery"])
        self.assertEqual(d["reason"],"RECENT_C3_ZERO_TOKEN_PREFILL_TIMEOUTS")
        self.assertLessEqual(d["preanswer_end_monotonic"],104)
        self.assertGreaterEqual(d["c3_reserved_seconds"],25)
        self.assertEqual(d["preanswer_seconds_available"],0)
        self.assertTrue(d["postcommit_body_eligible"])
        self.assertFalse(d["age_changed"])
        self.assertFalse(d["memory_or_native_weights_changed"])

    def test_one_failure_keeps_full_synchronous_cognitive_window(self):
        d=budget.plan(100,130,103.5,recent=[turn()])
        self.assertFalse(d["recovery"])
        self.assertAlmostEqual(d["preanswer_end_monotonic"],113.5)
        self.assertEqual(d["reason"],"NORMAL_COGNITIVE_PREANSWER")
        self.assertFalse(d["postcommit_body_eligible"])

    def test_longer_deep_turn_preserves_both_body_roles(self):
        d=budget.plan(100,190,104,recent=[turn(),turn(),turn()])
        self.assertFalse(d["recovery"])
        self.assertAlmostEqual(d["preanswer_end_monotonic"],140.5)

    def test_explicit_foreground_no_background_never_silently_defers(self):
        d=budget.plan(100,130,103.5,recent=[turn(),turn()],
                      background_enabled=False)
        self.assertFalse(d["recovery"])
        self.assertEqual(d["recent_real_prefill_failures"],2)

    def test_two_real_successes_reset_recovery(self):
        d=budget.plan(100,130,104,
            recent=[turn("FINAL",generated=6,phase="stream"),
                    turn("FINAL",generated=13,phase="stream"),
                    turn(),turn(),turn()])
        self.assertFalse(d["recovery"])
        self.assertEqual(d["recent_success_streak"],2)

    def test_untrusted_missing_data_is_not_a_phone_failure(self):
        bad=[
            turn("ERROR",generated=0),
            turn("DEADLINE",generated=1),
            turn("DEADLINE",phase="stream"),
            turn("DEADLINE",role="B1_DETAIL"),
            {"status":"DEADLINE","metadata":"PRIVATE MALFORMED JSON"},
            {"status":"DEADLINE","metadata":{"runner":{"role":"C3_LANGUAGE",
                 "generated_tokens":"0","last_phase":"prefill"}}},
        ]
        for row in bad:
            with self.subTest(row=row):
                self.assertFalse(budget.zero_token_prefill_failure(row))
        self.assertFalse(budget.plan(100,130,105,recent=bad)["recovery"])

    def test_direct_source_copy_never_changes_preanswer_budget(self):
        d=budget.plan(100,130,102,recent=[turn(),turn()],direct=True)
        self.assertFalse(d["recovery"])

    def test_recent_proof_selects_only_status_and_metadata(self):
        rows=[{"status":"DEADLINE","metadata":"{}","text":"PRIVATE NEVER EXPORT"}]
        store=DummyStore(rows)
        result=budget.recent_proof(store)
        self.assertEqual(result,[{"status":"DEADLINE","metadata":"{}"}])
        self.assertNotIn("text",store.query.lower())
        self.assertNotIn("PRIVATE",json.dumps(result))
        self.assertEqual(store.args,(budget.MAX_RECENT,))

    def test_bound_monotonic_inputs_and_conflicting_clock_rejected(self):
        with self.assertRaises(ValueError):
            budget.plan(100,float("nan"),102)
        with self.assertRaises(ValueError):
            budget.plan(100,99,100)


if __name__=="__main__":
    unittest.main()

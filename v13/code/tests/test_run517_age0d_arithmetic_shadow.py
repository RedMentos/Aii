"""Run517 WP-AGE0d: explicit answer-aware arithmetic, SHADOW only, no models."""
import tempfile
import unittest
from pathlib import Path

from v13 import answer_audit as A
from v13 import age as agectl
from v13 import neuromod as N
from v13 import selfmodel as S
from v13.runtime import Runtime


class PureArithmeticAudit(unittest.TestCase):
    def test_correct_and_incorrect_source_bound_subtraction(self):
        sources = ["Budget 117 euros. Cost 64 euros."]
        self.assertEqual(A.audit("CALC: 117 - 64 = 53", sources)["status"], "PASS")
        bad = A.audit("CALC: 117 - 64 = 52", sources)
        self.assertEqual(bad["status"], "CONTRADICTION")
        self.assertEqual(bad["mismatches"][0]["expected"], "53")
        self.assertEqual(bad["equations_checked"], 1)

    def test_exact_decimal_addition_and_multiplication(self):
        sources = ["Prices 0.1 and 0.2. Quantities 7 and 6."]
        self.assertEqual(A.audit("CALC: 0.1 + 0.2 = 0.3", sources)["status"], "PASS")
        self.assertEqual(A.audit("CALC: 7 * 6 = 42", sources)["status"], "PASS")
        self.assertEqual(A.audit("CALC: 7 * 6 = 43", sources)["status"], "CONTRADICTION")

    def test_no_marker_prose_question_echo_and_dates_abstain(self):
        source = ["Budget 117 euros. Cost 64 euros."]
        for answer in ("117 - 64 = 52", "What is 117 - 64?",
                       "The answer may be 52.", "2026-10-26",
                       "> CALC: 117 - 64 = 52"):
            with self.subTest(answer=answer):
                self.assertEqual(A.audit(answer, source)["status"],
                                 "ABSTAIN_NO_EXPLICIT_CALC")

    def test_unbound_operands_and_missing_source_abstain(self):
        self.assertEqual(A.audit("CALC: 117 - 64 = 52", [])["status"],
                         "ABSTAIN_NO_VERIFIED_SOURCE")
        self.assertEqual(A.audit("CALC: 117 - 64 = 52", ["Budget 117."])["status"],
                         "ABSTAIN_UNBOUND_OPERANDS")
        self.assertEqual(A.audit("CALC: 117 - 64 = 52", ["1170 and 64."])["status"],
                         "ABSTAIN_UNBOUND_OPERANDS")

    def test_bounds_nonfinite_and_ambiguous_expressions_abstain(self):
        self.assertEqual(A.audit("CALC: 1e309 + 2 = 3", ["1e309 2"])["status"],
                         "ABSTAIN_NO_EXPLICIT_CALC")
        self.assertEqual(A.audit("CALC: 1 / 3 = 0.33", ["1 3"])["status"],
                         "ABSTAIN_NO_EXPLICIT_CALC")
        self.assertEqual(A.audit("x" * 9000, ["1 2"])["status"], "ABSTAIN_LIMIT")
        self.assertEqual(A.audit("CALC: 1 + 2 = 3", ["x" * 17000])["status"],
                         "ABSTAIN_LIMIT")
        self.assertEqual(A.audit("CALC: 1 + 2 = 3", [None])["status"],
                         "ABSTAIN_INVALID_INPUT")
        self.assertEqual(A.audit("CALC: 1 + 2 = 3\n" * 4, ["1 2"])["status"],
                         "ABSTAIN_LIMIT")


class LateOfferShadowIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.r = Runtime(Path(self.tmp.name))
        self.addCleanup(self.r.close)
        self.system = S.SelfSystem(self.r, agectl.controller(self.r),
                                   N.Neuromod(self.r.store),
                                   clock=lambda: 1000.)
        event = self.r.store.event(self.r.session,
                                   "Budget 117 euros. Cost 64 euros.")
        self.offer = {
            "role": "B2_GIST",
            "offer": {"summary": "", "needs_reentry": False},
            "evidence_refs": [event["source_ref"]],
        }

    def ring(self):
        return self.r.store.state(S.ARITH_SHADOW_KEY, [])[0]

    def test_wrong_explicit_math_logged_even_when_old_heuristic_does_not_fire(self):
        self.assertEqual(self.system.correction_mode(), "shadow")
        result = self.system.late_offer("e1", self.offer, "CALC: 117 - 64 = 52")
        self.assertIsNone(result)
        rows = self.ring()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "CONTRADICTION_SHADOW_ONLY")
        self.assertFalse(rows[0]["user_notified"])
        self.assertEqual(rows[0]["mismatches"][0]["expected"], "53")
        self.assertEqual(self.r.store.state(S.SHADOW_KEY, [])[0], [])

    def test_correct_math_does_not_log(self):
        self.system.late_offer("e1", self.offer, "CALC: 117 - 64 = 53")
        self.assertEqual(self.ring(), [])

    def test_duplicate_late_offer_deduplicates(self):
        for _ in range(3):
            self.system.late_offer("e1", self.offer, "CALC: 117 - 64 = 52")
        self.assertEqual(len(self.ring()), 1)

    def test_forged_ref_abstains_without_user_delivery(self):
        self.offer["evidence_refs"][0] = dict(
            self.offer["evidence_refs"][0], sha256="0" * 64)
        said = []
        self.r.notice = said.append
        self.system.late_offer("e1", self.offer, "CALC: 117 - 64 = 52")
        self.assertEqual(self.ring(), [])
        self.assertEqual(said, [])

    def test_off_and_deliver_do_not_enable_new_diagnostic(self):
        said = []
        self.r.notice = said.append
        for mode in ("off", "deliver"):
            self.system.set_correction_mode(mode)
            self.system.late_offer(mode, self.offer, "CALC: 117 - 64 = 52")
        self.assertEqual(self.ring(), [])
        self.assertEqual(said, [])


if __name__ == "__main__":
    unittest.main()

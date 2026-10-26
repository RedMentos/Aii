"""Run495 preregistered actual Runtime quote-crowding and fail-closed bound tests."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13.runtime import Runtime
from v13.toolstep import ToolStep
from v13.agi import hub, eligibility as E

CURRENT = "Project Delta. Decide between Option A and Option B using the earlier rules."
USER_RULE = "Budget 50 euros. Deadline 5 days. Local-only requirement: true."
STALE_QUOTE = "Budget 140 euros. Deadline 9 days. Local-only requirement: false."
OPTIONS = ("Option A: cost 60 euros, duration 4 days, local true. "
           "Option B: cost 90 euros, duration 3 days, local true.")
FILLERS = ["Verified source note %d about supplier documentation." % i for i in range(4)]


class RuntimeEvidenceOverflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.cfg["eligibility_reader"] = "fixed"
        self.r.sleep.cycle.set_policy("enabled", "off")
        hub(self.r).tools.enable("eligibility")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def context(self, quotes):
        rows = [{"role": "user", "text": USER_RULE}]
        analysts = [{"role": "B1_DETAIL", "verified_quotes": [{"text": q} for q in quotes],
                     "hypothesis": {"summary": "Budget 999 euros."}}]
        return patch("v13.history.native_history", return_value=(rows, [])), \
               patch.object(self.r.cognition, "analyst_context", return_value=analysts), \
               patch.object(self.r.pool, "get", side_effect=AssertionError("MODEL_READ_FORBIDDEN"))

    def test_six_quotes_cannot_evict_direct_user_history_and_choose_stale(self):
        # Seven unique sources: 1 direct user + 6 verified body quotes.
        quotes = [OPTIONS, STALE_QUOTE, *FILLERS]
        self.assertEqual(len(quotes), 6)
        e = self.r.store.event(self.r.session, CURRENT)
        with self.context(quotes)[0], self.context(quotes)[1], self.context(quotes)[2]:
            proposal = ToolStep(self.r).plan(e, CURRENT, offers=[{"offer_id": "B1"}], version=1)
        self.assertIsNone(proposal, "overflow must refuse before quote truncation or model fallback")
        row = self.r.store.one("SELECT id FROM telemetry WHERE kind='tool_step_unavailable' ORDER BY id DESC LIMIT 1")
        self.assertIsNotNone(row)

    def test_at_six_source_bound_preserves_newest_direct_user_rule(self):
        quotes = [OPTIONS, STALE_QUOTE, *FILLERS[:3]]
        self.assertEqual(len(quotes), 5)
        e = self.r.store.event(self.r.session, CURRENT)
        h,q,c3 = self.context(quotes)
        with h,q,c3:
            ts = ToolStep(self.r)
            hist,verified = ts.earlier_parts(e,offers=[{"offer_id": "B1"}],version=1)
            self.assertEqual(hist, [USER_RULE])
            self.assertEqual(len(verified), 5)
            proposal = ts.plan(e, CURRENT, offers=[{"offer_id": "B1"}], version=1)
        self.assertIsNotNone(proposal)
        self.assertEqual(proposal["args"]["budget"], 50)
        self.assertEqual(ts.shadow(e, proposal)["result"]["action"], "NONE")

    def test_bounded_source_list_no_silent_history_loss(self):
        quotes = [OPTIONS, STALE_QUOTE, *FILLERS]
        e = self.r.store.event(self.r.session, CURRENT)
        h,q,c3 = self.context(quotes)
        with h,q,c3:
            with self.assertRaisesRegex(ValueError, "ELIG_SOURCE_OVERFLOW"):
                ToolStep(self.r).earlier_parts(e,offers=[{"offer_id": "B1"}],version=1)

    def test_without_earlier_evidence_current_rules_remain_usable(self):
        current = CURRENT + " Budget 50 euros. Deadline 5 days. Local-only requirement: true. " + OPTIONS
        e = self.r.store.event(self.r.session, current)
        with patch.object(self.r.pool, "get", side_effect=AssertionError("MODEL_READ_FORBIDDEN")):
            p = ToolStep(self.r).plan(e, current)
        self.assertEqual(p["args"]["budget"], 50)
        self.assertEqual(ToolStep(self.r).shadow(e, p)["result"]["action"], "NONE")


if __name__ == "__main__":
    unittest.main()

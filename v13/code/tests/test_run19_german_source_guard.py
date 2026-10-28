"""Run19 RED-first adversarial review of Run17 German SHADOW source authority."""
import hashlib
import unittest

from scripts import run15_step2_disjoint_bilingual_fixtures as cohort
from scripts import run17_german_typed_shadow as shadow
from tests.test_run17_german_typed_shadow import make_sources, evaluate, mutate


def case(kind):
    return next(x for x in cohort.FIXTURES if x["language"] == "DE" and x["type"] == kind)


def sheet(rows, args):
    ref = "run19:%s:stale-sheet" % args[0]
    text = ("Projekt %s Lieferantenblatt Revision 1. "
            "Option A: Kosten 2 Euro, Dauer 1 Tage, lokal ja. "
            "Option B: Kosten 3 Euro, Dauer 1 Tage, lokal ja.") % args[0]
    rows[ref] = {"ref": ref, "text": text,
                 "sha256": hashlib.sha256(text.encode()).hexdigest(),
                 "project": args[0], "session": "run17-session",
                 "kind": "history", "verified": True, "active": True,
                 "seq": 2}
    return ref


class SourceGuardAdversarial(unittest.TestCase):
    def test_mixed_english_project_in_german_sheet_refuses(self):
        rows, args = make_sources(case("SPLIT"))
        mutate(rows, args[3], rows[args[3]]["text"] + " Project Quasar archival notes.")
        with self.assertRaises(shadow.Refusal):
            evaluate(rows, args)

    def test_current_exact_options_override_stale_historical_sheet(self):
        rows, args = make_sources(case("RULE"))
        stale = sheet(rows, args)
        with self.assertRaises(shadow.Refusal):
            evaluate(rows, (*args[:3], stale, args[4]))

    def test_partial_current_option_cannot_fall_back_to_old_sheet(self):
        rows, args = make_sources(case("RULE"))
        mutate(rows, args[1], rows[args[1]]["text"].replace(
            "Option A: Kosten", "Option A: Preis"))
        stale = sheet(rows, args)
        with self.assertRaises(shadow.Refusal):
            evaluate(rows, (*args[:3], stale, args[4]))

    def test_future_old_note_or_future_sheet_refuses(self):
        rows, args = make_sources(case("SPLIT"))
        rows[args[1]]["seq"] = 3
        rows[args[2]]["seq"] = 4
        rows[args[3]]["seq"] = 2
        with self.assertRaises(shadow.Refusal):
            evaluate(rows, args)
        rows, args = make_sources(case("SPLIT"))
        rows[args[1]]["seq"] = 3
        rows[args[2]]["seq"] = 0
        rows[args[3]]["seq"] = 5
        with self.assertRaises(shadow.Refusal):
            evaluate(rows, args)

    def test_missing_or_boolean_event_sequence_refuses(self):
        rows, args = make_sources(case("SPLIT"))
        rows[args[2]].pop("seq", None)
        with self.assertRaises(shadow.Refusal):
            evaluate(rows, args)
        rows, args = make_sources(case("SPLIT"))
        rows[args[2]]["seq"] = True
        with self.assertRaises(shadow.Refusal):
            evaluate(rows, args)

    def test_good_monotonic_source_sequence_still_works(self):
        for kind in ("SPLIT", "RULE", "REVISION"):
            x = case(kind)
            rows, args = make_sources(x)
            with self.subTest(kind=kind):
                result = evaluate(rows, args)
                self.assertEqual(result["action"], x["oracle"]["action"])
                self.assertFalse(result["authority"])


if __name__ == "__main__":
    unittest.main()

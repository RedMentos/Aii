"""Run17 preregistered source/temporal adversarial tests; no native calls."""
import copy
import hashlib
import unittest

from scripts import run15_step2_disjoint_bilingual_fixtures as cohort
from scripts import run17_german_typed_shadow as shadow
from v13.agi import eligibility


def make_sources(case):
    name = case["id"]
    current = "run17:%s:current" % name
    old = "run17:%s:old" % name
    options = current if case["type"] == "RULE" else "run17:%s:sheet" % name
    rows = {}
    def add(ref, text, kind, seq):
        rows[ref] = {"ref": ref, "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest(),
                     "project": name, "session": "run17-session", "kind": kind, "seq": seq,
                     "verified": True, "active": True}
    add(current, case["current"], "current", 3)
    add(old, case["history"][0], "history", 0)
    if options != current:
        add(options, case["history"][2], "history", 2)
    return rows, (name, current, old, options, case["temporal_mode"])


def evaluate(rows, args):
    return shadow.evaluate(*args, source_reader=lambda ref: rows[ref])


def mutate(rows, ref, text):
    rows[ref]["text"] = text
    rows[ref]["sha256"] = hashlib.sha256(text.encode()).hexdigest()


class GermanShadow(unittest.TestCase):
    def setUp(self):
        self.cases = [x for x in cohort.FIXTURES if x["language"] == "DE"]
        self.assertEqual({x["type"] for x in self.cases}, {"SPLIT", "RULE", "REVISION"})

    def test_fresh_three_cases_exact_oracle_without_oracle_as_input(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                rows, args = make_sources(case)
                result = evaluate(rows, args)
                self.assertEqual(result["action"], case["oracle"]["action"])
                self.assertEqual(result["options"], case["oracle"]["options"])
                self.assertEqual(result["rules"], case["rules"])
                self.assertEqual(result["status"], "SHADOW_ONLY")
                self.assertFalse(result["authority"])
                self.assertEqual(result["evidence_level"], "software_source_only")
                self.assertNotIn("oracle", result)
                self.assertNotIn("history", result)
                self.assertNotIn("text", result)

    def test_independent_english_reader_unchanged_and_german_negative(self):
        for case in self.cases:
            source = case["current"] if case["type"] == "REVISION" else case["history"][0]
            self.assertFalse(eligibility.stated("deadline", case["rules"]["deadline"], source))
            self.assertFalse(eligibility.stated("local_only", case["rules"]["local_only"], source))
        self.assertEqual(shadow.REVISION, "run17-de-typed-shadow-v1")

    def test_reject_revoked_unverified_corrupt_or_unavailable_source(self):
        rows, args = make_sources(self.cases[0])
        for field, value in (("active", False), ("verified", False), ("sha256", "0"*64),
                             ("session", "other-session"), ("project", "Quasar"),
                             ("kind", "current")):
            bad = copy.deepcopy(rows)
            bad[args[2]][field] = value
            with self.subTest(field=field), self.assertRaises(shadow.Refusal):
                evaluate(bad, args)
        with self.assertRaises(shadow.Refusal):
            shadow.evaluate(*args, source_reader=lambda ref: rows[ref] if ref != args[2] else None)
        with self.assertRaises(shadow.Refusal):
            shadow.evaluate(*args, source_reader=None)

    def test_reject_project_distractor_and_cross_project_source(self):
        rows, args = make_sources(self.cases[0])
        mutate(rows, args[3], "Projekt Quasar Lieferantenblatt. " + rows[args[3]]["text"])
        with self.assertRaises(shadow.Refusal): evaluate(rows, args)
        rows, args = make_sources(self.cases[0])
        mutate(rows, args[2], rows[args[2]]["text"].replace("Nerava", "Orenda"))
        with self.assertRaises(shadow.Refusal): evaluate(rows, args)

    def test_reject_ambiguous_rule_and_out_of_window(self):
        case = next(x for x in self.cases if x["type"] == "SPLIT")
        rows, args = make_sources(case)
        mutate(rows, args[2], rows[args[2]]["text"] + " Budget 999 Euro.")
        with self.assertRaises(shadow.Refusal): evaluate(rows, args)
        rows, args = make_sources(case)
        mutate(rows, args[2], "Projekt Nerava Auftaktnotiz: " + "x "*150 + rows[args[2]]["text"])
        with self.assertRaises(shadow.Refusal): evaluate(rows, args)
        rows, args = make_sources(case)
        mutate(rows, args[2], rows[args[2]]["text"].replace("Frist 13 Tage", "Termin 13 Tage"))
        with self.assertRaises(shadow.Refusal): evaluate(rows, args)

    def test_reject_option_duplicate_missing_or_foreign_origin(self):
        case = next(x for x in self.cases if x["type"] == "SPLIT")
        rows, args = make_sources(case)
        mutate(rows, args[3], rows[args[3]]["text"] + " Option A: Kosten 1 Euro, Dauer 1 Tage, lokal ja.")
        with self.assertRaises(shadow.Refusal): evaluate(rows, args)
        rows, args = make_sources(case)
        mutate(rows, args[3], rows[args[3]]["text"].replace("Dauer 12 Tage", "Lieferung 12 Tage"))
        with self.assertRaises(shadow.Refusal): evaluate(rows, args)
        rows, args = make_sources(case)
        rows[args[3]]["kind"] = "current"
        with self.assertRaises(shadow.Refusal): evaluate(rows, args)

    def test_temporal_override_refuses_stale_or_mislabelled_rules(self):
        prior = next(x for x in self.cases if x["type"] == "RULE")
        revised = next(x for x in self.cases if x["type"] == "REVISION")
        rows, args = make_sources(prior)
        mutate(rows, args[1], rows[args[1]]["text"] + " Aktuelle verbindliche Regeln: Budget 1 Euro.")
        with self.assertRaises(shadow.Refusal): evaluate(rows, args)
        rows, args = make_sources(revised)
        wrong = (*args[:4], "RETAIN_PRIOR_RULES")
        with self.assertRaises(shadow.Refusal): evaluate(rows, wrong)
        rows, args = make_sources(revised)
        mutate(rows, args[1], rows[args[1]]["text"].replace("vollständig ersetzt", "teilweise ersetzt"))
        with self.assertRaises(shadow.Refusal): evaluate(rows, args)
        rows, args = make_sources(revised)
        mutate(rows, args[1], rows[args[1]]["text"] + " Frist 99 Tage.")
        with self.assertRaises(shadow.Refusal): evaluate(rows, args)

    def test_reject_ref_collision_unsupported_mode_and_no_source_callback(self):
        rows, args = make_sources(self.cases[0])
        with self.assertRaises(shadow.Refusal):
            shadow.evaluate(args[0], args[1], args[1], args[3], args[4], rows.get)
        with self.assertRaises(shadow.Refusal):
            shadow.evaluate(args[0], args[1], args[2], args[3], "UNKNOWN", rows.get)
        with self.assertRaises(shadow.Refusal):
            shadow.evaluate(args[0], "bad ref!", args[2], args[3], args[4], rows.get)


if __name__ == "__main__":
    unittest.main()

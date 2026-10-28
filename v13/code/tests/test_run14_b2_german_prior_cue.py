"""Run14 RED-first synthetic German earlier-rule source pointer tests."""
import hashlib
import unittest

from scripts import run13_b2_identity_ambiguity_guard as guard
from scripts import run14_b2_german_prior_cue as candidate

CURRENT_DE = "Projekt Aquila. Verwende die früheren Regeln und das aktuelle Lieferantenblatt."
CURRENT_EN = "Project Aquila. Use the earlier rules and latest supplier sheet."
OLD = "Projekt Aquila alte verbindliche Regeln. Budget 134 Euro. Frist 9 Tage. Lokalpflicht ja."
SHEET = ("Projekt Aquila aktuelles Lieferantenblatt. Option A 91 Euro, 7 Tage, lokal. "
         "Option B 105 Euro, 8 Tage, nicht lokal. Wiederholung der Lieferantenangaben. " * 2)
MIXED = "Projekt Aquila und Projekt Atlas Vergleich. Budget 999 Euro. Frist 1 Tag. Lokalpflicht nein."


def offer(text, n, **kw):
    r = {"source_id": "src_" + str(n), "sha256": hashlib.sha256(text.encode()).hexdigest(),
         "char_start": 0, "char_end": len(text), "modality": "text"}
    x = {"role": "B2_GIST", "offer_id": "pkt_" + str(n), "event_id": "event_" + str(n),
         "session": "s", "generation": "g", "model_revision": "m",
         "source_ref": r, "hypothesis": "H" * 120}
    x.update(kw)
    return x


def reader(items, texts, revoked=()):
    table = {x["source_ref"]["source_id"]: t for x, t in zip(items, texts)}
    def read(ref):
        if ref["source_id"] in revoked: raise ValueError("TOMBSTONED")
        t = table[ref["source_id"]]
        if hashlib.sha256(t.encode()).hexdigest() != ref["sha256"]:
            raise ValueError("HASH_CHANGED")
        return t[ref["char_start"]:ref["char_end"]]
    return read


def select(module, current, items, texts, **kw):
    return module.select_context(current, "current", "s", "g", "m",
                                 items, reader(items, texts), **kw)


class GermanPriorTests(unittest.TestCase):
    def test_original_german_source_order_is_wrong_under_cap(self):
        items = [offer(SHEET, 2), offer(OLD, 1)]
        x = select(guard, CURRENT_DE, items, [SHEET, OLD], cap=450, slots=2)
        self.assertEqual([a["source_ref"]["source_id"] for a in x["items"]], ["src_2"])

    def test_german_prior_rule_note_selected_under_same_cap(self):
        items = [offer(SHEET, 2), offer(OLD, 1)]
        x = select(candidate, CURRENT_DE, items, [SHEET, OLD], cap=450, slots=2)
        self.assertEqual([a["source_ref"]["source_id"] for a in x["items"]], ["src_1"])
        self.assertEqual(x["authority"], "SOURCE_POINTER_ONLY")
        self.assertFalse(x["canonical_gate_pass"])

    def test_english_existing_priority_unchanged(self):
        items = [offer(SHEET, 2), offer(OLD, 1)]
        x = select(candidate, CURRENT_EN, items, [SHEET, OLD], cap=450, slots=2)
        self.assertEqual([a["source_ref"]["source_id"] for a in x["items"]], ["src_1"])

    def test_current_revised_rules_not_displaced(self):
        items = [offer(SHEET, 2), offer(OLD, 1)]
        q = CURRENT_DE + " Die aktuellen verbindlichen Regeln sind neu: Budget 100 Euro, Frist 5 Tage, Lokalpflicht nein."
        x = select(candidate, q, items, [SHEET, OLD], cap=450, slots=2)
        self.assertEqual([a["source_ref"]["source_id"] for a in x["items"]], ["src_2"])

    def test_german_no_prior_rule_request_keeps_newest(self):
        items = [offer(SHEET, 2), offer(OLD, 1)]
        q = "Projekt Aquila. Verwende das aktuelle Lieferantenblatt."
        x = select(candidate, q, items, [SHEET, OLD], cap=450, slots=2)
        self.assertEqual([a["source_ref"]["source_id"] for a in x["items"]], ["src_2"])

    def test_multi_project_request_refused(self):
        items = [offer(OLD, 1)]
        q = CURRENT_DE + " Vergleiche auch Projekt Atlas."
        x = select(candidate, q, items, [OLD])
        self.assertEqual(x["items"], [])
        self.assertFalse(x["canonical_gate_pass"])

    def test_mixed_source_refused(self):
        items = [offer(MIXED, 2), offer(OLD, 1)]
        x = select(candidate, CURRENT_DE, items, [MIXED, OLD], cap=450, slots=2)
        self.assertEqual([a["source_ref"]["source_id"] for a in x["items"]], ["src_1"])

    def test_no_horizon_expansion_after_invalid_recent(self):
        items = [offer(MIXED, 3), offer(SHEET, 2), offer(OLD, 1)]
        x = select(candidate, CURRENT_DE, items, [MIXED, SHEET, OLD], cap=450, slots=2)
        self.assertNotIn("src_1", [a["source_ref"]["source_id"] for a in x["items"]])

    def test_tombstone_refused_and_wrong_model_not_read(self):
        item = offer(OLD, 1)
        gone = candidate.select_context(CURRENT_DE, "current", "s", "g", "m",
                                        [item], reader([item], [OLD], revoked={"src_1"}))
        self.assertEqual(gone["items"], [])
        wrong = offer(OLD, 1, model_revision="other")
        def no_read(ref): raise AssertionError("wrong-model source read")
        x = candidate.select_context(CURRENT_DE, "current", "s", "g", "m", [wrong], no_read)
        self.assertEqual(x["items"], [])

    def test_invalid_digest_not_read(self):
        item = offer(OLD, 1)
        item["source_ref"]["sha256"] = "invalid"
        def no_read(ref): raise AssertionError("invalid ref reached reader")
        x = candidate.select_context(CURRENT_DE, "current", "s", "g", "m", [item], no_read)
        self.assertEqual(x["items"], [])


if __name__ == "__main__":
    unittest.main()

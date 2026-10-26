"""Run512: adversarial complete source-slot provenance, no native inference."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run509_b2_rule_quote_prereg as frozen
import run511_b2_offer_collector as collector


class FakeStore:
    def __init__(self, texts):
        self.texts = texts

    def read_source(self, ref):
        return self.texts[ref["source_id"]]


def fixture_bindings():
    fixture = frozen.fixtures()[0]
    originals = list(fixture["history"]) + [fixture["current"]]
    refs = [{
        "source_id": f"source-{index}",
        "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
        "char_start": 0, "char_end": len(value), "modality": "text",
    } for index, value in enumerate(originals)]
    prep = {"prior_events": [{"source_ref": copy.deepcopy(ref)}
                             for ref in refs[:3]]}
    event = {"source_ref": copy.deepcopy(refs[3])}
    store = FakeStore({ref["source_id"]: value
                       for ref, value in zip(refs, originals)})
    return fixture, prep, event, store


class Run512SourceBindings(unittest.TestCase):
    def test_four_exact_slots_are_independently_replayable(self):
        fixture, prep, event, store = fixture_bindings()
        records, mapping = collector.verified_source_slots(
            store, prep, event, fixture)
        self.assertEqual([r["source_slot"] for r in records],
                         ["history0", "history1", "history2", "current"])
        self.assertEqual([r["source_text"] for r in records],
                         fixture["history"] + [fixture["current"]])
        self.assertEqual([r["source_id"] for r in records],
                         [f"source-{i}" for i in range(4)])
        self.assertEqual(len(mapping), 4)
        for record in records:
            self.assertEqual(
                hashlib.sha256(record["source_text"].encode()).hexdigest(),
                record["source_sha256"])
            self.assertEqual(record["char_start"], 0)
            self.assertEqual(record["char_end"], len(record["source_text"]))
            self.assertEqual(mapping[record["source_id"]], record["source_slot"])

    def test_full_slot_sha_mismatch_is_refused_even_without_quote(self):
        fixture, prep, event, store = fixture_bindings()
        prep["prior_events"][1]["source_ref"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_SLOT_REF_DRIFT"):
            collector.verified_source_slots(store, prep, event, fixture)

    def test_full_slot_truncated_range_is_refused(self):
        fixture, prep, event, store = fixture_bindings()
        event["source_ref"]["char_end"] -= 1
        with self.assertRaisesRegex(ValueError, "SOURCE_SLOT_REF_DRIFT"):
            collector.verified_source_slots(store, prep, event, fixture)

    def test_wrong_modality_and_boolean_range_are_refused(self):
        for field, value in (("modality", "image"),
                             ("char_start", False), ("char_end", True)):
            with self.subTest(field=field):
                fixture, prep, event, store = fixture_bindings()
                event["source_ref"][field] = value
                with self.assertRaisesRegex(ValueError, "SOURCE_SLOT_REF_DRIFT"):
                    collector.verified_source_slots(store, prep, event, fixture)

    def test_swapped_store_text_is_refused_even_if_sha_fields_look_valid(self):
        fixture, prep, event, store = fixture_bindings()
        store.texts["source-2"] = fixture["history"][1]
        with self.assertRaisesRegex(ValueError, "SOURCE_SLOT_TEXT_DRIFT"):
            collector.verified_source_slots(store, prep, event, fixture)

    def test_duplicate_and_empty_source_ids_are_refused(self):
        for value in ("source-0", ""):
            with self.subTest(source_id=value):
                fixture, prep, event, store = fixture_bindings()
                event["source_ref"]["source_id"] = value
                with self.assertRaisesRegex(ValueError, "SOURCE_ID_COLLISION"):
                    collector.verified_source_slots(store, prep, event, fixture)

    def test_unaltered_run511_plan_and_gates(self):
        plan = collector.plan(0)
        self.assertEqual(plan["expected_observations"], 12)
        self.assertFalse(plan["native_executed"])
        self.assertFalse(plan["canonical_gate_pass"])
        self.assertEqual(plan["step2_exit"], "UTILITY_FAIL")
        self.assertEqual(plan["b3_l1"], "FAIL")
        self.assertEqual(plan["body_jepa"], "UNAVAILABLE")
        self.assertEqual(plan["jepa_weight"], 0)
        self.assertFalse(plan["redmi_measured"])


if __name__ == "__main__":
    unittest.main()

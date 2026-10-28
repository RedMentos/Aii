"""Run23 RED-first: actual Store→typed German SHADOW integration, balanced cases."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run18_step2_balanced_controls as balanced
from scripts import run21_event_source_adapter_shadow as adapter
from scripts import run23_store_typed_bridge_shadow as bridge
from v13.config import initialize
from v13.store import Store


def inputs(case):
    return {k: case[k] for k in ("id", "language", "type",
                                  "history", "current", "temporal_mode")}


class RealStoreTypedBridge(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        home = Path(self.temp.name)
        initialize(home)
        self.store = Store(home)
        self.session = self.store.new_session()

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def setup_case(self, case):
        old = self.store.event(self.session, case["history"][0])
        sheet = self.store.event(self.session, case["history"][2])
        current = self.store.event(self.session, case["current"])
        return {"old": old["event_id"], "sheet": sheet["event_id"],
                "current": current["event_id"]}

    def evaluate(self, case, refs, option_role=None):
        return bridge.evaluate(
            self.store, self.session, case["id"], refs,
            case["temporal_mode"],
            option_role or ("current" if case["type"] == "RULE" else "sheet"))

    def test_three_disjoint_de_cases_have_balanced_actions_from_store(self):
        seen = []
        for case in balanced.FIXTURES:
            if case["language"] != "DE":
                continue
            with self.subTest(case=case["id"]):
                refs = self.setup_case(case)
                result = self.evaluate(inputs(case), refs)
                self.assertEqual(result["action"], case["oracle"]["action"])
                self.assertFalse(result["authority"])
                self.assertEqual(result["status"], "SHADOW_ONLY")
                self.assertEqual(result["verification_scope"],
                                 "EVENT_SOURCE_INTEGRITY_ONLY")
                self.assertEqual(set(result["source_hashes"]),
                                 {"old", "current", "options"})
                seen.append(result["action"])
        self.assertEqual(set(seen), {"A", "B", "NONE"})

    def test_refuse_revocation_after_evaluation_before_return(self):
        case = next(x for x in balanced.FIXTURES if x["id"] == "Veldora")
        refs = self.setup_case(case)
        old_src = json.loads(self.store.one(
            "SELECT packet FROM events WHERE id=?", (refs["old"],)
        )["packet"])["source_ref"]["source_id"]
        original = adapter.EventSourceReader.revalidate
        called = []
        def revoke(reader, ref, expected):
            if not called:
                called.append(True)
                with self.store.tx() as db:
                    db.execute("UPDATE sources SET deleted=1 WHERE id=?", (old_src,))
            return original(reader, ref, expected)
        with patch.object(adapter.EventSourceReader, "revalidate", revoke):
            with self.assertRaises((adapter.Refusal, bridge.Refusal)):
                self.evaluate(case, refs)

    def test_refuse_forged_generation_and_cross_session(self):
        case = next(x for x in balanced.FIXTURES if x["id"] == "Wynora")
        refs = self.setup_case(case)
        original = self.store.one(
            "SELECT packet FROM events WHERE id=?", (refs["current"],)
        )["packet"]
        p = json.loads(original)
        p["brain_generation_id"] = "gen_forged"
        with self.store.tx() as db:
            db.execute("UPDATE events SET packet=? WHERE id=?",
                       (json.dumps(p), refs["current"]))
        with self.assertRaises((adapter.Refusal, bridge.Refusal)):
            self.evaluate(case, refs)
        with self.store.tx() as db:
            db.execute("UPDATE events SET packet=? WHERE id=?",
                       (original, refs["current"]))
        other = self.store.new_session()
        foreign = self.store.event(other, case["history"][2])
        with self.assertRaises((adapter.Refusal, bridge.Refusal)):
            self.evaluate(case, dict(refs, sheet=foreign["event_id"]))

    def test_refuse_stale_sheet_when_current_contains_exact_options(self):
        case = next(x for x in balanced.FIXTURES if x["id"] == "Wynora")
        refs = self.setup_case(case)
        with self.assertRaises((adapter.Refusal, bridge.Refusal)):
            self.evaluate(case, refs, option_role="sheet")

    def test_refuse_wrong_project_and_source_order(self):
        case = next(x for x in balanced.FIXTURES if x["id"] == "Veldora")
        refs = self.setup_case(case)
        foreign = self.store.event(self.session,
            "Projekt Quasar Lieferantenblatt. Option A: Kosten 1 Euro.")
        with self.assertRaises((adapter.Refusal, bridge.Refusal)):
            self.evaluate(case, dict(refs, sheet=foreign["event_id"]))
        with self.assertRaises((adapter.Refusal, bridge.Refusal)):
            self.evaluate(case, dict(refs, old=refs["sheet"], sheet=refs["old"]))


if __name__ == "__main__":
    unittest.main()

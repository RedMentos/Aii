"""Run27 adversarial review of the real Store→German typed SHADOW bridge."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run18_step2_balanced_controls as balanced
from scripts import run23_store_typed_bridge_shadow as bridge
from scripts import run17_german_typed_shadow as german
from v13.config import initialize
from v13.store import Store


class StoreTypedBridgeReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        home = Path(self.temp.name)
        initialize(home)
        self.store = Store(home)
        self.session = self.store.new_session()
        self.case = next(x for x in balanced.FIXTURES if x["id"] == "Veldora")
        events = [
            self.store.event(self.session, self.case["history"][0]),
            self.store.event(self.session, self.case["history"][2]),
            self.store.event(self.session, self.case["current"]),
        ]
        self.refs = dict(zip(("old", "sheet", "current"),
                             (x["event_id"] for x in events)))
        self.source_id = events[0]["source_ref"]["source_id"]

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def evaluate(self, refs=None, temporal=None, option_role="sheet"):
        return bridge.evaluate(
            self.store, self.session, self.case["id"],
            refs if refs is not None else self.refs,
            temporal or self.case["temporal_mode"], option_role)

    def test_real_store_output_is_scoped_no_model_no_authority(self):
        result = self.evaluate()
        self.assertEqual(result["action"], self.case["oracle"]["action"])
        self.assertEqual(result["options"], self.case["oracle"]["options"])
        self.assertFalse(result["authority"])
        self.assertFalse(result["native_executed"])
        self.assertFalse(result["f5_decision_authority"])
        self.assertEqual(result["jepa_weight"], 0)
        self.assertEqual(set(result["all_three_source_hashes"]),
                         {"old", "sheet", "current"})

    def test_reject_invalid_role_mapping_and_temporal_contract(self):
        bad = [
            dict(self.refs, oracle="B"),
            dict(self.refs, old=self.refs["sheet"]),
            {"old": self.refs["old"], "current": self.refs["current"]},
        ]
        for refs in bad:
            with self.subTest(refs=refs):
                with self.assertRaises(bridge.Refusal):
                    self.evaluate(refs=refs)
        for mode in ("REVISED_CURRENT_RULES", "unknown"):
            with self.subTest(mode=mode):
                with self.assertRaises(bridge.Refusal):
                    self.evaluate(temporal=mode)
        with self.assertRaises(bridge.Refusal):
            self.evaluate(option_role="unregistered")

    def test_source_revoked_after_typed_evaluation_must_refuse(self):
        original = german.evaluate
        def revoke(*args, **kwargs):
            result = original(*args, **kwargs)
            with self.store.tx() as db:
                db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                           (self.source_id,))
            return result
        with patch.object(german, "evaluate", revoke):
            with self.assertRaises(bridge.Refusal):
                self.evaluate()

    def test_forged_typed_candidate_authority_or_hash_must_refuse(self):
        original = german.evaluate
        for label in ("authority", "hash", "status"):
            with self.subTest(label=label):
                def forged(*args, **kwargs):
                    result = original(*args, **kwargs)
                    if label == "authority":
                        result["authority"] = True
                    elif label == "hash":
                        result["source_hashes"]["old"] = "0" * 64
                    else:
                        result["status"] = "UTILITY_PASS_SCOPED"
                    return result
                with patch.object(german, "evaluate", forged):
                    with self.assertRaises(bridge.Refusal):
                        self.evaluate()


if __name__ == "__main__":
    unittest.main()

"""Read-only brain map regression: no Runtime, model or Termux dependency."""
import unittest
from types import SimpleNamespace
from v13.brain_panel import ORGANS, explain, operator_command, overview, status

class BrainPanelTests(unittest.TestCase):
    def setUp(self):
        self.r=SimpleNamespace(cfg={"learning_mode":"RECORD_ONLY"},current=None)
    def test_complete_unique_map_and_explicit_limit(self):
        card=overview(self.r)
        self.assertEqual(card["kind"],"READ_ONLY_NAVIGATION")
        self.assertEqual(len(card["organs"]),len(ORGANS))
        self.assertEqual(len({x["id"] for x in card["organs"]}),len(ORGANS))
        self.assertTrue(all(x["current_limit"] for x in card["organs"]))
        self.assertEqual(self.r.cfg,{"learning_mode":"RECORD_ONLY"})
    def test_user_friendly_names_and_unknown_rejection(self):
        self.assertEqual(explain("B1")["technical"],"B1_DETAIL")
        self.assertEqual(explain("jepa")["id"],"weltmodell")
        self.assertEqual(explain("C3")["id"],"sprache")
        with self.assertRaises(ValueError):
            explain("erfunden")
    def test_process_loaded_is_not_evidence_of_learning(self):
        before=status(self.r)
        self.assertFalse(before["world_jepa_instantiated"])
        self.r._world_jepa_online=object()
        after=status(self.r)
        self.assertTrue(after["world_jepa_instantiated"])
        self.assertFalse(after["native_model_training_proven"])
    def test_invalid_command_no_side_effect(self):
        with self.assertRaises(ValueError):
            operator_command(self.r,["explain"])
        self.assertEqual(self.r.cfg["learning_mode"],"RECORD_ONLY")

if __name__=="__main__":unittest.main()

"""Offline V14 outcome gate regressions: python -m unittest discover -s v13/code/tests -p 'test_temporal_outcomes_v14.py'"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "v13" / "temporal_outcomes.py"
spec = importlib.util.spec_from_file_location("temporal_outcomes_v14", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class OutcomeGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "ledger.db"
        self.ledger = mod.OutcomeLedger(self.path)
        self.ledger.expect(event_id="e1", source_ref="T8:1", owner="WORLD",
                           expected="file_exists", earliest=10, deadline=20, probability=.8)

    def tearDown(self):
        self.ledger.close()
        self.tmp.cleanup()

    def test_omission_requires_trusted_complete_coverage(self):
        self.assertEqual(self.ledger.resolve("e1", now=19, observed=False,
                         coverage_complete=True, trusted=True, observation_ref="T8:2")["status"], "PENDING")
        self.assertEqual(self.ledger.resolve("e1", now=21, observed=False,
                         coverage_complete=False, trusted=True, observation_ref="T8:2")["status"], "CENSORED")
        self.assertIsNone(self.ledger.read("e1")["error"])

    def test_negative_prediction_error_and_restart(self):
        result = self.ledger.resolve("e1", now=21, observed=False,
                  coverage_complete=True, trusted=True, observation_ref="T8:2")
        self.assertEqual(result, {"status": "OMITTED", "error": -.8, "trainable": True})
        self.ledger.close()
        self.ledger = mod.OutcomeLedger(self.path)
        self.assertEqual(self.ledger.read("e1")["outcome_ref"], "T8:2")
        self.assertEqual(self.ledger.read("e1")["error"], -.8)
        with self.assertRaises(ValueError):
            self.ledger.resolve("e1", now=22)

    def test_positive_requires_provenance(self):
        with self.assertRaises(ValueError):
            self.ledger.resolve("e1", now=15, observed=True, trusted=False)
        self.assertEqual(self.ledger.resolve("e1", now=15, observed=True,
                         trusted=True, observation_ref="T8:3")["error"], .2 - 0.0000000000000000555)

    def test_cancel_never_trains(self):
        self.assertFalse(self.ledger.resolve("e1", now=12, cancelled=True)["trainable"])

    def test_invalid_probability_rejected(self):
        with self.assertRaises(ValueError):
            self.ledger.expect(event_id="e2", source_ref="T8:1", owner="WORLD",
                               expected="x", earliest=0, deadline=1, probability=float("nan"))

if __name__ == "__main__":
    unittest.main()

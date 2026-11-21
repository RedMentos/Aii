import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from temporal_receiver import TemporalReadout

I = {"source": "T8:source", "evidence": "T8:receipt", "expected_outcome": "ok", "observed_outcome": "ok", "target": "WORLD_TEMPORAL", "requires_optimizer_permission": True, "prediction_error": .8}


class TestReceiver(unittest.TestCase):
    def test_numeric_restart_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "weights.json"; r = TemporalReadout(p, True); delta = r.update(I, "one", True)
            self.assertGreater(delta["WORLD"], delta["B1"]); self.assertGreater(delta["B1"], delta["B2"])
            self.assertGreater(r.read("WORLD"), r.read("WORLD", True)); snapshot = p.read_bytes()
            self.assertEqual(TemporalReadout(p).read("B1"), r.read("B1")); r.update({**I, "prediction_error": -.8}, "two", True)
            r.rollback(snapshot); self.assertEqual(p.read_bytes(), snapshot); self.assertEqual(r.seen, ["one"])

    def test_rollback_fsyncs_directory_entry_after_replace(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "weights.json"
            receiver = TemporalReadout(path, learning_enabled=True)
            receiver.update(I, "one", authorized=True)
            snapshot = path.read_bytes()
            receiver.update({**I, "prediction_error": -.8}, "two", authorized=True)
            with patch("temporal_receiver.os.fsync", wraps=os.fsync) as fsync:
                receiver.rollback(snapshot)
            self.assertGreaterEqual(fsync.call_count, 2)
            restored = TemporalReadout(path, learning_enabled=True)
            self.assertEqual(restored.seen, ["one"])
            self.assertEqual(path.read_bytes(), snapshot)

    def test_denials_and_atomic_failure(self):
        with tempfile.TemporaryDirectory() as d:
            r = TemporalReadout(Path(d) / "weights.json", True)
            with self.assertRaises(PermissionError): r.update(I, "x")
            with self.assertRaises(ValueError): r.update({**I, "source": "unknown"}, "x", True)
            with self.assertRaises(ValueError): r.update({**I, "prediction_error": float("nan")}, "x", True)
            with patch.object(r, "_save_unlocked", side_effect=OSError("disk")):
                with self.assertRaises(OSError): r.update(I, "x", True)
            self.assertEqual(r.weights["WORLD"], 0); r.update(I, "x", True)
            with self.assertRaises(ValueError): r.update(I, "x", True)

    def test_exact_boolean_permission_and_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            r = TemporalReadout(Path(d) / "weights.json", True)
            with self.assertRaises(PermissionError): r.update(I, "x", authorized="yes")
            with self.assertRaises(ValueError): r.update({**I, "expected_outcome": ""}, "x", True)
            with self.assertRaises(ValueError): TemporalReadout(Path(d) / "other.json", learning_enabled=1)


if __name__ == "__main__": unittest.main()

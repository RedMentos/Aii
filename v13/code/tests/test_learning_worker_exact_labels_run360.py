"""Run360: route-head worker must not reinterpret explicit human/scaffold labels.

CPU NumPy fixture only. The existing native learning cohort remains historical;
these tests do not establish learned utility or Body-JEPA.
"""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from v13.config import initialize
from v13.learning_worker import train


class ExactRouteLabelsRun360(unittest.TestCase):
    def fixture(self, root):
        labels = list(range(4)) * 4
        return {"config": initialize(root),
                "embeddings": np.tile(np.eye(4), (4, 1)).tolist(),
                "labels": labels,
                "scaffold_labels": labels.copy(),
                "active_checkpoint": None}

    def test_valid_integer_labels_still_train_and_write_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = train(self.fixture(root), root)
            self.assertEqual(result["n"], 16)
            self.assertTrue((root / "candidate.npz").is_file())
            self.assertTrue((root / "metrics.json").is_file())

    def test_noninteger_human_route_labels_rejected_before_any_candidate_write(self):
        for bad in (True, 1.9, "1", None, -1, 4):
            with self.subTest(bad=repr(bad)), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                request = self.fixture(root)
                request["labels"][5] = bad
                with self.assertRaisesRegex(ValueError, "integer route labels"):
                    train(request, root)
                self.assertFalse((root / "candidate.npz").exists())
                self.assertFalse((root / "metrics.json").exists())

    def test_noninteger_scaffold_labels_rejected_before_any_candidate_write(self):
        for bad in (True, 1.9, "1", None, -1, 4):
            with self.subTest(bad=repr(bad)), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                request = self.fixture(root)
                request["scaffold_labels"][15] = bad
                with self.assertRaisesRegex(ValueError, "integer scaffold labels"):
                    train(request, root)
                self.assertFalse((root / "candidate.npz").exists())
                self.assertFalse((root / "metrics.json").exists())

    def test_scaffold_length_must_match_without_partial_training(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = self.fixture(root)
            request["scaffold_labels"] = [0, 1, 2]
            with self.assertRaisesRegex(ValueError, "integer scaffold labels"):
                train(request, root)
            self.assertFalse((root / "candidate.npz").exists())


if __name__ == "__main__":
    unittest.main()

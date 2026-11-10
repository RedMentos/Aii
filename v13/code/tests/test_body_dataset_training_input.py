"""Read-only Body-JEPA item preparation from reviewed dataset; no training."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from v13.agi.body_dataset import compile_dataset
from v13.agi.body_dataset_training_input import prepare_body_training_items

class BodyInputTests(unittest.TestCase):
    def test_preparation_is_stable_role_isolated_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root/"source.jsonl"
            rows = []
            for role in ("B1_DETAIL", "B2_GIST"):
                for i in range(120):
                    h = hashlib.sha256(f"{role}-{i}".encode()).hexdigest()
                    rows.append({"role":role,"source_id":f"{role}-{i}",
                                 "source_sha256":h,"prompt":f"prompt {i}",
                                 "target":f"target {i}","reviewed":True,
                                 "permission":"TRAINING_APPROVED"})
            source.write_text("".join(json.dumps(x)+"\n" for x in rows))
            output = root/"dataset"
            compile_dataset(source, output)
            b1 = prepare_body_training_items(output, "B1_DETAIL")
            b2 = prepare_body_training_items(output, "B2_GIST")
            self.assertEqual(b1, prepare_body_training_items(output, "B1_DETAIL"))
            self.assertTrue(all(set(x)=={"memory_id","prompt","target"} for part in b1 for x in part))
            self.assertFalse({x["memory_id"] for part in b1 for x in part} &
                             {x["memory_id"] for part in b2 for x in part})
            with self.assertRaises(ValueError):
                prepare_body_training_items(output, "B1_DETAIL", max_items=1)
            with self.assertRaises(ValueError):
                prepare_body_training_items(output, "B1_DETAIL", max_items=257)

if __name__ == "__main__":
    unittest.main()

"""Dataset consumer integrity regressions; no weight training or promotion."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from v13.agi.body_dataset import compile_dataset
from v13.agi.body_dataset_reader import load_role_dataset

class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = self.root / "reviewed.jsonl"
        rows = []
        for role in ("B1_DETAIL", "B2_GIST"):
            for i in range(200):
                digest = hashlib.sha256(f"{role}-{i}".encode()).hexdigest()
                rows.append({"role": role, "source_id": f"{role}-{i}",
                             "source_sha256": digest, "prompt": f"question {i}",
                             "target": f"answer {i}", "reviewed": True,
                             "permission": "TRAINING_APPROVED"})
        source.write_text("".join(json.dumps(r)+"\n" for r in rows))
        self.output = self.root / "compiled"
        compile_dataset(source, self.output)

    def test_both_roles_and_disjoint_sources(self):
        for role in ("B1_DETAIL", "B2_GIST"):
            train, holdout = load_role_dataset(self.output, role)
            self.assertTrue(train and holdout)
            self.assertTrue(all(row["role"] == role for row in train+holdout))
            self.assertFalse({r["source_id"] for r in train} & {r["source_id"] for r in holdout})

    def test_modified_partition_fails_even_when_other_role_requested(self):
        p = self.output / "b1_detail_train.jsonl"
        p.write_bytes(p.read_bytes()+b"\n")
        with self.assertRaises(ValueError):
            load_role_dataset(self.output, "B2_GIST")

    def test_manifest_count_tamper_fails(self):
        p = self.output / "manifest.json"
        data = json.loads(p.read_text())
        data["files"]["b1_detail_train.jsonl"]["rows"] += 1
        p.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            load_role_dataset(self.output, "B1_DETAIL")

    def test_invalid_role_cap_and_symlink(self):
        with self.assertRaises(ValueError):
            load_role_dataset(self.output, "C3_LANGUAGE")
        with self.assertRaises(ValueError):
            load_role_dataset(self.output, "B1_DETAIL", max_rows=1)
        link = self.root / "link"
        link.symlink_to(self.output, target_is_directory=True)
        with self.assertRaises(ValueError):
            load_role_dataset(link, "B1_DETAIL")

if __name__ == "__main__":
    unittest.main()

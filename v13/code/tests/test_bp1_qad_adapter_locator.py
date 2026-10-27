import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import bp1_qad_adapter_locator as L


class AdapterLocatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.work = self.root / "trainer-work"
        self.adapter_dir = self.work / ("a" * 24)
        self.adapter_dir.mkdir(parents=True)
        self.adapter = self.adapter_dir / "adapter.gguf"
        self.peft = self.adapter_dir / "adapter_model.safetensors"
        self.adapter.write_bytes(b"synthetic gguf bytes")
        self.peft.write_bytes(b"synthetic peft bytes")
        self.proof_file = self.root / "BP1_QAD_TRAIN_PROOF.json"
        self.proof = {"mode": "train", "status": "TRAINED_SHADOW_ADAPTER_NOT_DEPLOYED",
                      "train_rows": 25, "train_sha256": L.TRAIN_SHA,
                      "native_training_executed": True, "heldout_files_opened": False,
                      "production_weight_authority": 0, "model_utility_proven": False,
                      "gates": dict(L.GATES),
                      "adapter": {"gguf_bytes": self.adapter.stat().st_size,
                                  "gguf_sha256": L.sha(self.adapter),
                                  "peft_sha256": L.sha(self.peft),
                                  "lora_b_nonzero": 7, "gguf_tensors": 44}}
        self.save()

    def save(self):
        self.proof_file.write_text(json.dumps(self.proof))

    def test_verified_real_trainer_layout(self):
        path, info = L.locate(self.work, self.proof_file)
        self.assertEqual(path, self.adapter.resolve())
        self.assertEqual(info["gguf_sha256"], L.sha(self.adapter))

    def test_missing_adapter_rejected(self):
        self.adapter.unlink()
        with self.assertRaisesRegex(ValueError, "exactly one"):
            L.locate(self.work, self.proof_file)

    def test_multiple_adapter_rejected(self):
        other = self.work / ("b" * 24)
        other.mkdir()
        (other / "adapter.gguf").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            L.locate(self.work, self.proof_file)

    def test_gguf_hash_tamper_rejected(self):
        self.adapter.write_bytes(b"synthetic gguf bytez")
        with self.assertRaisesRegex(ValueError, "GGUF adapter SHA"):
            L.locate(self.work, self.proof_file)

    def test_peft_hash_tamper_rejected(self):
        self.peft.write_bytes(b"synthetic peft bytez")
        with self.assertRaisesRegex(ValueError, "PEFT adapter SHA"):
            L.locate(self.work, self.proof_file)

    def test_symlink_adapter_rejected(self):
        original = self.adapter_dir / "original.gguf"
        self.adapter.rename(original)
        self.adapter.symlink_to(original)
        with self.assertRaisesRegex(ValueError, "path invalid"):
            L.locate(self.work, self.proof_file)

    def test_wrong_train_sha_rejected(self):
        self.proof["train_sha256"] = "0" * 64
        self.save()
        with self.assertRaisesRegex(ValueError, "train proof"):
            L.locate(self.work, self.proof_file)

    def test_production_authority_rejected(self):
        self.proof["production_weight_authority"] = 1
        self.save()
        with self.assertRaisesRegex(ValueError, "authority"):
            L.locate(self.work, self.proof_file)

    def test_heldout_opened_rejected(self):
        self.proof["heldout_files_opened"] = True
        self.save()
        with self.assertRaisesRegex(ValueError, "authority"):
            L.locate(self.work, self.proof_file)

    def test_digest_directory_rejected(self):
        other = self.work / "not-a-digest"
        self.adapter_dir.rename(other)
        with self.assertRaisesRegex(ValueError, "digest directory"):
            L.locate(self.work, self.proof_file)

    def test_duplicate_proof_json_rejected(self):
        self.proof_file.write_text('{"mode":"train","mode":"train"}')
        with self.assertRaisesRegex(ValueError, "duplicate proof"):
            L.locate(self.work, self.proof_file)


if __name__ == "__main__":
    unittest.main()

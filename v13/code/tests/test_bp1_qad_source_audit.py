"""QAD master source binding: fake official HF API responses only, no downloads."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from scripts import bp1_qad_source_audit as Q


def fake():
    files = [
        {"rfilename": "qad/model.safetensors", "lfs": {"sha256": "a"*64, "size": 1417952352}},
        {"rfilename": "qad/config.json", "size": 1300},
        {"rfilename": "qad/tokenizer.json", "lfs": {"sha256": "b"*64, "size": 4730000}},
        {"rfilename": Q.DEPLOYED, "lfs": {"sha256": Q.DEPLOYED_SHA, "size": 219312832}},
        {"rfilename": "LICENSE", "size": 10600},
        {"rfilename": "qad/chat_template.jinja", "size": 5500}
    ]
    return {"id": Q.REPO, "sha": Q.REVISION, "siblings": files, "cardData": {"license": "lfm1.0"}}


class QadSourceAuditTests(unittest.TestCase):
    def test_official_source_hashes_and_negative_gates(self):
        report = Q.audit(fake())
        self.assertEqual(report["source_master_sha256"], "a"*64)
        self.assertEqual(report["deployed_gguf_sha256"], Q.DEPLOYED_SHA)
        self.assertFalse(report["fp32_to_q4_behavioral_parity_verified"])
        self.assertFalse(report["native_c3_training_executed"])
        self.assertEqual(report["gates"]["jepa_weight"], 0)

    def test_wrong_revision_fails(self):
        info = fake(); info["sha"] = "f"*40
        with self.assertRaisesRegex(ValueError, "revision"):
            Q.audit(info)

    def test_missing_master_fails(self):
        info = fake(); info["siblings"] = info["siblings"][1:]
        with self.assertRaisesRegex(ValueError, "required"):
            Q.audit(info)

    def test_deployed_hash_change_fails(self):
        info = fake(); info["siblings"][3]["lfs"]["sha256"] = "f"*64
        with self.assertRaisesRegex(ValueError, "registered"):
            Q.audit(info)

    def test_legacy_lfs_oid_compatibility(self):
        info = fake()
        for name in (Q.MASTER, Q.DEPLOYED):
            entry = next(x for x in info["siblings"] if x["rfilename"] == name)
            entry["lfs"]["oid"] = "sha256:" + entry["lfs"].pop("sha256")
        report = Q.audit(info)
        self.assertEqual(report["deployed_gguf_sha256"], Q.DEPLOYED_SHA)

    def test_conflicting_lfs_hashes_rejected(self):
        info = fake()
        info["siblings"][0]["lfs"]["oid"] = "f"*64
        with self.assertRaisesRegex(ValueError, "conflicting"):
            Q.audit(info)

    def test_missing_lfs_hash_fails(self):
        info = fake(); del info["siblings"][0]["lfs"]
        with self.assertRaisesRegex(ValueError, "LFS"):
            Q.audit(info)

    def test_wrong_size_fails(self):
        info = fake(); info["siblings"][0]["lfs"]["size"] = 3
        with self.assertRaisesRegex(ValueError, "size"):
            Q.audit(info)

    def test_duplicate_file_fails(self):
        info = fake(); info["siblings"].append(copy.deepcopy(info["siblings"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            Q.audit(info)

    def test_optional_template_absence_is_reported_not_invented(self):
        info = fake(); info["siblings"] = [x for x in info["siblings"] if x["rfilename"] != "qad/chat_template.jinja"]
        report = Q.audit(info)
        self.assertIn("qad/chat_template.jinja", report["optional_files_absent"])

    def test_duplicate_json_keys_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            Q.parse('{"sha":"a","sha":"b"}')

    def test_nonfinite_metadata_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            Q.parse('{"size":NaN}')

    def test_exclusive_result_preserves_original(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "report.json"
            path.write_text("old")
            with self.assertRaises(FileExistsError):
                with path.open("xb") as f:
                    f.write(b"new")
            self.assertEqual(path.read_text(), "old")


if __name__ == "__main__":
    unittest.main()

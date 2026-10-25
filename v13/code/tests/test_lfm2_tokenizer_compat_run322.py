"""Run322 frozen-source/tokenizer compatibility fixture tests; no model or native calls."""
import copy
from collections import UserDict
import json
from pathlib import Path
import tempfile
import unittest

from scripts import probe_lfm2_tokenizer_compat_run322 as P


class Run322TokenizerCompatibility(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name, text in (
            ("config.json", "{}"),
            ("tokenizer_config.json", '{"tokenizer_class":"TokenizersBackend"}'),
            ("tokenizer.json", '{"model":{"type":"BPE"}}'),
        ):
            (self.root / name).write_text(text)
        self.manifest = {
            "hf_repo": P.REPO, "hf_revision": P.REVISION,
            "file_sha256": {name: P.digest(self.root / name)
                            for name in ("config.json", "tokenizer_config.json", "tokenizer.json")},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_frozen_snapshot_manifest_pass(self):
        result = P.verify_snapshot(self.root, self.manifest)
        self.assertEqual(result["files"], 3)

    def test_wrong_revision_fails_closed(self):
        bad = copy.deepcopy(self.manifest)
        bad["hf_revision"] = "main"
        with self.assertRaisesRegex(ValueError, "wrong pinned"):
            P.verify_snapshot(self.root, bad)

    def test_tampered_source_fails_closed(self):
        (self.root / "tokenizer.json").write_text("tampered")
        with self.assertRaisesRegex(ValueError, "source byte drift"):
            P.verify_snapshot(self.root, self.manifest)

    def test_symlink_refused(self):
        file = self.root / "tokenizer.json"
        file.unlink()
        file.symlink_to(self.root / "config.json")
        with self.assertRaisesRegex(ValueError, "source byte drift"):
            P.verify_snapshot(self.root, self.manifest)

    def test_wrong_tokenizer_class_refused_even_with_matching_hash(self):
        file = self.root / "tokenizer_config.json"
        file.write_text('{"tokenizer_class":"PreTrainedTokenizerFast"}')
        self.manifest["file_sha256"][file.name] = P.digest(file)
        with self.assertRaisesRegex(ValueError, "tokenizer class"):
            P.verify_snapshot(self.root, self.manifest)

    def test_invalid_or_nondiscrete_ids_fail(self):
        self.assertEqual(P.normalize_ids([[1, 2, 3]]), [1, 2, 3])
        self.assertEqual(P.normalize_ids({"input_ids": [1, 2, 3]}), [1, 2, 3])
        self.assertEqual(P.normalize_ids(UserDict({"input_ids": [1, 2, 3]})), [1, 2, 3])
        for ids in ([], [-1], [65536], [True], [1.0], ["1"], [1] * 2049):
            with self.subTest(ids=str(ids)[:20]), self.assertRaises(ValueError):
                P.normalize_ids(ids)

    def test_positive_and_negative_arms_are_both_required(self):
        old = {"schema": P.SCHEMA, "arm": "4.57.1", "status": "FAIL",
               "error": "ValueError: Tokenizer class TokenizersBackend does not exist",
               "hf_repo": P.REPO, "hf_revision": P.REVISION}
        new = {"schema": P.SCHEMA, "arm": "5.3.0", "status": "PASS",
               "hf_repo": P.REPO, "hf_revision": P.REVISION,
               "prompt_count": 5, "outputs": [{"n": 4, "sha256": "a" * 64} for _ in range(5)]}
        self.assertEqual(P.assess(old, new)["status"], "COMPAT_DIAGNOSTIC_SUPPORTED")
        self.assertFalse(P.assess(old, new)["native_conversion_proven"])
        self.assertEqual(P.assess({**old, "status": "PASS"}, new)["status"], "NOT_SUPPORTED")
        self.assertEqual(P.assess(old, {**new, "status": "FAIL"})["status"], "NOT_SUPPORTED")
        with self.assertRaisesRegex(ValueError, "wrong arm"):
            P.assess({**old, "arm": "5.3.0"}, new)


if __name__ == "__main__":
    unittest.main()

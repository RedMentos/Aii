"""P0X independent export verifier tests: original fixture plus tampered bytes."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import p0x_independent_source_holdout as source
from scripts import p0x_export_independent_verify as audit

PIN = "ab03aba600e8085b02247657cc5fb718195e89a83641ef69ad006a27c776647e"


def rewrite(root, name, records):
    raw = b"".join(json.dumps(row, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False).encode() + b"\n" for row in records)
    (root / name).write_bytes(raw)
    manifest = json.loads((root / "manifest.json").read_text())
    manifest["sha256"][name] = hashlib.sha256(raw).hexdigest()
    (root / "manifest.json").write_text(json.dumps(manifest))


class P0XIndependentExportAudit(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "fixture"
        source.export(self.root, PIN)

    def test_full_750_and_independent_oracle(self):
        result = audit.verify(self.root, PIN)
        self.assertEqual(result["checked_prompts"], 750)
        self.assertEqual(result["oracle_matches"], 150)
        self.assertFalse(result["canonical_gate_pass"])

    def test_wrong_external_pin_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "EXTERNAL_PIN|MANIFEST_PIN"):
            audit.verify(self.root, "0" * 64)

    def test_tampered_answers_even_if_hash_rewritten(self):
        answers = [json.loads(line) for line in
                   (self.root / "answers.jsonl").read_text().splitlines()]
        answers[0]["oracle_action"] = next(x for x in ("A", "B", "NONE")
                                            if x != answers[0]["oracle_action"])
        rewrite(self.root, "answers.jsonl", answers)
        with self.assertRaisesRegex(ValueError, "ANSWER_BALANCE|INDEPENDENT_ORACLE"):
            audit.verify(self.root, PIN)

    def test_c3_receives_b1_data_even_if_hash_rewritten(self):
        inputs = [json.loads(line) for line in
                  (self.root / "inputs.jsonl").read_text().splitlines()]
        index = next(i for i, p in enumerate(inputs) if p["arm"] == "c3_only")
        inputs[index]["messages"][0]["content"] += "\n\nB1 exact source:\n" + source.fixtures()[0]["b1_source"]
        rewrite(self.root, "inputs.jsonl", inputs)
        with self.assertRaisesRegex(ValueError, "C3_LEAK"):
            audit.verify(self.root, PIN)

    def test_shuffled_uses_same_project_even_if_hash_rewritten(self):
        inputs = [json.loads(line) for line in
                  (self.root / "inputs.jsonl").read_text().splitlines()]
        project = inputs[0]["id"]
        exact = next(p["messages"][0]["content"] for p in inputs
                     if p["id"] == project and p["arm"] == "both_exact")
        own_b1 = exact.split("\n\nB1 exact source:\n", 1)[1]
        index = next(i for i, p in enumerate(inputs)
                     if p["id"] == project and p["arm"] == "shuffled")
        message = inputs[index]["messages"][0]["content"]
        inputs[index]["messages"][0]["content"] = message.split(
            "\n\nFOREIGN B1 source:\n", 1)[0] + "\n\nFOREIGN B1 source:\n" + own_b1
        rewrite(self.root, "inputs.jsonl", inputs)
        with self.assertRaisesRegex(ValueError, "SHUFFLED_FOREIGN"):
            audit.verify(self.root, PIN)

    def test_cross_domain_source_injection_even_if_hash_rewritten(self):
        inputs = [json.loads(line) for line in
                  (self.root / "inputs.jsonl").read_text().splitlines()]
        index = next(i for i, p in enumerate(inputs) if p["arm"] == "both_exact")
        inputs[index]["messages"][0]["content"] = inputs[index]["messages"][0]["content"].replace(
            " archived ", " archived wrong ", 1)
        rewrite(self.root, "inputs.jsonl", inputs)
        with self.assertRaisesRegex(ValueError, "DOMAIN_IDENTITY|B2_ARM"):
            audit.verify(self.root, PIN)

    def test_unmodified_hash_mismatch(self):
        with (self.root / "inputs.jsonl").open("ab") as handle:
            handle.write(b"\n")
        with self.assertRaisesRegex(ValueError, "CONTENT_HASH"):
            audit.verify(self.root, PIN)

    def test_negative_gate_manifest_forgery(self):
        manifest = json.loads((self.root / "manifest.json").read_text())
        manifest["canonical_gate_pass"] = True
        (self.root / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "NEGATIVE_GATES"):
            audit.verify(self.root, PIN)


if __name__ == "__main__":
    unittest.main()

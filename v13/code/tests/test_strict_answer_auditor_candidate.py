import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import strict_answer_auditor_candidate as auditor


class StrictAnswerAuditorCandidateTests(unittest.TestCase):
    def check(self, raw, aliases, status):
        result = auditor.audit(raw, aliases)
        self.assertEqual(result["status"], status, result)
        self.assertEqual(result["raw_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["raw_size_bytes"], len(raw))
        return result

    def test_accepts_only_exact_normalized_atomic_alias(self):
        result = self.check(b'{"answer":"  MItZI  "}', ["Mitzi"], "MATCH")
        self.assertIsNotNone(result["aliases_sha256"])
        self.check('{"answer":"ＦＯＯ"}'.encode(), ["foo"], "MATCH")
        self.check(b'{"answer":"rot  weiss"}', ["Rot Weiss"], "MATCH")
        self.check(b'{"answer":"other"}', ["Mitzi"], "UNKNOWN")

    def test_old_substring_and_negation_counterexamples_are_unknown(self):
        for answer, aliases in [
            ("Your cat is not named Mitzi", ["Mitzi"]),
            ("not Mitzi", ["Mitzi"]),
            ("Have a nice day", ["ice"]),
            ("Mitzi maybe", ["Mitzi"]),
            ("Mitzi or Boris", ["Mitzi"]),
            ("I don't know", ["Mitzi"]),
            ("none", ["Mitzi"]),
        ]:
            with self.subTest(answer=answer):
                self.check(json.dumps({"answer": answer}).encode(), aliases, "UNKNOWN")

    def test_rejects_invalid_and_ambiguous_envelopes(self):
        for raw in [
            b'{"answer":"Mitzi","answer":"Mitzi"}',
            b'{"answer":"Mitzi","answer":"Boris"}',
            b'{"answer":"Mitzi","extra":"statement"}',
            b'{"answer":null}', b'{"answer":["Mitzi"]}',
            b'["Mitzi"]', b'"Mitzi"', b'{}', b'{"answer":NaN}',
            b'{"answer":"Mitzi"} trailing', b'{"answer":', b'\xff',
        ]:
            with self.subTest(raw=raw):
                self.check(raw, ["Mitzi"], "INVALID")

    def test_escapes_and_additional_assertions_do_not_match(self):
        for answer in ["Mitzi. Boris", "Mitzi\nBoris", "Mitzi; Boris",
                       "Mitzi\u200b", "Mitzi / Boris", "Mitzi?", "Mitzi Boris"]:
            with self.subTest(answer=answer):
                self.check(json.dumps({"answer": answer}).encode(), ["Mitzi"], "UNKNOWN")

    def test_invalid_aliases_cannot_whitelist_refusal_or_ambiguity(self):
        for aliases in [[], ["unknown"], ["not Mitzi"], ["not-Mitzi"], ["Mitzi-or-Boris"], ["Mitzi or Boris"],
                        ["Mitzi", "MITZI"], ["Mitzi. Boris"], [""], [42]]:
            with self.subTest(aliases=aliases):
                self.check(b'{"answer":"Mitzi"}', aliases, "INVALID_CONFIG")

    def test_full_hash_binds_invalid_and_oversize_raw_bytes(self):
        raw = b'{"answer":"Mitzi"}' + b' ' * auditor.MAX_RAW_BYTES
        result = self.check(raw, ["Mitzi"], "INVALID")
        self.assertEqual(result["reason"], "response_too_large")
        raw_a = b'{"answer":"Mitzi"}'
        raw_b = b'{ "answer":"Mitzi"}'
        self.assertNotEqual(self.check(raw_a, ["Mitzi"], "MATCH")["raw_sha256"],
                            self.check(raw_b, ["Mitzi"], "MATCH")["raw_sha256"])

    def test_cli_is_disabled_unless_explicitly_enabled(self):
        script = Path(auditor.__file__)
        raw = b'{"answer":"Mitzi"}'
        disabled = subprocess.run([sys.executable, str(script)], input=raw, capture_output=True, check=True)
        self.assertEqual(json.loads(disabled.stdout)["status"], "DISABLED")
        enabled = subprocess.run([sys.executable, str(script), "--enable", "--alias", "Mitzi"],
                                 input=raw, capture_output=True, check=True)
        result = json.loads(enabled.stdout)
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual(result["raw_sha256"], hashlib.sha256(raw).hexdigest())

    def test_cli_hashes_entire_oversized_stream(self):
        raw = b'x' * (auditor.MAX_RAW_BYTES + 90000)
        proc = subprocess.run([sys.executable, str(Path(auditor.__file__)), "--enable", "--alias", "Mitzi"],
                              input=raw, capture_output=True)
        self.assertEqual(proc.returncode, 2)
        result = json.loads(proc.stdout)
        self.assertEqual(result["status"], "INVALID")
        self.assertEqual(result["raw_size_bytes"], len(raw))
        self.assertEqual(result["raw_sha256"], hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    unittest.main()

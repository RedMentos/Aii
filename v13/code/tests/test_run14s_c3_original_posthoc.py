"""Run14S strict posthoc parser tests; no fake native evidence."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run14s_c3_original_posthoc as audit

FIXTURE = (Path(__file__).resolve().parents[1] /
           "docs/fixtures/run14l_c3_structured_seed307_20261030.json")


class Run14SPosthoc(unittest.TestCase):
    def setUp(self):
        self.case = {"project": "Cedar307", "budget": 11300, "a": "Amber",
                     "a_cost": 5290, "a_days": 13, "b": "Quartz",
                     "b_cost": 6575, "b_days": 17}
        self.facts = ["Project Cedar307", "Amber leaves 6010 Euro",
                      "Quartz leaves 4725 Euro", "Amber finishes sooner"]

    def test_strict_source_strings_and_extras_remain_separate(self):
        self.assertTrue(audit._text_four_exact(self.case, {"VERIFIED_FACTS": self.facts}))
        self.assertTrue(audit._text_four_exact(self.case, {
            "VERIFIED_FACTS": self.facts, "INVENTED": ["not allowed"]}))
        for bad in ([*self.facts[:-1], "Quartz finishes sooner"],
                    [*self.facts[:1], "Amber leaves 6011 Euro", *self.facts[2:]],
                    self.facts[::-1], self.facts[:3], self.facts + ["extra"]):
            with self.subTest(bad=bad):
                self.assertFalse(audit._text_four_exact(self.case, {"VERIFIED_FACTS": bad}))
        self.assertFalse(audit._text_four_exact(self.case, {"VERIFIED_FACTS": [dict(a=1)]}))
        self.assertFalse(audit._text_four_exact(self.case, {"VERIFIED_FACTS": "not a list"}))
        self.assertFalse(audit._text_four_exact(self.case, [*self.facts]))
        self.assertTrue(audit._text_four_exact(self.case, {"VERIFIED_FACTS": [
            "Project Cedar307.", "Amber leaves 6010 euros remaining.",
            "Quartz leaves 4725 euros remaining", "Amber finishes sooner."]}))

    def test_json_fence_is_strict_and_duplicate_nonfinite_fail_closed(self):
        good = "```json\n" + json.dumps({"VERIFIED_FACTS": self.facts}) + "\n```"
        kind, obj = audit._parse_fenced(good)
        self.assertEqual(kind, "CLOSED_JSON_OBJECT")
        self.assertTrue(audit._text_four_exact(self.case, obj))
        for raw in (good + " explanation", good.replace("```json", "~~~json"),
                    "```json\n{" + '"VERIFIED_FACTS":[],"VERIFIED_FACTS":[]' + "}\n```",
                    "```json\n{\"x\":NaN}\n```", "```json\n[]\n```", "x" * 5000):
            with self.subTest(raw=raw[:20]):
                kind, _ = audit._parse_fenced(raw)
                self.assertNotEqual(kind, "CLOSED_JSON_OBJECT")

    def test_fixture_hash_and_original_zip_sha_are_immutable(self):
        self.assertEqual(audit._sha(json.dumps(tuple(audit._fixture(FIXTURE)),
                        sort_keys=True, separators=(",", ":"))), audit.FIXTURE_SHA256)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fixture.json"
            original = json.loads(FIXTURE.read_text(encoding="utf-8"))
            original["cases"][0]["budget"] += 1
            p.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaises(ValueError):
                audit._fixture(p)
            bad_zip = Path(td) / "fake.zip"
            bad_zip.write_bytes(b"not a real native artifact")
            with self.assertRaises(ValueError):
                audit._read_original_zip(bad_zip)

    def test_posthoc_never_dispatches_native_or_writes(self):
        # A forged artifact cannot be admitted; only pinned original bytes can.
        with patch.object(audit, "_read_original_zip", side_effect=ValueError("ORIGINAL_ZIP_SHA_RED")):
            with self.assertRaises(ValueError):
                audit.audit(Path("does-not-exist.zip"), FIXTURE)


if __name__ == "__main__":
    unittest.main()

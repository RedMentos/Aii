"""Run11Q source-bound arithmetic shadow scoring, adversarial synthetic ZIP tests."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from scripts import c2_c3_body_source_arithmetic_shadow_run11q as a

FIXTURES = [
    {"project": "Zephyr47", "budget": 287, "a": "Marigold",
     "a_cost": 191, "a_days": 4, "b": "Basalt", "b_cost": 263, "b_days": 7},
    {"project": "Solstice47", "budget": 346, "a": "Kestrel",
     "a_cost": 214, "a_days": 8, "b": "Linden", "b_cost": 319, "b_days": 3},
    {"project": "Talon47", "budget": 229, "a": "Orion",
     "a_cost": 173, "a_days": 6, "b": "Willow", "b_cost": 205, "b_days": 2},
]
OUTPUTS = [
    "Marigold: 191 Euro remaining; faster with a 4-day timeline.\n"
    "Basalt: 263 Euro remaining; slower with a 7-day timeline.",
    "The remaining budget for Option Kestrel is 132 Euro, and for Option "
    "Linden it is 127 Euro.",
    "Option Orion leaves 56 Euro; Option Willow leaves 124 Euro.",
]


def make_report():
    return {
        "schema": "v13.c2_c3_body.auto_native_smoke.v1",
        "seed": 47, "fixture_sha256": a.FIXTURE_SHA256,
        "fixtures": [dict(f) for f in FIXTURES],
        "rows": [{"fixture": f["project"], "final_output": output,
                  "output_role": "B1_DETAIL"} for f, output in zip(FIXTURES, OUTPUTS)],
    }


def zip_bytes(report=None, extras=None, manifest_override=None):
    report = make_report() if report is None else report
    members = {"HEAD.txt": a.ORIGINAL_HEAD.encode(),
               "pilot/report.json": json.dumps(report, sort_keys=True).encode()}
    members.update(extras or {})
    manifest = "".join(f"{hashlib.sha256(value).hexdigest()}  ./{name}\n"
                       for name, value in sorted(members.items()))
    members["SHA256SUMS"] = (manifest if manifest_override is None else
                            manifest_override).encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, value in members.items():
            z.writestr(name, value)
    return out.getvalue()


class SourceArithmeticShadowRun11Q(unittest.TestCase):
    def test_fixture_exact_and_original_three_outputs(self):
        self.assertEqual(a._digest(json.dumps(FIXTURES, sort_keys=True,
                         separators=(",", ":")).encode()), a.FIXTURE_SHA256)
        report = a.score_report(make_report(), a.ORIGINAL_ZIP_SHA256)
        self.assertEqual(report["total_options"], 6)
        self.assertEqual(report["totals"], {"MATCH": 2,
                         "CONTRADICTS_SOURCE": 4,
                         "CONTRADICTORY_CLAIMS": 0, "UNSCORED": 0})
        self.assertFalse(report["utility_gate_pass"])
        self.assertFalse(report["native_route_selection_proven"])
        self.assertFalse(report["redmi_measured"])

    def test_option_linked_grammar_rejects_bare_cost_and_time(self):
        f = FIXTURES[0]
        for output in ("191 Euro costs and 4 days, Basalt costs 263 Euro.",
                       "287 Euro budget; 4 days.",
                       "OtherMarigold: 96 Euro remaining.",
                       "Option Marigold leaves 96 dollars."):
            self.assertEqual(a.score_option(f, output, "a")["status"], "UNSCORED")

    def test_coreference_only_with_same_sentence_remaining_budget_anchor(self):
        f = FIXTURES[1]
        self.assertEqual(a.extract_remaining(OUTPUTS[1], "Linden", "Kestrel"), {127})
        self.assertEqual(a.extract_remaining("For Option Linden it is 127 Euro.",
                                             "Linden", "Kestrel"), set())
        self.assertEqual(a.extract_remaining(
            "Remaining budget for Option Kestrel is 132 Euro. "
            "For Option Linden it is 127 Euro.", "Linden", "Kestrel"), set())

    def test_conflicting_claims_are_never_a_match(self):
        f = FIXTURES[2]
        row = a.score_option(f, "Option Orion leaves 56 Euro; "
                               "Option Orion leaves 99 Euro.", "a")
        self.assertEqual(row["status"], "CONTRADICTORY_CLAIMS")
        self.assertEqual(row["extracted_claims"], [56, 99])

    def test_swapped_labels_and_wrong_number_contradict_source(self):
        f = FIXTURES[2]
        self.assertEqual(a.score_option(f, "Option Orion leaves 24 Euro.", "a")["status"],
                         "CONTRADICTS_SOURCE")
        self.assertEqual(a.score_option(f, "Option Willow leaves 56 Euro.", "b")["status"],
                         "CONTRADICTS_SOURCE")

    def test_forged_precomputed_score_is_ignored(self):
        r = make_report()
        r["rows"][0]["scores"] = [{"status": "MATCH"}]
        result = a.score_report(r, a.ORIGINAL_ZIP_SHA256)
        self.assertEqual(result["totals"]["MATCH"], 2)

    def test_synthetic_complete_zip_passes_with_explicit_test_hash(self):
        b = zip_bytes()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "original.zip"
            p.write_bytes(b)
            report, sha = a.load_verified_zip(p, hashlib.sha256(b).hexdigest())
            self.assertEqual(sha, hashlib.sha256(b).hexdigest())
            self.assertEqual(a.score_report(report, sha)["totals"]["MATCH"], 2)
            with self.assertRaisesRegex(ValueError, "ORIGINAL_ZIP_SHA_MISMATCH"):
                a.load_verified_zip(p)

    def test_changed_source_fixture_rejected_even_with_rehashed_zip(self):
        r = make_report()
        r["fixtures"][0] = dict(r["fixtures"][0], budget=288)
        b = zip_bytes(r)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "changed.zip"
            p.write_bytes(b)
            with self.assertRaisesRegex(ValueError, "FIXTURE_CONTENT_CHANGED"):
                a.load_verified_zip(p, hashlib.sha256(b).hexdigest())

    def test_bad_manifest_rejected(self):
        b = zip_bytes(manifest_override="0" * 64 + "  ./HEAD.txt\n")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.zip"
            p.write_bytes(b)
            with self.assertRaisesRegex(ValueError, "MANIFEST_INCOMPLETE"):
                a.load_verified_zip(p, hashlib.sha256(b).hexdigest())

    def test_zip_traversal_rejected(self):
        b = zip_bytes(extras={"../escape.txt": b"no"})
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.zip"
            p.write_bytes(b)
            with self.assertRaisesRegex(ValueError, "UNSAFE_ZIP_MEMBER"):
                a.load_verified_zip(p, hashlib.sha256(b).hexdigest())

    def test_duplicate_zip_member_rejected(self):
        b = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(b, "w") as z:
                z.writestr("HEAD.txt", a.ORIGINAL_HEAD)
                z.writestr("HEAD.txt", a.ORIGINAL_HEAD)
                z.writestr("pilot/report.json", json.dumps(make_report()))
                z.writestr("SHA256SUMS", "")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "dup.zip"
            p.write_bytes(b.getvalue())
            with self.assertRaisesRegex(ValueError, "ZIP_MEMBERS_INVALID"):
                a.load_verified_zip(p, hashlib.sha256(b.getvalue()).hexdigest())


if __name__ == "__main__":
    unittest.main()

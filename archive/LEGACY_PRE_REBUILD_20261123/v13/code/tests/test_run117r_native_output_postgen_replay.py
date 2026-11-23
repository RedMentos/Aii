"""Run117R synthetic ZIP replay adversarial tests; no native model execution."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import run117r_native_output_postgen_replay as replay
from scripts import run117q_native_attribution_readonly as audit

PRIOR = ("Project Kairo. Budget 200 euros. Deadline 5 days. "
         "Local-only requirement: true. These are the binding project rules.")
CURRENT = ("Project Kairo. Apply the earlier project rules. "
           "Option A costs 190 euros, takes 4 days, and is local. "
           "Option B costs 170 euros, takes 7 days, and is local. "
           "Choose the cheapest eligible option and state its remaining budget.")


class ReplayTests(unittest.TestCase):
    def synthetic_zip(self, path, *, forged_score=False):
        fixture = {"rows": [{"id": "Kairo", "prior": PRIOR,
                             "current": CURRENT,
                             "oracle": {"choice": "A", "remaining": 10}}]}
        raw = '{"choice":"B","remaining":30}'
        typed = '{"choice":"A","remaining":10}'
        arms = [{"arm": name, "output": typed if i else raw,
                 "score": {"correct": 1 if i or forged_score else 0}}
                for i, name in enumerate(audit.ARMS)]
        original = {"rows": [{"id": "Kairo", "arms": arms}]}
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as z:
            z.writestr(audit.FIXTURE_PATH, json.dumps(fixture))
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("NATIVE_CASE/report.json", json.dumps(original))
            z.writestr("V13-Phone-Run116-Native.zip", inner.getvalue())

    def test_wrong_raw_native_text_refused_typed_text_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "synthetic-not-native.zip"
            self.synthetic_zip(p)
            with patch.object(replay.audit, "audit", return_value={
                "scores": dict(zip(audit.ARMS, (0, 1, 1)))}):
                result = replay.replay(p)
            self.assertEqual(result["accepted_counts"],
                             dict(zip(audit.ARMS, (0, 1, 1))))
            self.assertEqual(result["status"],
                             "ORIGINAL_NATIVE_OUTPUT_REPLAY_SHADOW_PASS")
            self.assertFalse(result["native_inference_this_run"])
            self.assertTrue(result["synthetic_body_observers"])
            self.assertFalse(result["output_committed"])
            self.assertEqual(result["delivery_authority"], 0)

    def test_forged_native_score_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "synthetic-forged-score.zip"
            self.synthetic_zip(p, forged_score=True)
            with patch.object(replay.audit, "audit", return_value={
                "scores": dict(zip(audit.ARMS, (0, 1, 1)))}):
                with self.assertRaisesRegex(ValueError,
                                            "REPLAY_EXPECTED_GATE_MISMATCH_RED"):
                    replay.replay(p)

    def test_wrong_original_outer_hash_refused_before_replay(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "fake.zip"
            self.synthetic_zip(p)
            with self.assertRaisesRegex(ValueError, "ORIGINAL_OUTER_SHA_RED"):
                replay.replay(p)


if __name__ == "__main__":
    unittest.main()

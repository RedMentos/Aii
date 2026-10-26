"""Run432 cross-review RED: learned user-rule second reader must fail cautious.

A NaN/Infinity classifier artifact must not silently turn a suspected restriction
into 'no rule'. Only software/source tests; no new rule-accuracy claim.
"""
import copy
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from v13 import userrules as U
from v13 import userrules_second as S


class Run432SecondOpinionIntegrity(unittest.TestCase):
    LINE = "Hallo, wie geht es dir?"

    def _second_reason(self):
        return [r for r in U.parse(self.LINE, second="jef")
                if r["kind"] == "UNCLEAR" and "SECOND" in r["reasons"]]

    def test_nonfinite_bias_must_ask_not_silently_decline(self):
        bad = copy.deepcopy(S.load())
        bad["bias"] = float("nan")
        with mock.patch.object(S, "load", return_value=bad):
            self.assertTrue(self._second_reason())

    def test_nonfinite_threshold_must_ask_not_silently_decline(self):
        bad = copy.deepcopy(S.load())
        bad["threshold"] = float("nan")
        with mock.patch.object(S, "load", return_value=bad):
            self.assertTrue(self._second_reason())

    def test_nonfinite_active_weight_must_ask_not_silently_decline(self):
        bad = copy.deepcopy(S.load())
        active = S.features(self.LINE)[0]
        bad["w"][active] = float("-inf")
        with mock.patch.object(S, "load", return_value=bad):
            self.assertTrue(self._second_reason())

    def test_nonfinite_json_artifact_is_refused_before_cache(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad-second.json"
            path.write_text(json.dumps({
                "schema": "USER_RULES_SECOND_V1", "dim": S.DIM,
                "bias": float("nan"), "threshold": 0.43,
                "weights": {"0": 0.1}
            }), encoding="utf-8")
            with self.assertRaises(ValueError):
                S.load(path)

    def test_valid_model_score_and_caution_behavior_unchanged(self):
        m = S.load()
        self.assertTrue(math.isfinite(S.score(self.LINE, m)))
        self.assertEqual(S.suspects(self.LINE, m),
                         S.score(self.LINE, m) >= m["threshold"])
        self.assertTrue(S.suspects("Du lässt die Finger von meinen Aufnahmen."))


if __name__ == "__main__":
    unittest.main()

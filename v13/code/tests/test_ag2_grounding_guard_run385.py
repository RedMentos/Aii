"""Run385 RED-first: AG2 input boundaries and optimistic modality check (SQLite Runtime)."""
import copy
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from v13.runtime import Runtime
from v13.agi import hub
from v13.agi.grounding import KEY


class GroundingGuardRun385(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.tmp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.g = hub(self.runtime).grounding

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def state(self):
        return copy.deepcopy(self.g.box.load()[0])

    def test_nonbool_modality_flags_fail_closed_without_writes(self):
        original = self.state()
        for bad in ("false", "off", "0", 1, 0, None, [], {}):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    self.g.set_modality("camera", bad)
                self.assertEqual(self.state(), original)

    def test_step8_modalities_cannot_be_activated_through_ag2(self):
        original = self.state()
        for name in ("screen", "camera", "audio", "effector"):
            with self.subTest(name=name):
                with self.assertRaises(PermissionError):
                    self.g.set_modality(name, True)
                self.assertEqual(self.state(), original)
                with self.assertRaises(PermissionError):
                    self.g.expect("sensing", "ctx", {}, modality=name)

    def test_preexisting_step8_flag_cannot_bypass_unimplemented_port_gate(self):
        # A pre-patch database may already contain a camera=True flag.
        st, version = self.g.box.load()
        st["modalities"]["camera"] = True
        self.runtime.store.set_state(KEY, st, expected=version)
        with self.assertRaises(PermissionError):
            self.g.expect("camera_capture", "ctx", {}, modality="camera")
        self.assertEqual(self.g.report()["open"], 0)
        # Disabling a stale flag remains an allowed cleanup operation.
        self.g.set_modality("camera", False)
        self.assertFalse(self.state()["modalities"]["camera"])

    def test_existing_text_tool_paths_and_explicit_disable_preserved(self):
        self.g.set_modality("text", True)
        aid, pred = self.g.expect("text_answer", "ctx", {"question": "x"})
        self.assertEqual(pred["coverage"], 0)
        rec = self.g.observe(aid, "ok")
        self.assertEqual(rec["cause"], "SELF")
        self.g.set_modality("text", False)
        with self.assertRaises(PermissionError):
            self.g.expect("text_answer", "ctx", {})
        self.g.set_modality("tool", True)
        aid, _ = self.g.expect("tool:calc", "x", {"x": 1}, modality="tool")
        self.assertEqual(self.g.observe(aid, {"status": "EXECUTED", "result": 2})["grounded_error"], 1.)

    def test_modality_rechecked_within_optimistic_state_mutation(self):
        original_load = self.g.box.load
        calls = 0

        def raced_load():
            nonlocal calls
            calls += 1
            if calls == 2:
                st, version = original_load()
                st["modalities"]["text"] = False
                self.runtime.store.set_state(KEY, st, expected=version)
            return original_load()

        with mock.patch.object(self.g.box, "load", side_effect=raced_load):
            with self.assertRaises(PermissionError):
                self.g.expect("text_answer", "ctx", {})
        self.assertEqual(self.g.report()["open"], 0)
        self.assertFalse(self.state()["modalities"]["text"])

    def test_counterfactual_rejects_invalid_coverage_denominator(self):
        before = self.state()
        for bad in (0, -1, True, False, "20", None, float("nan"), float("inf"), float("-inf")):
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError):
                    self.g.counterfactual("text_answer", "ctx", coverage_full=bad)
                self.assertEqual(self.state(), before)

    def test_valid_counterfactual_remains_nonfactual_and_ood_bounded(self):
        unseen = self.g.counterfactual("text_answer", "ctx", coverage_full=20)
        self.assertEqual(unseen["authority"], "SIMULATION_NOT_FACT")
        self.assertTrue(unseen["ood"])
        self.assertEqual(unseen["counterfactual_confidence"], 0.)
        aid, _ = self.g.expect("text_answer", "ctx", {})
        self.g.observe(aid, "ok")
        seen = self.g.counterfactual("text_answer", "ctx", coverage_full=1)
        self.assertEqual(seen["authority"], "SIMULATION_NOT_FACT")
        self.assertFalse(seen["ood"])
        self.assertEqual(seen["coverage_share"], 1.)
        self.assertEqual(seen["counterfactual_confidence"], 1.)
        self.assertTrue(math.isfinite(seen["counterfactual_confidence"]))


if __name__ == "__main__":
    unittest.main()

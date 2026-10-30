"""Small source/gradient integrity checks for the *separate* native 350M probe.

These tests use only synthetic tensors. They cannot substitute for the pinned
LFM2.5 real-master Action run or establish any V13 gate.
"""
import subprocess
import sys
from pathlib import Path
import unittest

import torch
from scripts import bodyjepa_real_master_gradient_20261030 as native

SCRIPT = Path(native.__file__)


class BodyJepaNativeProbeContract(unittest.TestCase):
    def test_gradient_norm_is_exact_l2_and_handles_unselected_parameters(self):
        grads = (torch.tensor([3., 4.]), None, torch.tensor([-12.]))
        self.assertAlmostEqual(native.norm(grads), 13.)
        self.assertEqual(native.norm([None, None]), 0.)

    def test_frozen_digest_tracks_every_frozen_tensor_not_adapter(self):
        m = torch.nn.Module()
        m.register_parameter("frozen_a", torch.nn.Parameter(
            torch.arange(5, dtype=torch.float32), requires_grad=False))
        m.register_parameter("frozen_b", torch.nn.Parameter(
            torch.arange(7, dtype=torch.float32), requires_grad=False))
        m.register_parameter("adapter", torch.nn.Parameter(
            torch.ones(3, dtype=torch.float32), requires_grad=True))
        first, n = native.tensor_digest(m)
        self.assertEqual(n, 12)
        with torch.no_grad():
            m.adapter.add_(1.)
        self.assertEqual(native.tensor_digest(m), (first, n))
        with torch.no_grad():
            m.frozen_b[-1].add_(1.)
        self.assertNotEqual(native.tensor_digest(m)[0], first)

    def test_native_opt_in_required_before_master_or_model_load(self):
        run = subprocess.run(
            [sys.executable, str(SCRIPT), "--master", "/nonexistent/v13-master",
             "--out", "/nonexistent/v13-result"],
            capture_output=True, text=True, timeout=15)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("--execute-native", run.stderr)
        self.assertNotIn("Traceback", run.stderr)

    def test_chat_template_requires_one_real_int64_batch_row(self):
        class Fake:
            def __init__(self, row):
                self.row = row
                self.kw = None

            def apply_chat_template(self, *args, **kw):
                self.kw = kw
                return {"input_ids": self.row}

        good = Fake(torch.tensor([[7, 8, 9]], dtype=torch.long))
        self.assertEqual(native.prompt_ids(good, "invented prompt"), [7, 8, 9])
        self.assertTrue(good.kw["return_dict"])
        self.assertEqual(good.kw["return_tensors"], "pt")
        self.assertTrue(good.kw["add_generation_prompt"])
        for bad in (torch.tensor([7, 8]), torch.tensor([[7], [8]]),
                    torch.empty((1, 0), dtype=torch.long),
                    torch.tensor([[7., 8.]]), [[7, 8]], None):
            with self.subTest(bad=repr(bad)):
                with self.assertRaisesRegex(ValueError, "single nonempty int64"):
                    native.prompt_ids(Fake(bad), "invented prompt")

    def test_fixture_is_disjoint_invented_and_model_revision_is_pinned(self):
        self.assertEqual(len(native.PROMPTS), 2)
        self.assertEqual(len(set(native.PROMPTS)), 2)
        self.assertEqual(len(set(native.TARGETS)), 2)
        self.assertEqual(native.SEED, 73)
        self.assertEqual(len(native.MASTER_SHA256), 64)
        self.assertEqual(native.REVISION, "120bf032c36dd1273de754669da040dba7ad4982")


if __name__ == "__main__":
    unittest.main()

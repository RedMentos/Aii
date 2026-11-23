"""Run13P pure source/gradient contracts; no native model downloads."""
import math
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

import torch

from scripts import bodyjepa_ce_contrast_gradient_run13p as p


class GradientAttributionRun13P(unittest.TestCase):
    def test_frozen_disjoint_fixture_and_no_runtime_authority(self):
        self.assertEqual(p.fixture_hash(), p.FIXTURE_SHA256)
        self.assertEqual(p.SEED, 257)
        self.assertEqual(len(p.FIXTURE), 4)
        self.assertEqual(len({q for q, _ in p.FIXTURE}), 4)
        self.assertEqual(len({a for _, a in p.FIXTURE}), 4)
        self.assertEqual(p.WEIGHT, .25)
        self.assertEqual(p.TEMP, .1)
        self.assertEqual(sorted(p.DERANGEMENT), list(range(4)))
        self.assertTrue(all(i != j for i, j in enumerate(p.DERANGEMENT)))

    def test_signed_direction_and_weighted_ratio(self):
        ce = [torch.tensor([3., 4.])]
        own = [torch.tensor([4., 3.])]
        wrong = [torch.tensor([-4., -3.])]
        predictor = [torch.tensor([0., 2.])]
        out = p.gradient_summary(torch, ce, own, wrong, predictor)
        self.assertAlmostEqual(out["ce_adapter_l2"], 5.)
        self.assertAlmostEqual(out["contrastive_adapter_l2"], 5.)
        self.assertAlmostEqual(out["shuffled_adapter_l2"], 5.)
        self.assertAlmostEqual(out["contrastive_predictor_l2"], 2.)
        self.assertAlmostEqual(out["ce_vs_contrastive_signed_cosine"], 24/25)
        self.assertAlmostEqual(out["correct_vs_shuffled_signed_cosine"], -1.)
        self.assertAlmostEqual(out["weighted_contrastive_over_ce_l2"], .25)

    def test_zero_missing_nonfinite_and_misaligned_fail_closed(self):
        valid = [torch.tensor([1., 2.])]
        zero = [torch.zeros(2)]
        nan = [torch.tensor([float("nan"), 2.])]
        cases = [
            ([], valid, valid, valid),
            (valid, [], valid, valid),
            (valid, valid, valid, []),
            (zero, valid, valid, valid),
            (valid, zero, valid, valid),
            (valid, valid, zero, valid),
            (valid, valid, valid, zero),
            (valid, nan, valid, valid),
            (valid, valid, nan, valid),
            (valid, valid + valid, valid, valid),
        ]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                p.gradient_summary(torch, *args)

    def test_detach_grads_preserves_shape_and_rejects_bad_gradient(self):
        params = [torch.nn.Parameter(torch.ones(2)),
                  torch.nn.Parameter(torch.ones(3))]
        grads = p._detach_grads([torch.tensor([2., 3.]), None], params)
        self.assertEqual(len(grads), 2)
        self.assertFalse(grads[0].requires_grad)
        self.assertEqual(grads[1].tolist(), [0., 0., 0.])
        for bad in ([torch.ones(4), None],
                    [torch.tensor([float("inf"), 1.]), None],
                    [torch.ones(2)]):
            with self.assertRaises(ValueError):
                p._detach_grads(bad, params)

    def test_frozen_tensor_digest_detects_real_changes(self):
        m = torch.nn.Linear(3, 2)
        for x in m.parameters():
            x.requires_grad_(False)
        a, n = p.tensor_digest(m)
        b, n2 = p.tensor_digest(m)
        self.assertEqual((a, n), (b, n2))
        with torch.no_grad():
            m.weight[0, 0] += 1.
        c, _ = p.tensor_digest(m)
        self.assertNotEqual(a, c)

    def test_explicit_opt_in_and_refuse_overwrite_before_native(self):
        with TemporaryDirectory() as td:
            path = Path(td)
            with self.assertRaises(SystemExit):
                p.main(["--master", str(path), "--out", str(path / "out")])
            (path / "out").write_text("keep")
            with self.assertRaisesRegex(ValueError, "REFUSE_OVERWRITE"):
                p.main(["--master", str(path), "--out", str(path / "out"),
                        "--execute-native"])
            self.assertEqual((path / "out").read_text(), "keep")


if __name__ == "__main__":
    unittest.main()

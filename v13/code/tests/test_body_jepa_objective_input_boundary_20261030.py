"""IH-H25 research ObjectiveAdapter input boundary; fail-closed before student graph."""
import unittest

import torch

from tests.test_body_jepa_objective_bridge_20261030 import BodyJepaObjectiveBridgeTests
from v13.body_jepa_objective_bridge import research_loss


class BodyJepaObjectiveInputBoundaryTests(BodyJepaObjectiveBridgeTests):
    # Inherit the existing tiny-model fixture and the established valid-path
    # assertions, so any guard cannot accidentally disable the research loss.

    def test_boolean_eligibility_is_not_a_numeric_credit_measure(self):
        for weights in ([True, .5, .25], [1., False, .25],
                        torch.tensor([True, True, False])):
            with self.subTest(weights=str(weights)):
                with self.assertRaises(ValueError):
                    research_loss(dict(self.batch, eligibility=weights))

    def test_both_view_pairs_have_typed_aligned_lengths(self):
        bad_lens = (
            [3, 2, 3],                              # not a Tensor
            torch.tensor([3, 2]),                   # fewer source rows
            torch.tensor([3., 2., 3.]),             # fractional token counts
            torch.tensor([3, 0, 3]),                # empty row
            torch.tensor([3, 999, 3]),              # beyond padded width
        )
        for key in ("context_view_ids", "target_view_ids"):
            for lens in bad_lens:
                with self.subTest(key=key, lengths=str(lens)):
                    pair = (self.batch[key][0], lens)
                    with self.assertRaises(ValueError):
                        research_loss(dict(self.batch, **{key: pair}))

    def test_target_latents_source_rows_and_finiteness(self):
        for target in (self.target[:2], torch.full_like(self.target, float("nan"))):
            with self.subTest(shape=tuple(target.shape)):
                with self.assertRaises(ValueError):
                    research_loss(dict(self.batch, target_latents=target))

    def test_view_ids_are_integral_and_source_aligned(self):
        for key in ("context_view_ids", "target_view_ids"):
            ids, lens = self.batch[key]
            for bad_ids in (ids.float(), ids[:2], torch.full_like(ids, -1)):
                with self.subTest(key=key, shape=tuple(bad_ids.shape)):
                    with self.assertRaises(ValueError):
                        research_loss(dict(self.batch, **{key: (bad_ids, lens)}))


if __name__ == "__main__":
    unittest.main()

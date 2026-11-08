import pytest
from v13.body_jepa import anchor_retention_kl


def test_anchor_retention_measures_actual_candidate_logits():
    torch = pytest.importorskip('torch')
    class Model:
        def __init__(self, shift):
            self.shift = shift
        def __call__(self, ids):
            class Output: pass
            out = Output()
            out.logits = torch.stack([torch.tensor([[3., 0.], [0., 3.]]) + self.shift])
            return out
    seq = [1, 2]
    base = torch.log_softmax(Model(torch.zeros((2, 2)))(torch.tensor([seq])).logits[0], -1)
    assert anchor_retention_kl(torch, Model(torch.zeros((2, 2))), [seq], [base]) == pytest.approx(0, abs=1e-7)
    shifted = torch.tensor([[0., 2.], [2., 0.]])
    assert anchor_retention_kl(torch, Model(shifted), [seq], [base]) > 0.5
    assert anchor_retention_kl(torch, Model(shifted), [], []) is None
    with pytest.raises(ValueError):
        anchor_retention_kl(torch, Model(shifted), [seq], [])
    with pytest.raises(ValueError, match='invalid retention logits'):
        anchor_retention_kl(torch, Model(torch.full((2, 2), float('nan'))), [seq], [base])

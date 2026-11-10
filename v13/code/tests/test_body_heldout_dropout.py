"""Regression: retention probes must not depend on training dropout RNG."""
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

torch=pytest.importorskip("torch")
from v13.body_jepa import heldout_retention_kl


class DropoutBody(torch.nn.Module):
    def __init__(self):
        super().__init__()
        torch.manual_seed(310)
        self.base=torch.nn.Linear(5,5,bias=False)
        self.base.requires_grad_(False)
        self.adapter=torch.nn.Linear(5,5,bias=False)
        self.dropout=torch.nn.Dropout(p=.85)
        self.disabled=False

    @contextmanager
    def disable_adapter(self):
        was=self.disabled
        self.disabled=True
        try:
            yield
        finally:
            self.disabled=was

    def forward(self,input_ids):
        x=torch.nn.functional.one_hot(input_ids,num_classes=5).float()
        logits=self.base(x)
        if not self.disabled:
            logits=logits+self.adapter(self.dropout(x))
        return SimpleNamespace(logits=logits)


def test_retention_is_repeatable_with_dropout_and_restores_training_state():
    m=DropoutBody().train()
    probes=[[1,2,3],[2,4,1]]
    initial_rng=torch.get_rng_state().clone()
    a=heldout_retention_kl(torch,m,probes)
    assert torch.equal(initial_rng,torch.get_rng_state())
    b=heldout_retention_kl(torch,m,probes)
    assert a==b
    assert all(x>0 for x in a)
    assert m.training and m.dropout.training and not m.disabled
    assert m.adapter.weight.grad is None


@pytest.mark.parametrize("bad", [[],[-1],[True],["3"]])
def test_retention_bad_probe_restores_training_mode(bad):
    m=DropoutBody().train()
    with pytest.raises(ValueError,match="heldout probe"):
        heldout_retention_kl(torch,m,[bad])
    assert m.training and m.dropout.training and not m.disabled


def test_retention_nonfinite_baseline_restores_training_mode():
    m=DropoutBody().train()
    with torch.no_grad():
        m.base.weight.fill_(float("nan"))
    with pytest.raises(ValueError,match="invalid heldout distribution"):
        heldout_retention_kl(torch,m,[[1,2]])
    assert m.training and m.dropout.training and not m.disabled


def test_retention_respects_caller_eval_mode():
    m=DropoutBody().eval()
    heldout_retention_kl(torch,m,[[1,2]])
    assert not m.training and not m.dropout.training

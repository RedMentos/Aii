"""Body-JEPA streamed exact KL with real Torch weight gradients; tiny CPU-only body.

No actual B1/B2 weights, tokenizer or trained utility is claimed.
"""
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

torch=pytest.importorskip("torch")
from v13.body_jepa import streamed_anchor_kl, BodyJepaTrainer


class TinyPeftLike(torch.nn.Module):
    def __init__(self):
        super().__init__()
        torch.manual_seed(31)
        self.base=torch.nn.Linear(5,5,bias=False)
        self.base.requires_grad_(False)
        self.adapter=torch.nn.Linear(5,5,bias=False)
        self.disabled=False
        self.dropout=torch.nn.Dropout(0.)

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
        result=self.base(x)
        if not self.disabled:
            result=result+.25*self.adapter(x)
        return SimpleNamespace(logits=result)


def test_streamed_kl_matches_full_cached_distribution_and_updates_only_adapter():
    model=TinyPeftLike()
    ids=[1,2,3,4]
    with torch.no_grad(),model.disable_adapter():
        reference=torch.log_softmax(model(torch.tensor([ids])).logits[0],-1)
    adapted=torch.log_softmax(model(torch.tensor([ids])).logits[0],-1)
    cached=(reference.exp()*(reference-adapted)).sum(-1).mean()
    model.train(True)
    kl=streamed_anchor_kl(torch,model,ids)
    assert torch.allclose(kl,cached,rtol=1e-5,atol=1e-7)
    assert model.training and not model.disabled
    before=model.adapter.weight.detach().clone()
    kl.backward()
    assert model.base.weight.grad is None
    assert model.adapter.weight.grad is not None
    assert torch.isfinite(model.adapter.weight.grad).all()
    opt=torch.optim.SGD(model.adapter.parameters(),lr=.05)
    opt.step()
    assert not torch.equal(model.adapter.weight,before)
    assert not model.disabled


@pytest.mark.parametrize("bad",[[],[-1],[True],["3"],[1,3.2]])
def test_streaming_anchor_rejects_malformed_token_ids(bad):
    m=TinyPeftLike()
    with pytest.raises(ValueError,match="token IDs"):
        streamed_anchor_kl(torch,m,bad)


def test_streaming_anchor_fails_closed_without_disable_adapter():
    with pytest.raises(ValueError,match="disable_adapter"):
        streamed_anchor_kl(torch,object(),[1,2])


def test_streaming_anchor_restores_train_and_disabled_mode_after_exception():
    m=TinyPeftLike()
    m.train(True)
    m.base.weight.data.fill_(float('nan'))
    with pytest.raises(ValueError,match="distribution"):
        streamed_anchor_kl(torch,m,[1,3])
    assert m.training and not m.disabled


def test_historical_caching_remains_explicit_default_for_registered_experiments():
    from v13.body_jepa import DEFAULTS
    assert DEFAULTS["anchor_reference_mode"]=="cached"

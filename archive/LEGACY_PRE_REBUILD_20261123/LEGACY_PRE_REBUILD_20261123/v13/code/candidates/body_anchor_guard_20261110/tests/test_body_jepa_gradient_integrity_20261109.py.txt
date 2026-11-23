"""Real torch gradient-integrity checks before the body JEPA optimizer step."""
import pytest
torch = pytest.importorskip("torch")
from v13.body_jepa import checked_gradient_step


def setup():
    p=torch.nn.Parameter(torch.tensor([1., 2.]))
    opt=torch.optim.SGD([p],lr=.1)
    return p,opt


def test_finite_gradient_changes_actual_parameter():
    p,opt=setup()
    (p.square().sum()).backward()
    checked_gradient_step(torch,[p],opt)
    assert torch.allclose(p.detach(),torch.tensor([.8,1.6]))


@pytest.mark.parametrize("bad", [float("nan"),float("inf"),-float("inf")])
def test_nonfinite_gradient_never_updates_parameter(bad):
    p,opt=setup()
    before=p.detach().clone()
    p.grad=torch.tensor([1.,bad])
    with pytest.raises(ValueError,match="nonfinite"):
        checked_gradient_step(torch,[p],opt)
    assert torch.equal(p.detach(),before)
    assert not opt.state


def test_missing_gradients_fail_closed():
    p,opt=setup()
    with pytest.raises(ValueError,match="no trainable gradients"):
        checked_gradient_step(torch,[p],opt)
    assert torch.equal(p.detach(),torch.tensor([1.,2.]))


def test_explicit_clip_bounds_update():
    p,opt=setup()
    p.grad=torch.tensor([30.,40.])
    checked_gradient_step(torch,[p],opt,max_norm=1.)
    assert torch.linalg.vector_norm(p.grad).item() <= 1.00001
    assert torch.linalg.vector_norm(p.detach()-torch.tensor([1.,2.])).item() <= .100001


@pytest.mark.parametrize("bad", [0.,-1.,float("nan"),float("inf"),True])
def test_invalid_clip_never_updates(bad):
    p,opt=setup()
    p.grad=torch.ones_like(p)
    with pytest.raises(ValueError,match="grad_clip_norm"):
        checked_gradient_step(torch,[p],opt,max_norm=bad)
    assert torch.equal(p.detach(),torch.tensor([1.,2.]))

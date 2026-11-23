"""EMA adapter target swap must never leave the live body partially modified."""
import pytest
torch = pytest.importorskip("torch")
from v13.body_jepa import EmaAdapter


def test_swap_restores_student_after_target_exception():
    params = [torch.nn.Parameter(torch.tensor([1.])), torch.nn.Parameter(torch.tensor([2.]))]
    ema = EmaAdapter(params, .9)
    for s in ema.shadow:
        s.fill_(99.)
    with pytest.raises(RuntimeError, match="target failed"):
        with ema.swap():
            assert all(float(p.item()) == 99. for p in params)
            raise RuntimeError("target failed")
    assert [float(p.item()) for p in params] == [1., 2.]


def test_enter_failure_rolls_back_prior_copies(monkeypatch):
    params = [torch.nn.Parameter(torch.tensor([1.])), torch.nn.Parameter(torch.tensor([2.]))]
    ema = EmaAdapter(params, .9)
    for s in ema.shadow:
        s.fill_(99.)
    original = torch.Tensor.copy_
    calls = [0]
    def fail_second_once(self, other, *args, **kwargs):
        calls[0] += 1
        if calls[0] == 2:
            raise RuntimeError("injected copy failure")
        return original(self, other, *args, **kwargs)
    monkeypatch.setattr(torch.Tensor, "copy_", fail_second_once)
    with pytest.raises(RuntimeError, match="injected copy failure"):
        with ema.swap():
            pytest.fail("body must not execute")
    assert [float(p.item()) for p in params] == [1., 2.]


@pytest.mark.parametrize("decay", [float("nan"), float("inf"), -0.1, 1.0])
def test_invalid_decay_rejected(decay):
    with pytest.raises(ValueError):
        EmaAdapter([torch.nn.Parameter(torch.tensor([1.]))], decay)


def test_changed_parameter_metadata_fails_before_mutation():
    p = torch.nn.Parameter(torch.tensor([1.]))
    ema = EmaAdapter([p], .9)
    ema.shadow[0] = torch.tensor([99., 100.])
    with pytest.raises(ValueError, match="metadata"):
        with ema.swap():
            pass
    assert p.item() == 1.


def test_ema_update_rejects_corrupted_shadow_before_any_change():
    a = torch.nn.Parameter(torch.tensor([1.]))
    b = torch.nn.Parameter(torch.tensor([2.]))
    ema = EmaAdapter([a,b], .9)
    ema.shadow[1] = torch.tensor([4.,5.])
    before = ema.shadow[0].clone()
    with pytest.raises(ValueError, match="metadata"):
        ema.update()
    assert torch.equal(ema.shadow[0], before)
    assert ema.updates == 0

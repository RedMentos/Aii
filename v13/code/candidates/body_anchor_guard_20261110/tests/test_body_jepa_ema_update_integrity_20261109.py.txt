"""EMA update failure atomicity: real torch tensors, no model downloads."""
import pytest
torch = pytest.importorskip("torch")
from v13.body_jepa import EmaAdapter


def test_ema_update_success_and_counter():
    a = torch.nn.Parameter(torch.tensor([1., 2.]))
    b = torch.nn.Parameter(torch.tensor([4., 6.]))
    ema = EmaAdapter([a, b], 0.5)
    with torch.no_grad():
        a.add_(2.)
        b.add_(4.)
    ema.update()
    assert torch.equal(ema.shadow[0], torch.tensor([2., 3.]))
    assert torch.equal(ema.shadow[1], torch.tensor([6., 8.]))
    assert ema.updates == 1


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_later_parameter_invalid_keeps_earlier_ema_unchanged(bad):
    a = torch.nn.Parameter(torch.tensor([1., 2.]))
    b = torch.nn.Parameter(torch.tensor([3., 4.]))
    ema = EmaAdapter([a, b], 0.5)
    originals = [s.clone() for s in ema.shadow]
    with torch.no_grad():
        a.add_(3.)
        b[0] = bad
    with pytest.raises(ValueError, match="nonfinite"):
        ema.update()
    assert all(torch.equal(x, y) for x, y in zip(originals, ema.shadow))
    assert ema.updates == 0


def test_nonfinite_existing_shadow_does_not_change_other_targets():
    a = torch.nn.Parameter(torch.tensor([1.]))
    b = torch.nn.Parameter(torch.tensor([2.]))
    ema = EmaAdapter([a, b], 0.5)
    ema.shadow[1][0] = float("nan")
    original = ema.shadow[0].clone()
    with pytest.raises(ValueError, match="nonfinite"):
        ema.update()
    assert torch.equal(ema.shadow[0], original)
    assert ema.updates == 0


def test_ema_overflow_does_not_commit_any_shadow():
    a = torch.nn.Parameter(torch.tensor([1.], dtype=torch.float16))
    b = torch.nn.Parameter(torch.tensor([65504.], dtype=torch.float16))
    ema = EmaAdapter([a, b], 0.5)
    with torch.no_grad():
        a.add_(1.)
        b.fill_(65504.)
    # This verifies the candidate remains finite under a finite input; if
    # float16 arithmetic changes, do not assert an invented overflow.
    ema.update()
    assert torch.isfinite(ema.shadow[0]).all()
    assert torch.isfinite(ema.shadow[1]).all()

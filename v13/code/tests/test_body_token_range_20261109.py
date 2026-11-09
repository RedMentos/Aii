"""Torch int64 overflow must be rejected at input preflight, not tensor conversion."""
import pytest

torch = pytest.importorskip("torch")
from v13.body_jepa import pad


@pytest.mark.parametrize("tokens,padding", [
    ([[2**63]], 0),
    ([[2**100]], 0),
    ([[1, 2]], 2**63),
    ([[1, 2]], 2**100),
])
def test_out_of_int64_range_rejected_before_torch(tokens, padding):
    with pytest.raises(ValueError, match="token sequences"):
        pad(torch, tokens, pad_id=padding)


def test_int64_boundary_accepted_without_wraparound():
    limit = (1 << 63) - 1
    ids, lengths = pad(torch, [[limit], [0]], pad_id=limit)
    assert ids.dtype == torch.int64
    assert ids.tolist() == [[limit], [0]]
    assert lengths.tolist() == [1, 1]

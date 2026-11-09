"""Frozen anchor cache: no shared mutable state, no unbounded device retention."""
import pytest

torch = pytest.importorskip("torch")
from v13.body_jepa import BodyJepaTrainer

@pytest.fixture(autouse=True)
def clean_cache():
    old = BodyJepaTrainer._anchor_cache
    BodyJepaTrainer._anchor_cache = {}
    yield
    BodyJepaTrainer._anchor_cache = old

def test_cache_is_detached_cpu_snapshot_and_independent_on_read():
    p = torch.nn.Parameter(torch.randn(2, 3))
    original = torch.log_softmax(p, -1)
    seq = [[1, 2]]
    BodyJepaTrainer._cache_anchors(("master",), seq, [original])
    assert not BodyJepaTrainer._anchor_cache[("master",)][1][0].requires_grad
    assert BodyJepaTrainer._anchor_cache[("master",)][1][0].device.type == "cpu"
    seq[0][0] = 99
    with torch.no_grad():
        original.fill_(42)
    first_seq, first_lp = BodyJepaTrainer._cached_anchors(("master",))
    assert first_seq == [[1, 2]]
    assert not torch.all(first_lp[0] == 42)
    first_seq[0][0] = 100
    first_lp[0].fill_(123)
    second_seq, second_lp = BodyJepaTrainer._cached_anchors(("master",))
    assert second_seq == [[1, 2]]
    assert not torch.all(second_lp[0] == 123)

def test_cache_evicts_oldest_and_refreshes_replacement():
    for i in range(3):
        BodyJepaTrainer._cache_anchors((i,), [[i]], [torch.zeros(1, 2)])
    assert list(BodyJepaTrainer._anchor_cache) == [(1,), (2,)]
    BodyJepaTrainer._cache_anchors((1,), [[8]], [torch.ones(1, 2)])
    BodyJepaTrainer._cache_anchors((3,), [[3]], [torch.zeros(1, 2)])
    assert list(BodyJepaTrainer._anchor_cache) == [(1,), (3,)]
    assert BodyJepaTrainer._cached_anchors((1,))[0] == [[8]]

@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_cache_moves_cuda_reference_to_cpu():
    t = torch.randn(1, 4, device="cuda", requires_grad=True)
    BodyJepaTrainer._cache_anchors(("cuda",), [[1]], [t])
    assert BodyJepaTrainer._cached_anchors(("cuda",))[1][0].device.type == "cpu"

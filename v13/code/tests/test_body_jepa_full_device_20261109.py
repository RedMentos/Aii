"""Device-aligned body JEPA batches and weight-validation regressions."""
import inspect
import pytest

torch = pytest.importorskip("torch")
from v13.body_jepa import pad, BodyJepaTrainer, validated_weights


def test_pad_can_materialize_directly_on_requested_device():
    ids, lengths = pad(torch, [[4, 5], [7]], pad_id=0, device=torch.device("cpu"))
    assert ids.tolist() == [[4, 5], [7, 0]]
    assert lengths.tolist() == [2, 1]
    assert ids.device == lengths.device == torch.device("cpu")


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_pad_cuda_lengths_and_ids():
    ids, lengths = pad(torch, [[4, 5], [7]], device=torch.device("cuda"))
    assert ids.device.type == lengths.device.type == "cuda"
    assert ids.cpu().tolist() == [[4, 5], [7, 0]]


def test_trainer_explicitly_places_ce_and_anchor_inputs_on_model_device():
    source = inspect.getsource(BodyJepaTrainer.fit)
    assert "device=model_device" in source
    assert "device=per.device" in source
    assert "anchor_logp[j].to(device=cl.device" in source
    assert "make_predictor(torch,dim).to(device=model_device)" in source
    assert "detach().cpu().numpy()" in source


@pytest.mark.parametrize("weights", [
    [float("nan")], [float("inf")], [-1.0], [0.0, 0.0], ["oops"], [None]
])
def test_trainer_rejects_invalid_eligibility_before_model_load(weights):
    with pytest.raises(ValueError, match="eligibility"):
        validated_weights([{"weight": w} for w in weights])


def test_eligibility_accepts_bounded_nonnegative_batch():
    assert validated_weights([{"weight": 0.0}, {"weight": 0.5}, {}]) == [0.0, 0.5, 1.0]

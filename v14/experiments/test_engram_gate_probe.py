import torch

from v14.experiments.engram_gate_probe import (
    LearnedContextTopK,
    make_task,
    run_seed,
)


def test_inference_gate_selects_exact_top_k():
    model = LearnedContextTopK()
    model.eval()
    inputs, _ = make_task(0, 32, 7)
    _, mask = model(inputs)
    assert torch.all(mask.sum(dim=1) == 8)


def test_context_conditioned_masks_and_negative_control():
    result = run_seed(0, "learned", epochs=12)
    assert result.max_gate_grad_l2 > 0
    assert result.parameter_l1_delta > 0
    assert result.gate_parameter_l1_delta > 0
    assert result.context_mask_jaccard < 0.25
    assert result.context_shuffle_accuracy < 0.60


def test_dense_and_static_baselines_have_no_learned_gate_metrics():
    dense = run_seed(0, "dense", epochs=2)
    static = run_seed(0, "static", epochs=2)
    assert dense.max_gate_grad_l2 == 0
    assert static.max_gate_grad_l2 == 0
    assert dense.context_mask_jaccard is None
    assert static.context_shuffle_accuracy is None

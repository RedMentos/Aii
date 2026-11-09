"""Fail-closed numeric and token preflight for body-JEPA training inputs."""
import math
import pytest
from v13.body_jepa import validated_weights, pad

torch = pytest.importorskip("torch")


def test_finite_weights_remain_usable():
    assert validated_weights([{"weight": 0.25}, {"weight": 0.75}]) == [0.25, 0.75]


@pytest.mark.parametrize("items", [
    [{"weight": 1e308}, {"weight": 1e308}],
    [{"weight": float("inf")}],
    [{"weight": float("nan")}],
    [{"weight": 0.0}, {"weight": 0.0}],
])
def test_invalid_or_overflowing_eligibility_fails_before_model_load(items):
    with pytest.raises(ValueError, match="eligibility"):
        validated_weights(items)


@pytest.mark.parametrize("seqs", [
    [[1, True]],
    [[1, -1]],
    [[1, 2.0]],
    [[1, float("nan")]],
    [[1], []],
    [[1], "23"],
])
def test_invalid_token_sequences_rejected(seqs):
    with pytest.raises(ValueError, match="token sequences"):
        pad(torch, seqs)


def test_negative_or_boolean_padding_id_rejected():
    for value in (-1, True):
        with pytest.raises(ValueError, match="token sequences"):
            pad(torch, [[1, 2]], pad_id=value)


def test_valid_padding_retains_lengths_and_values():
    ids, lens = pad(torch, [[2, 3], [4]], pad_id=0)
    assert ids.tolist() == [[2, 3], [4, 0]]
    assert lens.tolist() == [2, 1]

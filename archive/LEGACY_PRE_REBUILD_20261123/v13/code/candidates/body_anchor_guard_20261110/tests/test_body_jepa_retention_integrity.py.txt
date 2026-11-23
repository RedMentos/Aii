"""Regression for frozen-anchor retention validation and dropout-stable probing."""
import pytest

torch = pytest.importorskip("torch")
from v13.body_jepa import anchor_retention_kl


class TinyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.dropout = torch.nn.Dropout(p=0.9)
        self.proj = torch.nn.Linear(3, 3, bias=False)
        with torch.no_grad():
            self.proj.weight.copy_(torch.eye(3))

    def forward(self, ids):
        x = torch.nn.functional.one_hot(ids, 3).float()
        return type("Out", (), {"logits": self.proj(self.dropout(x))})()


def test_train_mode_dropout_does_not_change_retention_or_flags():
    model = TinyModel()
    model.train()
    model.dropout.eval()  # mixed child state must survive
    anchor = [0, 1, 2]
    with torch.no_grad():
        base = torch.log_softmax(model(torch.tensor([anchor])).logits[0], -1)
    model.dropout.train()
    first = anchor_retention_kl(torch, model, [anchor], [base])
    second = anchor_retention_kl(torch, model, [anchor], [base])
    assert first == second == 0.0
    assert model.training and model.dropout.training


def test_corrupted_reference_is_rejected_and_flags_restored():
    model = TinyModel()
    model.train()
    anchor = [0, 1, 2]
    with torch.no_grad():
        base = torch.log_softmax(model(torch.tensor([anchor])).logits[0], -1)
    with pytest.raises(ValueError, match="unnormalized"):
        anchor_retention_kl(torch, model, [anchor], [base + 0.5])
    assert model.training and model.dropout.training


def test_nonfinite_reference_rejected():
    model = TinyModel()
    base = torch.full((3, 3), float("nan"))
    with pytest.raises(ValueError, match="nonfinite"):
        anchor_retention_kl(torch, model, [[0, 1, 2]], [base])

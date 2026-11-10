"""Body-JEPA retention must place anchor tokens on the candidate device."""
import pytest

torch = pytest.importorskip("torch")
from v13.body_jepa import anchor_retention_kl


class TinyBody(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.eye(3))

    def forward(self, ids):
        x = torch.nn.functional.one_hot(ids, 3).float()
        return type("Out", (), {"logits": x @ self.weight})()


def test_anchor_token_tensor_explicitly_targets_model_device(monkeypatch):
    model = TinyBody()
    anchors = [[0, 1, 2]]
    with torch.no_grad():
        base = torch.log_softmax(model(torch.tensor(anchors)).logits[0], -1)
    original = torch.tensor
    seen = []

    def observed_tensor(*args, **kwargs):
        seen.append(kwargs.get("device"))
        return original(*args, **kwargs)

    monkeypatch.setattr(torch, "tensor", observed_tensor)
    result = anchor_retention_kl(torch, model, anchors, [base])
    assert result == 0.0
    assert seen == [model.weight.device]

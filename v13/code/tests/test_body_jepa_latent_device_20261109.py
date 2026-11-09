"""B1/B2 JEPA latent device placement; CPU structural proof, optional CUDA runtime proof."""
import pytest

torch = pytest.importorskip("torch")
from v13.body_jepa import last_token_latent


class TinyHidden(torch.nn.Module):
    def __init__(self, output_device=None):
        super().__init__()
        self.output_device = output_device

    def forward(self, input_ids, attention_mask, output_hidden_states):
        assert output_hidden_states is True
        assert input_ids.device == attention_mask.device
        values = input_ids.float().unsqueeze(-1)
        if self.output_device is not None:
            values = values.to(self.output_device)
        return type("Hidden", (), {"hidden_states": (values,)})()


def test_mask_and_index_ranges_explicitly_use_input_device(monkeypatch):
    real = torch.arange
    requested = []

    def tracked(*args, **kwargs):
        requested.append(kwargs.get("device"))
        return real(*args, **kwargs)

    monkeypatch.setattr(torch, "arange", tracked)
    ids = torch.tensor([[3, 4, 0], [5, 6, 7]])
    lengths = torch.tensor([2, 3])
    result = last_token_latent(torch, TinyHidden(), (ids, lengths))
    assert result.tolist() == [[4.0], [7.0]]
    assert requested == [ids.device, ids.device]


def test_hidden_device_mismatch_fails_closed():
    ids = torch.tensor([[3, 4]])
    lengths = torch.tensor([2])
    with pytest.raises(ValueError, match="latent device"):
        last_token_latent(torch, TinyHidden(output_device="meta"), (ids, lengths))


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_real_cuda_input_with_cpu_collator_lengths():
    ids = torch.tensor([[3, 4, 0], [5, 6, 7]], device="cuda")
    lengths = torch.tensor([2, 3], device="cpu")
    result = last_token_latent(torch, TinyHidden().cuda(), (ids, lengths))
    assert result.device == ids.device
    assert result.cpu().tolist() == [[4.0], [7.0]]

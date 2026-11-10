"""Only run inside the hash-bound reconciled Body-JEPA source copy."""
import math
from unittest.mock import patch

import pytest
import torch

from v13.body_jepa import EmaAdapter, anchor_retention_kl, anchor_retention_values
from v13 import body_jepa_atomic_step_candidate as atomic
from test_body_jepa_checkpoint_fit import TinyTrainer


def test_new_per_anchor_retention_and_old_scalar_api_are_consistent():
    class Body(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.weight = torch.nn.Parameter(torch.eye(2))
        def forward(self, ids):
            logits = torch.nn.functional.one_hot(ids % 2, 2).float() @ self.weight
            return type('Output', (), {'logits': logits})()
    model = Body()
    anchors = [[0, 1], [1, 1]]
    reference = [torch.log_softmax(model(torch.tensor([seq])).logits[0].detach(), -1) for seq in anchors]
    values = anchor_retention_values(torch, model, anchors, reference)
    assert len(values) == 2 and max(abs(value) for value in values) < 1e-7
    assert anchor_retention_kl(torch, model, anchors, reference) == 0.
    assert anchor_retention_values(torch, model, [], []) == []
    assert anchor_retention_kl(torch, model, [], []) is None
    with pytest.raises(ValueError, match='unnormalized'):
        anchor_retention_values(torch, model, [[0]], [torch.tensor([[-5., -5.]])])


def test_nonfinite_ema_is_rejected_without_partial_mutation():
    p = torch.nn.Parameter(torch.tensor([1.]))
    ema = EmaAdapter([p], .5)
    original = ema.shadow[0].clone()
    with torch.no_grad():
        p.fill_(float('nan'))
    with pytest.raises(ValueError, match='nonfinite'):
        ema.update()
    assert torch.equal(ema.shadow[0], original) and ema.updates == 0


def test_nonfinite_optimizer_state_cannot_mutate_parameter():
    p = torch.nn.Parameter(torch.tensor([1.]))
    ema = EmaAdapter([p], .5)
    opt = torch.optim.AdamW([p], lr=.01)
    p.grad = torch.ones_like(p)
    atomic.checked_training_step(torch, [p], opt, ema)
    before, before_ema = p.detach().clone(), ema.shadow[0].clone()
    opt.state[p]['exp_avg'].fill_(float('nan'))
    p.grad = torch.ones_like(p)
    with pytest.raises(ValueError, match='nonfinite'):
        atomic.checked_training_step(torch, [p], opt, ema)
    assert torch.equal(p.detach(), before) and torch.equal(ema.shadow[0], before_ema)
    assert ema.updates == 1


def test_real_tiny_fit_updates_parameters_and_emits_both_anchor_contracts(tmp_path):
    cfg = {'rank':2, 'targets':('c_attn',), 'locality_swaps':0, 'anchor_weight':.1,
           'jepa_weight':.3, 'jepa_target':'ema', 'max_steps':1, 'min_steps':1,
           'target_loss':-1., 'threads':1, 'seed':9}
    items = [{'memory_id':'one', 'prompt':'What is the item?', 'target':'Blue'},
             {'memory_id':'two', 'prompt':'Where is the item?', 'target':'North'}]
    trainer = TinyTrainer('/tmp/synthetic-master', tmp_path, master_sha256='a'*64,
                          anchors=['First anchor', 'Second anchor'], cfg=cfg)
    observed = []
    original = atomic.checked_training_step
    def record_step(torch_module, params, opt, ema, max_norm=None):
        params = list(params)
        before = [param.detach().clone() for param in params]
        original(torch_module, params, opt, ema, max_norm)
        observed.append(any(not torch.equal(param.detach(), old) for param, old in zip(params, before)))
    with patch.object(atomic, 'checked_training_step', side_effect=record_step):
        result = trainer.fit(items, 'synthetic-generation')
    metrics = result['metrics']
    assert observed == [True]
    assert metrics['steps'] == metrics['ema_updates'] == 1
    assert metrics['retention_anchor_count'] == metrics['retention_probe_count'] == 2
    assert math.isfinite(metrics['retention_anchor_kl_mean'])
    assert math.isfinite(metrics['retention_anchor_kl_max'])
    assert metrics['retention_anchor_kl_max'] >= metrics['retention_anchor_kl_mean']
    assert metrics['final_anchor_kl'] == pytest.approx(metrics['retention_anchor_kl_mean'], abs=1e-7)


def test_real_tiny_fit_ema_failure_rolls_back_step(tmp_path):
    cfg = {'rank':2, 'targets':('c_attn',), 'locality_swaps':0, 'anchor_weight':0.,
           'jepa_weight':.3, 'jepa_target':'ema', 'max_steps':1, 'min_steps':1,
           'target_loss':-1., 'threads':1, 'seed':9}
    items = [{'memory_id':'one', 'prompt':'What is the item?', 'target':'Blue'},
             {'memory_id':'two', 'prompt':'Where is the item?', 'target':'North'}]
    trainer = TinyTrainer('/tmp/synthetic-master', tmp_path, master_sha256='a'*64, cfg=cfg)
    seen = []
    original = atomic.checked_training_step
    def fail_and_check(torch_module, params, opt, ema, max_norm=None):
        params = list(params)
        before = [p.detach().clone() for p in params]
        grads = [None if p.grad is None else p.grad.detach().clone() for p in params]
        with patch.object(ema, 'update', side_effect=RuntimeError('injected ema failure')):
            with pytest.raises(RuntimeError, match='injected ema failure'):
                original(torch_module, params, opt, ema, max_norm)
        assert all(torch.equal(p.detach(), old) for p, old in zip(params, before))
        assert all((p.grad is None and old is None) or torch.equal(p.grad, old) for p, old in zip(params, grads))
        assert not opt.state and ema.updates == 0
        seen.append(True)
        raise RuntimeError('stopped after verified rollback')
    with patch.object(atomic, 'checked_training_step', side_effect=fail_and_check):
        with pytest.raises(RuntimeError, match='stopped after verified rollback'):
            trainer.fit(items, 'synthetic-generation')
    assert seen == [True]

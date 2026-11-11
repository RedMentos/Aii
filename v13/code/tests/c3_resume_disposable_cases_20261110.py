"""Actual Torch C3 checkpoint corruption and restart tests in a disposable copy."""
import copy
import hashlib
from unittest.mock import patch

import pytest
import torch
from transformers import GPT2Config, GPT2LMHeadModel

from test_body_jepa_checkpoint_fit import Tokenizer
from v13 import lora_resume_atomic_candidate as guarded
from v13.common import Cancelled, Unavailable
from v13.lora_trainer import LoraTrainer


class Model(torch.nn.Module):
    def __init__(self, value=1.):
        super().__init__()
        self.lora_test = torch.nn.Parameter(torch.tensor([value]))


def ready_checkpoint():
    model = Model()
    opt = torch.optim.AdamW(model.parameters(), lr=.01)
    model.lora_test.grad = torch.ones_like(model.lora_test)
    opt.step()
    state = {'dataset_hash': 'dataset', 'step': 1,
             'hist': [{'step': 1, 'ce': 1., 'anchor_kl': 0., 'jepa': None}],
             'lora': {'lora_test': model.lora_test.detach().clone()},
             'opt': copy.deepcopy(opt.state_dict()),
             'optimizer_layout': guarded.optimizer_layout(model, opt),
             'shuffle_rng_state': torch.Generator().manual_seed(19).get_state(),
             'torch_rng_state': torch.get_rng_state().clone(),
             'resume_source_sha256': 'a' * 64}
    return model, opt, state


def restore(model, opt, state):
    return guarded.restore(torch, model, opt, state, 'dataset', 4, 'a' * 64, 19, 2, 0, 0.)


def test_valid_restore_and_next_real_optimizer_step_match():
    source, source_opt, state = ready_checkpoint()
    target = Model(9.)
    target_opt = torch.optim.AdamW(target.parameters(), lr=.01)
    gen = restore(target, target_opt, state)
    assert torch.equal(gen.get_state(), state['shuffle_rng_state'])
    assert torch.equal(target.lora_test, source.lora_test)
    for model, opt in ((source, source_opt), (target, target_opt)):
        opt.zero_grad()
        model.lora_test.grad = torch.full_like(model.lora_test, .25)
        opt.step()
    assert torch.equal(target.lora_test, source.lora_test)


def test_corrupt_resume_fails_before_adapter_or_optimizer_changes():
    _, _, original = ready_checkpoint()
    cases = []
    bad = copy.deepcopy(original); bad['opt'] = {}; cases.append(bad)
    bad = copy.deepcopy(original); next(iter(bad['opt']['state'].values()))['exp_avg'].fill_(float('nan')); cases.append(bad)
    bad = copy.deepcopy(original); next(iter(bad['opt']['state'].values()))['exp_avg_sq'].fill_(-1); cases.append(bad)
    bad = copy.deepcopy(original); next(iter(bad['opt']['state'].values()))['exp_avg'] = torch.zeros(2); cases.append(bad)
    bad = copy.deepcopy(original); next(iter(bad['opt']['state'].values()))['step'].fill_(2); cases.append(bad)
    bad = copy.deepcopy(original); bad['opt']['state'][999] = {}; cases.append(bad)
    bad = copy.deepcopy(original); bad['opt']['param_groups'][0]['lr'] = .09; cases.append(bad)
    bad = copy.deepcopy(original); bad['optimizer_layout'] = [['foreign']]; cases.append(bad)
    bad = copy.deepcopy(original); bad['shuffle_rng_state'] = torch.tensor([1, 2], dtype=torch.uint8); cases.append(bad)
    bad = copy.deepcopy(original); bad['torch_rng_state'] = torch.tensor([1, 2], dtype=torch.uint8); cases.append(bad)
    bad = copy.deepcopy(original); bad['resume_source_sha256'] = 'b' * 64; cases.append(bad)
    bad = copy.deepcopy(original); bad['hist'][0]['jepa'] = float('nan'); cases.append(bad)
    for state in cases:
        target = Model(9.)
        opt = torch.optim.AdamW(target.parameters(), lr=.01)
        before = target.lora_test.detach().clone()
        old_opt = copy.deepcopy(opt.state_dict())
        old_rng = torch.get_rng_state().clone()
        with pytest.raises((ValueError, RuntimeError)):
            restore(target, opt, state)
        assert torch.equal(target.lora_test, before)
        assert opt.state_dict() == old_opt
        assert torch.equal(torch.get_rng_state(), old_rng)


def test_failed_optimizer_load_restores_adapter_and_optimizer():
    _, _, state = ready_checkpoint()
    target = Model(9.)
    opt = torch.optim.AdamW(target.parameters(), lr=.01)
    before = target.lora_test.detach().clone()
    old = copy.deepcopy(opt.state_dict())
    real = opt.load_state_dict
    calls = []
    def fail_once(value):
        calls.append(True)
        if len(calls) == 1:
            raise RuntimeError('injected optimizer load failure')
        return real(value)
    with patch.object(opt, 'load_state_dict', side_effect=fail_once):
        with pytest.raises(RuntimeError, match='injected optimizer'):
            restore(target, opt, state)
    assert len(calls) == 2 and torch.equal(target.lora_test, before)
    assert opt.state_dict() == old


def test_partial_model_load_is_rolled_back():
    _, _, state = ready_checkpoint()
    target = Model(9.)
    opt = torch.optim.AdamW(target.parameters(), lr=.01)
    before = target.lora_test.detach().clone()
    real = target.load_state_dict
    calls = []
    def fail_after_load(value, strict=False):
        result = real(value, strict=strict)
        calls.append(True)
        if len(calls) == 1:
            raise RuntimeError('injected model load failure')
        return result
    with patch.object(target, 'load_state_dict', side_effect=fail_after_load):
        with pytest.raises(RuntimeError, match='injected model'):
            restore(target, opt, state)
    assert len(calls) == 2 and torch.equal(target.lora_test, before) and not opt.state


def test_failed_recovery_marks_optimizer_unusable():
    _, _, state = ready_checkpoint()
    target = Model(9.)
    opt = torch.optim.AdamW(target.parameters(), lr=.01)
    with patch.object(opt, 'load_state_dict', side_effect=RuntimeError('injected load failure')):
        with pytest.raises(RuntimeError, match='discard model and optimizer'):
            restore(target, opt, state)
    assert opt._v13_c3_resume_unusable is True
    with pytest.raises(RuntimeError, match='discard C3 optimizer'):
        restore(target, opt, state)


def test_source_binding_changes_with_weight_generation_master_and_config():
    args = ['a' * 64, 'generation', [{'prompt': 'p', 'target': 't', 'weight': 1.}],
            ['anchor'], [{'prompt': 'probe'}], {'lr': .01}]
    tag = guarded.binding(*args)
    for index, value in ((0, 'b' * 64), (1, 'another-generation'),
                         (2, [{'prompt': 'p', 'target': 't', 'weight': .5}]),
                         (5, {'lr': .02})):
        changed = copy.deepcopy(args)
        changed[index] = value
        assert guarded.binding(*changed) != tag
    assert guarded.binding(None, *args[1:]) is None


class TinyLora(LoraTrainer):
    def _load(self):
        torch.set_num_threads(1)
        torch.manual_seed(123)
        model = GPT2LMHeadModel(GPT2Config(vocab_size=64, n_positions=96,
                                         n_ctx=96, n_embd=16, n_layer=1, n_head=2))
        return torch, Tokenizer(), model

    @staticmethod
    def _greedy(torch_module, model, ids, n):
        return [2]

    def _export(self, torch_module, model, out, lc):
        self.saved_adapter = {k: v.detach().clone() for k, v in model.state_dict().items() if 'lora_' in k}
        path = out / 'adapter.gguf'
        path.write_bytes(b'SYNTHETIC_TEST_NOT_NATIVE')
        return {'gguf': str(path), 'gguf_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def test_real_tiny_c3_fit_resume_and_reject_changed_weight(tmp_path):
    cfg = {'rank': 2, 'targets': ('c_attn',), 'locality_swaps': 0, 'anchor_weight': 0.,
           'jepa_weight': 0., 'max_steps': 2, 'min_steps': 2, 'target_loss': -1.,
           'ckpt_every': 1, 'threads': 1, 'seed': 9}
    items = [{'memory_id': 'one', 'prompt': 'What is the item?', 'target': 'Blue', 'weight': 1.},
             {'memory_id': 'two', 'prompt': 'Where is the item?', 'target': 'North', 'weight': 1.}]
    full = TinyLora('/tmp/synthetic-master', tmp_path / 'full', master_sha256='a' * 64, cfg=cfg)
    expected = full.fit(items, 'synthetic-generation')
    partial = TinyLora('/tmp/synthetic-master', tmp_path / 'resume', master_sha256='a' * 64, cfg=cfg)
    calls = []
    def cancel_after_one():
        calls.append(True)
        return len(calls) >= 2
    with pytest.raises(Cancelled):
        partial.fit(items, 'synthetic-generation', cancel=cancel_after_one)
    checkpoint = next((tmp_path / 'resume').rglob('ckpt.pt'))
    original = checkpoint.read_bytes()
    changed = copy.deepcopy(items)
    changed[0]['weight'] = .25
    foreign = TinyLora('/tmp/synthetic-master', tmp_path / 'resume', master_sha256='a' * 64, cfg=cfg)
    with pytest.raises(Unavailable, match='invalid LoRA training checkpoint'):
        foreign.fit(changed, 'synthetic-generation')
    assert checkpoint.read_bytes() == original
    other_generation = TinyLora('/tmp/synthetic-master', tmp_path / 'resume', master_sha256='a' * 64, cfg=cfg)
    with pytest.raises(Unavailable, match='invalid LoRA training checkpoint'):
        other_generation.fit(items, 'other-generation')
    corrupted = torch.load(checkpoint, map_location='cpu', weights_only=True)
    next(iter(corrupted['opt']['state'].values()))['exp_avg'].fill_(float('nan'))
    torch.save(corrupted, checkpoint)
    invalid_bytes = checkpoint.read_bytes()
    bad_optimizer = TinyLora('/tmp/synthetic-master', tmp_path / 'resume', master_sha256='a' * 64, cfg=cfg)
    with pytest.raises(Unavailable, match='invalid LoRA training checkpoint'):
        bad_optimizer.fit(items, 'synthetic-generation')
    assert checkpoint.read_bytes() == invalid_bytes
    checkpoint.write_bytes(original)
    resumed = TinyLora('/tmp/synthetic-master', tmp_path / 'resume', master_sha256='a' * 64, cfg=cfg)
    actual = resumed.fit(items, 'synthetic-generation')
    assert actual['metrics']['resumed'] and actual['metrics']['steps'] == 2
    assert actual['metrics']['loss_history'] == expected['metrics']['loss_history']
    assert set(resumed.saved_adapter) == set(full.saved_adapter)
    for key in full.saved_adapter:
        assert torch.equal(resumed.saved_adapter[key], full.saved_adapter[key])


def test_actual_consolidation_calls_tiny_c3_trainer_without_promoting(tmp_path):
    from v13.agi.weights import WeightConsolidation
    from v13.runtime import Runtime
    r = Runtime(tmp_path / 'runtime')
    try:
        r.sleep.cycle.set_policy('enabled', 'off')
        event = r.store.event(r.session, 'What is the name of my cat?')
        r.memory.feedback(event['event_id'], 'fact', 'Mitzi', permission='learn')
        cfg = {'rank': 2, 'targets': ('c_attn',), 'locality_swaps': 0, 'anchor_weight': 0.,
               'jepa_weight': 0., 'max_steps': 1, 'min_steps': 1, 'target_loss': -1.,
               'ckpt_every': 1, 'threads': 1, 'seed': 9, 'max_tokens': 80}
        trainer = TinyLora('/tmp/synthetic-master', tmp_path / 'training', master_sha256='a' * 64, cfg=cfg)
        trainer.role = 'C3_LANGUAGE'
        weights = WeightConsolidation(r.store, r.cfg | {'learning_mode': 'SHADOW_UPDATE'}, trainer=trainer)
        staged = weights.stage(require_replay_pass=False)
        trained = weights.train_and_gate(staged['batch_id'])
        assert trained['status'] == 'TRAINED'
        assert trained['trainer']['metrics']['steps'] == 1
        assert trained['trainer']['role'] == 'C3_LANGUAGE'
        assert trainer.saved_adapter and next((tmp_path / 'training').rglob('ckpt.pt')).is_file()
        assert not (r.home / 'config/lora-active.json').exists()
    finally:
        r.close()

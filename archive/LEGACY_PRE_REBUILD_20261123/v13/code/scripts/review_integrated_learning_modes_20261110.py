"""Synthetic read-only review of exact #1663 code; select checkout via PYTHONPATH."""
import json
import tempfile
from pathlib import Path
import torch
from v13 import world_model
from v13.body_jepa import EmaAdapter
from v13.lora_trainer import _valid_lora_resume, _valid_lora_tensors
from v13.runtime import Runtime

p = torch.nn.Parameter(torch.tensor([1.]))
ema = EmaAdapter([p], .9)
with torch.no_grad():
    p.fill_(float('nan'))
ema.update()
assert not bool(torch.isfinite(ema.shadow[0]).all()) and ema.updates == 1

m = torch.nn.Module()
m.lora_test = torch.nn.Parameter(torch.tensor([1.]))
opt = torch.optim.AdamW(m.parameters())
state = {'dataset_hash': 'synthetic', 'step': 0, 'hist': [],
         'lora': {'lora_test': torch.tensor([9.])}, 'opt': {}}
assert _valid_lora_resume(state, 'synthetic', 10)
assert _valid_lora_tensors(torch, state['lora'], m.state_dict())
m.load_state_dict(state['lora'], strict=False)
try:
    opt.load_state_dict(state['opt'])
except KeyError:
    pass
else:
    raise AssertionError('expected optimizer error')
assert float(m.lora_test.detach()[0]) == 9.

m2 = torch.nn.Module()
m2.lora_test = torch.nn.Parameter(torch.tensor([1.]))
opt2 = torch.optim.AdamW(m2.parameters())
m2.lora_test.grad = torch.ones_like(m2.lora_test)
opt2.step()
snapshot = opt2.state_dict()
next(iter(snapshot['state'].values()))['exp_avg'].fill_(float('nan'))
state2 = {'dataset_hash': 'synthetic', 'step': 1,
          'hist': [{'step': 1, 'ce': 1., 'anchor_kl': 0.}],
          'lora': {'lora_test': torch.tensor([1.])}, 'opt': snapshot}
assert _valid_lora_resume(state2, 'synthetic', 10)
assert _valid_lora_tensors(torch, state2['lora'], m2.state_dict())
m2.load_state_dict(state2['lora'], strict=False)
opt2.load_state_dict(state2['opt'])
opt2.zero_grad()
m2.lora_test.grad = torch.ones_like(m2.lora_test)
opt2.step()
assert not bool(torch.isfinite(m2.lora_test).all())

with tempfile.TemporaryDirectory(prefix='v13-pr1663-counterexamples-') as d:
    r = Runtime(Path(d))
    r.sleep.cycle.set_policy('enabled', 'off')
    original_transitions = world_model.transitions
    try:
        r.cfg['learning_mode'] = 'RECORD_ONLY'
        world_model.transitions = lambda store, limit=2048: [
            {'s': [0., 0., 0., 0.], 'y': [.5, .1, 1.],
             'a': world_model.ACTIONS[0], 'action_id': 'synthetic_action'}]
        online = r.online_world_update(limit=64)
        assert online['learned'] == 1 and online['seen'] == 1
        rows = [{'s': [i/100., (i%3)/3., .2, .3], 'y': [.1, .2, i/100.],
                 'a': world_model.ACTIONS[i % len(world_model.ACTIONS)],
                 'action_id': 'synthetic_action_%03d' % i} for i in range(80)]
        world_model.transitions = lambda store, limit=2048: rows
        jepa = r.world_jepa_update(steps=1, limit=128)
        assert jepa['train_rows'] > 0 and jepa['source_verified'] is True
        r.world_jepa_save()
        world_model.transitions = lambda store, limit=2048: []
        del r._world_jepa_online
        checkpoint = r.world_jepa_restore()
        assert checkpoint['restored'] is True
        print(json.dumps({'head': '95aea15a046e73acf82c67ccf934cebda651ef87',
                          'ema_nonfinite_accepted': True, 'ema_updates': ema.updates,
                          'malformed_optimizer_left_model_value': float(m.lora_test.detach()[0]),
                          'nonfinite_optimizer_moment_corrupted_next_step': True,
                          'record_only_online_learned': online['learned'],
                          'record_only_jepa_trained_rows': jepa['train_rows'],
                          'restore_with_empty_current_stub_feed': checkpoint['restored'],
                          'claim_limit': 'synthetic Torch and stubbed transitions; not native/Redmi or real-source revocation'}, sort_keys=True))
    finally:
        world_model.transitions = original_transitions
        r.close()

"""Real Runtime/AG6/SQLite/Tiny-Torch Body route; no native model evidence."""
import json
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import torch

from v13 import agi, inputs
from v13 import body_jepa_runtime_candidate as route
from v13 import body_jepa_atomic_step_candidate as atomic
from v13.agi import trainers
from v13.body_jepa import BodyJepaTrainer
from v13.common import file_hash, Cancelled
from v13.lora_trainer import AdapterRegistry, runner_lora_args
from v13.operator import Operator
from v13.runtime import Runtime
from v13.sleep import SCHEDULE_KEY
from test_body_jepa_checkpoint_fit import TinyTrainer


def prepare(r, monkeypatch):
    r.sleep.cycle.set_policy('enabled', 'off')
    r._route = Mock(return_value=('simple', {'source': 'SYNTHETIC_BODY_ROUTE'}))
    r.pool.get = Mock(return_value=SimpleNamespace(role='C3_LANGUAGE', last_metrics={},
                       generate=lambda *a, **kw: iter(['synthetic answer'])))
    r.learner.output_delta = Mock(return_value=None)
    models = {}
    masters = {}
    for role in (*route.ROLES, 'C3_LANGUAGE'):
        model = r.home / 'models' / (role + '.gguf')
        model.parent.mkdir(parents=True, exist_ok=True)
        model.write_bytes(b'GGUF_SYNTHETIC_ONLY_' + role.encode())
        models[role] = model
        master = r.home / 'models' / ('master-' + role)
        master.mkdir()
        (master / 'model.safetensors').write_bytes(b'SYNTHETIC_MASTER_' + role.encode())
        (master / 'config.json').write_text(json.dumps({'model_type':'gpt2','hidden_size':16,'num_hidden_layers':1}))
        masters[role] = master
    (r.home / 'bin').mkdir(exist_ok=True)
    (r.home / 'bin/llama-server').write_bytes(b'SYNTHETIC_NOT_EXECUTED')
    original_path = r.models.path_for
    monkeypatch.setattr(r.models, 'path_for', lambda role: models[role] if role in models else original_path(role))
    monkeypatch.setattr(trainers, '_torch', lambda kind='lora': True)
    monkeypatch.setattr(trainers, 'arch_match', lambda *a: True)
    monkeypatch.setattr(BodyJepaTrainer, '_load', TinyTrainer._load)
    monkeypatch.setattr(BodyJepaTrainer, '_greedy', staticmethod(TinyTrainer._greedy))
    monkeypatch.setattr(BodyJepaTrainer, '_export', TinyTrainer._export)
    r._body_test_deltas = []
    step = atomic.checked_training_step
    r._body_clean_step = step
    def record(torch_module, params, opt, ema, max_norm=None):
        params = list(params)
        before = [p.detach().clone() for p in params]
        step(torch_module, params, opt, ema, max_norm)
        r._body_test_deltas.append((route.box(r).load()[0]['selected'],
            any(not torch.equal(p.detach(), old) for p, old in zip(params, before)), ema.updates))
    monkeypatch.setattr(atomic, 'checked_training_step', record)
    return models, masters


@pytest.fixture
def live(tmp_path, monkeypatch):
    r = Runtime(tmp_path)
    models, masters = prepare(r, monkeypatch)
    try:
        yield r, models, masters
    finally:
        r.close()


def turn(r, text):
    event = r.submit(text)
    end = time.monotonic() + 10
    while not r.idle() and time.monotonic() < end:
        time.sleep(.003)
    assert r.idle() and r.last_answer()['status'] == 'FINAL', json.dumps(r.last_answer())
    return event


def feedback(r, permission='learn', prompt='What is Cedar color?', target='Blue'):
    event = turn(r, prompt)
    memory = r.memory.feedback(event, 'fact', target, permission=permission)
    return event, memory


def select(r, masters, role='B1_DETAIL'):
    op = Operator(r)
    out = json.loads(op.run(':growth trainer body-jepa ' + role + ' ' + str(masters[role])))
    assert out['active'] == 'body-jepa' and out['selected_role'] == role
    configured = json.loads(op.run(':growth trainer cfg rank=2 targets=\'["c_attn"]\' max_steps=1 min_steps=1 locality_swaps=0 anchor_weight=0 jepa_weight=0.3 threads=1 max_tokens=64 checkpoint_resume=true'))
    assert configured['body_cfg']['checkpoint_resume'] is True
    g = agi.hub(r)
    g.weights.trainer.anchors = []
    g.weights.trainer.probes = []
    g.weights.trainer.evaluator = None  # No native result is fabricated.
    return g


def test_real_body_operator_stage_train_separates_both_organs_and_c3(live):
    r, models, masters = live
    op = Operator(r)
    op.run(':learning shadow')
    _, memory = feedback(r)
    _, only_record = feedback(r, 'record', 'What is Alder color?', 'Green')
    g = select(r, masters)
    assert g.weights.role == 'B1_DETAIL'
    assert [i['memory_id'] for i in g.weights.candidates(False)] == [memory]
    staged = g.weights.stage('USER', require_replay_pass=False, include_sdft=True)
    batch = g.weights.batch(staged['batch_id'])
    assert batch['target_role'] == 'B1_DETAIL' and len(batch['items']) == 1
    result = g.weights.train(staged['batch_id'])
    assert result['status'] == 'TRAINED'
    assert result['trainer']['role'] == 'B1_DETAIL'
    assert result['trainer']['metrics']['steps'] == result['trainer']['metrics']['ema_updates'] == 1
    assert result['trainer']['metrics']['body_sources_verified'] is True
    assert result['trainer']['eval'] is None
    first_key, first_id = g.weights.state_key, staged['batch_id']
    first = result['trainer']['artifact']
    assert 'B1_DETAIL' in first
    assert AdapterRegistry(r.store).report()['active'] == {}
    g = select(r, masters, 'B2_GIST')
    second = g.weights.stage('USER', require_replay_pass=False)
    assert second['status'] == 'STAGED' and g.weights.state_key != first_key
    assert g.weights.batch(second['batch_id'])['target_role'] == 'B2_GIST'
    trained = g.weights.train(second['batch_id'])
    assert trained['status'] == 'TRAINED' and 'B2_GIST' in trained['trainer']['artifact']
    assert r._body_test_deltas == [('B1_DETAIL', True, 1), ('B2_GIST', True, 1)]
    assert first != trained['trainer']['artifact']
    with pytest.raises(ValueError):
        g.weights.batch(first_id)
    op.run(':growth trainer none')
    assert route.box(r).load()[0]['selected'] is None and agi.hub(r).weights.role == 'C3_LANGUAGE'
    g = select(r, masters)
    assert g.weights.batch(first_id)['status'] == 'TRAINED'


def test_record_only_and_pause_do_not_call_body_load(live, monkeypatch):
    r, _, masters = live
    feedback(r)
    g = select(r, masters)
    assert g.weights.stage('USER', require_replay_pass=False)['status'] == 'SKIPPED_RECORD_ONLY'
    Operator(r).run(':learning shadow')
    staged = g.weights.stage('USER', require_replay_pass=False)
    loader = Mock(side_effect=AssertionError('must not load model'))
    monkeypatch.setattr(g.weights.trainer, '_load', loader)
    inputs.set_pause(r.store, 'training', True)
    with pytest.raises(ValueError, match='veto'):
        g.weights.train(staged['batch_id'])
    loader.assert_not_called()
    assert g.weights.batch(staged['batch_id'])['status'] == 'STAGED'


@pytest.mark.parametrize('change', ['permission', 'prompt', 'source'])
def test_staged_body_data_is_revalidated_before_fit(live, monkeypatch, change):
    r, _, masters = live
    Operator(r).run(':learning shadow')
    event, mid = feedback(r)
    g = select(r, masters)
    staged = g.weights.stage('USER', require_replay_pass=False)
    loader = Mock(side_effect=AssertionError('must not load model'))
    monkeypatch.setattr(g.weights.trainer, '_load', loader)
    with r.store.tx() as db:
        if change == 'permission':
            db.execute("UPDATE feedback SET permission='record' WHERE event_id=?", (event,))
        elif change == 'prompt':
            db.execute("UPDATE memories SET key_text='Forged prompt' WHERE id=?", (mid,))
        else:
            db.execute('UPDATE sources SET deleted=1 WHERE id=(SELECT source_id FROM events WHERE id=?)', (event,))
    result = g.weights.train(staged['batch_id'])
    assert result['status'] == 'SOURCE_INVALID'
    loader.assert_not_called()


def test_body_choice_is_explicit_and_master_profile_is_bound(live):
    r, _, masters = live
    with pytest.raises(PermissionError):
        route.choose(r, 'B1_DETAIL', masters['B1_DETAIL'])
    with pytest.raises(ValueError, match='B1_DETAIL'):
        route.choose(r, 'C3_LANGUAGE', masters['C3_LANGUAGE'], authority='EXPLICIT_HUMAN')
    select(r, masters)
    (masters['B1_DETAIL'] / 'config.json').write_text('{}')
    out = trainers.install(agi.hub(r), r)
    assert out['active'] == 'none' and 'BODY_MASTER_BINDING_CHANGED' in out['reasons']


def test_body_choice_and_role_batch_survive_real_runtime_restart(tmp_path, monkeypatch):
    r = Runtime(tmp_path)
    try:
        _, masters = prepare(r, monkeypatch)
        Operator(r).run(':learning shadow')
        feedback(r)
        g = select(r, masters)
        staged = g.weights.stage('USER', require_replay_pass=False)
        original_step = r._body_clean_step
        r.close()
        r = Runtime(tmp_path)
        r.sleep.cycle.set_policy('enabled', 'off')
        models = {role:r.home / 'models' / (role + '.gguf') for role in (*route.ROLES, 'C3_LANGUAGE')}
        original_path = r.models.path_for
        monkeypatch.setattr(r.models, 'path_for', lambda role: models[role] if role in models else original_path(role))
        g = agi.hub(r)
        assert g.weights.role == 'B1_DETAIL'
        assert g.weights.batch(staged['batch_id'])['target_role'] == 'B1_DETAIL'
        # Drop the test recorder that closes over the old Runtime. The actual
        # optimizer path remains unchanged and runs in the reopened Runtime.
        monkeypatch.setattr(atomic, 'checked_training_step', original_step)
        g.weights.trainer.anchors=[];g.weights.trainer.probes=[];g.weights.trainer.evaluator=None
        trained=g.weights.train(staged['batch_id'])
        assert trained['status']=='TRAINED' and trained['trainer']['metrics']['ema_updates']==1
    finally:
        r.close()


def test_body_batch_cannot_cross_train_on_a_different_role(live):
    r, _, masters = live
    Operator(r).run(':learning shadow')
    feedback(r)
    g = select(r, masters)
    staged = g.weights.stage('USER', require_replay_pass=False)
    g.weights.trainer.role = 'B2_GIST'
    with pytest.raises(ValueError, match='target organ'):
        g.weights.train(staged['batch_id'])


def test_switch_to_record_only_after_staging_still_prevents_fit(live, monkeypatch):
    r, _, masters=live
    Operator(r).run(':learning shadow')
    feedback(r)
    g=select(r,masters)
    staged=g.weights.stage('USER',require_replay_pass=False)
    fit=Mock(side_effect=AssertionError('mode switch must prevent trainer call'))
    monkeypatch.setattr(g.weights.trainer,'fit',fit)
    r.cfg['learning_mode']='RECORD_ONLY'
    with pytest.raises(ValueError,match='RECORD_ONLY'):
        g.weights.train(staged['batch_id'])
    fit.assert_not_called()


def test_explicit_cancellation_before_fit_does_not_load_a_body(live, monkeypatch):
    r, _, masters=live
    Operator(r).run(':learning shadow')
    feedback(r)
    g=select(r,masters)
    staged=g.weights.stage('USER',require_replay_pass=False)
    loader=Mock(side_effect=AssertionError('cancel must prevent model loading'))
    monkeypatch.setattr(g.weights.trainer,'_load',loader)
    import threading
    cancel=threading.Event();cancel.set()
    with pytest.raises(Cancelled):
        g.weights.train(staged['batch_id'],cancel=cancel)
    loader.assert_not_called()


def test_existing_serving_registry_applies_only_to_its_exact_role_and_base(live, tmp_path):
    r, models, _ = live
    path = tmp_path / 'synthetic-adapter.gguf'
    path.write_bytes(b'SYNTHETIC_ADAPTER_PROTOCOL_TEST_ONLY')
    registry = AdapterRegistry(r.store)
    registry.activate('B1_DETAIL', path, file_hash(path), file_hash(models['B1_DETAIL']), 'synthetic-human-approved-protocol-test')
    assert runner_lora_args(r.home, 'B1_DETAIL', models['B1_DETAIL'])[:2] == ['--lora-scaled', str(path)]
    assert runner_lora_args(r.home, 'B2_GIST', models['B2_GIST']) == []
    assert runner_lora_args(r.home, 'C3_LANGUAGE', models['C3_LANGUAGE']) == []
    assert runner_lora_args(r.home, 'B1_DETAIL', models['B2_GIST']) == []
    registry.deactivate('B1_DETAIL')
    assert runner_lora_args(r.home, 'B1_DETAIL', models['B1_DETAIL']) == []


def test_body_training_does_not_overwrite_saved_c3_master_profile(live):
    r, _, masters = live
    op = Operator(r)
    op.run(':growth trainer lora ' + str(masters['C3_LANGUAGE']))
    original = dict(trainers._box(r.store).load()[0])
    select(r, masters, 'B1_DETAIL')
    select(r, masters, 'B2_GIST')
    op.run(':growth trainer lora')
    restored = trainers._box(r.store).load()[0]
    assert restored == original
    assert agi.hub(r).weights.role == 'C3_LANGUAGE'


def test_consent_revoked_after_a_real_step_never_publishes_trained_batch(live, monkeypatch):
    r, _, masters = live
    Operator(r).run(':learning shadow')
    event, _ = feedback(r)
    g = select(r, masters)
    staged = g.weights.stage('USER', require_replay_pass=False)
    step = atomic.checked_training_step
    def revoke(*args, **kwargs):
        step(*args, **kwargs)
        with r.store.tx() as db:
            db.execute("UPDATE feedback SET permission='record' WHERE event_id=?", (event,))
    monkeypatch.setattr(atomic, 'checked_training_step', revoke)
    with pytest.raises(ValueError, match='permission changed'):
        g.weights.train(staged['batch_id'])
    batch = g.weights.batch(staged['batch_id'])
    assert batch['status'] == 'STAGED' and batch['trainer'] is None
    assert r._body_test_deltas == [('B1_DETAIL', True, 1)]
    assert AdapterRegistry(r.store).report()['active'] == {}


def test_actual_scheduled_body_job_uses_correct_role_and_retains_checkpoint(live, monkeypatch):
    r, _, masters = live
    Operator(r).run(':learning shadow')
    event, _ = feedback(r)
    select(r, masters, 'B2_GIST')
    state, version = r.sleep.cycle.queue.load()
    state['items'][event] = {'event_id':event, 'reps':1, 'retired':False}
    r.store.set_state(SCHEDULE_KEY, state, expected=version)
    original_build = route.build
    def build(runtime):
        trainer, info = original_build(runtime)
        trainer.anchors = [];trainer.probes = [];trainer.evaluator = None
        return trainer, info
    monkeypatch.setattr(route, 'build', build)
    Operator(r).run(':growth consolidate')
    end = time.monotonic() + 10
    while time.monotonic() < end:
        pending = [e for e in r.sleep.scheduler.pending() if e['action']=='growth_consolidate']
        if not pending and r._body_test_deltas:
            break
        time.sleep(.01)
    g = agi.hub(r)
    assert r.idle() and r._body_test_deltas == [('B2_GIST', True, 1)]
    batches = g.weights.box.load()[0]['batches']
    assert len(batches)==1 and next(iter(batches.values()))['status']=='TRAINED'
    assert list((r.home/'training/ag6/body-jepa/B2_GIST').rglob('*.pt'))


def test_body_evaluator_gate_requires_separate_human_approval_before_serving(live):
    r, models, masters = live
    Operator(r).run(':learning shadow')
    feedback(r)
    g = select(r, masters)
    seen = []
    class SyntheticEvaluator:
        def evaluate(self, items, probes, **kwargs):
            seen.append('evaluate')
            return {'model_sha256':file_hash(models['B1_DETAIL']), 'kl_to_base':0., 'learned_recall':1.,
                    'base_eval':{'overall':1.,'unseen':1.,'near_miss_leak':0.},
                    'candidate_eval':{'overall':1.,'unseen':1.,'near_miss_leak':0.,'forgetting':{'rate':0.}},
                    'evidence':'SYNTHETIC_EVALUATOR_NOT_NATIVE'}
        def close(self):seen.append('close')
    g.weights.trainer.evaluator = lambda path:SyntheticEvaluator()
    staged = g.weights.stage('USER', require_replay_pass=False)
    result = g.weights.train_and_gate(staged['batch_id'])
    assert result['status']=='PENDING_USER' and seen==['evaluate','close']
    assert AdapterRegistry(r.store).report()['active']=={}
    def alter(state, role):state['batches'][staged['batch_id']]['trainer']['role']=role
    g.weights.box.mutate(lambda state:alter(state,'B2_GIST'))
    with pytest.raises(ValueError,match='organ'):
        g.weights.approve(staged['batch_id'])
    assert AdapterRegistry(r.store).report()['active']=={}
    g.weights.box.mutate(lambda state:alter(state,'B1_DETAIL'))
    approved = g.weights.approve(staged['batch_id'])
    assert approved['status']=='APPROVED'
    args = runner_lora_args(r.home,'B1_DETAIL',models['B1_DETAIL'])
    assert args[:2]==['--lora-scaled',result['trainer']['artifact']]
    assert runner_lora_args(r.home,'C3_LANGUAGE',models['C3_LANGUAGE'])==[]
    g.weights.rollback(staged['batch_id'])
    assert runner_lora_args(r.home,'B1_DETAIL',models['B1_DETAIL'])==[]

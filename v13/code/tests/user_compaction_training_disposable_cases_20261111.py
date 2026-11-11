"""Actual authorized numeric learning still uses compacted USER provenance."""
import json
import time

import pytest

import user_message_compaction_disposable_cases_20261111 as prep
from body_role_runtime_disposable_cases_20261111 import prepare as body_prepare, select
from c3_resume_disposable_cases_20261110 import TinyLora
from integrated_jepa_disposable_cases import populate
from v13.agi import hub
from v13.agi.weights import WeightConsolidation
from v13.operator import Operator
from v13.runtime import Runtime


@pytest.fixture
def live(tmp_path, monkeypatch):
    runtime = Runtime(tmp_path/'home')
    models, masters = body_prepare(runtime, monkeypatch)
    sent = [];prep.configure(runtime, sent)
    event, mid, ref, text = prep.seed(runtime)
    prep.enable(runtime)
    assert prep.request(runtime)['compacted']
    try:
        yield runtime, masters, event, mid, ref, text
    finally:
        runtime.close()


def test_actual_c3_step_after_user_text_compaction_keeps_source_and_sql_empty(live, tmp_path):
    runtime, _, event, mid, ref, text = live
    runtime.memory.feedback(event, 'fact', 'Blue', permission='learn')
    Operator(runtime).run(':learning shadow')
    cfg = {'rank':2, 'targets':('c_attn',), 'locality_swaps':0, 'anchor_weight':0.,
           'jepa_weight':0., 'max_steps':1, 'min_steps':1, 'target_loss':-1.,
           'ckpt_every':1, 'threads':1, 'seed':9, 'max_tokens':80}
    trainer = TinyLora('/tmp/synthetic-master', tmp_path/'tiny-c3', master_sha256='a'*64, cfg=cfg)
    trainer.role = 'C3_LANGUAGE'
    weights = WeightConsolidation(runtime.store, runtime.cfg, trainer=trainer)
    staged = weights.stage('USER', require_replay_pass=False)
    items = weights.batch(staged['batch_id'])['items']
    assert len(items) == 1 and items[0]['prompt'] == text and items[0]['source_dependencies'] == [ref]
    result = weights.train(staged['batch_id'])
    assert result['status'] == 'TRAINED' and result['trainer']['metrics']['steps'] == 1
    assert trainer.saved_adapter
    assert runtime.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == ''
    assert runtime.store.read_source(ref) == text
    assert not (runtime.home/'config/lora-active.json').exists()


def test_actual_body_step_after_user_text_compaction_keeps_ema_and_provenance(live):
    runtime, masters, event, mid, ref, text = live
    runtime.memory.feedback(event, 'fact', 'Blue ' * 120, permission='learn')
    Operator(runtime).run(':learning shadow')
    select(runtime, masters, 'B1_DETAIL')
    weights = hub(runtime).weights
    staged = weights.stage('USER', require_replay_pass=False)
    item = weights.batch(staged['batch_id'])['items'][0]
    assert item['prompt'] == text and item['source_dependencies'] == [ref]
    result = weights.train(staged['batch_id'])
    assert result['status'] == 'TRAINED'
    assert runtime._body_test_deltas and all(changed and ema > 0 for _, changed, ema in runtime._body_test_deltas)
    assert runtime.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == ''
    assert runtime.store.read_source(ref) == text
    assert not (runtime.home/'config/lora-active.json').exists()


def test_world_numeric_update_checkpoint_restart_contains_compacted_user_sources(live):
    runtime, _, event, mid, ref, text = live
    populate(runtime)
    Operator(runtime).run(':learning shadow')
    result = runtime.world_jepa_update(steps=1, limit=128, authority='EXPLICIT_HUMAN')
    assert result['trained']
    ids = {row['id'] for row in runtime.store.rows('SELECT id FROM actions WHERE event_id=?', (event,))}
    assert ids and ids.issubset(runtime._world_jepa_lineage)
    assert runtime.world_jepa_save(authority='EXPLICIT_HUMAN')['persisted']
    lineage = dict(runtime._world_jepa_lineage)
    home = runtime.home;runtime.close()
    restarted = Runtime(home)
    try:
        restarted.sleep.cycle.set_policy('enabled', 'off')
        Operator(restarted).run(':learning shadow')
        assert restarted.world_jepa_restore(authority='EXPLICIT_HUMAN')['restored']
        assert restarted._world_jepa_lineage == lineage
        assert restarted.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'] == ''
        assert restarted.store.read_source(ref) == text
    finally:
        restarted.close()

"""Optimizer/inverse/RNG continuity on the actual staged World Runtime route."""
import copy
import hashlib
import io
import json
import zipfile

import numpy as np
import pytest

from v13 import world_jepa as wj
from v13 import world_jepa_shadow_checkpoint as checkpoint
from v13 import world_jepa_training_state_candidate as state
from v13.operator import Operator
from v13.runtime import Runtime
from integrated_jepa_disposable_cases import populate


def same(a, b):
    assert type(a) is type(b)
    if isinstance(a, np.ndarray):
        assert a.dtype == b.dtype and np.array_equal(a, b)
    elif isinstance(a, dict):
        assert a.keys() == b.keys()
        for key in a:
            same(a[key], b[key])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            same(x, y)
    else:
        assert a == b


def test_exact_runtime_continuation_with_and_without_restart(tmp_path):
    r = Runtime(tmp_path)
    try:
        populate(r)
        op = Operator(r)
        op.run(':learning shadow')
        result = json.loads(op.run(':growth jepa 2 160'))
        assert result['trained'] and result['optimizer_steps'] == 2 and not result['optimizer_state_continued']
        initial = r._world_jepa_online
        saved = json.loads(op.run(':growth jepa save'))
        assert saved['optimizer_state_persisted'] is True
        assert initial._training_state['main']['t'] == 2
        assert initial._training_state['bootstrap'][0]['adam']['t'] == 1
        assert any(np.any(a) for a in initial._training_state['main']['m'].values())
        result = json.loads(op.run(':growth jepa 2 160'))
        assert result['trained'] and result['optimizer_steps'] == 4 and result['optimizer_state_continued']
        direct = copy.deepcopy(r._world_jepa_online.__dict__)
        receipts = dict(r._world_jepa_lineage)
        assert direct['_training_state']['main']['t'] == 4
        assert direct['_training_state']['bootstrap'][0]['adam']['t'] == 2
        assert not np.array_equal(direct['enc']['W1'], initial.enc['W1'])
        assert not np.array_equal(direct['_training_state']['inverse']['Q1'],
                                  initial._training_state['inverse']['Q1'])
        r.close()
        r = Runtime(tmp_path)
        op = Operator(r)
        op.run(':learning shadow')
        restored = json.loads(op.run(':growth jepa restore'))
        assert restored['optimizer_state_persisted'] is True
        same(r._world_jepa_online._training_state, initial._training_state)
        assert json.loads(op.run(':growth jepa 2 160'))['trained']
        same(r._world_jepa_online.__dict__, direct)
        assert r._world_jepa_lineage == receipts
        print('JEPA_RESUME_EXACT', json.dumps({'main_steps':4,'bootstrap_steps':2,
              'model_ema_inverse_moments_rng_exact':True,'source_lineage_exact':True}))
    finally:
        r.close()


@pytest.fixture
def fitted():
    rng = np.random.default_rng(23)
    x = rng.normal(size=(32, 4))
    a = np.eye(2)[np.arange(32) % 2]
    return wj.WorldJEPA(seed=7, ensemble=2).fit(x, a, x + .1 * a[:, :1], steps=2), (x, a, x + .1 * a[:, :1])


def test_repeated_fit_calls_keep_moments_inverse_and_rng(fitted):
    model, data = fitted
    previous = copy.deepcopy(model._training_state)
    assert previous['main']['t'] == 2
    model.partial_fit(*data, steps=2)
    assert model._training_state['main']['t'] == 4
    assert model._training_state['rng'] != previous['rng']
    assert any(not np.array_equal(model._training_state['main']['m'][k], previous['main']['m'][k])
               for k in previous['main']['m'])


@pytest.mark.parametrize('corruption', ['moment', 'negative_variance', 'step', 'inverse', 'rng', 'objective'])
def test_invalid_training_state_rejected_before_weight_mutation(fitted, corruption):
    model, data = fitted
    value = model._training_state
    if corruption == 'moment':
        value['main']['m']['eW1'][0, 0] = np.nan
    elif corruption == 'negative_variance':
        value['main']['v']['eW1'][0, 0] = -1.
    elif corruption == 'step':
        value['main']['t'] = True
    elif corruption == 'inverse':
        value['inverse']['Q1'] = value['inverse']['Q1'][:1]
    elif corruption == 'rng':
        value['rng']['state']['inc'] = 0
    else:
        value['objective'] = '0' * 64
    before = model.enc['W1'].copy()
    target = model.tgt['W1'].copy()
    with pytest.raises(ValueError, match='World-JEPA'):
        model.partial_fit(*data, steps=1)
    assert np.array_equal(before, model.enc['W1']) and np.array_equal(target, model.tgt['W1'])


def test_failed_training_keeps_full_committed_state(fitted, monkeypatch):
    model, data = fitted
    old = copy.deepcopy(model.__dict__)
    def failure(*args, **kwargs):
        raise RuntimeError('injected actual gradient failure')
    monkeypatch.setattr(wj, 'loss_grads', failure)
    with pytest.raises(RuntimeError, match='gradient failure'):
        model.partial_fit(*data, steps=2)
    same(old, model.__dict__)


def test_resume_checkpoint_rejects_malicious_npy_shape_before_loading(tmp_path, fitted, monkeypatch):
    model, _ = fitted
    dest = tmp_path / 'state.npz'
    checkpoint.save(model, dest, '1' * 64)
    source = zipfile.ZipFile(io.BytesIO(dest.read_bytes()))
    target = io.BytesIO()
    with source, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as out:
        for member in source.infolist():
            if member.filename == 'training__main__m__eW1.npy':
                buf = io.BytesIO()
                np.lib.format.write_array_header_1_0(buf, {'shape':(10**12,), 'fortran_order':False, 'descr':'<f8'})
                out.writestr(member.filename, buf.getvalue())
            else:
                out.writestr(member, source.read(member))
    raw = target.getvalue();dest.write_bytes(raw)
    def forbidden(*args, **kwargs):
        raise AssertionError('np.load must not consume a forged allocation header')
    monkeypatch.setattr(np, 'load', forbidden)
    with pytest.raises(ValueError, match='header exceeds'):
        checkpoint.load(dest, '1' * 64, hashlib.sha256(raw).hexdigest())


def test_inference_only_state_is_not_silently_resumed(fitted):
    model, data = fitted
    del model._training_state
    before = model.enc['W1'].copy()
    with pytest.raises(ValueError, match='training state'):
        model.partial_fit(*data, steps=2)
    assert np.array_equal(before, model.enc['W1'])

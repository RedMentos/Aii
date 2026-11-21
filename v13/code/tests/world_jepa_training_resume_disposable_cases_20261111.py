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
from v13 import world_jepa_training_state as state
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


def test_legacy_v1_inference_checkpoint_bootstraps_from_unknown_step_count(tmp_path, fitted):
    model, data = fitted
    del model._training_state
    meta, arrays = checkpoint._extract(model, '1' * 64)
    meta = dict(meta)
    meta.pop('fit_steps')
    meta['schema'] = checkpoint.LEGACY_SCHEMA
    legacy = tmp_path / 'legacy-v1.npz'
    raw_stream = io.BytesIO()
    np.savez_compressed(raw_stream, meta=np.frombuffer(checkpoint._meta_json(meta), dtype=np.uint8),
                        **arrays)
    raw = raw_stream.getvalue()
    legacy.write_bytes(raw)
    restored = checkpoint.load(legacy, '1' * 64, hashlib.sha256(raw).hexdigest())
    assert restored._fit_steps == 0
    before = restored.enc['W1'].copy()
    with pytest.raises(ValueError, match='explicit optimizer bootstrap permission'):
        restored.partial_fit(*data, steps=2)
    assert np.array_equal(before, restored.enc['W1'])
    restored.partial_fit(*data, steps=2, allow_optimizer_bootstrap=True)
    assert restored._training_state['origin'] == 'BOOTSTRAPPED_FROM_INFERENCE_ONLY'
    assert restored._training_state['main']['t'] == 2
    assert restored._fit_steps == 2


def test_inference_only_state_is_not_silently_resumed(fitted):
    model, data = fitted
    del model._training_state
    before = model.enc['W1'].copy()
    with pytest.raises(ValueError, match='explicit optimizer bootstrap permission'):
        model.partial_fit(*data, steps=2)
    assert np.array_equal(before, model.enc['W1'])
    model.partial_fit(*data, steps=2, allow_optimizer_bootstrap=True)
    assert model._training_state['origin'] == 'BOOTSTRAPPED_FROM_INFERENCE_ONLY'
    assert model._training_state['main']['t'] == 2
    assert model._fit_steps == 4
    assert not np.array_equal(before, model.enc['W1'])


def test_legacy_inference_checkpoint_bootstrap_is_explicit_and_persisted(tmp_path, fitted):
    model, data = fitted
    del model._training_state
    legacy = tmp_path / 'legacy-inference.npz'
    receipt = checkpoint.save(model, legacy, '1' * 64)
    assert receipt['optimizer_state_persisted'] is False
    restored = checkpoint.load(legacy, '1' * 64, receipt['sha256'])
    before = restored.enc['W1'].copy()
    with pytest.raises(ValueError, match='explicit optimizer bootstrap permission'):
        restored.partial_fit(*data, steps=2)
    assert np.array_equal(before, restored.enc['W1'])
    restored.partial_fit(*data, steps=2, allow_optimizer_bootstrap=True)
    assert restored._training_state['origin'] == 'BOOTSTRAPPED_FROM_INFERENCE_ONLY'
    saved = tmp_path / 'resumed.npz'
    receipt = checkpoint.save(restored, saved, '1' * 64)
    assert receipt['optimizer_state_persisted'] is True
    assert receipt['optimizer_state_bootstrapped'] is True
    roundtrip = checkpoint.load(saved, '1' * 64, receipt['sha256'])
    same(roundtrip._training_state, restored._training_state)



def _ablation_cohort(seed, task, n=96):
    rng = np.random.default_rng(seed)
    x = rng.normal(0., 0.6, size=(n, 4))
    action_ids = rng.integers(0, 2, size=n)
    a = np.eye(2, dtype=float)[action_ids]
    if task == 'old':
        action0 = np.array([0.9, -0.45, 0.35, 0.2])
        action1 = np.array([-0.7, 0.3, -0.2, 0.4])
    else:
        action0 = np.array([-0.55, 0.7, 0.15, -0.35])
        action1 = np.array([0.75, -0.25, 0.45, -0.5])
    effect = a[:, 0:1] * action0[None, :] + a[:, 1:2] * action1[None, :]
    x2 = 0.82 * x + effect + 0.03 * rng.normal(size=x.shape)
    return x, a, x2


def _ablation_source_sha(*cohorts):
    digest = hashlib.sha256()
    for cohort in cohorts:
        for value in cohort:
            digest.update(np.ascontiguousarray(value, dtype=np.float64).tobytes())
    return digest.hexdigest()


def _ablation_parameter_delta(left, right):
    pairs = []
    for group in ('enc', 'tgt'):
        pairs.extend((left.__dict__[group][key], right.__dict__[group][key])
                     for key in left.__dict__[group])
    pairs.extend((a[key], b[key]) for a, b in zip(left.preds, right.preds) for key in a)
    pairs.extend((left._training_state['inverse'][key],
                  right._training_state['inverse'][key])
                 for key in left._training_state['inverse'])
    return float(np.sqrt(sum(float(np.sum((a - b) ** 2)) for a, b in pairs)))


def _ablation_moment_norm(model):
    total = 0.0
    groups = [model._training_state['main']]
    groups.extend(item['adam'] for item in model._training_state['bootstrap'])
    for group in groups:
        for slot in ('m', 'v'):
            total += sum(float(np.sum(value ** 2)) for value in group[slot].values())
    return float(np.sqrt(total))


def test_matched_persistent_vs_reset_optimizer_ablation_on_disjoint_holdouts(tmp_path):
    """Diagnostic only: same two pages and zero replay; never assume carried Adam always wins."""
    summaries = []
    for seed in (3, 17, 41):
        train_old = _ablation_cohort(1000 + seed, 'old')
        train_new = _ablation_cohort(2000 + seed, 'new')
        holdout_old = _ablation_cohort(3000 + seed, 'old')
        holdout_new = _ablation_cohort(4000 + seed, 'new')
        train_source_ids = {f'train-old-{seed}', f'train-new-{seed}'}
        holdout_source_ids = {f'holdout-old-{seed}', f'holdout-new-{seed}'}
        assert train_source_ids.isdisjoint(holdout_source_ids)

        source_sha_page1 = _ablation_source_sha(train_old)
        source_sha_all = _ablation_source_sha(train_old, train_new)
        initial = wj.WorldJEPA(seed=seed, ensemble=2).fit(
            *train_old, steps=32)
        persistent_path = tmp_path / f'persistent-{seed}-page1.npz'
        reset_path = tmp_path / f'reset-{seed}-page1.npz'
        persistent_receipt = checkpoint.save(initial, persistent_path, source_sha_page1)
        reset_copy = copy.deepcopy(initial)
        delattr(reset_copy, '_training_state')
        reset_receipt = checkpoint.save(reset_copy, reset_path, source_sha_page1)
        assert persistent_receipt['optimizer_state_persisted'] is True
        assert reset_receipt['optimizer_state_persisted'] is False

        persistent = checkpoint.load(
            persistent_path, source_sha_page1, persistent_receipt['sha256'])
        reset = checkpoint.load(reset_path, source_sha_page1, reset_receipt['sha256'])
        assert np.array_equal(persistent.enc['W1'], reset.enc['W1'])
        assert np.array_equal(persistent.tgt['W1'], reset.tgt['W1'])
        old_before = persistent.prediction_loss(*holdout_old)
        new_before = persistent.prediction_loss(*holdout_new)
        assert np.isclose(old_before, reset.prediction_loss(*holdout_old), atol=1e-12)
        assert np.isclose(new_before, reset.prediction_loss(*holdout_new), atol=1e-12)

        persistent.partial_fit(*train_new, steps=32)
        reset.partial_fit(*train_new, steps=32, allow_optimizer_bootstrap=True)
        persistent_final_path = tmp_path / f'persistent-{seed}-final.npz'
        reset_final_path = tmp_path / f'reset-{seed}-final.npz'
        persistent_final = checkpoint.save(
            persistent, persistent_final_path, source_sha_all)
        reset_final = checkpoint.save(reset, reset_final_path, source_sha_all)
        assert persistent_final['optimizer_state_persisted'] is True
        assert persistent_final['optimizer_state_bootstrapped'] is False
        assert reset_final['optimizer_state_persisted'] is True
        assert reset_final['optimizer_state_bootstrapped'] is True
        assert persistent._fit_steps == reset._fit_steps == 64
        assert persistent._training_state['main']['t'] == 64
        assert reset._training_state['main']['t'] == 32
        assert persistent._training_state['bootstrap'][0]['adam']['t'] == 32
        assert reset._training_state['bootstrap'][0]['adam']['t'] == 16
        assert persistent._training_state['origin'] == 'FRESH'
        assert reset._training_state['origin'] == 'BOOTSTRAPPED_FROM_INFERENCE_ONLY'
        assert persistent_final['sha256'] != reset_final['sha256']

        old_persistent = persistent.prediction_loss(*holdout_old)
        old_reset = reset.prediction_loss(*holdout_old)
        new_persistent = persistent.prediction_loss(*holdout_new)
        new_reset = reset.prediction_loss(*holdout_new)
        perm = np.random.default_rng(9000 + seed).permutation(len(holdout_new[1]))
        zero_actions = np.zeros_like(holdout_new[1])
        shuffled_actions = holdout_new[1][perm]
        controls_persistent = {
            'actual': new_persistent,
            'zero': persistent.prediction_loss(holdout_new[0], zero_actions, holdout_new[2]),
            'shuffled': persistent.prediction_loss(holdout_new[0], shuffled_actions, holdout_new[2]),
        }
        controls_reset = {
            'actual': new_reset,
            'zero': reset.prediction_loss(holdout_new[0], zero_actions, holdout_new[2]),
            'shuffled': reset.prediction_loss(holdout_new[0], shuffled_actions, holdout_new[2]),
        }
        p_restored = checkpoint.load(
            persistent_final_path, source_sha_all, persistent_final['sha256'])
        r_restored = checkpoint.load(
            reset_final_path, source_sha_all, reset_final['sha256'])
        same(p_restored._training_state, persistent._training_state)
        same(r_restored._training_state, reset._training_state)
        assert np.isclose(p_restored.prediction_loss(*holdout_old), old_persistent, atol=1e-12)
        assert np.isclose(r_restored.prediction_loss(*holdout_new), new_reset, atol=1e-12)

        persistent_delta = _ablation_parameter_delta(persistent, initial)
        reset_delta = _ablation_parameter_delta(reset, initial)
        persistent_vs_reset = _ablation_parameter_delta(persistent, reset)
        persistent_ema_delta = float(np.sqrt(sum(
            np.sum((persistent.tgt[key] - initial.tgt[key]) ** 2)
            for key in persistent.tgt)))
        reset_ema_delta = float(np.sqrt(sum(
            np.sum((reset.tgt[key] - initial.tgt[key]) ** 2)
            for key in reset.tgt)))
        values = [old_before, new_before, old_persistent, old_reset,
                  new_persistent, new_reset, persistent_delta, reset_delta,
                  persistent_vs_reset, persistent_ema_delta, reset_ema_delta,
                  _ablation_moment_norm(persistent), _ablation_moment_norm(reset),
                  *controls_persistent.values(), *controls_reset.values()]
        assert np.isfinite(values).all()
        assert persistent_delta > 0 and reset_delta > 0 and persistent_vs_reset > 0
        assert persistent_ema_delta > 0 and reset_ema_delta > 0
        summaries.append({
            'seed': seed,
            'train_source_ids': sorted(train_source_ids),
            'holdout_source_ids': sorted(holdout_source_ids),
            'update_steps_each_arm': 64,
            'replay_bytes_each_arm': 0,
            'persistent_main_adam_t': persistent._training_state['main']['t'],
            'reset_main_adam_t': reset._training_state['main']['t'],
            'persistent_bootstrap_adam_t': persistent._training_state['bootstrap'][0]['adam']['t'],
            'reset_bootstrap_adam_t': reset._training_state['bootstrap'][0]['adam']['t'],
            'persistent_origin': persistent._training_state['origin'],
            'reset_origin': reset._training_state['origin'],
            'persistent_parameter_delta_norm': persistent_delta,
            'reset_parameter_delta_norm': reset_delta,
            'persistent_vs_reset_parameter_delta_norm': persistent_vs_reset,
            'persistent_ema_delta_norm': persistent_ema_delta,
            'reset_ema_delta_norm': reset_ema_delta,
            'persistent_old_holdout_delta': old_persistent - old_before,
            'reset_old_holdout_delta': old_reset - old_before,
            'persistent_new_holdout_gain': new_before - new_persistent,
            'reset_new_holdout_gain': new_before - new_reset,
            'persistent_action_controls': controls_persistent,
            'reset_action_controls': controls_reset,
            'persistent_moment_norm': _ablation_moment_norm(persistent),
            'reset_moment_norm': _ablation_moment_norm(reset),
            'final_checkpoint_sha256_differs': persistent_final['sha256'] != reset_final['sha256'],
        })
    print('WORLDJEPA_PERSIST_RESET_ABLATION', json.dumps(summaries, sort_keys=True))

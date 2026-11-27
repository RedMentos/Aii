"""Optimizer/inverse/RNG continuity on the actual staged World Runtime route."""
import copy
import errno
import hashlib
import os
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




@pytest.mark.parametrize('denied_errno', [errno.EPERM, errno.EACCES])
def test_checkpoint_publish_uses_renameat2_after_hardlink_denial(tmp_path, fitted, monkeypatch, denied_errno):
    model, _ = fitted
    destination = tmp_path / 'rename-fallback.npz'
    called = []
    real_rename = checkpoint._rename_named_no_replace

    def deny_hardlink(dir_fd, source, dest):
        raise PermissionError(denied_errno, 'ordinary hardlink denied', dest)

    def tracked_rename(dir_fd, source, dest):
        called.append((source, dest))
        return real_rename(dir_fd, source, dest)

    monkeypatch.setattr(checkpoint, '_hardlink_named_no_replace', deny_hardlink)
    monkeypatch.setattr(checkpoint, '_rename_named_no_replace', tracked_rename)
    receipt = checkpoint.save(model, destination, '1' * 64)
    assert len(called) == 1
    assert destination.is_file() and not destination.is_symlink()
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == receipt['sha256']
    assert not list(tmp_path.glob(checkpoint.PENDING_PREFIX + '*'))
    restored = checkpoint.load(destination, '1' * 64, receipt['sha256'])
    same(restored._training_state, model._training_state)


def test_checkpoint_renameat2_refuses_existing_target(tmp_path):
    source = tmp_path / 'pending'
    target = tmp_path / 'target'
    source.write_bytes(b'new checkpoint')
    target.write_bytes(b'preserve existing bytes')
    source.chmod(0o600)
    target.chmod(0o600)
    dir_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with pytest.raises(OSError) as caught:
            checkpoint._rename_named_no_replace(dir_fd, source.name, target.name)
        assert caught.value.errno == errno.EEXIST
    finally:
        os.close(dir_fd)
    assert source.read_bytes() == b'new checkpoint'
    assert target.read_bytes() == b'preserve existing bytes'


def test_checkpoint_cleanup_reaps_only_owned_crash_pending_names(tmp_path):
    orphan = tmp_path / (checkpoint.PENDING_PREFIX + 'orphan')
    orphan.write_bytes(b'interrupted before publish')
    orphan.chmod(0o600)
    target = tmp_path / ('jepa-' + 'a' * 32 + '.npz')
    target.write_bytes(b'complete checkpoint')
    target.chmod(0o600)
    linked = tmp_path / (checkpoint.PENDING_PREFIX + 'linked')
    os.link(target, linked)
    unrelated = tmp_path / 'keep-me'
    unrelated.write_bytes(b'unrelated')
    assert checkpoint.cleanup_pending(tmp_path) == 2
    assert not orphan.exists() and not linked.exists()
    assert target.read_bytes() == b'complete checkpoint'
    assert unrelated.read_bytes() == b'unrelated'
    unsafe = tmp_path / (checkpoint.PENDING_PREFIX + 'symlink')
    unsafe.symlink_to(unrelated)
    with pytest.raises(ValueError, match='pending'):
        checkpoint.cleanup_pending(tmp_path)
    assert unsafe.is_symlink()


def test_checkpoint_save_fails_closed_when_both_no_clobber_publishers_fail(tmp_path, fitted, monkeypatch):
    model, _ = fitted
    destination = tmp_path / 'unpublished.npz'

    def denied(dir_fd, source, dest):
        raise PermissionError(errno.EACCES, 'publication denied', dest)

    monkeypatch.setattr(checkpoint, '_hardlink_named_no_replace', denied)
    monkeypatch.setattr(checkpoint, '_rename_named_no_replace', denied)
    with pytest.raises(PermissionError):
        checkpoint.save(model, destination, '1' * 64)
    assert not destination.exists()
    assert not list(tmp_path.glob(checkpoint.PENDING_PREFIX + '*'))


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
    """Diagnostic only: identical weights/data/updates/zero replay; reset Adam+RNG, not model weights."""
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
        reset_inverse = copy.deepcopy(initial._training_state['inverse'])
        delattr(reset_copy, '_training_state')
        reset_copy._training_state = state.bootstrap_from_inference(reset_copy)
        reset_copy._training_state['inverse'] = reset_inverse
        reset_receipt = checkpoint.save(reset_copy, reset_path, source_sha_page1)
        assert persistent_receipt['optimizer_state_persisted'] is True
        assert persistent_receipt['optimizer_state_bootstrapped'] is False
        assert reset_receipt['optimizer_state_persisted'] is True
        assert reset_receipt['optimizer_state_bootstrapped'] is True

        persistent = checkpoint.load(
            persistent_path, source_sha_page1, persistent_receipt['sha256'])
        reset = checkpoint.load(reset_path, source_sha_page1, reset_receipt['sha256'])
        assert np.array_equal(persistent.enc['W1'], reset.enc['W1'])
        assert np.array_equal(persistent.tgt['W1'], reset.tgt['W1'])
        assert np.isclose(_ablation_parameter_delta(persistent, reset), 0.0, atol=1e-12)
        assert persistent._training_state['main']['t'] == 32
        assert reset._training_state['main']['t'] == 0
        assert persistent._training_state['bootstrap'][0]['adam']['t'] == 16
        assert reset._training_state['bootstrap'][0]['adam']['t'] == 0
        same(persistent._training_state['inverse'], reset._training_state['inverse'])
        assert all(np.count_nonzero(value) == 0
                   for value in reset._training_state['main']['m'].values())
        assert reset._training_state['rng'] != persistent._training_state['rng']
        old_before = persistent.prediction_loss(*holdout_old)
        new_before = persistent.prediction_loss(*holdout_new)
        assert np.isclose(old_before, reset.prediction_loss(*holdout_old), atol=1e-12)
        assert np.isclose(new_before, reset.prediction_loss(*holdout_new), atol=1e-12)

        persistent.partial_fit(*train_new, steps=32)
        # The reset state is already explicitly bootstrapped and checkpointed; this page only resumes it.
        reset.partial_fit(*train_new, steps=32)
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

def _ablation_reset_optimizer(model):
    """Reset Adam/RNG while preserving the currently learned model and inverse head."""
    inverse = copy.deepcopy(model._training_state['inverse'])
    delattr(model, '_training_state')
    model._training_state = state.bootstrap_from_inference(model)
    model._training_state['inverse'] = inverse


def _ablation_replay_phase(new_cohort, replay_cohort, replay_enabled):
    if not replay_enabled:
        return new_cohort, 0, len(new_cohort[0])
    count = len(new_cohort[0]) // 2
    mixed = tuple(
        np.concatenate((np.asarray(new)[:count], np.asarray(replay)[:count]), axis=0)
        for new, replay in zip(new_cohort, replay_cohort)
    )
    replay_bytes = sum(int(np.asarray(value)[:count].nbytes) for value in replay_cohort)
    return mixed, replay_bytes, count


def _ablation_gradient_norm(model, cohort):
    x, actions, x2 = cohort
    target = wj.encode(model.tgt, x2)[0]
    out = wj.loss_grads(
        model.enc, model.preds[0], x, actions, target,
        inv=model._training_state['inverse'], x2=x2, inv_w=wj.INV_W,
    )
    gradients = out[2:]
    arrays = [value for group in gradients if isinstance(group, dict)
              for value in group.values()]
    norm = float(np.sqrt(sum(float(np.sum(value ** 2)) for value in arrays)))
    assert np.isfinite(norm) and norm > 0
    return norm


def _ablation_action_controls(model, cohort, seed):
    x, actions, x2 = cohort
    zero = np.zeros_like(actions)
    permutation = np.random.default_rng(seed).permutation(len(actions))
    shuffled = actions[permutation]
    return {
        'actual': model.prediction_loss(x, actions, x2),
        'zero': model.prediction_loss(x, zero, x2),
        'shuffled': model.prediction_loss(x, shuffled, x2),
    }


def test_a_b_a_return_to_old_dynamics_with_optimizer_and_replay_ablation(tmp_path):
    """Diagnostic only: source-disjoint A->B->A with matched steps and replay accounting."""
    summaries = []
    for seed in (5, 19, 43):
        train_a1 = _ablation_cohort(1100 + seed, 'old')
        train_b = _ablation_cohort(2100 + seed, 'new')
        train_a2 = _ablation_cohort(3100 + seed, 'old')
        holdout_a = _ablation_cohort(4100 + seed, 'old')
        holdout_b = _ablation_cohort(5100 + seed, 'new')
        train_sources = {
            f'train-A1-{seed}', f'train-B-{seed}', f'train-A2-{seed}'
        }
        holdout_sources = {f'holdout-A-{seed}', f'holdout-B-{seed}'}
        assert train_sources.isdisjoint(holdout_sources)

        initial = wj.WorldJEPA(seed=seed, ensemble=2).fit(*train_a1, steps=32)
        old_before = initial.prediction_loss(*holdout_a)
        new_before = initial.prediction_loss(*holdout_b)
        assert np.isfinite([old_before, new_before]).all()

        for replay_mode in ('none', 'uniform'):
            replay_enabled = replay_mode == 'uniform'
            b_data, b_replay_bytes, b_new_rows = _ablation_replay_phase(
                train_b, train_a1, replay_enabled
            )
            a_data, a_replay_bytes, a_new_rows = _ablation_replay_phase(
                train_a2, train_b, replay_enabled
            )
            for optimizer_mode in ('persistent', 'reset_each_phase'):
                model = copy.deepcopy(initial)
                if optimizer_mode == 'reset_each_phase':
                    _ablation_reset_optimizer(model)
                gradient_b = _ablation_gradient_norm(model, b_data)
                model.partial_fit(*b_data, steps=32)

                source_sha_b = _ablation_source_sha(train_a1, b_data)
                b_path = tmp_path / f'a-b-a-{seed}-{replay_mode}-{optimizer_mode}-b.npz'
                b_receipt = checkpoint.save(model, b_path, source_sha_b)
                assert b_receipt['optimizer_state_persisted'] is True
                assert b_receipt['optimizer_state_bootstrapped'] is (
                    optimizer_mode == 'reset_each_phase'
                )
                b_restored = checkpoint.load(b_path, source_sha_b, b_receipt['sha256'])
                same(b_restored._training_state, model._training_state)
                model = b_restored

                old_after_b = model.prediction_loss(*holdout_a)
                new_after_b = model.prediction_loss(*holdout_b)
                if optimizer_mode == 'reset_each_phase':
                    _ablation_reset_optimizer(model)
                gradient_a = _ablation_gradient_norm(model, a_data)
                model.partial_fit(*a_data, steps=32)

                source_sha_final = _ablation_source_sha(train_a1, b_data, a_data)
                final_path = tmp_path / f'a-b-a-{seed}-{replay_mode}-{optimizer_mode}-final.npz'
                final_receipt = checkpoint.save(model, final_path, source_sha_final)
                assert final_receipt['optimizer_state_persisted'] is True
                assert final_receipt['optimizer_state_bootstrapped'] is (
                    optimizer_mode == 'reset_each_phase'
                )
                final = checkpoint.load(final_path, source_sha_final, final_receipt['sha256'])
                same(final._training_state, model._training_state)
                assert final._fit_steps == model._fit_steps == 96

                old_after_a = final.prediction_loss(*holdout_a)
                new_after_a = final.prediction_loss(*holdout_b)
                rollback = checkpoint.load(b_path, source_sha_b, b_receipt['sha256'])
                assert np.isclose(rollback.prediction_loss(*holdout_a), old_after_b, atol=1e-12)
                assert np.isclose(rollback.prediction_loss(*holdout_b), new_after_b, atol=1e-12)
                assert np.isclose(final.prediction_loss(*holdout_a), old_after_a, atol=1e-12)
                assert np.isclose(final.prediction_loss(*holdout_b), new_after_a, atol=1e-12)

                parameter_delta = _ablation_parameter_delta(final, initial)
                ema_delta = float(np.sqrt(sum(
                    np.sum((final.tgt[key] - initial.tgt[key]) ** 2)
                    for key in final.tgt
                )))
                persistent_expected = optimizer_mode == 'persistent'
                expected_main_t = 96 if persistent_expected else 32
                expected_bootstrap_t = 48 if persistent_expected else 16
                assert final._training_state['main']['t'] == expected_main_t
                assert final._training_state['bootstrap'][0]['adam']['t'] == expected_bootstrap_t
                assert final._training_state['origin'] == (
                    'FRESH' if persistent_expected else 'BOOTSTRAPPED_FROM_INFERENCE_ONLY'
                )
                assert parameter_delta > 0 and ema_delta > 0

                controls_a = _ablation_action_controls(final, holdout_a, 6100 + seed)
                controls_b = _ablation_action_controls(final, holdout_b, 7100 + seed)
                values = [
                    old_before, new_before, old_after_b, new_after_b,
                    old_after_a, new_after_a, gradient_b, gradient_a,
                    parameter_delta, ema_delta, _ablation_moment_norm(final),
                    *controls_a.values(), *controls_b.values(),
                ]
                assert np.isfinite(values).all()
                summaries.append({
                    'seed': seed,
                    'replay_mode': replay_mode,
                    'optimizer_mode': optimizer_mode,
                    'train_source_ids': sorted(train_sources),
                    'holdout_source_ids': sorted(holdout_sources),
                    'source_disjoint': True,
                    'update_steps_each_phase': 32,
                    'total_update_steps_after_A1': 96,
                    'new_rows_per_phase': {'B': b_new_rows, 'A_return': a_new_rows},
                    'replay_bytes_each_phase': {
                        'B': b_replay_bytes, 'A_return': a_replay_bytes,
                    },
                    'gradient_norms': {'B_before_update': gradient_b, 'A_return_before_update': gradient_a},
                    'parameter_delta_norm': parameter_delta,
                    'ema_delta_norm': ema_delta,
                    'moment_norm': _ablation_moment_norm(final),
                    'A_holdout_loss': {
                        'after_A1': old_before, 'after_B': old_after_b, 'after_A_return': old_after_a,
                    },
                    'B_holdout_loss': {
                        'after_A1': new_before, 'after_B': new_after_b, 'after_A_return': new_after_a,
                    },
                    'A_reacquisition_gain_after_return': old_after_b - old_after_a,
                    'B_forgetting_after_return': new_after_a - new_after_b,
                    'A_negative_controls': controls_a,
                    'B_negative_controls': controls_b,
                    'optimizer_main_t': final._training_state['main']['t'],
                    'optimizer_bootstrap_t': final._training_state['bootstrap'][0]['adam']['t'],
                    'optimizer_origin': final._training_state['origin'],
                    'rollback_checkpoint_sha256': b_receipt['sha256'],
                    'final_checkpoint_sha256': final_receipt['sha256'],
                    'rollback_readback_exact': True,
                })
    print('WORLDJEPA_A_B_A_RETURN_ABLATION', json.dumps(summaries, sort_keys=True))

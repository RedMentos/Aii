"""Real NumPy World-JEPA replay previews stay detached and evidence-limited."""
import copy
import threading

import numpy as np
import pytest

from v13 import world_jepa as wj
from v13 import world_jepa_replay as legacy
from v13 import world_jepa_replay_shadow_candidate as candidate


def rows(n=12, offset=0.):
    x = np.arange(n * 4, dtype=np.float64).reshape(n, 4) / 100 + offset
    a = np.eye(2, dtype=np.float64)[np.arange(n) % 2]
    y = x + np.column_stack((a[:, 0] * .2, a[:, 1] * .3, np.zeros(n), np.zeros(n)))
    return x, a, y


def fitted():
    return wj.WorldJEPA(seed=3, ensemble=2).fit(*rows(24, -50.), steps=2, log_every=1)


def data():
    return rows(12, 0.), rows(12, 10.), rows(8, 20.), rows(8, 30.)


def assert_equal(a, b):
    if isinstance(a, np.ndarray):
        np.testing.assert_array_equal(a, b)
    elif isinstance(a, dict):
        assert a.keys() == b.keys()
        for key in a:
            assert_equal(a[key], b[key])
    elif isinstance(a, (tuple, list)):
        assert type(a) is type(b) and len(a) == len(b)
        for left, right in zip(a, b):
            assert_equal(left, right)
    else:
        assert a == b


def test_real_model_preview_uses_actual_row_counts_and_changes_only_copy():
    model = fitted()
    original = copy.deepcopy(model.__dict__)
    staged, report = candidate.preview_replay(model, *data(), steps=2, replay_fraction=.25, seed=3)
    assert (report['new_train_rows'], report['replay_train_rows']) == (12, 6)
    assert report['actual_replay_fraction'] == pytest.approx(6 / 18)
    assert report['scope'] == 'DETACHED_SHADOW_PREVIEW'
    assert report['live_model_updated'] is False and report['active_model_promoted'] is False
    assert report['pretrained_weights_changed'] is False
    assert report['source_id_disjointness_verified'] is False
    assert report['optimizer_state_continued'] is False
    assert report['fixed_target_retention_verified'] is False
    assert report['retention_measurement_scope'] == 'MOVING_EMA_TARGET_DIAGNOSTIC_ONLY'
    assert staged is not model and staged._fit_steps == model._fit_steps + 2
    assert not np.array_equal(staged.enc['W1'], model.enc['W1'])
    assert all(np.isfinite(report[key]) for key in ('old_holdout_before', 'old_holdout_after',
        'old_holdout_delta', 'new_holdout_before', 'new_holdout_after', 'new_holdout_delta'))
    assert_equal(model.__dict__, original)


def test_mixture_uses_all_actual_indices_and_is_deterministic():
    n, r, old, fresh = data()
    expected = candidate._validated_inputs(n, r, old, fresh, 4, .25, 4)
    a, count_n, count_r = candidate._mixture(expected[0], expected[1], .25, 4)
    b, _, _ = candidate._mixture(expected[0], expected[1], .25, 4)
    assert (count_n, count_r) == (12, 6)
    assert len(a[0]) == 18 and len({tuple(row) for row in a[0]}) == 18
    assert any(np.array_equal(row, n[0][-1]) for row in a[0])  # not capped at first three
    for x, y in zip(a, b):
        np.testing.assert_array_equal(x, y)


def test_actual_sample_limit_and_selection_are_bounded():
    n, r = rows(4096, 0.), rows(4096, 1000.)
    a, nc, rc = candidate._mixture(n, r, .25, 7)
    assert (nc, rc) == (3072, 1024)
    assert len(a[0]) == legacy.MAX_ROWS == 4096
    assert len(np.unique(a[0], axis=0)) == 4096


def test_transition_snapshot_cannot_be_changed_through_caller_arrays():
    supplied = data()
    frozen = candidate._validated_inputs(*supplied, 1, .25, 7)
    before = copy.deepcopy(frozen)
    for triple in supplied:
        for array in triple:
            array[...] = 12345
    assert_equal(frozen, before)
    assert all(not np.shares_memory(a, b) for original, snapshot in zip(supplied, frozen)
               for a, b in zip(original, snapshot))


def test_caller_mutation_after_split_check_cannot_change_heldout_preview(monkeypatch):
    model = fitted()
    supplied = data()
    old_before = supplied[2][0].copy()
    paused, release = threading.Event(), threading.Event()
    results, errors, observed_old = [], [], []
    original_mixture = candidate._mixture
    original_loss = wj.WorldJEPA.prediction_loss
    def pause_before_sampling(*args):
        paused.set()
        if not release.wait(5):
            raise TimeoutError('test did not release preview')
        return original_mixture(*args)
    def observe_loss(self, x, a, y):
        observed_old.append(x.copy())
        return original_loss(self, x, a, y)
    def run():
        try:
            results.append(candidate.preview_replay(model, *supplied, steps=1))
        except BaseException as exc:
            errors.append(exc)
    monkeypatch.setattr(candidate, '_mixture', pause_before_sampling)
    monkeypatch.setattr(wj.WorldJEPA, 'prediction_loss', observe_loss)
    worker = threading.Thread(target=run)
    worker.start()
    try:
        assert paused.wait(5)
        # Introduce a training/holdout collision only after the split check.
        for k in range(3): supplied[2][k][4] = supplied[0][k][8]
    finally:
        release.set()
        worker.join(5)
    assert not worker.is_alive() and not errors and results
    assert results[0][1]['exact_cross_split_duplicate_check'] is True
    np.testing.assert_array_equal(observed_old[0], old_before)


@pytest.mark.parametrize('steps,fraction,seed', [
    (0, .25, 0), (True, .25, 0), (1, True, 0), (1, float('nan'), 0),
    (1, -.1, 0), (1, 1.1, 0), (1, .2, -1), (legacy.MAX_STEPS + 1, .2, 0),
])
def test_bad_budget_rejected_without_live_mutation(steps, fraction, seed):
    model = fitted(); original = copy.deepcopy(model.__dict__)
    with pytest.raises(ValueError):
        candidate.preview_replay(model, *data(), steps=steps, replay_fraction=fraction, seed=seed)
    assert_equal(model.__dict__, original)


def test_exact_cross_split_duplicate_rejected_before_training():
    model = fitted(); original = copy.deepcopy(model.__dict__)
    n, r, old, fresh = data()
    old = tuple(v.copy() for v in old)
    for k in range(3): old[k][4] = n[k][8]
    with pytest.raises(ValueError, match='multiple splits'):
        candidate.preview_replay(model, n, r, old, fresh, steps=2)
    assert_equal(model.__dict__, original)


def test_identical_holdout_copies_are_rejected():
    n, r, old, fresh = data()
    with pytest.raises(ValueError, match='multiple splits'):
        candidate.preview_replay(fitted(), n, r, old, tuple(x.copy() for x in old), steps=1)


def test_sign_of_zero_does_not_hide_duplicate():
    n, r, old, fresh = data()
    old = tuple(v.copy() for v in old)
    for k in range(3): old[k][0] = n[k][0]
    old[0][0, 0] = -0.
    with pytest.raises(ValueError, match='multiple splits'):
        candidate.preview_replay(fitted(), n, r, old, fresh, steps=1)


def test_bad_dimensions_and_byte_budget_rejected_without_training(monkeypatch):
    model = fitted(); original = copy.deepcopy(model.__dict__)
    n, r, old, fresh = data()
    with pytest.raises(ValueError, match='incompatible'):
        candidate.preview_replay(model, n, r, old, (fresh[0][:, :3], fresh[1], fresh[2][:, :3]), steps=1)
    monkeypatch.setattr(candidate, 'MAX_TRANSITION_BYTES', 100)
    with pytest.raises(ValueError, match='byte budget'):
        candidate.preview_replay(model, n, r, old, fresh, steps=1)
    assert_equal(model.__dict__, original)


def test_nonfinite_postcheck_never_changes_original_model(monkeypatch):
    model = fitted(); original = copy.deepcopy(model.__dict__); start = model._fit_steps
    old_loss = wj.WorldJEPA.prediction_loss
    def bad_after_update(self, *args):
        if self._fit_steps > start:
            return float('nan')
        return old_loss(self, *args)
    monkeypatch.setattr(wj.WorldJEPA, 'prediction_loss', bad_after_update)
    with pytest.raises(ValueError, match='post-update'):
        candidate.preview_replay(model, *data(), steps=2)
    assert_equal(model.__dict__, original)


def test_failed_partial_update_discards_mutated_copy(monkeypatch):
    model = fitted(); original = copy.deepcopy(model.__dict__)
    def mutate_then_fail(self, *args, **kwargs):
        self.enc['W1'][0, 0] = 12345
        raise RuntimeError('injected fit failure')
    monkeypatch.setattr(wj.WorldJEPA, 'partial_fit', mutate_then_fail)
    with pytest.raises(RuntimeError, match='injected fit failure'):
        candidate.preview_replay(model, *data(), steps=2)
    assert_equal(model.__dict__, original)


def test_zero_or_nonfinite_baselines_and_bad_staged_state_rejected(monkeypatch):
    model = fitted(); original = copy.deepcopy(model.__dict__)
    monkeypatch.setattr(wj.WorldJEPA, 'prediction_loss', lambda *args: float('inf'))
    with pytest.raises(ValueError, match='baseline'):
        candidate.preview_replay(model, *data(), steps=1)
    assert_equal(model.__dict__, original)


def test_unfitted_subclass_and_unknown_extra_state_are_refused():
    n, r, old, fresh = data()
    with pytest.raises(ValueError):
        candidate.preview_replay(wj.WorldJEPA(seed=3), n, r, old, fresh, steps=1)
    class Subclass(wj.WorldJEPA): pass
    with pytest.raises(ValueError, match='instance required'):
        candidate.preview_replay(Subclass(), n, r, old, fresh, steps=1)
    model = fitted(); model.unreviewed_state = 1
    with pytest.raises(ValueError, match='unsupported'):
        candidate.preview_replay(model, n, r, old, fresh, steps=1)


def test_caller_supplied_history_deepcopy_hook_never_executes():
    model = fitted()
    previous = model.enc['W1'].copy()
    called = []
    class MaliciousHistory:
        def __deepcopy__(self, memo):
            called.append(True)
            model.enc['W1'][0, 0] = 9999
            return self
    model.history.append(MaliciousHistory())
    with pytest.raises(ValueError, match='history'):
        candidate.preview_replay(model, *data(), steps=1)
    assert not called
    np.testing.assert_array_equal(model.enc['W1'], previous)


def test_changed_source_pin_refused_before_any_model_mutation(monkeypatch):
    model = fitted(); old = copy.deepcopy(model.__dict__)
    monkeypatch.setitem(candidate.PINS, 'world_jepa.py', '0' * 64)
    with pytest.raises(ValueError, match='source changed'):
        candidate.preview_replay(model, *data(), steps=1)
    assert_equal(model.__dict__, old)

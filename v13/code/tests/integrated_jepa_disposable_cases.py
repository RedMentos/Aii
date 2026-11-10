"""Run only inside the exact-source, layered JEPA Runtime test copy."""
import json
import time
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from v13 import inputs, online_world_policy, world_model
from v13 import world_jepa_lineage_checkpoint_candidate as lineage_checkpoint
from v13.operator import Operator
from v13.runtime import Runtime
from v13.world_jepa_action_outcome_adapter import build


def populate(runtime):
    runtime.sleep.cycle.set_policy('enabled', 'off')
    count = [0]
    def route(*args, **kwargs):
        value = ('simple', 'detail')[count[0] % 2]
        count[0] += 1
        return value, {'source': 'SYNTHETIC_TEST'}
    runtime._route = Mock(side_effect=route)
    runtime.pool.get = Mock(return_value=SimpleNamespace(role='C3_LANGUAGE', last_metrics={},
                        generate=lambda *a, **kw: iter(['synthetic response'])))
    runtime.learner.output_delta = Mock(return_value=None)
    events = []
    for i in range(160):
        events.append(runtime.submit('Synthetic sample ' + str(i) + ' x' * i))
        deadline = time.monotonic() + 10
        while not runtime.idle() and time.monotonic() < deadline:
            time.sleep(.003)
        assert runtime.idle() and runtime.last_answer()['status'] == 'FINAL'
        if i >= 63:
            try:
                build(world_model.transitions(runtime.store, limit=160))
                break
            except ValueError:
                pass
    else:
        raise AssertionError('synthetic rows did not meet disjoint holdout requirements')
    return events


def test_explicit_runtime_learning_and_lineage_bound_restart(tmp_path, monkeypatch):
    r = Runtime(tmp_path)
    try:
        events = populate(r)
        op = Operator(r)
        assert r.cfg['learning_mode'] == 'RECORD_ONLY'
        assert json.loads(op.run(':growth jepa 1 160'))['status'] == 'SKIPPED_RECORD_ONLY'
        with pytest.raises(ValueError, match='RECORD_ONLY'):
            op.run(':growth jepa save')
        assert not (tmp_path / 'world_jepa_lineage').exists()
        assert not hasattr(r, '_world_jepa_online')
        assert r.world_jepa_update(steps=1, limit=160)['status'] == 'SKIPPED_EXPLICIT_HUMAN_REQUIRED'
        op.run(':learning shadow')
        inputs.set_pause(r.store, 'training', True)
        assert json.loads(op.run(':growth jepa 1 160'))['status'] == 'SKIPPED_PAUSED_TRAINING'
        with pytest.raises(ValueError, match='PAUSED_TRAINING'):
            op.run(':growth jepa restore')
        assert not hasattr(r, '_world_jepa_online')
        inputs.set_pause(r.store, 'training', False)
        first = json.loads(op.run(':growth jepa 1 160'))
        model = r._world_jepa_online
        assert first['trained'] is True and first['source_verified'] is True
        assert first['lineage_scope'] == 'IN_MEMORY_BOUNDED_NOT_DURABLE'
        assert model._fit_steps == 1 and r._world_jepa_lineage
        before = model.enc['W1'].copy()
        first_receipts = dict(r._world_jepa_lineage)
        saved = json.loads(op.run(':growth jepa save'))
        assert saved['persisted'] and saved['optimizer_state_persisted'] is False
        with pytest.raises(ValueError, match='no previous'):
            op.run(':growth jepa previous')
        second = json.loads(op.run(':growth jepa 1 160'))
        assert second['trained'] is True and r._world_jepa_online is not model
        assert np.array_equal(model.enc['W1'], before)
        assert not np.array_equal(r._world_jepa_online.enc['W1'], before)
        second_weights = r._world_jepa_online.enc['W1'].copy()
        second_receipts = dict(r._world_jepa_lineage)
        assert json.loads(op.run(':growth jepa save'))['persisted']
        previous = json.loads(op.run(':growth jepa previous'))
        assert previous['selection'] == 'previous' and previous['manifest_changed'] is False
        assert np.array_equal(r._world_jepa_online.enc['W1'], before)
        assert r._world_jepa_lineage == first_receipts
        assert json.loads(op.run(':growth jepa restore'))['selection'] == 'active'
        assert np.array_equal(r._world_jepa_online.enc['W1'], second_weights)

        home = tmp_path / 'world_jepa_lineage'
        manifest_path = home / 'manifest.json'
        manifest = manifest_path.read_bytes()
        unrelated = home / 'unrelated-user-data'
        unrelated.write_text('preserve')
        with monkeypatch.context() as patch:
            patch.setattr(lineage_checkpoint, '_publish_manifest', Mock(side_effect=OSError('injected publish failure')))
            with pytest.raises(OSError, match='injected publish failure'):
                op.run(':growth jepa save')
        assert manifest_path.read_bytes() == manifest and unrelated.read_text() == 'preserve'
        generation = json.loads(manifest)['active']['id']
        receipt_path = home / ('lineage-' + generation + '.json')
        receipt = receipt_path.read_bytes()
        receipt_path.write_bytes(receipt + b' ')
        current = r._world_jepa_online
        with pytest.raises(ValueError, match='receipt changed'):
            op.run(':growth jepa restore')
        assert r._world_jepa_online is current
        receipt_path.write_bytes(receipt)
        model_path = home / ('jepa-' + generation + '.npz')
        model_bytes = model_path.read_bytes()
        model_path.write_bytes(model_bytes + b'corruption')
        with pytest.raises(ValueError, match='bytes changed'):
            op.run(':growth jepa restore')
        assert r._world_jepa_online is current
        model_path.write_bytes(model_bytes)
        with monkeypatch.context() as patch:
            patch.setattr(lineage_checkpoint, 'QUOTA', 1)
            with pytest.raises(ValueError, match='quota'):
                op.run(':growth jepa save')
        assert manifest_path.read_bytes() == manifest and unrelated.read_text() == 'preserve'
        sentinel = home / 'symlink-entry'
        sentinel.symlink_to(unrelated)
        with pytest.raises(ValueError, match='unsafe JEPA checkpoint directory entry'):
            op.run(':growth jepa save')
        assert unrelated.read_text() == 'preserve'
        sentinel.unlink()

        # Recreate the actual Runtime and SQLite store; the first two private
        # generations remain independently selectable after the restart.
        r.close()
        r = Runtime(tmp_path)
        op = Operator(r)
        op.run(':learning shadow')
        restored = json.loads(op.run(':growth jepa restore'))
        assert restored['restored'] and restored['optimizer_state_persisted'] is False
        assert np.array_equal(r._world_jepa_online.enc['W1'], second_weights)
        assert r._world_jepa_lineage == second_receipts
        assert json.loads(op.run(':growth jepa previous'))['selection'] == 'previous'
        assert np.array_equal(r._world_jepa_online.enc['W1'], before)
        op.run(':growth jepa restore')
        assert json.loads(op.run(':growth jepa 1 160'))['trained']
        assert not np.array_equal(r._world_jepa_online.enc['W1'], second_weights)
        live = r._world_jepa_online
        before = live.enc['W1'].copy()
        prior_receipts = dict(r._world_jepa_lineage)
        original_tx = r.store.tx
        @contextmanager
        def fail_commit():
            with original_tx() as c:
                yield c
                raise OSError('synthetic commit failure')
        with monkeypatch.context() as patch:
            patch.setattr(r.store, 'tx', fail_commit)
            with pytest.raises(OSError, match='commit failure'):
                op.run(':growth jepa 1 160')
            with pytest.raises(OSError, match='commit failure'):
                op.run(':growth jepa restore')
        assert r._world_jepa_online is live and np.array_equal(live.enc['W1'], before)
        assert r._world_jepa_lineage == prior_receipts
        touched = []
        class UnsafeHistory:
            def __deepcopy__(self, memo):
                touched.append(True)
                live.enc['W1'][0, 0] += 1
                return self
        live.history.append(UnsafeHistory())
        with pytest.raises(ValueError, match='history'):
            op.run(':growth jepa 1 160')
        assert not touched and np.array_equal(live.enc['W1'], before)
        live.history.pop()
        # If publication succeeds but reporting fails, the operation may have
        # taken effect.  Both the new generation and the prior one stay valid.
        before_manifest = json.loads(manifest_path.read_bytes())
        publish = lineage_checkpoint._publish_manifest
        def fail_after_publish(fd, value):
            publish(fd, value)
            raise OSError('injected post-publication failure')
        with monkeypatch.context() as patch:
            patch.setattr(lineage_checkpoint, '_publish_manifest', fail_after_publish)
            with pytest.raises(OSError, match='post-publication failure'):
                op.run(':growth jepa save')
        after_manifest = json.loads(manifest_path.read_bytes())
        assert after_manifest['active']['id'] != before_manifest['active']['id']
        assert after_manifest['previous'] == before_manifest['active']
        assert json.loads(op.run(':growth jepa previous'))['selection'] == 'previous'
        assert json.loads(op.run(':growth jepa restore'))['selection'] == 'active'
        assert not (tmp_path / 'world_jepa_online').exists()
        live = r._world_jepa_online
        before = live.enc['W1'].copy()
        first_source = r.store.one('SELECT source_id FROM events WHERE id=?', (events[0],))['source_id']
        with r.store.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (first_source,))
        with pytest.raises(ValueError, match='source no longer verifiable'):
            op.run(':growth jepa restore')
        assert r._world_jepa_online is live and np.array_equal(live.enc['W1'], before)
        # The oldest receipt is outside this small new batch; previous lineage
        # must still be checked rather than silently forgotten.
        with pytest.raises(ValueError, match='source no longer verifiable'):
            op.run(':growth jepa 1 16')
        assert r._world_jepa_online is live and np.array_equal(live.enc['W1'], before)
        assert r._world_jepa_quarantined is True
        with pytest.raises(ValueError, match='quarantined'):
            op.run(':growth jepa 1 16')
    finally:
        r.close()


def test_unbound_prior_model_is_never_continued(tmp_path):
    r = Runtime(tmp_path)
    try:
        r.sleep.cycle.set_policy('enabled', 'off')
        r.cfg['learning_mode'] = 'SHADOW_UPDATE'
        marker = object()
        r._world_jepa_online = marker
        with pytest.raises(ValueError, match='unbound legacy'):
            r.world_jepa_update(steps=1, limit=32, authority=online_world_policy.HUMAN)
        assert r._world_jepa_online is marker
    finally:
        r.close()


def test_save_restore_require_authority_and_never_touch_existing_files(tmp_path):
    r = Runtime(tmp_path)
    try:
        home = tmp_path / 'world_jepa_online'
        home.mkdir()
        prior = home / 'active.json'
        prior.write_text('existing legacy manifest')
        with pytest.raises(PermissionError): r.world_jepa_restore()
        Operator(r).run(':learning shadow')
        with pytest.raises(ValueError, match='lineage'):
            r.world_jepa_restore(authority=online_world_policy.HUMAN)
        with pytest.raises(ValueError, match='lineage'):
            r.world_jepa_save(authority=online_world_policy.HUMAN)
        assert prior.read_text() == 'existing legacy manifest'
        assert not (tmp_path / 'world_jepa_lineage').exists()
    finally:
        r.close()

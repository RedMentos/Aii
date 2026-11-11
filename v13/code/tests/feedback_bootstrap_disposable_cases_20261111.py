"""User correction preview tied to the same real T8 event as World learning."""
import json

import numpy as np
import pytest

from integrated_online_world_disposable_cases import synthetic_c3, turn
from test_local_error_route_shadow_candidate_20261109 import correction, emit
from v13 import dataset_probe_candidate, local_error_route_shadow_candidate, online_world_policy
from v13.neuromod import Neuromod
from v13.operator import Operator
from v13.runtime import Runtime


def test_one_event_links_world_receipt_to_explicit_error_preview_without_weight_update(tmp_path):
    r = Runtime(tmp_path)
    try:
        synthetic_c3(r)
        eid = turn(r)
        Operator(r).run(':learning shadow')
        assert r.online_world_update(limit=64, authority=online_world_policy.HUMAN)['learned'] == 1
        world = r._online_world
        action_ids = set(world.processed)
        assert len(action_ids) == 1
        before = world.model.U.copy()
        before_count = world.model.seen
        input_ref, label_ref = correction(r, eid, route='detail', permission='learn')
        n10 = Neuromod(r.store)
        emit(n10, eid, input_ref, label_ref, 0.)
        preview = local_error_route_shadow_candidate.preview(n10, r.session, eid, [1., 0.])
        assert preview['status'] == 'SHADOW_PREVIEW' and preview['t8_action_id'] in action_ids
        assert preview['observed_route'] == 'simple' and preview['corrected_route'] == 'detail'
        assert preview['event_delta'] < 0 and preview['weighted_gradient_norm'] > 0
        assert preview['training_authority'] == preview['decision_authority'] == 0
        assert world.model.seen == before_count and np.array_equal(world.model.U, before)
        with r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?', (label_ref['source_id'],))
        with pytest.raises(ValueError):
            local_error_route_shadow_candidate.preview(n10, r.session, eid, [1., 0.])
        assert world.model.seen == before_count and np.array_equal(world.model.U, before)
    finally:
        r.close()


def test_dataset_catalog_lists_offline_without_admitting_training(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('catalog listing must not open a connection')
    monkeypatch.setattr(dataset_probe_candidate, '_open_viewer', no_network)
    entries = dataset_probe_candidate.list_catalog()
    assert len(entries) == 47 and sum(row['access'] == 'PROBE' for row in entries) == 18
    manifest = json.loads(dataset_probe_candidate.CATALOG_PATH.read_text())
    assert manifest['policy']['automatic_download'] is False
    assert manifest['policy']['automatic_training'] is False

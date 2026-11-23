"""One source through Runtime, learning, compressed archive and revocation."""
import json
import time

import pytest

from integrated_online_world_disposable_cases import synthetic_c3
from v13 import archive, archive_stream_range_candidate, online_world_policy, source_lifecycle_candidate
from v13.online_world import OnlineWorld
from v13.operator import Operator
from v13.runtime import Runtime


def test_archived_user_source_remains_verified_for_world_then_revocation_quarantines(tmp_path):
    r = Runtime(tmp_path)
    try:
        synthetic_c3(r)
        text = 'Synthetic long context Ω😀 for the archive. ' * 180
        r.submit(text)
        deadline = time.monotonic() + 10
        while not r.idle() and time.monotonic() < deadline:
            time.sleep(.003)
        assert r.idle() and r.last_answer()['status'] == 'FINAL'
        eid = r.last_answer()['event_id']
        event = r.store.one('SELECT packet FROM events WHERE id=?', (eid,))
        ref = json.loads(event['packet'])['source_ref']
        Operator(r).run(':learning shadow')
        assert r.online_world_update(limit=64, authority=online_world_policy.HUMAN)['learned'] == 1
        world = r._online_world
        plain = r.home / 'data/blobs' / ref['sha256']
        assert plain.is_file()
        assert archive.archive_blob(r.store, ref['sha256'], clock=lambda: time.time() + 40 * 86400) == 'ARCHIVED'
        assert not plain.exists() and plain.with_name(plain.name + '.z').is_file()
        span = dict(ref, char_start=11, char_end=91)
        assert archive_stream_range_candidate.read_span(r.store, span) == text[11:91]
        assert len(world.predict([0., 0., 0., 1.], 'simple')) == 3
        r.close()
        r = Runtime(tmp_path)
        Operator(r).run(':learning shadow')
        world = OnlineWorld(r)
        assert len(world.predict([0., 0., 0., 1.], 'simple')) == 3
        with r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?', (ref['source_id'],))
        assert source_lifecycle_candidate.cleanup_unreferenced(r.store, ref['source_id']) == 'REMOVED'
        assert not plain.exists() and not plain.with_name(plain.name + '.z').exists()
        with pytest.raises(ValueError, match='source changed or revoked'):
            world.predict([0., 0., 0., 1.], 'simple')
        with pytest.raises(ValueError):
            archive_stream_range_candidate.read_span(r.store, span)
    finally:
        r.close()

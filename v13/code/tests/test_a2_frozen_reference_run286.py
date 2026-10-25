"""Run286: actual SQLite source + frozen A2 blob guard (software only)."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from v13.a2_reference import TEACHER_DIM, validated_teacher_feature
from v13.common import atomic_write, file_hash
from v13.config import initialize
from v13.contracts import packet
from v13.store import Store


class A2FrozenReferenceRun286(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        initialize(self.home)
        self.s = Store(self.home)
        self.e = self.s.event(self.s.new_session(), 'Project R286 budget is 400 units.')
        self.ref = self.e['source_ref']
        self.vector = [float(i % 31 + 1) / 31 for i in range(TEACHER_DIM)]
        self.path = self.home / 'data/blobs/a2_test.json'
        atomic_write(self.path, json.dumps({'embedding': self.vector}, allow_nan=False))
        self.p = packet('PerceptPacket', 'A2_FROZEN_REFERENCE', self.e['event_id'], self.s.generation_id,
                        [self.ref], source_ref=self.ref, segments=[], modality='text',
                        teacher_truth_authority=False, encoder_revision='pinned-needle-rev',
                        feature_path=str(self.path.relative_to(self.home)),
                        feature_sha256=file_hash(self.path), feature_dim=TEACHER_DIM,
                        stop_gradient=True)

    def tearDown(self):
        self.s.close()
        self.temp.cleanup()

    def check(self, packet_=None):
        return validated_teacher_feature(self.s, self.home, packet_ or self.p,
                                         generation=self.s.generation_id,
                                         encoder_revision='pinned-needle-rev',
                                         event_id=self.e['event_id'])

    def test_actual_sqlite_source_and_exact_frozen_vector(self):
        self.assertEqual(self.check(), self.vector)
        self.assertEqual(self.s.read_source(self.ref), 'Project R286 budget is 400 units.')

    def test_changed_generation_revision_or_event_refused(self):
        for key, val in [('brain_generation_id', 'wrong'), ('encoder_revision', 'wrong'), ('event_id', 'evt_wrong')]:
            p = copy.deepcopy(self.p); p[key] = val
            with self.subTest(key=key), self.assertRaises(ValueError): self.check(p)

    def test_teacher_truth_or_gradient_authority_refused(self):
        for key, val in [('teacher_truth_authority', True), ('stop_gradient', False), ('feature_dim', True)]:
            p = copy.deepcopy(self.p); p[key] = val
            with self.subTest(key=key), self.assertRaises(ValueError): self.check(p)

    def test_source_lineage_change_and_revocation_refused(self):
        p = copy.deepcopy(self.p); p['provenance'] = []
        with self.assertRaises(ValueError): self.check(p)
        with self.s.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (self.ref['source_id'],))
        with self.assertRaises(ValueError): self.check()

    def test_hash_tamper_and_nonfinite_refused(self):
        self.path.write_text('broken')
        with self.assertRaises(ValueError): self.check()
        for value in [float('nan'), float('inf'), True]:
            v = self.vector.copy(); v[0] = value
            atomic_write(self.path, json.dumps({'embedding': v}, allow_nan=True))
            p = copy.deepcopy(self.p); p['feature_sha256'] = file_hash(self.path)
            with self.subTest(value=str(value)), self.assertRaises(ValueError): self.check(p)

    def test_blob_directory_symlink_refused(self):
        blob = self.home / 'data/blobs'
        moved = self.home / 'data/blobs-real'
        blob.rename(moved)
        blob.symlink_to(moved, target_is_directory=True)
        with self.assertRaises(OSError): self.check()

    def test_zero_vector_and_extra_payload_refused(self):
        atomic_write(self.path, json.dumps({'embedding': [0.0] * TEACHER_DIM}))
        p = copy.deepcopy(self.p); p['feature_sha256'] = file_hash(self.path)
        with self.assertRaises(ValueError): self.check(p)
        atomic_write(self.path, json.dumps({'embedding': self.vector, 'truth': True}))
        p['feature_sha256'] = file_hash(self.path)
        with self.assertRaises(ValueError): self.check(p)

    def test_path_traversal_and_symlink_refused(self):
        for path in ['../../outside.json', 'data/blobs/../a2_test.json', 'data/blobs/other.json', '/tmp/a2_test.json']:
            p = copy.deepcopy(self.p); p['feature_path'] = path
            with self.subTest(path=path), self.assertRaises((ValueError, FileNotFoundError)): self.check(p)
        self.path.unlink()
        target = self.home / 'other.json'; target.write_text(json.dumps({'embedding': self.vector}))
        self.path.symlink_to(target)
        with self.assertRaises(OSError): self.check()


if __name__ == '__main__': unittest.main()

"""Real SQLite and artifact-path tests; all model outputs are synthetic."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from v13 import aplane
from v13.aplane_gate_bound_candidate import current_binding, student_gate_bound
from v13.common import atomic_write, dumps, file_hash, now, uid
from v13.config import initialize
from v13.contracts import packet
from v13.store import Store


class BoundGateCandidate(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.s = Store(self.home)
        self.models = {'C2_CONTROL': 'c2-fixture-v1'}
        self.s.ensure_generation_snapshot(self.cfg, self.models)
        self.session = self.s.new_session()

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def install(self, component):
        update = uid('upd')
        stem = 'head' if component == 'route' else component
        rel = 'checkpoints/' + stem + '-' + update + '.npz'
        atomic_write(self.home / rel, 'synthetic-' + update)
        manifest = {'commit_eligible': True, 'component': component,
                    'encoder_revision': self.models['C2_CONTROL']}
        with self.s.tx() as c:
            c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',
                      (update, self.s.generation_id, 'PENDING_APPROVAL', rel,
                       file_hash(self.home / rel), dumps(manifest), now()))
        self.s.switch_generation(update, self.cfg, self.models)

    def ready(self):
        self.install('route')
        self.install('a3_student')

    def observation(self, i):
        e = self.s.event(self.session, 'unique synthetic input ' + str(i))
        feature = self.home / 'data/blobs' / (uid('a3') + '.json')
        atomic_write(feature, dumps({'generation': self.s.generation_id,
                                    'component': 'a3_student',
                                    'encoder_revision': self.models['C2_CONTROL'],
                                    'in_support': True}))
        p = packet('PerceptPacket', 'A5_PERCEPT', e['event_id'], self.s.generation_id,
                   [e['source_ref']], source_ref=e['source_ref'], segments=[], modality='text',
                   student_feature_path=str(feature.relative_to(self.home)),
                   student_feature_sha256=file_hash(feature))
        self.s.add_packet('PerceptPacket', p)
        return e, p

    def evaluation(self, e, percept, agree=True, binding=True):
        extra = ({'candidate_model_binding': binding} if isinstance(binding, dict) else
                 {'candidate_model_binding': current_binding(self.s, self.models['C2_CONTROL'])} if binding else {})
        ev = packet('StudentEvaluation', 'C2_CONTROL', e['event_id'], self.s.generation_id,
                    [e['source_ref']], percept_packet_id=percept['packet_id'],
                    source_ref=e['source_ref'], student_route='detail',
                    teacher_route='detail' if agree else 'gist', agreement=agree,
                    routing_authority=0, **extra)
        self.s.add_packet('StudentEvaluation', ev)
        return ev

    def gate(self):
        return student_gate_bound(self.s, self.models['C2_CONTROL'])

    def test_missing_live_model_or_checkpoint_cannot_pass(self):
        self.assertFalse(self.gate()['pass'])
        self.install('route')
        self.assertFalse(self.gate()['pass'])
        self.install('a3_student')
        self.assertFalse(student_gate_bound(self.s, 'wrong-c2-revision')['pass'])
        entry = self.s.components()['a3_student']
        atomic_write(self.home / entry['path'], 'tampered')
        self.assertFalse(self.gate()['pass'])

    def test_legacy_records_and_missing_binding_never_gain_authority(self):
        self.ready()
        for i in range(50):
            e, p = self.observation(i)
            self.evaluation(e, p, binding=False)
        self.assertTrue(aplane.student_gate(self.s)['pass'])
        g = self.gate()
        self.assertFalse(g['pass'])
        self.assertEqual((g['n'], g['excluded']), (0, 50))

    def test_fifty_duplicates_are_one_event_and_latest_wins(self):
        self.ready()
        e, p = self.observation(1)
        for _ in range(50):
            self.evaluation(e, p)
        self.assertTrue(aplane.student_gate(self.s)['pass'])
        g = self.gate()
        self.assertEqual(g['n'], 1)
        self.assertFalse(g['pass'])
        self.evaluation(e, p, agree=False)
        g = self.gate()
        self.assertEqual((g['n'], g['agreement']), (1, 0.0))
        # A bad/newest packet must not allow the older successful one to count.
        self.evaluation(e, p, binding=False)
        self.assertEqual(self.gate()['n'], 0)

    def test_separate_events_with_same_source_report_low_diversity(self):
        self.ready()
        for _ in range(50):
            e, p = self.observation(1)
            self.evaluation(e, p)
        g = self.gate()
        self.assertTrue(g['pass'])  # legacy numerical threshold, not authorization
        self.assertEqual((g['n'], g['unique_source_hashes']), (50, 1))

    def test_feature_hash_and_payload_are_the_same_bytes(self):
        import json
        from v13 import aplane_gate_bound_candidate as candidate
        self.ready()
        e, p = self.observation(1)
        feature = self.home / p['student_feature_path']
        payload = json.loads(feature.read_text())
        payload['in_support'] = False
        atomic_write(feature, dumps(payload))
        p['student_feature_sha256'] = file_hash(feature)
        with self.s.tx() as c:
            c.execute('UPDATE packets SET payload=? WHERE id=?', (dumps(p), p['packet_id']))
        self.evaluation(e, p)

        original_hash = candidate.file_hash
        def swap_after_hash(path):
            h = original_hash(path)
            if Path(path) == feature:
                changed = dict(payload, in_support=True)
                atomic_write(feature, dumps(changed))
            return h
        # The old implementation called file_hash(feature) then separately
        # read its JSON, allowing this swap to admit the wrong bytes.
        with patch.object(candidate, 'file_hash', side_effect=swap_after_hash):
            g = self.gate()
        self.assertEqual(g['n'], 0)
        self.assertFalse(g['pass'])

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO requires POSIX')
    def test_fifo_feature_is_rejected_without_blocking(self):
        self.ready()
        e, p = self.observation(1)
        self.evaluation(e, p)
        feature = self.home / p['student_feature_path']
        feature.unlink()
        os.mkfifo(feature)
        # Run out of process so a regression that blocks on FIFO cannot hang
        # the entire test suite. Store is reopened, not inherited across fork.
        script = ('import json,sys; from pathlib import Path; from v13.store import Store; '
                  'from v13.aplane_gate_bound_candidate import student_gate_bound; '
                  's=Store(Path(sys.argv[1])); '
                  'print(json.dumps(student_gate_bound(s, "c2-fixture-v1"))); s.close()')
        self.s.close()  # Store deliberately holds an exclusive process lock.
        try:
            proc = subprocess.run([sys.executable, '-c', script, str(self.home)],
                                  capture_output=True, text=True, timeout=5)
        finally:
            self.s = Store(self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        import json
        result = json.loads(proc.stdout)
        self.assertEqual(result['n'], 0)
        self.assertFalse(result['pass'])

    def test_fresh_distinct_events_pass_old_generation_does_not(self):
        self.ready()
        for i in range(50):
            e, p = self.observation(i)
            self.evaluation(e, p)
        self.assertTrue(self.gate()['pass'])
        old = self.s.generation_id
        self.install('a3_student')
        self.assertNotEqual(old, self.s.generation_id)
        self.assertTrue(aplane.student_gate(self.s)['pass'])
        self.assertEqual(self.gate()['n'], 0)
        for i in range(50):
            e, p = self.observation('new-' + str(i))
            self.evaluation(e, p)
        self.assertTrue(self.gate()['pass'])
        self.install('route')
        self.assertEqual(self.gate()['n'], 0)
        self.assertFalse(self.gate()['pass'])

    def test_mismatched_model_binding_and_retention_dip_fail(self):
        self.ready()
        old_binding = current_binding(self.s, self.models['C2_CONTROL'])
        wrong = dict(old_binding, route={'sha256': '0' * 64, 'update_id': 'wrong'})
        for i in range(50):
            e, p = self.observation(i)
            self.evaluation(e, p, binding=wrong)
        self.assertEqual(self.gate()['n'], 0)
        for i in range(100):
            e, p = self.observation('matched-' + str(i))
            self.evaluation(e, p, agree=i < 93)
        g = self.gate()
        self.assertEqual(g['agreement'], .93)
        self.assertFalse(g['retention_pass'])
        self.assertFalse(g['pass'])

    def test_source_and_feature_tampering_or_deletion_excludes_event(self):
        self.ready()
        for i in range(50):
            e, p = self.observation(i)
            self.evaluation(e, p)
            if i == 0:
                victim_e, victim_p = e, p
        self.assertTrue(self.gate()['pass'])
        original_feature = (self.home / victim_p['student_feature_path']).read_bytes()
        atomic_write(self.home / victim_p['student_feature_path'], 'tamper')
        self.assertFalse(self.gate()['pass'])
        self.assertEqual(self.gate()['n'], 49)
        atomic_write(self.home / victim_p['student_feature_path'], original_feature)
        self.assertTrue(self.gate()['pass'])
        with self.s.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (victim_e['source_ref']['source_id'],))
        self.assertFalse(self.gate()['pass'])
        self.assertEqual(self.gate()['n'], 49)

    def test_new_generation_during_evaluation_invalidates_snapshot(self):
        self.ready()
        for i in range(50):
            e, p = self.observation(i)
            self.evaluation(e, p)
        outer = self

        class DriftStore:
            def __getattr__(self, name):
                return getattr(outer.s, name)

            def rows(self, sql, args=()):
                result = outer.s.rows(sql, args)
                if 'MAX(q.rowid)' in sql:
                    outer.install('route')
                return result

        g = student_gate_bound(DriftStore(), self.models['C2_CONTROL'])
        self.assertFalse(g['pass'])
        self.assertIn('generation_changed', g['reason'])


if __name__ == '__main__':
    unittest.main()

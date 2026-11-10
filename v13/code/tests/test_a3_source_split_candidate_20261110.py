from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from v13.a3_source_split_candidate import partition, worker_indices
from v13.config import initialize
from v13.store import Store


class A3SourceSplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        home = Path(self.tmp.name)
        initialize(home)
        self.s = Store(home)

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def samples(self, n=100):
        return [self.s.source('synthetic A3 source %03d: München 🚀' % i) for i in range(n)]

    def test_all_groups_are_disjoint_and_stable_when_rows_added(self):
        refs = self.samples()
        first = partition(self.s, refs[:70], (0, 0, 0))
        second = partition(self.s, refs, (0, 0, 0))
        for name in ('train', 'validation', 'test'):
            self.assertEqual(first['split_indices'][name], [i for i in second['split_indices'][name] if i < 70])
        sets = [{refs[i]['sha256'] for i in second['split_indices'][name]} for name in ('train','validation','test')]
        self.assertTrue(all(not a.intersection(b) for i, a in enumerate(sets) for b in sets[i+1:]))
        self.assertEqual(sum(map(len, second['split_indices'].values())), 100)
        self.assertEqual(second['claim'], 'SOURCE_GROUP_SPLIT_ONLY_NO_PROMOTION')
        self.assertEqual(second['manifest_sha256'], partition(self.s, refs, (0,0,0))['manifest_sha256'])
        self.assertNotEqual(second['manifest_sha256'], partition(self.s, refs, (1,0,0))['manifest_sha256'])

    def test_different_spans_of_same_source_stay_in_one_split(self):
        ref = self.s.source('Alpha Beta Gamma')
        a, b = dict(ref, char_start=0, char_end=5), dict(ref, char_start=6, char_end=10)
        result = partition(self.s, [a, b], (0, 0, 0))
        self.assertIn([0, 1], result['split_indices'].values())
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            partition(self.s, [a, a], (0, 0, 0))

    def test_duplicate_content_cannot_be_sneaked_in_with_different_source_id(self):
        a = self.s.source('same text')
        b = self.s.source('same text')
        self.assertEqual(a['sha256'], b['sha256'])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            partition(self.s, [a, b], (0, 0, 0))

    def test_identical_slice_from_different_full_sources_is_rejected(self):
        a = self.s.source('left repeated')
        b = self.s.source('right repeated')
        a.update(char_start=5)
        b.update(char_start=6)
        self.assertNotEqual(a['sha256'], b['sha256'])
        self.assertEqual(self.s.read_source(a), self.s.read_source(b))
        with self.assertRaisesRegex(ValueError, 'Duplicate source slice content'):
            partition(self.s, [a, b], (0, 0, 0))

    def test_existing_worker_receives_no_reserved_test_sources(self):
        refs = self.samples()
        manifest = partition(self.s, refs)
        result = worker_indices(manifest)
        self.assertFalse(set(result['worker_source_indices']) & set(result['reserved_test_source_indices']))
        self.assertEqual({result['worker_source_indices'][i] for i in result['worker_train_indices']},
                         set(manifest['split_indices']['train']))
        self.assertEqual({result['worker_source_indices'][i] for i in result['worker_validation_indices']},
                         set(manifest['split_indices']['validation']))
        manifest['split_indices']['test'].pop()
        with self.assertRaisesRegex(ValueError, 'manifest changed'):
            worker_indices(manifest)

    def test_actual_student_worker_fits_only_train_and_validation_sources(self):
        from v13.student_worker import TEACHER_DIM, train
        refs = self.samples()
        manifest = partition(self.s, refs)
        plan = worker_indices(manifest)
        idx = plan['worker_source_indices']
        rng = np.random.default_rng(20261110)
        teacher = rng.normal(size=(len(idx), TEACHER_DIM))
        inputs = {'config': initialize(Path(self.tmp.name)) | {'student_steps': 1},
                  'texts': [self.s.read_source(refs[i]) for i in idx],
                  'source_groups': [refs[i]['sha256'] for i in idx],
                  'teacher_embeddings': teacher.tolist()}
        out = Path(self.tmp.name) / 'candidate'
        out.mkdir()
        metrics = train(inputs, out)
        used = set(metrics['train_source_groups']) | set(metrics['held_out_source_groups'])
        reserved = {refs[i]['sha256'] for i in plan['reserved_test_source_indices']}
        self.assertFalse(used & reserved)
        self.assertEqual(used, {refs[i]['sha256'] for i in idx})
        self.assertTrue((out / 'candidate.npz').exists())

    def test_missing_deleted_corrupt_sources_or_small_splits_fail(self):
        ref = self.s.source('valid source')
        with self.assertRaisesRegex(ValueError, 'Insufficient'):
            partition(self.s, [ref])
        with self.assertRaises(ValueError):
            partition(self.s, [dict(ref, sha256='0'*64)], (0,0,0))
        with self.s.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (ref['source_id'],))
        with self.assertRaises(ValueError):
            partition(self.s, [ref], (0,0,0))

    def test_mutating_store_and_caller_do_not_change_snapshots(self):
        a, b = self.samples(2)
        supplied = dict(a)
        real = self.s
        class MutatingStore:
            def read_source(self, ref):
                text = real.read_source(ref)
                ref.update(b)
                supplied.update(b)
                return text
        result = partition(MutatingStore(), [supplied], (0,0,0))
        self.assertEqual(result['source_refs'][0], a)

    def test_invalid_ref_and_minimums_rejected(self):
        ref = self.s.source('Äpfel')
        for bad in [None, {}, dict(ref, char_start=True), dict(ref, char_end=0),
                    dict(ref, char_end=999), dict(ref, modality='audio')]:
            with self.subTest(bad=bad), self.assertRaises((ValueError,KeyError)):
                partition(self.s, [bad], (0,0,0))
        with self.assertRaises(ValueError):
            partition(self.s, [ref], (0,False,0))


if __name__ == '__main__':
    unittest.main()

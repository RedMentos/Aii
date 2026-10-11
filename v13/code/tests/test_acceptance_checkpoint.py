"""Filesystem/process recovery checks only; none of these are model proof."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from acceptance_checkpoint import VERSION, acquire_lock, validate_resume, preserve_interrupted, process_identity
from v13.common import file_hash


class AcceptanceCheckpoint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        self.plan = [{'name': 'one', 'script': 'non_native_fixture', 'expected': 'FIXTURE_ONLY'},
                     {'name': 'two', 'script': 'non_native_fixture', 'expected': 'FIXTURE_ONLY'}]
        self.binding = {'source': 'frozen', 'installed': 'frozen', 'device': 'fixture'}
        artifact = self.out / 'one.json'
        artifact.write_text(json.dumps({'status': 'FIXTURE_ONLY', 'native_inference': False}))
        (self.out / 'one.log').write_text('fixture, not model execution\n')
        (self.out / 'one.features.json.gz').write_bytes(b'non-native companion fixture')
        row = {'name': 'one', 'status': 'PASS', 'exit_code': 0, 'observed_status': 'FIXTURE_ONLY', 'artifact_sha256': file_hash(artifact),
               'checkpoint_files': {p.name: file_hash(p) for p in self.out.glob('one.*')}}
        self.report = {'checkpoint_version': VERSION, 'resume_binding': self.binding,
                       'stage_spec': self.plan, 'stages': [row]}

    def test_exact_completed_stage_and_completed_failure_are_retained(self):
        self.assertEqual(validate_resume(self.report, self.out, self.binding, self.plan), 1)
        self.report['stages'][0].update(status='FAIL', exit_code=2)
        self.assertEqual(validate_resume(self.report, self.out, self.binding, self.plan), 1)
        self.assertEqual(self.report['stages'][0]['status'], 'FAIL')

    def test_changed_features_log_source_plan_and_legacy_are_refused(self):
        for name in ('one.log', 'one.features.json.gz', 'one.json'):
            path = self.out / name
            original = path.read_bytes()
            path.write_bytes(original + b'changed')
            with self.assertRaises(ValueError): validate_resume(self.report, self.out, self.binding, self.plan)
            path.write_bytes(original)
        for binding, plan in [({'source': 'different'}, self.plan), (self.binding, self.plan[:1])]:
            with self.assertRaises(ValueError): validate_resume(self.report, self.out, binding, plan)
        legacy = copy.deepcopy(self.report);legacy.pop('checkpoint_version')
        with self.assertRaises(ValueError): validate_resume(legacy, self.out, self.binding, self.plan)
        altered = copy.deepcopy(self.report);altered['stages'][0]['observed_status'] = 'INVENTED_PASS'
        with self.assertRaises(ValueError): validate_resume(altered, self.out, self.binding, self.plan)

    def test_interrupted_attempt_bytes_and_original_row_are_preserved(self):
        row = {'name': 'two', 'status': 'RUNNING'}
        self.report['stages'].append(row)
        (self.out / 'two.log').write_bytes(b'actual interruption fixture')
        self.assertEqual(validate_resume(self.report, self.out, self.binding, self.plan), 1)
        preserve_interrupted(self.report, self.out)
        saved = self.report['interrupted_attempts'][0]
        self.assertEqual(saved['row'], row)
        self.assertEqual((self.out / saved['directory'] / 'two.log').read_bytes(), b'actual interruption fixture')
        self.assertEqual(len(self.report['stages']), 1)

    def test_exclusive_collector_and_live_previous_process_refuse_duplicate_run(self):
        lock = acquire_lock(self.out)
        self.addCleanup(lock.close)
        with self.assertRaises(BlockingIOError): acquire_lock(self.out)
        self.report['stages'].append({'name': 'two', 'status': 'RUNNING',
                                      'process_identity': process_identity(os.getpid())})
        with self.assertRaisesRegex(ValueError, 'still alive'):
            validate_resume(self.report, self.out, self.binding, self.plan)

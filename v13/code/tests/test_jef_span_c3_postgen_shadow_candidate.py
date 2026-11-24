"""Run117AB real Store postgen and original recorded native output replay."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.jef_span_c3_postgen_shadow_candidate import evaluate, PASS

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/RUN117Z_REAL_JEF_NATIVE_SEED1065.json'
FIXTURE_SHA = 'cb008f27a4d1ef7f0f288419ac276ebb67c8d7958da3c62104994822dd90634d'
ORIGINAL = Path(os.environ.get('V13_RUN117Z_ORIGINAL_ZIP',
                               '/mnt/data/run117z-original-native.zip'))
ORIGINAL_SHA = '65939e4dea18f15bf11d5b1b3c5128f5a6128c6d03b9d2beb090f185d03fb69a'


class PostgenGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA
        cls.rows = json.loads(FIXTURE.read_text())['rows']

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.row = self.rows[0]
        self.r = QuoteRuntime(Path(self.tmp.name) / 'home', self.row)
        self.prior = self.r.store.event(self.r.session, self.row['prior'])
        self.current = self.r.store.event(self.r.session, self.row['current'])

    def tearDown(self):
        self.r.close();self.tmp.cleanup()

    def run_guard(self, callback=lambda _: '{"choice":"A","remaining":50}', **kw):
        return evaluate(self.r, self.prior, self.current, callback,
                        **({'operator_opt_in': True, 'callback_opt_in': True} | kw))

    def assert_no_authority(self, r):
        self.assertFalse(r['output_committed'])
        self.assertEqual(r['tool_dispatches'], 0)
        self.assertEqual(r['delivery_authority'], 0)
        self.assertEqual(r['learning_authority'], 0)
        self.assertEqual(r['jepa_weight'], 0)
        self.assertFalse(r['native_proof'])
        self.assertFalse(r['whole_system_complete'])

    def test_default_off_and_callback_consent_required(self):
        called = []
        for kw in ({'operator_opt_in': False}, {'callback_opt_in': False}):
            r = self.run_guard(lambda _: called.append(True), **kw)
            self.assertEqual(r['status'], 'OFF')
            self.assert_no_authority(r)
        self.assertEqual(called, [])

    def test_recorded_native_six_typed_outputs_replay_without_inference(self):
        self.assertEqual(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(), ORIGINAL_SHA)
        with zipfile.ZipFile(ORIGINAL) as z:
            native = json.loads(z.read('NATIVE_CASE/report.json'))
        self.assertEqual(native['native_c3_calls'], 12)
        for row, native_row in zip(self.rows, native['rows']):
            with self.subTest(project=row['id']):
                with tempfile.TemporaryDirectory() as d:
                    r = QuoteRuntime(Path(d) / 'home', row)
                    try:
                        prior = r.store.event(r.session, row['prior'])
                        current = r.store.event(r.session, row['current'])
                        typed = next(a for a in native_row['arms']
                                     if a['arm'] == 'REAL_STORE_JEF_TYPED')
                        output = typed['output']
                        result = evaluate(r, prior, current, lambda _: output,
                                          operator_opt_in=True, callback_opt_in=True)
                        self.assertEqual(result['status'], PASS, result)
                        self.assertTrue(result['source_rechecked'])
                        self.assertTrue(result['formatter_match_shadow'])
                        self.assertEqual(result['output_sha256'],
                                         hashlib.sha256(output.encode()).hexdigest())
                        self.assertFalse(result['native_proof'])
                        self.assertEqual(r.store.one('SELECT COUNT(*) AS n FROM actions')['n'], 0)
                        self.assert_no_authority(result)
                    finally:
                        r.close()

    def test_correct_synthetic_callback_is_shadow_only(self):
        r = self.run_guard()
        self.assertEqual(r['status'], PASS)
        self.assertTrue(r['callback_invoked'])
        self.assert_no_authority(r)

    def test_wrong_output_rejected(self):
        for raw in ('{"choice":"B","remaining":50}',
                    '{"choice":"A","remaining":49}',
                    '{"choice":"NONE","remaining":null}'):
            with self.subTest(raw=raw):
                r = self.run_guard(lambda _: raw)
                self.assertEqual(r['status'], 'FORMATTER_CANDIDATE_MISMATCH_RED')
                self.assertNotIn('output_sha256', r)
                self.assert_no_authority(r)

    def test_malformed_duplicate_extra_bool_nan_code_fence_oversize(self):
        cases = ('{"choice":"A","choice":"B","remaining":50}',
                 '{"choice":"A","remaining":50,"approved":true}',
                 '{"choice":"A","remaining":true}',
                 '{"choice":"A","remaining":NaN}',
                 '{"choice":"A","remaining":null}',
                 '{"choice":"A","remaining":-1}',
                 '```json\n{"choice":"A","remaining":50}\n```',
                 '{"choice":"A","remaining":50}' + ' ' * 300,
                 '{"choice":"A","remaining":50} trailing')
        for raw in cases:
            with self.subTest(raw=raw[:40]):
                r = self.run_guard(lambda _: raw)
                self.assertEqual(r['status'], 'FORMATTER_JSON_RED', r)
                self.assert_no_authority(r)

    def test_callback_prompt_mutation_rejected(self):
        def callback(messages):
            messages[1]['content'] = '{}'
            return '{"choice":"A","remaining":50}'
        r = self.run_guard(callback)
        self.assertEqual(r['status'], 'CALLBACK_PROMPT_MUTATED_RED')
        self.assert_no_authority(r)

    def test_late_user_correction_rejected(self):
        def callback(_):
            self.r.store.event(self.r.session, 'Project Helix correction. Cancel the request.')
            return '{"choice":"A","remaining":50}'
        r = self.run_guard(callback)
        self.assertEqual(r['status'], 'CALLBACK_STORE_CHANGED_RED')
        self.assert_no_authority(r)

    def test_store_write_rejected(self):
        def callback(_):
            with self.r.store.tx() as db:
                db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                           (self.prior['source_ref']['source_id'],))
            return '{"choice":"A","remaining":50}'
        r = self.run_guard(callback)
        self.assertEqual(r['status'], 'CALLBACK_STORE_CHANGED_RED')
        self.assert_no_authority(r)

    def test_deleted_source_preflight_refused_no_callback(self):
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.prior['source_ref']['source_id'],))
        called = []
        r = self.run_guard(lambda _: called.append(True))
        self.assertEqual(r['status'], 'SOURCE_PREFLIGHT_RED')
        self.assertEqual(called, [])
        self.assert_no_authority(r)

    def test_callback_exception_and_approval_refused(self):
        def bad(_):
            raise RuntimeError('synthetic callback failure')
        r = self.run_guard(bad)
        self.assertEqual(r['status'], 'CALLBACK_EXCEPTION_RED')
        self.assertEqual(r['error_type'], 'RuntimeError')
        self.assert_no_authority(r)
        called = []
        r = self.run_guard(lambda _: called.append(True),
                           approval_receipt={'approved': True})
        self.assertEqual(r['status'], 'REAL_TTY_APPROVAL_UNSUPPORTED_RED')
        self.assertEqual(called, [])
        self.assert_no_authority(r)


if __name__ == '__main__':
    unittest.main()

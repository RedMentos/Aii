"""Run571 source-only fail-stop native executor contract tests; never run a model."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run571_current_default_native as runner


class CurrentDefaultExecutor(unittest.TestCase):
    def test_plan_is_exclusive_and_does_not_call_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / 'new'
            with patch.object(runner.original_native, 'verify_installed') as verify, \
                 patch.object(runner.z2b, 'run_one') as native:
                p = runner.prepare_plan(work)
                self.assertEqual(p['planned_native_consumer_rows'], 84)
                self.assertEqual(runner.exact_plan(work), p)
                self.assertFalse(p['native_executed'])
                verify.assert_not_called()
                native.assert_not_called()
                with self.assertRaisesRegex(ValueError, 'FRESH_WORK_DIRECTORY_REQUIRED'):
                    runner.prepare_plan(work)

    def test_missing_or_tampered_plan_refused_before_model_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            with patch.object(runner.original_native, 'verify_installed') as verify:
                with self.assertRaisesRegex(ValueError, 'SOURCE_PLAN_MISSING'):
                    runner.execute(work, work / 'installed')
                runner.prepare_plan(work)
                data = json.loads((work / runner.PLAN).read_text())
                data['row_keys'][0] = 'TAMPER'
                (work / runner.PLAN).write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError, 'SOURCE_PLAN_CHANGED'):
                    runner.execute(work, work / 'installed')
                verify.assert_not_called()

    def test_harness_globals_restored_on_normal_and_exception(self):
        original_fixtures = runner.z2.FIXTURES
        original_z2 = dict(runner.z2.ARMS)
        original_z2b = dict(runner.z2b.ARMS)
        original_seeds = runner.z2b.SEEDS
        with runner.isolated_harness():
            self.assertEqual([f['id'] for f in runner.z2.FIXTURES],
                             [s[0] for s in runner.new.SPECS])
            self.assertEqual(runner.z2b.SEEDS, (41,))
            self.assertEqual(runner.z2b.ARMS['CURRENT'],
                             {'base': 'CURRENT', 'query': False})
            self.assertEqual(runner.z2.ARMS['CURRENT']['b2_quote_select'], 'pointer')
            self.assertEqual(runner.z2.ARMS['LEGACY']['b2_quote_select'], 'off')
        self.assertIs(runner.z2.FIXTURES, original_fixtures)
        self.assertEqual(runner.z2.ARMS, original_z2)
        self.assertEqual(runner.z2b.ARMS, original_z2b)
        self.assertEqual(runner.z2b.SEEDS, original_seeds)
        with self.assertRaisesRegex(RuntimeError, 'SYNTHETIC_FAILURE'):
            with runner.isolated_harness():
                raise RuntimeError('SYNTHETIC_FAILURE')
        self.assertIs(runner.z2.FIXTURES, original_fixtures)
        self.assertEqual(runner.z2.ARMS, original_z2)
        self.assertEqual(runner.z2b.ARMS, original_z2b)
        self.assertEqual(runner.z2b.SEEDS, original_seeds)

    def test_installed_model_preflight_refusal_has_no_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            runner.prepare_plan(work)
            with patch.object(runner.original_native, 'verify_installed',
                              side_effect=ValueError('PINNED_MODEL_MISSING')), \
                 patch.object(runner.z2b, 'run_one') as native:
                with self.assertRaisesRegex(ValueError, 'PINNED_MODEL_MISSING'):
                    runner.execute(work, work / 'installed')
                native.assert_not_called()
            self.assertFalse((work / runner.PROGRESS).exists())
            self.assertFalse((work / runner.RESULT).exists())

    def test_first_native_failure_stops_without_retry_or_next_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            p = runner.prepare_plan(work)
            preflight = {
                'model_sha256': p['original_model_sha256_expected_not_retrieved'],
                'runner_sha256': p['original_runner_sha256_expected_not_retrieved'],
                'runtime_library_sha256': {'lib.so': 'a' * 64},
                'native_executed': False,
            }
            old = runner.z2.FIXTURES
            with patch.object(runner.original_native, 'verify_installed', return_value=preflight), \
                 patch.object(runner.z2b, 'run_one',
                              side_effect=RuntimeError('SYNTHETIC_NATIVE_FAIL')) as native:
                with self.assertRaisesRegex(RuntimeError, 'SYNTHETIC_NATIVE_FAIL'):
                    runner.execute(work, work / 'installed')
                native.assert_called_once()
                with self.assertRaisesRegex(ValueError, 'REFUSE_REUSE_OR_PARTIAL_NATIVE_ATTEMPT'):
                    runner.execute(work, work / 'installed')
            progress = [json.loads(x) for x in (work / runner.PROGRESS).read_text().splitlines()]
            self.assertEqual([(x['arm'], x['state']) for x in progress],
                             [('CURRENT', 'STARTED')])
            self.assertFalse((work / runner.RESULT).exists())
            self.assertIs(runner.z2.FIXTURES, old)

    def make_arm(self, work, arm):
        rid = runner.z2b.run_id(arm, runner.new.SEED)
        source = []
        tool = []
        for spec in runner.new.SPECS:
            for variant in runner.new.VARIANTS:
                messages = [{'role': 'user', 'content': spec[0]}]
                source.append({'fixture': spec[0], 'variant': variant,
                               'oracle_visible_to_native': False,
                               'consumer_messages': messages})
                tool.append({'fixture': spec[0], 'variant': variant,
                             'oracle_visible_to_native': False,
                             'status': 'RECORDED',
                             'consumer_messages_sha256':
                                 hashlib.sha256(runner.new.canonical(messages)).hexdigest(),
                             'score': {'utility': .25}})
        summary = {'run': rid, 'arm': arm, 'seed': runner.new.SEED,
                   'tool_summary': {v: {'wrong_committed': 0, 'mean_utility': .25}
                                    for v in runner.new.VARIANTS}}
        (work / ('step2_' + rid + '.json')).write_text(json.dumps({
            'installed_artifacts_unchanged': True, 'rows': source}))
        (work / ('tool_' + rid + '.json')).write_text(json.dumps({
            'installed_artifacts_unchanged': True, 'rows': tool}))
        (work / ('summary_' + rid + '.json')).write_text(json.dumps(summary))
        return summary

    def test_structural_receipt_rejects_wrong_committed_and_oracle(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            summary = self.make_arm(work, 'CURRENT')
            receipt = runner.validate_arm(work, 'CURRENT', summary)
            self.assertEqual(receipt['rows'], 42)
            self.assertEqual(receipt['wrong_committed'], 0)
            bad = copy.deepcopy(summary)
            bad['tool_summary']['both_exact']['wrong_committed'] = 1
            (work / 'summary_CURRENT_s41.json').write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, 'WRONG_COMMITTED_OR_VARIANT_MISSING'):
                runner.validate_arm(work, 'CURRENT', bad)
            (work / 'summary_CURRENT_s41.json').write_text(json.dumps(summary))
            path = work / 'tool_CURRENT_s41.json'
            tool = json.loads(path.read_text())
            tool['rows'][0]['oracle_visible_to_native'] = True
            path.write_text(json.dumps(tool))
            with self.assertRaisesRegex(ValueError, 'ORACLE_OR_ROW_STATUS'):
                runner.validate_arm(work, 'CURRENT', summary)

    def test_nonfinite_and_consumer_tampering_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            summary = self.make_arm(work, 'LEGACY')
            path = work / 'tool_LEGACY_s41.json'
            tool = json.loads(path.read_text())
            tool['rows'][0]['score']['utility'] = float('nan')
            path.write_text(json.dumps(tool))
            with self.assertRaisesRegex(ValueError, 'NONFINITE_OR_INVALID_UTILITY'):
                runner.validate_arm(work, 'LEGACY', summary)
            tool['rows'][0]['score']['utility'] = .25
            tool['rows'][0]['consumer_messages_sha256'] = '0' * 64
            path.write_text(json.dumps(tool))
            with self.assertRaisesRegex(ValueError, 'CONSUMER_SOURCE_BINDING_CHANGED'):
                runner.validate_arm(work, 'LEGACY', summary)


if __name__ == '__main__':
    unittest.main()

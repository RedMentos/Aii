"""Mock-only STEP2 collector tests. No models or native inference."""
import fcntl
import json
from pathlib import Path
import tempfile
import unittest

from scripts.step2_fourarm_native_collector_candidate import (
    ARMS, SEEDS, canonical, collect, load_registration,
    make_registration, sha, write_new, verify_native_reports, VARIANTS,
)


class CollectorCandidate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.lock = self.root / 'coordinator.lock'
        self.lock.touch()
        self.work = self.root / 'fresh'
        self.sources = {f'source{i}.py': str(i) * 64 for i in range(10)}
        self.artifacts = {'model_sha256': {'B1_DETAIL': 'a' * 64,
                                           'B2_GIST': 'b' * 64,
                                           'C3_LANGUAGE': 'c' * 64},
                          'runner_sha256': 'd' * 64}
        self.ids = [f'Fixture{i}' for i in range(10)]
        self.reg = make_registration(self.sources, self.artifacts, self.ids, 'e' * 64)
        self.regfile = self.root / 'registered.json'
        raw = canonical(self.reg)
        write_new(self.regfile, raw)
        self.pin = sha(raw)
        self.calls = []

    def fake_run(self, arm, seed, run_dir):
        self.calls.append((arm, seed))
        run_dir.mkdir(parents=True, exist_ok=False)
        rid = f'{arm}_s{seed}'
        raw = run_dir / f'step2_{rid}.json'
        tool = run_dir / f'tool_{rid}.json'
        raw.write_text(json.dumps({'arm': arm, 'seed': seed, 'status': 'RECORDED'}))
        tool.write_text(json.dumps({'arm': arm, 'seed': seed, 'status': 'RECORDED'}))
        models = dict(self.artifacts['model_sha256'])
        if arm.startswith('S'):
            models['B2_GIST'] = models['B1_DETAIL']
        summary = {'arm': arm, 'seed': seed, 'step2_status': 'UTILITY_FAIL',
                   'tool_status': 'TOOL_UTILITY_FAIL',
                   'enable': {'seed': seed},
                   'queried_offers': {'offers': 2, 'with_question': 2}}
        return summary, raw, tool, models

    def call(self):
        return collect(self.regfile, self.pin, self.lock, self.work,
                       lambda: self.sources, lambda: self.artifacts,
                       self.fake_run, 'LINUX_NATIVE',
                       exclusive_owner_confirmed=True)

    def test_mock_twelve_serial_runs_are_sealed_without_gate_promotion(self):
        result = self.call()
        self.assertEqual(result['runs'], 12)
        self.assertFalse(result['canonical_gate_pass'])
        self.assertEqual(self.calls, [(arm, seed) for seed in SEEDS for arm in ARMS])
        manifest = (self.work / 'manifest.json').read_bytes()
        self.assertEqual(result['manifest_sha256'], sha(manifest))
        data = json.loads(manifest)
        self.assertEqual(data['fixture_ids'], self.ids)
        self.assertEqual(len(data['runs']), 12)
        for entry in data['runs']:
            summary = (self.work / entry['summary']).read_bytes()
            raw = (self.work / entry['raw']).read_bytes()
            self.assertEqual(sha(summary), entry['summary_sha256'])
            self.assertEqual(sha(raw), entry['raw_sha256'])
            sealed = json.loads(summary)
            self.assertEqual(sealed['raw_sha256'], sha(raw))
            self.assertEqual(sealed['registration_sha256'], self.pin)
            self.assertFalse(sealed['canonical_gate_pass'])
            self.assertEqual(sealed['jepa_weight'], 0)
        with self.assertRaises(ValueError):
            self.call()  # No stale reuse, no overwrite.

    def test_no_owner_or_wrong_registration_refuses_before_work(self):
        with self.assertRaises(ValueError):
            collect(self.regfile, self.pin, self.lock, self.work,
                    lambda: self.sources, lambda: self.artifacts,
                    self.fake_run, 'LINUX_NATIVE', exclusive_owner_confirmed=False)
        self.assertFalse(self.work.exists())
        with self.assertRaises(ValueError):
            collect(self.regfile, '0' * 64, self.lock, self.work,
                    lambda: self.sources, lambda: self.artifacts,
                    self.fake_run, 'LINUX_NATIVE', exclusive_owner_confirmed=True)
        self.assertFalse(self.work.exists())
        self.assertEqual(self.calls, [])

    def test_changed_source_model_or_lock_refuses_without_native(self):
        old = self.sources
        self.sources = dict(old, extra='f' * 64)
        with self.assertRaises(ValueError):
            self.call()
        self.sources = old
        old_art = self.artifacts
        self.artifacts = dict(old_art, runner_sha256='9' * 64)
        with self.assertRaises(ValueError):
            self.call()
        self.artifacts = old_art
        with self.lock.open('r+') as locked:
            fcntl.flock(locked, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.call()
            fcntl.flock(locked, fcntl.LOCK_UN)
        self.assertFalse(self.work.exists())
        self.assertEqual(self.calls, [])

    def test_incomplete_native_row_retained_without_manifest(self):
        def bad(arm, seed, run_dir):
            summary, raw, tool, models = self.fake_run(arm, seed, run_dir)
            summary['tool_status'] = 'RUNNING'
            return summary, raw, tool, models
        with self.assertRaises(ValueError):
            collect(self.regfile, self.pin, self.lock, self.work,
                    lambda: self.sources, lambda: self.artifacts,
                    bad, 'LINUX_NATIVE', exclusive_owner_confirmed=True)
        self.assertEqual(self.calls, [('TC', 27)])
        self.assertTrue((self.work / 'native_TC_s27' / 'step2_TC_s27.json').exists())
        self.assertFalse((self.work / 'manifest.json').exists())

    def test_source_drift_after_first_native_row_preserves_closed_partial(self):
        def drifting(arm, seed, run_dir):
            result = self.fake_run(arm, seed, run_dir)
            self.sources = dict(self.sources, changed='f' * 64)
            return result
        with self.assertRaises(ValueError):
            collect(self.regfile, self.pin, self.lock, self.work,
                    lambda: self.sources, lambda: self.artifacts,
                    drifting, 'LINUX_NATIVE', exclusive_owner_confirmed=True)
        self.assertEqual(self.calls, [('TC', 27)])
        self.assertTrue((self.work / 'TC_s27.raw').exists())
        self.assertTrue((self.work / 'TC_s27.json').exists())
        self.assertFalse((self.work / 'manifest.json').exists())

    def test_exact_native_row_digest_verification_rejects_tampering(self):
        rows = [{'fixture': fid, 'variant': variant, 'status': 'RECORDED',
                 'score': {'utility': 0.0}}
                for fid in self.ids for variant in VARIANTS]
        hashes = {r['fixture'] + ':' + r['variant']: sha(canonical(r)) for r in rows}
        source = {'status': 'UTILITY_FAIL', 'fixture_sha256': 'e' * 64,
                  'fixtures': [{'id': fid} for fid in self.ids],
                  'source_unchanged': True, 'installed_artifacts_unchanged': True,
                  'all_structural_checks_passed': True,
                  'rows': rows, 'row_sha256': hashes}
        tool = {'status': 'TOOL_UTILITY_FAIL', 'installed_artifacts_unchanged': True,
                'rows': [dict(r) for r in rows], 'row_sha256': dict(hashes)}
        def verify():
            return verify_native_reports(canonical(source), canonical(tool), self.ids, 'e' * 64)
        self.assertEqual(len(verify()[0]['rows']), 70)
        source['rows'][0]['score']['utility'] = 1.0
        with self.assertRaises(ValueError):
            verify()
        source['rows'][0]['score']['utility'] = 0.0
        tool['rows'].pop()
        with self.assertRaises(ValueError):
            verify()
        tool['rows'].append(dict(rows[-1]))
        tool['status'] = 'RUNNING'
        with self.assertRaises(ValueError):
            verify()
        tool['status'] = 'TOOL_UTILITY_FAIL'
        source['source_unchanged'] = False
        with self.assertRaises(ValueError):
            verify()

    def test_registration_rejects_shared_body_as_two_distinct(self):
        same = {'model_sha256': {'B1_DETAIL': 'a' * 64,
                                 'B2_GIST': 'a' * 64,
                                 'C3_LANGUAGE': 'c' * 64},
                'runner_sha256': 'd' * 64}
        with self.assertRaises(ValueError):
            make_registration(self.sources, same, self.ids, 'e' * 64)
        self.assertEqual(load_registration(self.regfile, self.pin), self.reg)


if __name__ == '__main__':
    unittest.main()

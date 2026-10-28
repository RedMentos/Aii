"""Cross-organ native-shaped MOCK evidence: software-only, never a native proof."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.step2_fourarm_native_collector_candidate import (
    ARMS, SEEDS, VARIANTS, canonical, collect, make_registration, sha, write_new,
)
from scripts.step2_longnote_fourarm_io import load
from tests.test_step2_longnote_fourarm_analysis_20261028 import IDS, fixture


def report_pair(summary, fixtures, fixture_hash, models, runner_sha256):
    rows = []
    for i, fid in enumerate(IDS):
        for variant in VARIANTS:
            # Deterministic synthetic field checks, matching the summary profiles.
            fields = {}
            for key in ('A.remaining', 'A.eligible', 'B.remaining', 'B.eligible', 'action'):
                fields[key] = i < (2 if variant == 'b1_only' else 9)
            for key in ('A.cost', 'A.days', 'A.local', 'B.cost', 'B.days', 'B.local'):
                fields[key] = i < (9 if variant == 'b1_only' else 2)
            rows.append({'fixture': fid, 'variant': variant, 'status': 'RECORDED',
                         'score': {'utility': summary['episode_utility_tool'][fid + ':' + variant],
                                   'field_checks': fields}})
    hashes = {r['fixture'] + ':' + r['variant']: sha(canonical(r)) for r in rows}
    source = {'status': summary['step2_status'], 'fixture_sha256': fixture_hash,
              'mock_run': {'arm': summary['arm'], 'seed': summary['seed']},
              'fixtures': fixtures, 'rows': rows, 'row_sha256': hashes,
              'source_unchanged': True, 'all_structural_checks_passed': True,
              'installed_artifacts_unchanged': True,
              'z2b_run': {'arm': summary['arm'], 'seed': summary['seed'],
                          'enable': summary['enable']},
              'z2b_queried_offers': summary['queried_offers'],
              'preparations': [{'status': 'RECORDED', 'model_sha256': models,
                                'runner_sha256': runner_sha256}]}
    tool = {'status': summary['tool_status'], 'rows': copy.deepcopy(rows),
            'mock_run': {'arm': summary['arm'], 'seed': summary['seed']},
            'row_sha256': dict(hashes), 'installed_artifacts_unchanged': True}
    return canonical(source), canonical(tool)


class CollectorScorerIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lock = self.root / 'coordinator.lock'
        self.lock.touch()
        self.work = self.root / 'sealed'
        self.sources = {f'source{i}.py': str(i) * 64 for i in range(10)}
        self.models = {'B1_DETAIL': 'a' * 64, 'B2_GIST': 'b' * 64,
                       'C3_LANGUAGE': 'c' * 64}
        self.artifacts = {'model_sha256': self.models, 'runner_sha256': 'd' * 64}
        self.fixtures = [{'id': fid} for fid in IDS]
        self.fixture_hash = sha(canonical(self.fixtures))
        self.registration = self.root / 'registration.json'
        reg = make_registration(self.sources, self.artifacts, IDS, self.fixture_hash)
        raw = canonical(reg)
        write_new(self.registration, raw)
        self.pin = sha(raw)
        self.by_key = {(r['arm'], r['seed']): r for r in fixture()}

    def run_one(self, arm, seed, run_dir):
        run_dir.mkdir(parents=True, exist_ok=False)
        summary = copy.deepcopy(self.by_key[arm, seed])
        models = dict(self.models)
        if arm.startswith('S'):
            models['B2_GIST'] = models['B1_DETAIL']
        first, second = report_pair(summary, self.fixtures, self.fixture_hash,
                                    models, self.artifacts['runner_sha256'])
        source = run_dir / 'step2.json'
        tool = run_dir / 'tool.json'
        source.write_bytes(first)
        tool.write_bytes(second)
        return summary, source, tool, models

    def collect(self):
        return collect(self.registration, self.pin, self.lock, self.work,
                       lambda: self.sources, lambda: self.artifacts,
                       self.run_one, 'LINUX_NATIVE',
                       exclusive_owner_confirmed=True)

    def check(self, pin):
        return load(self.work, 'manifest.json', pin, IDS, self.fixture_hash)

    def reseal(self, name, data):
        (self.work / name).write_bytes(data)
        manifest = json.loads((self.work / 'manifest.json').read_bytes())
        for entry in manifest['runs']:
            if entry['summary'] == name:
                entry['summary_sha256'] = sha(data)
            if entry['raw'] == name:
                entry['raw_sha256'] = sha(data)
                summary = json.loads((self.work / entry['summary']).read_bytes())
                summary['raw_sha256'] = sha(data)
                summary_data = canonical(summary)
                (self.work / entry['summary']).write_bytes(summary_data)
                entry['summary_sha256'] = sha(summary_data)
        raw_manifest = canonical(manifest)
        (self.work / 'manifest.json').write_bytes(raw_manifest)
        return sha(raw_manifest)

    def test_mock_collector_to_scorer_roundtrip_never_promotes(self):
        sealed = self.collect()
        self.assertEqual(sealed['runs'], 12)
        result = self.check(sealed['manifest_sha256'])
        self.assertTrue(result['candidate_supported'])  # mock diagnostic only
        self.assertFalse(result['canonical_gate_pass'])
        self.assertFalse(result['step2_gate_promoted'])
        self.assertEqual(result['jepa_weight'], 0)
        self.assertEqual(result['evidence_kind'], 'LINUX_NATIVE')  # label, NOT native proof

    def test_resealed_summary_score_must_not_disagree_with_raw_tool_rows(self):
        sealed = self.collect()
        path = self.work / 'TP_s27.json'
        summary = json.loads(path.read_bytes())
        summary['episode_utility_tool'][IDS[0] + ':both_exact'] = 0.0
        new_pin = self.reseal(path.name, canonical(summary))
        with self.assertRaises(ValueError):
            self.check(new_pin)

    def test_resealed_malformed_raw_must_not_be_accepted_as_native(self):
        sealed = self.collect()
        new_pin = self.reseal('TP_s27.raw', b'not-length-prefixed-native-evidence')
        with self.assertRaises(ValueError):
            self.check(new_pin)


if __name__ == '__main__':
    unittest.main()

"""Tamper counterexamples for read-only original Run13R artifact review."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

import run13s_independent_raw_review as audit

ORIGINAL = Path(os.environ.get('RUN13R_ORIGINAL_ZIP', '/mnt/data/run13r-native-original.zip'))


class TestIndependentReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL.is_file():
            raise unittest.SkipTest('Original ZIP required for artifact-bound tests')
        with zipfile.ZipFile(ORIGINAL) as z:
            cls.original = {n: z.read(n) for n in z.namelist()}

    def altered(self, mutate, rehash=True):
        files = dict(self.original)
        mutate(files)
        if rehash:
            files['SHA256SUMS'] = ''.join(
                f'{hashlib.sha256(files[n]).hexdigest()}  ./{n}\n'
                for n in sorted(files) if n != 'SHA256SUMS').encode()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'artifact.zip'
            with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                for n, data in files.items():
                    z.writestr(n, data)
            yield path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_original_full_raw_replay(self):
        result = audit.inspect_zip(ORIGINAL)
        self.assertEqual(result['reported_status_replayed'], 'DIAGNOSTIC_HURT')
        self.assertEqual(result['row_nll_values_verified'], 256)
        self.assertEqual(result['cohort_arms_verified'], 8)

    def test_outer_zip_sha_guard(self):
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_ZIP_SHA256_MISMATCH'):
            audit.inspect_zip(ORIGINAL, '0'*64)

    def test_inner_sha_guard(self):
        def m(f): f['HEAD.txt'] = b'wrong\n'
        for path, sha in self.altered(m, rehash=False):
            with self.assertRaisesRegex(ValueError, 'INNER_SHA256_RED'):
                audit.inspect_zip(path, sha)

    def test_source_head_guard_even_with_rehashed_manifest(self):
        def m(f): f['HEAD.txt'] = b'wrong\n'
        for path, sha in self.altered(m):
            with self.assertRaisesRegex(ValueError, 'SOURCE_HEAD_RED'):
                audit.inspect_zip(path, sha)

    def test_nonzero_stage_guard(self):
        def m(f): f['NATIVE_EXIT.txt'] = b'1\n'
        for path, sha in self.altered(m):
            with self.assertRaisesRegex(ValueError, 'STAGE_RED:NATIVE'):
                audit.inspect_zip(path, sha)

    def test_forged_gate_guard(self):
        def m(f):
            r = json.loads(f['REPORT.json'])
            r['utility_gate_pass'] = True
            f['REPORT.json'] = json.dumps(r).encode()
        for path, sha in self.altered(m):
            with self.assertRaisesRegex(ValueError, 'NEGATIVE_GATE_RED'):
                audit.inspect_zip(path, sha)

    def test_forged_mean_guard(self):
        def m(f):
            r = json.loads(f['REPORT.json'])
            r['results']['271']['CE_0']['summary']['paraphrase'] = 0.01
            f['REPORT.json'] = json.dumps(r).encode()
        for path, sha in self.altered(m):
            with self.assertRaisesRegex(ValueError, 'MISMATCH:NLL_MEAN'):
                audit.inspect_zip(path, sha)

    def test_forged_hit_guard(self):
        def m(f):
            r = json.loads(f['REPORT.json'])
            r['results']['271']['CE_0']['paraphrase_generated'][0]['answer_hit'] = False
            f['REPORT.json'] = json.dumps(r).encode()
        for path, sha in self.altered(m):
            with self.assertRaisesRegex(ValueError, 'GREEDY_HIT_REPLAY_RED'):
                audit.inspect_zip(path, sha)

    def test_forged_baseline_guard(self):
        def m(f):
            r = json.loads(f['REPORT.json'])
            obj = r['results']['277']['SHUFFLED_12']
            obj['baseline_rows']['train'][0]['nll'] += 0.1
            obj['baseline']['train'] += 0.025
            f['REPORT.json'] = json.dumps(r).encode()
        for path, sha in self.altered(m):
            with self.assertRaisesRegex(ValueError, 'BASELINE_DRIFT_RED'):
                audit.inspect_zip(path, sha)

    def test_forged_verdict_guard(self):
        def m(f):
            r = json.loads(f['REPORT.json'])
            r['status'] = 'BOUNDED_SYNTHETIC_SCALE_SIGNAL_NOT_UTILITY_GATE'
            f['REPORT.json'] = json.dumps(r).encode()
        for path, sha in self.altered(m):
            with self.assertRaisesRegex(ValueError, 'VERDICT_REPLAY_RED'):
                audit.inspect_zip(path, sha)


if __name__ == '__main__':
    unittest.main()
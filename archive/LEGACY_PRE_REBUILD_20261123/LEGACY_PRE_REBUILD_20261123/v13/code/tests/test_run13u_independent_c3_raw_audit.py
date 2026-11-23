"""Synthetic tamper tests for read-only original Run13T artifact audit."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import run13u_independent_c3_raw_audit as a


class AuditSynthetic(unittest.TestCase):
    def make_files(self):
        files = {s + '_EXIT.txt': b'0\n' for s in a.STAGES}
        files['PRIVACY_RAW.log'] = b'privacy scan base..HEAD: CLEAN\n'
        files['TEST_RAW.log'] = b'Ran 18 tests in 0.222s\n\nOK\n'
        for i, case in enumerate(a.CASE_ROWS):
            answer = a.expected_answer(case)
            prompt = a.COPY_PREFIX + answer + a.COPY_SUFFIX
            for j, arm in enumerate(a.ARMS):
                system = a.SYSTEM_BASELINE if j == 0 else a.SYSTEM_STRICT
                row = {
                    'schema': a.SCHEMA, 'seed': a.SEED, 'index': i,
                    'project': case[0], 'arm': arm,
                    'source_event_id': f's{i}', 'query_event_id': f'q{i}',
                    'context_plan_packet_id': f'p{i}',
                    'source_sha256': a.sha(f'source{i}'.encode()),
                    'answer_sha256': a.sha(answer.encode()),
                    'prompt_sha256': a.sha(prompt.encode()),
                    'system_sha256': a.sha(system.encode()),
                    'model_sha256': a.MODEL_SHA,
                    'model_revision': a.MODEL_REVISION,
                    'learning_mode': 'RECORD_ONLY', 'jepa_weight': 0,
                    'step2_status': 'UTILITY_FAIL', 'b3_status': 'NO_PROMOTION',
                    'body_jepa_status': 'UNAVAILABLE', 'redmi_measured': False,
                    'whole_system_complete': False, 'native_calls': 1,
                    'native_status': 'FINAL', 'native_reaped': True,
                    'native_role': 'C3_LANGUAGE', 'native_pid': 10000 + 2*i + j,
                    'native_release': {'process_reaped': True},
                    'native_metrics': {'status': 'FINAL', 'role': 'C3_LANGUAGE',
                                       'actual_model': 'LFM2.5-350M-QAD-Q4_0.gguf'},
                    'final_output': answer, 'exact_copy': True,
                    'wrong_claims': 0, 'source_facts_verified': True,
                    'score': {'numeric': {'correct': 2}, 'faster_correct': True,
                              'strict_full': True},
                }
                files[f'pilot/raw/{i:02d}_{arm}.json'] = json.dumps(row).encode()
        totals = {arm: {'n': 8, 'native_final': 8, 'exact_copy': 8,
                        'source_facts_verified': 8, 'wrong_claims': 0,
                        'numeric_correct': 16, 'faster_correct': 8,
                        'strict_full': 8, 'literal_abstain_dot': 0} for arm in a.ARMS}
        report = {'schema': a.SCHEMA, 'seed': a.SEED,
                  'fixture_sha256': a.FIXTURE_SHA256, 'rows': 16,
                  'totals': totals, 'status': 'NO_ATTRIBUTABLE_FIDELITY_GAIN',
                  'learning_mode': 'RECORD_ONLY', 'step2_status': 'UTILITY_FAIL',
                  'b3_status': 'NO_PROMOTION', 'body_jepa_status': 'UNAVAILABLE',
                  'jepa_weight': 0, 'redmi_measured': False,
                  'utility_gate_promoted': False, 'whole_system_complete': False,
                  'production_activation': False, 'semantic_quality_proven': False,
                  'all_native_final': True, 'all_native_reaped': True}
        files['pilot/report.json'] = json.dumps(report).encode()
        return files

    def with_zip(self, files, *, rehash=True):
        if rehash:
            files['SHA256SUMS'] = ''.join(
                f'{hashlib.sha256(files[n]).hexdigest()}  ./{n}\n'
                for n in sorted(files) if n != 'SHA256SUMS').encode()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'original.zip'
            with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                for n, data in files.items():
                    z.writestr(n, data)
            yield path, a.sha(path.read_bytes())

    def test_synthetic_raw_replay(self):
        for path, sha in self.with_zip(self.make_files()):
            result = a.audit(path, sha)
            self.assertEqual(result['native_rows'], 16)
            self.assertEqual(result['replayed_status'], 'NO_ATTRIBUTABLE_FIDELITY_GAIN')

    def test_outer_hash_mismatch(self):
        for path, sha in self.with_zip(self.make_files()):
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_ZIP_SHA_RED'):
                a.audit(path, '0'*64)

    def test_inner_hash_mismatch(self):
        files = self.make_files()
        files['SHA256SUMS'] = ''.join(
            f'{hashlib.sha256(files[n]).hexdigest()}  ./{n}\n'
            for n in sorted(files)).encode()
        files['NATIVE_EXIT.txt'] = b'1\n'
        for path, sha in self.with_zip(files, rehash=False):
            with self.assertRaisesRegex(ValueError, 'MANIFEST_HASH_RED'):
                a.audit(path, sha)

    def test_forged_answer_hash_with_valid_inner_hashes(self):
        files = self.make_files()
        key = 'pilot/raw/00_COPY_BASELINE.json'
        row = json.loads(files[key]); row['answer_sha256'] = '0'*64
        files[key] = json.dumps(row).encode()
        for path, sha in self.with_zip(files):
            with self.assertRaisesRegex(ValueError, 'ROW_BINDING_RED'):
                a.audit(path, sha)

    def test_forged_wrong_claims_with_valid_inner_hashes(self):
        files = self.make_files()
        key = 'pilot/raw/01_COPY_STRICT.json'
        row = json.loads(files[key]); row['wrong_claims'] = 1
        files[key] = json.dumps(row).encode()
        for path, sha in self.with_zip(files):
            with self.assertRaisesRegex(ValueError, 'WRONG_CLAIMS_REPLAY_RED'):
                a.audit(path, sha)

    def test_forged_report_verdict_with_valid_inner_hashes(self):
        files = self.make_files()
        r = json.loads(files['pilot/report.json'])
        r['status'] = 'BOUNDED_SYNTHETIC_FIDELITY_SIGNAL_NOT_UTILITY_GATE'
        files['pilot/report.json'] = json.dumps(r).encode()
        for path, sha in self.with_zip(files):
            with self.assertRaisesRegex(ValueError, 'VERDICT_REPLAY_RED'):
                a.audit(path, sha)


if __name__ == '__main__':
    unittest.main()
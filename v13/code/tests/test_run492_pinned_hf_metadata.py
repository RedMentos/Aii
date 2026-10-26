"""Run492: no-network fail-closed Hugging Face pinned model metadata tests."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run492_pinned_hf_metadata as m


def payload(spec):
    return {'id': spec['repo'], 'sha': spec['revision'],
            'private': False, 'gated': False,
            'cardData': {'license': spec['license']},
            'tags': ['license:' + spec['license']],
            'siblings': [{'rfilename': spec['file'],
                          'size': spec['size'],
                          'lfs': {'sha256': spec['sha256'], 'size': spec['size']}}]}


class PinnedModelMetadata(unittest.TestCase):
    def test_three_registered_roles_have_exact_pins(self):
        self.assertEqual(set(m.SPECS), {'B1_DETAIL', 'B2_GIST', 'C3_LANGUAGE'})
        for role, spec in m.SPECS.items():
            with self.subTest(role=role):
                self.assertEqual(len(spec['revision']), 40)
                self.assertEqual(len(spec['sha256']), 64)
                self.assertIn('/revision/' + spec['revision'], m.api_url(spec))
                result = m.verify_model(role, payload(spec), 'a' * 64)
                self.assertEqual(result['sha256'], spec['sha256'])
                self.assertIsNone(result['license_accepted_by_user'])

    def test_changed_sha_size_and_revision_rejected(self):
        spec = m.SPECS['B1_DETAIL']
        for mutate, error in [
            (lambda d: d['siblings'][0]['lfs'].update(sha256='0' * 64), 'PINNED_MODEL_LFS_SHA256_CHANGED'),
            (lambda d: d['siblings'][0]['lfs'].update(size=1), 'PINNED_MODEL_SIZE_CHANGED'),
            (lambda d: d.update(sha='f' * 40), 'MODEL_REPO_OR_REVISION_CHANGED'),
        ]:
            d = payload(spec)
            mutate(d)
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                m.verify_model('B1_DETAIL', d, 'a' * 64)

    def test_private_gated_or_license_change_rejected(self):
        spec = m.SPECS['B2_GIST']
        for mutate, error in [
            (lambda d: d.update(private=True), 'MODEL_NOT_PUBLIC_UNGATED'),
            (lambda d: d.update(gated='auto'), 'MODEL_NOT_PUBLIC_UNGATED'),
            (lambda d: (d['cardData'].update(license='other'), d.update(tags=[])),
             'MODEL_LICENSE_METADATA_CHANGED'),
        ]:
            d = payload(spec)
            mutate(d)
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                m.verify_model('B2_GIST', d, 'a' * 64)

    def test_missing_lfs_or_duplicate_file_rejected(self):
        spec = m.SPECS['C3_LANGUAGE']
        d = payload(spec)
        d['siblings'][0].pop('lfs')
        with self.assertRaisesRegex(ValueError, 'MODEL_LFS_SHA256_UNAVAILABLE'):
            m.verify_model('C3_LANGUAGE', d, 'a' * 64)
        d = payload(spec)
        d['siblings'].append(copy.deepcopy(d['siblings'][0]))
        with self.assertRaisesRegex(ValueError, 'PINNED_MODEL_FILENAME_MISSING_OR_DUPLICATE'):
            m.verify_model('C3_LANGUAGE', d, 'a' * 64)

    def test_offline_mock_audit_no_model_download_and_negative_gates(self):
        def fake_fetch(spec):
            return payload(spec), hashlib.sha256(spec['repo'].encode()).hexdigest()
        result = m.audit(fake_fetch)
        self.assertEqual(result['status'], 'PINNED_PUBLIC_MODEL_METADATA_VERIFIED')
        self.assertEqual(result['model_bytes_downloaded'], 0)
        self.assertIs(result['native_executed'], False)
        self.assertIs(result['runner_verified'], False)
        self.assertIs(result['canonical_gate_pass'], False)
        self.assertEqual(result['step2_exit'], 'UTILITY_FAIL')
        self.assertIsNone(result['license_accepted_by_user'])

    def test_incomplete_metadata_fails_entire_audit(self):
        def fake_fetch(spec):
            d = payload(spec)
            if spec['repo'].startswith('ggml-org/'):
                d['siblings'] = []
            return d, 'a' * 64
        with self.assertRaisesRegex(ValueError, 'PINNED_MODEL_FILENAME_MISSING_OR_DUPLICATE'):
            m.audit(fake_fetch)


if __name__ == '__main__':
    unittest.main()

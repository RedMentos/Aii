"""No-model integrity and exact-pairing tests for the C2 audit."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import c2_pairwise_transfer_audit as A


class PairedAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.items = [{'id': f'{route}-{lang}-{i:02d}', 'label': route, 'lang': lang,
                       'text': f'Unique synthetic {route} {lang} {i}'}
                      for route in A.ROUTES for lang in ('en', 'de') for i in range(8)]
        self.needle = [{'id': it['id'], 'label': it['label'], 'pred': it['label'],
                        'validated': True, 'confidence': .5, 'latency_s': .2} for it in self.items]
        self.scaffold = [{'id': it['id'], 'label': it['label'], 'pred': it['label'], 'latency_s': .01} for it in self.items]

    def fixture(self):
        sha = A.sha256(json.dumps(self.items, ensure_ascii=False, sort_keys=True).encode())
        data = {'schema': 'v13.c2.bilingual_transfer64.v1', 'items_sha256': sha, 'items': self.items}
        raw = json.dumps(data, ensure_ascii=False).encode()
        path = self.root/'fixture.json'; path.write_bytes(raw)
        return path, A.git_blob(raw), sha

    def rows(self, name, rows):
        path = self.root/(name+'.json'); raw = json.dumps(rows).encode(); path.write_bytes(raw)
        return path, A.sha256(raw)

    def test_exact_paired_mcnemar_and_strata(self):
        for i in range(8):
            self.needle[i]['pred'] = 'detail'
        for i in range(8,39):
            self.scaffold[i]['pred'] = 'detail' if self.items[i]['label'] != 'detail' else 'simple'
        report = A.audit(self.items, self.needle, self.scaffold, 'a'*64, 'b'*64)
        self.assertEqual(report['overall']['needle_only'], 31)
        self.assertEqual(report['overall']['scaffold_only'], 8)
        self.assertAlmostEqual(report['overall']['mcnemar_exact_two_sided_p'], .0002940768754342571)
        self.assertEqual(sum(x['n'] for x in report['by_language'].values()),64)
        self.assertEqual(report['gate'],'NOT_PROMOTED')
        self.assertFalse(report['phone_measured'])

    def test_mcnemar_symmetric_and_no_discordance(self):
        self.assertEqual(A.mcnemar_exact(0,0),1.)
        self.assertEqual(A.mcnemar_exact(2,0),.5)
        self.assertEqual(A.mcnemar_exact(8,31),A.mcnemar_exact(31,8))
        with self.assertRaises(ValueError): A.mcnemar_exact(True,2)

    def test_fixture_frozen_pin_and_tamper(self):
        path, blob, sha = self.fixture()
        self.assertEqual(len(A.registered_fixture(path,expected_blob=blob,expected_items=sha)),64)
        with self.assertRaisesRegex(ValueError,'blob mismatch'):
            A.registered_fixture(path,expected_blob='0'*40,expected_items=sha)
        self.items[0]['text']='changed'
        with self.assertRaisesRegex(ValueError,'item digest mismatch'):
            with patch.object(A,'git_blob',return_value=blob):
                # Mutate payload without updating declared items hash.
                data=json.loads(path.read_text());data['items'][0]['text']='changed';path.write_text(json.dumps(data))
                A.registered_fixture(path,expected_blob=blob,expected_items=sha)

    def test_raw_hash_order_label_and_validation(self):
        path, digest = self.rows('needle',self.needle)
        self.assertEqual(len(A.read_pinned_rows(path,digest,self.items,'needle')),64)
        with self.assertRaisesRegex(ValueError,'SHA256 mismatch'):
            A.read_pinned_rows(path,'f'*64,self.items,'needle')
        bad=[dict(x) for x in self.needle];bad[0]['id']=bad[1]['id']
        p,h=self.rows('duplicate',bad)
        with self.assertRaisesRegex(ValueError,'IDs'):
            A.read_pinned_rows(p,h,self.items,'needle')
        bad=[dict(x) for x in self.needle];bad[0]['validated']=False
        p,h=self.rows('invalid',bad)
        with self.assertRaisesRegex(ValueError,'invalid native'):
            A.read_pinned_rows(p,h,self.items,'needle')

    def test_nonfinite_and_boolean_metrics_fail_closed(self):
        for field, value in [('latency_s',float('nan')),('latency_s',float('inf')),('latency_s',True),('confidence',float('nan')),('confidence',True)]:
            bad=[dict(x) for x in self.needle];bad[0][field]=value
            p,h=self.rows('bad',bad)
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                A.read_pinned_rows(p,h,self.items,'needle')

    def test_main_writes_exclusive_nonpromoting_report(self):
        from unittest.mock import patch
        needle_path, needle_sha = self.rows('needle', self.needle)
        scaffold_path, scaffold_sha = self.rows('scaffold', self.scaffold)
        fixture, _, _ = self.fixture()
        out = self.root / 'audit.json'
        args = ['--fixture', str(fixture), '--needle-rows', str(needle_path),
                '--needle-sha256', needle_sha, '--scaffold-rows', str(scaffold_path),
                '--scaffold-sha256', scaffold_sha, '--out', str(out)]
        with patch.object(A, 'registered_fixture', return_value=self.items):
            self.assertEqual(A.main(args), 0)
            report = json.loads(out.read_text())
            self.assertEqual(report['overall']['n'], 64)
            self.assertEqual(report['evidence_kind'], 'OFFLINE_PINNED_INPUT_NOT_NATIVE_ATTESTATION')
            self.assertEqual(report['step2'], 'UTILITY_FAIL')
            self.assertFalse(report['whole_system_complete'])
            with self.assertRaises(FileExistsError):
                A.main(args)
        self.assertEqual(json.loads(out.read_text()), report)

    def test_rejects_wrong_labels_even_if_predictions_match(self):
        bad=[dict(x) for x in self.scaffold];bad[0]['label']='detail'
        p,h=self.rows('scaffold',bad)
        with self.assertRaisesRegex(ValueError,'label'):
            A.read_pinned_rows(p,h,self.items,'scaffold')


if __name__=='__main__':
    unittest.main()

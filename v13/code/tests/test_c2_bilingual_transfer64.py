"""No-model tests for the separately registered bilingual C2 transfer64."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

try:
    from scripts import c2_bilingual_transfer64 as T
except ImportError:
    spec = importlib.util.spec_from_file_location('c2_bilingual_transfer64',
        '/mnt/data/v13_c2_transfer64/c2_bilingual_transfer64.py')
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)


class Transfer64Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.original = self.root / 'original.json'
        self.old_items = [{'id':'old','text':'Unrelated old prompt','label':'simple'}]
        self.old_hash = hashlib.sha256(json.dumps(self.old_items, ensure_ascii=False,
                                                 sort_keys=True).encode()).hexdigest()
        self.original.write_text(json.dumps({'items_sha256':self.old_hash,'items':self.old_items}))

    def load(self):
        with patch.object(T, 'ORIGINAL_SHA', self.old_hash):
            return T.fixture(original=self.original)

    def test_frozen_64_balanced_disjoint(self):
        items = self.load()
        self.assertEqual(len(items), 64)
        self.assertEqual(len({x['text'] for x in items}), 64)
        for route in T.ROUTES:
            for lang in ('en','de'):
                self.assertEqual(sum(x['label']==route and x['lang']==lang for x in items),8)

    def test_original_96_registration_drift_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Original 96 cohort pin'):
            T.fixture(original=self.original)

    def test_overlap_with_original_cohort_rejected(self):
        self.old_items[0]['text'] = self.load()[0]['text']
        self.old_hash = hashlib.sha256(json.dumps(self.old_items, ensure_ascii=False,
                                                 sort_keys=True).encode()).hexdigest()
        self.original.write_text(json.dumps({'items_sha256':self.old_hash,'items':self.old_items}))
        with self.assertRaisesRegex(ValueError, 'overlaps original'):
            self.load()

    def test_mutated_transfer_fixture_rejected_even_with_new_item_hash(self):
        data = json.loads(T.FIXTURE.read_text())
        data['items'][0]['text'] = 'Changed after freeze'
        data['items_sha256'] = hashlib.sha256(json.dumps(data['items'], ensure_ascii=False,
                                                          sort_keys=True).encode()).hexdigest()
        changed = self.root / 'changed.json'
        changed.write_text(json.dumps(data, ensure_ascii=False))
        with patch.object(T, 'ORIGINAL_SHA', self.old_hash):
            with self.assertRaisesRegex(ValueError, 'Git blob drift'):
                T.fixture(changed, self.original)

    def test_native_report_uses_existing_summary_and_preserves_gates(self):
        items = self.load()
        rows = [{'id':x['id'],'label':x['label'],'pred':x['label'],
                 'latency_s':.25} for x in items]
        fake = types.ModuleType('scripts.c2_benchmark')
        fake.summarize = lambda rr, extra=None: {'n':len(rr),'accuracy':sum(x['pred']==x['label'] for x in rr)/len(rr)} | (extra or {})
        with patch.dict(sys.modules, {'scripts.c2_benchmark':fake}):
            report = T.report_from_rows(items, 'needle', rows, {'peak_rss_bytes':123}, 'a'*40)
        self.assertEqual(report['overall']['accuracy'],1.)
        self.assertEqual(report['per_language']['en']['n'],32)
        self.assertEqual(report['per_language']['de']['n'],32)
        self.assertEqual(report['step2_utility'],'FAIL')
        self.assertEqual(report['b3_l1'],'FAIL')
        self.assertFalse(report['whole_system_complete'])
        self.assertFalse(report['phone_measured'])
        self.assertFalse(report['training_or_calibration_on_transfer_rows'])

    def test_missing_and_invalid_predictions_fail(self):
        items = self.load()
        rows = [{'id':x['id'],'label':x['label'],'pred':x['label'],
                 'latency_s':.25} for x in items]
        with self.assertRaisesRegex(ValueError,'Missing'):
            T.report_from_rows(items, 'needle', rows[:-1], {})
        rows[0]['pred']='unsupported_tool'
        with self.assertRaisesRegex(ValueError,'Invalid'):
            T.report_from_rows(items, 'needle', rows, {})

    def test_fsync_output_refuses_overwrite(self):
        out = self.root / 'report.json'
        T.save_new(out, {'phone_measured':False})
        with self.assertRaises(FileExistsError):
            T.save_new(out, {'phone_measured':True})
        self.assertFalse(json.loads(out.read_text())['phone_measured'])


if __name__ == '__main__':
    unittest.main()
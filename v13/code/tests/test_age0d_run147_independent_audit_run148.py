"""Run148 cross-host integrity adversarial regressions, stdlib only."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import unittest
import zipfile

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
if not SCRIPTS.exists(): SCRIPTS=Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPTS))
from age0d_run147_independent_audit_run148 import audit_zip,sha,independent_checker,independent_label

ARTIFACT=Path(os.environ.get('RUN147_ARTIFACT','/mnt/data/RUN147_native.zip'))


def repack(payload,alter=None):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        report=json.loads(z.read('RUN147_C3_VARIED_NATIVE_REPORT.json'))
        log=z.read('RUN147_VARIED_NATIVE_RAW.log')
    if alter:alter(report)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('RUN147_C3_VARIED_NATIVE_REPORT.json',json.dumps(report))
        z.writestr('RUN147_VARIED_NATIVE_RAW.log',log)
    return buf.getvalue()


class Run148Audit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload=ARTIFACT.read_bytes()

    def test_01_closed_real_artifact(self):
        result=audit_zip(self.payload)
        self.assertEqual(result['integrity'],'PASS')
        self.assertEqual((result['rows'],result['correct_format_label'],result['wrong_format_label'],result['unknown_format_label']),(96,79,4,13))
        self.assertEqual(result['overall_gate'],'UNVERIFIED')
        self.assertEqual(result['original_K2'],'INSUFFICIENT')

    def test_02_reject_modified_zip_even_if_content_plausible(self):
        tampered=repack(self.payload)
        with self.assertRaisesRegex(ValueError,'artifact_digest_mismatch'):audit_zip(tampered)

    def assertTamper(self,modify,code):
        altered=repack(self.payload,modify)
        with self.assertRaisesRegex(ValueError,code):audit_zip(altered,sha(altered))

    def test_03_source_truth_tamper(self):
        self.assertTamper(lambda r:r['rows'][0].__setitem__('truth','999'), 'registered_task_digest')

    def test_04_response_bytes_tamper(self):
        self.assertTamper(lambda r:r['rows'][0].__setitem__('response','999'), 'response_digest')

    def test_05_duplicate_question(self):
        self.assertTamper(lambda r:r['rows'][1].__setitem__('question',r['rows'][0]['question']), 'question_uniqueness')

    def test_06_gate_promotion(self):
        self.assertTamper(lambda r:r['gates'].__setitem__('STEP2','PASS'), 'negative_gates')

    def test_07_status_tamper(self):
        self.assertTamper(lambda r:r['rows'][0].__setitem__('new_check','MISMATCH'), 'independent_checker_disagreement')

    def test_08_summary_denominator_tamper(self):
        self.assertTamper(lambda r:r['summary'].__setitem__('label_wrong',10), 'summary_denominators')

    def test_09_model_provenance_tamper(self):
        self.assertTamper(lambda r:r['provenance'].__setitem__('model_sha256','0'*64), 'native_hashes')

    def test_10_label_and_echo(self):
        self.assertEqual(independent_label('42'),'42')
        self.assertEqual(independent_label('2 × 21 = 42'),'42')
        self.assertIsNone(independent_label('2 × 21 = 42\n\n'))
        self.assertEqual(independent_checker('Compute 2 times 21.','2 × 21 = 42'),'CORRECT')
        self.assertEqual(independent_checker('Compute 2 times 21.','2 × 21 = 43'),'MISMATCH')
        self.assertEqual(independent_checker('Compute 2 times 21.','3 × 21 = 42'),'ABSTAIN')

    def test_11_bad_row_id(self):
        self.assertTamper(lambda r:r['rows'][0].__setitem__('id',3), 'row_id_order')

    def test_12_missing_native_unload(self):
        self.assertTamper(lambda r:r['unload'].__setitem__('process_reaped',False),'native_unload')

if __name__=='__main__':unittest.main()

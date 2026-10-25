"""Run153 closed native artifact integrity and source-binding adversarial tests."""
import io
import json
import os
from pathlib import Path
import sys
import unittest
import zipfile

SCRIPT=Path(__file__).resolve().parents[1]/'scripts'
if not SCRIPT.exists():SCRIPT=Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPT))
from age0d_run151_independent_audit_run153 import audit,digest,parse

ARTIFACT=Path(os.environ.get('RUN151_ARTIFACT','/mnt/data/RUN151_native_first.zip'))


def rewrite(original,mutate):
    with zipfile.ZipFile(io.BytesIO(original)) as z:
        j=json.loads(z.read('RUN151_C3_VARIED_NATIVE_REPORT.json'));log=z.read('RUN151_VARIED_NATIVE_RAW.log')
    mutate(j)
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('RUN151_C3_VARIED_NATIVE_REPORT.json',json.dumps(j))
        z.writestr('RUN151_VARIED_NATIVE_RAW.log',log)
    return out.getvalue()


class Run153Audit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=ARTIFACT.read_bytes()

    def test_01_exact_closed_native_artifact(self):
        r=audit(self.data)
        self.assertEqual((r['integrity'],r['rows'],r['overall_gate']),('PASS',288,'UNVERIFIED'))
        self.assertEqual((r['v2_supported'],r['v3_supported']),(244,276))
        self.assertEqual(r['source_mismatched_strict_label_ids'],[243])
        self.assertEqual((r['source_bound_strict_correct'],r['source_bound_strict_wrong']),(217,27))

    def test_02_zip_tamper_rejected(self):
        bad=rewrite(self.data,lambda r:None)
        with self.assertRaisesRegex(ValueError,'artifact_digest'):audit(bad)

    def assertTamper(self,mutate,code):
        bad=rewrite(self.data,mutate)
        with self.assertRaisesRegex(ValueError,code):audit(bad,digest(bad))

    def test_03_source_truth_tamper(self):
        self.assertTamper(lambda r:r['rows'][0].__setitem__('truth','999'),'task_digest')

    def test_04_response_tamper(self):
        self.assertTamper(lambda r:r['rows'][0].__setitem__('response','999'),'response_hash')

    def test_05_negative_gate_tamper(self):
        self.assertTamper(lambda r:r['gates'].__setitem__('STEP2','PASS'),'negative_gates')

    def test_06_checker_status_tamper(self):
        self.assertTamper(lambda r:r['rows'][0].__setitem__('v3_check','ABSTAIN'),'independent_checker')

    def test_07_model_hash_tamper(self):
        self.assertTamper(lambda r:r['provenance'].__setitem__('model_sha256','0'*64),'native_provenance')

    def test_08_source_mismatch_is_abstain(self):
        q='Calculate 550 divided by 22.';answer='55 ÷ 22 = 2'
        self.assertEqual(parse(q,answer,2,False),2)
        self.assertIsNone(parse(q,answer,2,True))
        self.assertIsNone(parse(q,answer,3,True))

    def test_09_v3_new_formats_and_conflicts(self):
        q='Compute 2 plus 2.'
        self.assertIsNone(parse(q,'2 + 2 = **4**',2,True))
        self.assertEqual(parse(q,'2 + 2 = **4**',3,True),4)
        self.assertEqual(parse(q,'2 + 2 = 4\n\n',3,True),4)
        self.assertIsNone(parse(q,'2 + 2 = 4\nwrong',3,True))
        self.assertIsNone(parse(q,'3 + 2 = 5\n\n',3,True))

if __name__=='__main__':unittest.main()

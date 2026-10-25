"""Run154 two-artifact native replication integrity and non-determinism tests."""
import io
import json
import os
from pathlib import Path
import sys
import unittest
import zipfile

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
if not SCRIPTS.exists():SCRIPTS=Path(__file__).resolve().parent
sys.path.insert(0,str(SCRIPTS))
from age0d_run151_replication_compare_run154 import compare,digest,FIRST,SECOND

FIRST_PATH=Path(os.environ.get('RUN151_FIRST','/mnt/data/RUN151_native_first.zip'))
SECOND_PATH=Path(os.environ.get('RUN151_SECOND','/mnt/data/RUN151_native_second.zip'))


def tamper(payload,modify):
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        report=json.loads(z.read('RUN151_C3_VARIED_NATIVE_REPORT.json'));log=z.read('RUN151_VARIED_NATIVE_RAW.log')
    modify(report);buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('RUN151_C3_VARIED_NATIVE_REPORT.json',json.dumps(report))
        z.writestr('RUN151_VARIED_NATIVE_RAW.log',log)
    return buf.getvalue()


class Run154Replication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.a=FIRST_PATH.read_bytes();cls.b=SECOND_PATH.read_bytes()

    def test_01_exact_native_replication(self):
        r=compare(self.a,self.b)
        self.assertEqual((r['response_identical'],r['response_different'],r['v3_status_changed']),(267,21,7))
        self.assertEqual(r['different_by_operation'],{'divided by':4,'times':17})
        self.assertEqual((r['first_v3_supported'],r['second_v3_supported']),(276,274))
        self.assertFalse(r['deterministic_repeat']);self.assertEqual(r['overall_gate'],'UNVERIFIED')

    def test_02_digest_tamper_rejected(self):
        with self.assertRaisesRegex(ValueError,'artifact_hash'):compare(self.a,self.b+b'garbage')

    def assertTamper(self,modify,reason):
        bad=tamper(self.b,modify)
        with self.assertRaisesRegex(ValueError,reason):compare(self.a,bad,FIRST,digest(bad))

    def test_03_task_truth_tamper(self):
        self.assertTamper(lambda r:r['rows'][0].__setitem__('truth','999'),'task_digest')

    def test_04_response_hash_tamper(self):
        self.assertTamper(lambda r:r['rows'][0].__setitem__('response','wrong'),'response_hash')

    def test_05_gate_tamper(self):
        self.assertTamper(lambda r:r['gates'].__setitem__('STEP2','PASS'),'gates')

    def test_06_model_hash_tamper(self):
        self.assertTamper(lambda r:r['provenance'].__setitem__('model_sha256','0'*64),'provenance')

    def test_07_same_artifact_not_a_replication(self):
        with self.assertRaisesRegex(ValueError,'not_independent_artifacts'):compare(self.a,self.a,FIRST,FIRST)

if __name__=='__main__':unittest.main()

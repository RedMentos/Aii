"""Run155 independent adversarial raw-log integrity tests (software only)."""
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile
import hashlib
import types
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from age0d_run151_log_binding_review_run155 import bind_rows,audit,GATES


def fixtures():
    rows=[{'id':i,'new_check':'CORRECT','v3_check':'CORRECT',
           'old_check':'ABSTAIN','label':str(i)} for i in range(288)]
    log='PREAMBLE\n'+''.join(f'RUN151_ROW {i} CORRECT CORRECT ABSTAIN {i}\n' for i in range(288))+'DONE\n'
    return rows,log


def pack(rows,log):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('RUN151_C3_VARIED_NATIVE_REPORT.json',json.dumps({'rows':rows,'gates':GATES,'age0d_delivery':'OFF'}))
        z.writestr('RUN151_VARIED_NATIVE_RAW.log',log)
    return buf.getvalue()


class RawLogBinding(unittest.TestCase):
    def test_exact_288_lines(self):
        rows,log=fixtures()
        self.assertEqual(bind_rows(rows,log)['rows_bound'],288)
        data=pack(rows,log)
        stub=types.ModuleType('scripts.age0d_run151_replication_compare_run154')
        stub.load=lambda b,sha:{'rows':rows}
        with patch.dict(sys.modules,{'scripts':types.ModuleType('scripts'),
                                     'scripts.age0d_run151_replication_compare_run154':stub}):
            self.assertEqual(audit(data,hashlib.sha256(data).hexdigest())['overall_gate'],'UNVERIFIED')

    def test_swapped_lines_rejected(self):
        rows,log=fixtures();lines=log.splitlines();lines[1],lines[2]=lines[2],lines[1]
        with self.assertRaisesRegex(ValueError,'raw_log_mismatch'):bind_rows(rows,'\n'.join(lines))

    def test_repeated_rows_rejected(self):
        rows,log=fixtures();lines=log.splitlines();lines[2]=lines[1]
        with self.assertRaisesRegex(ValueError,'raw_log_mismatch'):bind_rows(rows,'\n'.join(lines))

    def test_forged_status_rejected(self):
        rows,log=fixtures();log=log.replace('RUN151_ROW 23 CORRECT','RUN151_ROW 23 MISMATCH')
        with self.assertRaisesRegex(ValueError,'raw_log_mismatch'):bind_rows(rows,log)

    def test_malformed_status_rejected(self):
        rows,log=fixtures();log=log.replace('RUN151_ROW 23 CORRECT','RUN151_ROW 23 SUCCESS')
        with self.assertRaisesRegex(ValueError,'raw_log_format'):bind_rows(rows,log)

    def test_missing_line_rejected(self):
        rows,log=fixtures();log=log.replace('RUN151_ROW 23 CORRECT CORRECT ABSTAIN 23\n','')
        with self.assertRaisesRegex(ValueError,'raw_log_count'):bind_rows(rows,log)

    def test_report_order_rejected(self):
        rows,log=fixtures();rows[0]['id']=2
        with self.assertRaisesRegex(ValueError,'report_row_order'):bind_rows(rows,log)

    def test_artifact_digest_rejected(self):
        rows,log=fixtures();data=pack(rows,log)
        with self.assertRaisesRegex(ValueError,'artifact_sha256'):audit(data,'0'*64)

    def test_fake_native_artifact_fails_closed(self):
        rows,log=fixtures();data=pack(rows,log)
        with self.assertRaises((ImportError,ModuleNotFoundError,ValueError,KeyError)):
            audit(data,hashlib.sha256(data).hexdigest())

    def test_gate_promotion_rejected(self):
        rows,log=fixtures();data=pack(rows,log)
        with zipfile.ZipFile(io.BytesIO(data)) as z:report=json.loads(z.read('RUN151_C3_VARIED_NATIVE_REPORT.json'))
        report['gates']['STEP2']='PASS'
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('RUN151_C3_VARIED_NATIVE_REPORT.json',json.dumps(report))
            z.writestr('RUN151_VARIED_NATIVE_RAW.log',log)
        with self.assertRaisesRegex(ValueError,'negative_gates'):audit(b.getvalue(),hashlib.sha256(b.getvalue()).hexdigest())

if __name__=='__main__':unittest.main()

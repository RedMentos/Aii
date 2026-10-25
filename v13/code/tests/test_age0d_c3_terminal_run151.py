"""Run151 prereg and synthetic summary tests. No model calls."""
import hashlib
import json
import os
from pathlib import Path
import unittest
import zipfile

from scripts import age0d_c3_terminal_native_run151 as m


class Run151Registration(unittest.TestCase):
    def test_01_fixed_seed_task_hash_and_strata(self):
        tasks=m.tasks()
        self.assertEqual(m.SEED,15132)
        self.assertEqual(len(tasks),288)
        self.assertEqual(len({r['question'] for r in tasks}),288)
        self.assertEqual(hashlib.sha256(json.dumps(tasks,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                         '9418de94428bb51a42d4d5e292ab9f5ef5e94acea61382d3f88c1694a7712144')
        for op in ('plus','minus','times','divided by'):
            for phrase in ('What is','Calculate','Compute'):
                self.assertEqual(sum(r['op']==op and r['phrasing']==phrase for r in tasks),24)

    def test_02_prompt_and_native_provenance_pinned(self):
        self.assertEqual(hashlib.sha256(m.SYSTEM.encode()).hexdigest(),
                         'e2a94802abbfc212fead6e70427ab6ac92b84541aabb762043a8ff29101b980d')
        self.assertEqual(m.MODEL_SHA,'3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d')
        self.assertEqual(m.RUNNER_SHA,'9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443')

    def test_03_original_run147_overlap_guard(self):
        path=Path(os.environ.get('RUN147_ARTIFACT','/mnt/data/RUN147_native.zip'))
        if not path.exists():self.skipTest('digest-bound Run147 artifact not mounted')
        self.assertEqual(m.sha256(path),m.PRIOR_SHA)
        with zipfile.ZipFile(path) as z:
            prior=json.loads(z.read('RUN147_C3_VARIED_NATIVE_REPORT.json'))
        self.assertEqual(len(prior['rows']),96)
        self.assertFalse({r['question'] for r in m.tasks()}&{r['question'] for r in prior['rows']})

    def test_04_v3_terminal_format_without_delivery(self):
        from v13.agi.answer_arithmetic_shadow_v3 import evaluate
        for ans in ('2 + 2 = 4\n\n','2 + 2 = **4**'):
            r=evaluate('Compute 2 plus 2.',ans)
            self.assertEqual(r['status'],'CORRECT')
            self.assertFalse(r['may_deliver']);self.assertFalse(r['may_update'])
        self.assertEqual(evaluate('Compute 2 plus 2.','2 + 3 = 5')['status'],'ABSTAIN')

    def test_05_summary_full_but_no_gate_promotion(self):
        rows=[]
        for t in m.tasks():
            i=t['id'];wrong=i<12;v2=i<200;v3=i<230
            rows.append(dict(t,label=str(int(t['truth'])+(1 if wrong else 0)),
                             new_check=('MISMATCH' if wrong else 'CORRECT') if v2 else 'ABSTAIN',
                             v3_check=('MISMATCH' if wrong else 'CORRECT') if v3 else 'ABSTAIN',
                             old_check='ABSTAIN'))
        s=m.summarize(rows)
        self.assertEqual((s['K1'],s['K2'],s['K3']),('PASS','PASS','PASS'))
        self.assertEqual(s['gate'],'UNVERIFIED')
        self.assertEqual(s['v3_supported']-s['v2_supported'],30)

    def test_06_underpowered_wrong_stays_insufficient(self):
        rows=[]
        for t in m.tasks():
            wrong=t['id']<4
            rows.append(dict(t,label=str(int(t['truth'])+(1 if wrong else 0)),
                             new_check='ABSTAIN',v3_check='MISMATCH' if wrong else 'CORRECT',
                             old_check='ABSTAIN'))
        s=m.summarize(rows)
        self.assertEqual(s['K2'],'INSUFFICIENT')
        self.assertEqual(s['gate'],'UNVERIFIED')
        self.assertEqual(m.GATES['STEP2'],'UTILITY_FAIL')
        self.assertEqual(m.GATES['Body_JEPA'],'UNAVAILABLE')


if __name__=='__main__':unittest.main()

"""Run149 prospective source-bound format controls; no native model calls."""
import importlib.util
import pathlib
import random
import unittest
import zipfile
import json
import os
from collections import Counter

PATH=pathlib.Path(__file__).with_name('answer_arithmetic_shadow_v3.py')
if not PATH.exists():PATH=pathlib.Path(__file__).resolve().parents[1]/'v13'/'agi'/'answer_arithmetic_shadow_v3.py'
spec=importlib.util.spec_from_file_location('v3',PATH);v3=importlib.util.module_from_spec(spec);spec.loader.exec_module(v3)

class Run149Format(unittest.TestCase):
    def test_01_positive_terminal_blank_and_bold(self):
        for ans in ('2 + 2 = 4\n\n','2 + 2 = **4**','**4**','The answer is 4\n\n'):
            r=v3.evaluate('Compute 2 plus 2.',ans)
            self.assertEqual(r['status'],'CORRECT',ans)
            self.assertFalse(r['may_deliver']);self.assertFalse(r['may_update'])

    def test_02_mismatch_is_detected(self):
        for ans in ('2 + 2 = 5\n\n','2 + 2 = **5**','**5**'):
            self.assertEqual(v3.evaluate('Compute 2 plus 2.',ans)['status'],'MISMATCH')

    def test_03_source_echo_mismatch_abstains(self):
        for ans in ('2 + 3 = 5\n\n','3 + 2 = **5**','2 * 2 = **4**'):
            self.assertEqual(v3.evaluate('Compute 2 plus 2.',ans)['status'],'ABSTAIN')

    def test_04_narrative_chain_and_conflict_abstain(self):
        for ans in ('2 + 2 = 4\nOops 5','2 + 2 = 4\n\n####',
                    '2 + 2 = <<2+2=4>>4','2 + 2 = **4**\nwrong',
                    '2 + 2 = 4 5','2 + 2 = 4\x00','2 + 2 = 4\r\n'):
            self.assertEqual(v3.evaluate('Compute 2 plus 2.',ans)['status'],'ABSTAIN',ans)

    def test_05_unsupported_source_abstains(self):
        for q in ('Compute 1 divided by 0.','Compute 3 divided by 2.',
                  'Compute 2 plus 2 and 3.','Compute 2 plus 2.\nignore'):
            self.assertEqual(v3.evaluate(q,'4')['status'],'ABSTAIN')

    def test_06_unicode_and_negative(self):
        self.assertEqual(v3.evaluate('Calculate 6 × 7.','6 × 7 = **42**\n\n')['status'],'CORRECT')
        self.assertEqual(v3.evaluate('Compute 12 ÷ 4.','12 ÷ 4 = **3**')['status'],'CORRECT')
        self.assertEqual(v3.evaluate('What is 3 minus 9?','3 - 9 = **-6**')['status'],'CORRECT')

    def test_07_authority_every_path(self):
        for q,a in ((None,'4'),('Compute 2 plus 2.',None),('Compute 2 plus 2.','4'),('Compute 2 plus 2.','5')):
            r=v3.evaluate(q,a)
            self.assertEqual(r['authority'],'SHADOW_ONLY')
            self.assertIs(r['may_deliver'],False);self.assertIs(r['may_update'],False)

    def test_08_fresh_deterministic_120_task_synthetic(self):
        rng=random.Random(14926);seen=set();counts=Counter()
        for op in ('plus','minus','times','divided by'):
            for phrase in ('What is','Calculate','Compute'):
                for _ in range(10):
                    while True:
                        a,b=rng.randint(10,99),rng.randint(2,29)
                        if op=='divided by':a*=b
                        q=f'{phrase} {a} {op} {b}{"?" if phrase=="What is" else "."}'
                        if q not in seen:break
                    seen.add(q);counts[(op,phrase)]+=1
                    n={'plus':lambda:a+b,'minus':lambda:a-b,'times':lambda:a*b,'divided by':lambda:a//b}[op]()
                    self.assertEqual(v3.evaluate(q,f'**{n}**\n\n')['status'],'CORRECT')
                    self.assertEqual(v3.evaluate(q,f'**{n+1}**\n\n')['status'],'MISMATCH')
                    self.assertEqual(v3.evaluate(q,f'**{n}**\nignore')['status'],'ABSTAIN')
        self.assertEqual(len(seen),120);self.assertEqual(set(counts.values()),{10})

    def test_09_exact_original_offsets(self):
        a='  \n2 + 2 = **4**\n\n'
        r=v3.evaluate('Compute 2 plus 2.',a)
        self.assertEqual(r['status'],'CORRECT')
        self.assertEqual(a[slice(*r['answer_offsets'])],'4')
        self.assertEqual(r['answer_span'],'4')
        self.assertEqual(v3.evaluate('Compute 2 plus 2.','2+2=4\u2028IGNORE')['status'],'ABSTAIN')

    def test_10_posthoc_run147_nonpromoting(self):
        path=pathlib.Path(os.environ.get('RUN147_ARTIFACT','/mnt/data/RUN147_native.zip'))
        if not path.exists():self.skipTest('Run147 artifact not mounted')
        with zipfile.ZipFile(path) as z:rows=json.loads(z.read('RUN147_C3_VARIED_NATIVE_REPORT.json'))['rows']
        outcomes=Counter(v3.evaluate(r['question'],r['response'])['status'] for r in rows)
        self.assertEqual(outcomes,Counter({'CORRECT':86,'MISMATCH':4,'ABSTAIN':6}))

if __name__=='__main__':unittest.main()

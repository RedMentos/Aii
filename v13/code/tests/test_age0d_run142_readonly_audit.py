"""Adversarial independent software tests for Run143 post-hoc Run142 audit."""
import copy
import hashlib
import unittest
from scripts.age0d_run142_readonly_audit import audit, parse_strict_answer, EXPECTED_GATES, MODEL_SHA, RUNNER_SHA


def fixture():
    rows=[]
    for i in range(80):
        if i<10: op,a,b='plus',20+i,12
        elif i<30: op,a,b='minus',20+i,12
        elif i<70: op,a,b='times',20+i,12
        else: op,a,b='divided by',24+(i-70)*12,12
        truth={'plus':a+b,'minus':a-b,'times':a*b,'divided by':a//b}[op]
        q=f'What is {a} {op} {b}?'
        sym={'plus':'+','minus':'-','times':'×','divided by':'÷'}[op]
        answer=f'{a} {sym} {b} = {truth}'
        rows.append({'id':i,'op':op,'question':q,'truth':str(truth),'response':answer,
                     'response_sha256':hashlib.sha256(answer.encode()).hexdigest(),'check':'ABSTAIN'})
    return {'schema':'V13_RUN142_C3_AGE0D_NATIVE_V1','evidence_class':'LINUX_X86_64_NATIVE_SINGLE_C3',
            'status':'LINUX_NATIVE_C3_COHORT_EXECUTED','seed':14225,'gates':dict(EXPECTED_GATES),
            'provenance':{'model_sha256':MODEL_SHA,'runner_archive_sha256':RUNNER_SHA},'rows':rows}


class Run143Audit(unittest.TestCase):
    def test_echo_unicode_and_bare(self):
        self.assertEqual(parse_strict_answer('What is 23 times 12?','23 × 12 = 276'),'276')
        self.assertEqual(parse_strict_answer('What is 24 divided by 12?','24 ÷ 12 = 2'),'2')
        self.assertEqual(parse_strict_answer('What is 20 minus 30?','20 - 30 = -10'),'-10')
        self.assertEqual(parse_strict_answer('What is 23 plus 12?','The answer is 35.'),'35')
    def test_no_ambiguous_or_changed_echo(self):
        q='What is 23 times 12?'
        for s in ['23 × 12 = 276\nFinal answer: 276','23 × 12 = **276**','23 × 12 = 276 extra',
                  '12 × 23 = 276','23 ÷ 12 = 276','23 × 12 = 27,6','23 × 12 = <<276>>',
                  '23 × 12 = 276\r', '23 × 12 = 276\n']:
            self.assertIsNone(parse_strict_answer(q,s),s)
    def test_full_recovery_is_diagnostic_not_gate(self):
        a=audit(fixture(),'a'*64)
        self.assertEqual(a['diagnostic_statuses'],{'CORRECT':80})
        self.assertEqual(a['original_abstains_with_strict_diagnostic'],80)
        self.assertEqual(a['gate'],'UNVERIFIED')
        self.assertEqual(a['age0d_delivery'],'OFF')
    def test_reject_tampered_source_and_provenance(self):
        for change in ('truth','hash','id','model','gate','status'):
            d=fixture()
            if change=='truth':d['rows'][0]['truth']='123'
            if change=='hash':d['rows'][0]['response_sha256']='bad'
            if change=='id':d['rows'][1]['id']=0
            if change=='model':d['provenance']['model_sha256']='bad'
            if change=='gate':d['gates']['STEP2']='PASS'
            if change=='status':d['status']='PARTIAL_OR_FAILED'
            with self.subTest(change=change),self.assertRaises(ValueError):audit(d,'a'*64)
    def test_checker_disagreement_recorded_not_overwritten(self):
        d=fixture();d['rows'][0]['check']='CORRECT';d['rows'][0]['response']='20 + 12 = 33'
        d['rows'][0]['response_sha256']=hashlib.sha256(d['rows'][0]['response'].encode()).hexdigest()
        a=audit(d,'b'*64)
        self.assertEqual(a['original_supported_disagreement'],1)
        self.assertEqual(a['conflict_ids'],[0])

if __name__=='__main__':unittest.main()

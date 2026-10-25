"""Run181 synthetic paired-report audit tests; no native model."""
import importlib.util
import json
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/run181_gist_offer_audit.py'
spec=importlib.util.spec_from_file_location('run181_audit',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class AuditTests(unittest.TestCase):
    def fixture(self):
        expected=[{'kind':'owner','text':'The owner is A.','key':'A','stale':None} for _ in range(36)]
        content=json.dumps({'summary':'A','quotes':['The owner is A.']})
        arm=[{'index':i,'kind':'owner','content':content,'prompt_tokens':100,'seconds':1,
              'parsed':True,'hit':True,'stale':False,'quotes_valid':True,'quote_has_key':True}
             for i in range(36)]
        rep={'kind':'V13_G1B_GIST_UTILITY','binding':{'model_sha256':m.MODEL_SHA},
             'claim_limit':'Linux CPU, not Redmi',
             'fixed960':[dict(x) for x in arm],'event960':[dict(x) for x in arm],'gist':[dict(x) for x in arm],
             'summary':{a:{'hit':1.0,'quotes_valid':1.0,'prompt_tokens_mean':100.0} for a in m.ARMS},
             'paired':{a:{'wins':0,'losses':0} for a in
                 ('gist_vs_fixed960','gist_vs_event960','event960_vs_fixed960')},
             'decision':{'criteria':{'hit_wins_gt_losses':False,'quote_validity_not_lower':True,
                                     'prompt_tokens_within_10pct':True},'verdict':'GIST_NO_GAIN'}}
        return rep,expected

    def test_valid_no_gain_does_not_promote(self):
        rep,rows=self.fixture();out=m.audit(rep,rows)
        self.assertEqual(out['verdict'],'GIST_NO_GAIN')
        self.assertFalse(out['activation_authorized'])

    def test_duplicate_or_missing_row_refused(self):
        rep,rows=self.fixture();rep['gist'][0]['index']=1
        with self.assertRaisesRegex(ValueError,'incomplete/duplicate'):
            m.audit(rep,rows)

    def test_score_tamper_refused(self):
        rep,rows=self.fixture();rep['gist'][0]['hit']=False
        with self.assertRaisesRegex(ValueError,'scored evidence mismatch'):
            m.audit(rep,rows)

    def test_false_paired_promotion_refused(self):
        rep,rows=self.fixture();rep['decision']['verdict']='GIST_HELPS_CANDIDATE'
        with self.assertRaisesRegex(ValueError,'decision criteria/verdict mismatch'):
            m.audit(rep,rows)


if __name__=='__main__':unittest.main()

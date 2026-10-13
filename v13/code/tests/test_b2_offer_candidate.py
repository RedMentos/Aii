"""Isolated B2-offer candidate (scripts/b2_offer_candidate.py): patch applies, off = live, on = no B2 body_state + longer quotes."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
PROBE=r'''
import json,sys,tempfile,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path[:0]=[sys.argv[1],sys.argv[1]+'/scripts']
import b2_offer_candidate as c
binding=c.install()
from v13.runtime import Runtime
from v13 import cognition as live_view
out={'binding':binding,'module_is_candidate':'quote_min_chars' in live_view.offer_schema.__code__.co_varnames}
with tempfile.TemporaryDirectory() as d:
    r=Runtime(Path(d))
    try:
        for label,cfg in (('off',{}),('on',c.ENABLE)):
            r.cfg.update({'b2_offer_body_state':True,'offer_quote_min_chars':0}|cfg);seen={}
            def generate(messages,*a,**k):
                seen['q']=json.loads(messages[1]['content']);seen['schema']=a[3] if len(a)>3 else k.get('schema')
                return iter([json.dumps({'summary':'Budget 100','quotes':['Budget 100 euros'],'uncertainty':'low','needs_reentry':False})])
            r.pool.get=Mock(return_value=SimpleNamespace(role='B2_GIST',last_metrics={},generate=generate))
            row={}
            for role in ('B2_GIST','B1_DETAIL'):
                e=r.store.event(r.session,'Project Aurora. Budget 100 euros. Deadline 5 days.')
                p=r.cognition.offer(role,e,0,time.monotonic()+30)
                row[role]={'body_state':'body_state' in seen['q'],'quote_cap':seen['schema']['properties']['quotes']['items']['maxLength'],'evidence':len(p['evidence_refs'])}
            out[label]=row
    finally:r.close()
print(json.dumps(out))
'''

def probe():
    r=subprocess.run([sys.executable,'-c',PROBE,str(ROOT)],capture_output=True,text=True,cwd=str(ROOT),timeout=120)
    if r.returncode:raise AssertionError(r.stderr[-2000:])
    return json.loads(r.stdout.strip().splitlines()[-1])

class B2OfferCandidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.out=probe()
    def test_patch_applies_and_is_loaded_without_touching_live(self):
        b=self.out['binding'];self.assertTrue(self.out['module_is_candidate'])
        import hashlib
        self.assertEqual(b['live_cognition_sha256'],hashlib.sha256((ROOT/'v13/cognition.py').read_bytes()).hexdigest())
        self.assertNotEqual(b['candidate_cognition_sha256'],b['live_cognition_sha256'])
    def test_switches_off_behave_like_live(self):
        from v13.cognition import offer_schema
        live=offer_schema(160)['properties']['quotes']['items']['maxLength']
        for role in ('B2_GIST','B1_DETAIL'):
            self.assertTrue(self.out['off'][role]['body_state']);self.assertEqual(self.out['off'][role]['quote_cap'],live)
    def test_switches_on_drop_body_state_for_b2_only_and_lengthen_quotes(self):
        on=self.out['on']
        self.assertFalse(on['B2_GIST']['body_state']);self.assertTrue(on['B1_DETAIL']['body_state'])
        self.assertEqual(on['B2_GIST']['quote_cap'],90);self.assertEqual(on['B2_GIST']['evidence'],1)
    def test_longer_quotes_keep_the_worst_case_within_the_same_budget(self):
        sys.path.insert(0,str(ROOT/'scripts'))
        import b2_offer_candidate as c
        _,text=c.candidate_source()
        ns={'__name__':'v13._cand','__package__':'v13'};exec(compile(text,'cognition_candidate','exec'),ns)
        for tokens in (96,160,256):
            pr=ns['offer_schema'](tokens,90)['properties'];chars=max(110,int((tokens-30)*2.2))
            worst=pr['summary']['maxLength']+pr['uncertainty']['maxLength']+pr['quotes']['maxItems']*pr['quotes']['items']['maxLength']
            self.assertLessEqual(worst,chars);self.assertGreaterEqual(pr['summary']['maxLength'],48)
            live=ns['offer_schema'](tokens)['properties']['quotes']['items']['maxLength']
            self.assertEqual(pr['quotes']['items']['maxLength'],max(live,min(90,(chars-48-pr['uncertainty']['maxLength'])//2)))
        self.assertEqual(ns['offer_schema'](160,90)['properties']['quotes']['items']['maxLength'],90)

if __name__=='__main__':unittest.main()

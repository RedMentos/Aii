"""WP-U7 §3.2A: gist slots point back to fine spans with coverage/compression/boundary/fallback; A bundles fine context."""
import unittest
from v13 import gist as G

TEXT=('Das Projekt Aurora startet im Mai. Das Budget beträgt 120 Euro für Material. '
      'Danach folgt eine längere Planungsphase mit vielen Abstimmungen zwischen den Teams. ')*6
REF={'source_id':'s','sha256':'0'*64,'char_start':10,'char_end':10+len(TEXT),'modality':'text'}

class GistCoupling(unittest.TestCase):
    def test_slots_carry_spans_coverage_compression_boundary_and_fallback(self):
        p=G.plan(TEXT,REF,{'tokens_per_group':8,'slots':4})
        self.assertTrue(p['coarsened'])
        for x in p['slots']:
            self.assertEqual((x['covered']['char_start'],x['covered']['char_end']),(x['source_ref']['char_start'],x['source_ref']['char_end']))
            spans=x['source_span_refs'];self.assertEqual(spans[0]['char_start'],x['covered']['char_start']);self.assertEqual(spans[-1]['char_end'],x['covered']['char_end'])
            self.assertEqual(x['compression_ratio'],float(x['units']));self.assertIn(x['fallback'],('EXACT_STORE','B1_DETAIL'))
            self.assertTrue(0<=x['boundary_confidence']<=1)
        self.assertTrue(any(len(x['source_span_refs'])>1 for x in p['slots']))  # coarse older slots cover several fine groups
        self.assertEqual(p['slots'][0]['fallback'],'EXACT_STORE')  # contains 120 / Mai numbers
        # every covered span reads back exactly from the source text
        for x in p['slots']:self.assertEqual(TEXT[x['covered']['char_start']-10:x['covered']['char_end']-10],x['text'])

class LocalBundle(unittest.TestCase):
    def test_bundles_fine_context_around_detail_spans(self):
        i=TEXT.find('120 Euro');b=G.local_bundle(TEXT,REF,[(i,i+8)])
        self.assertEqual(len(b),1);x=b[0]
        self.assertIn('120 Euro',x['text']);self.assertGreater(len(x['text']),len('120 Euro')+20)
        self.assertEqual((x['authority'],x['provisional'],x['fallback']),('PROVISIONAL_LOCAL_GIST',True,'B1_DETAIL'))
        self.assertLessEqual(x['compression_ratio'],G.LOCAL_MAX_UNITS)
        self.assertEqual(TEXT[x['covered']['char_start']-10:x['covered']['char_end']-10],x['text'])
        self.assertEqual(G.local_bundle(TEXT,REF,[(i,i+8),(i+1,i+7)]),b)  # same neighbourhood once
        self.assertEqual(G.local_bundle(TEXT,REF,[]),[])

class B1Reentry(unittest.TestCase):
    def test_reentry_records_local_gist_and_prompts_it_only_when_active(self):
        import json,tempfile,time
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import Mock
        from v13.runtime import Runtime
        tmp=tempfile.TemporaryDirectory();r=Runtime(Path(tmp.name))
        try:
            e=r.store.event(r.session,TEXT);seen=[]
            def generate(messages,*a,**k):
                seen.append(json.loads(messages[1]['content']));return iter([json.dumps({'summary':'Budget 120','quotes':['120 Euro'],'uncertainty':'high','needs_reentry':True})])
            r.pool.get=Mock(return_value=SimpleNamespace(role='B1_DETAIL',last_metrics={},generate=generate))
            r.cognition.offer('B1_DETAIL',e,0,time.monotonic()+30)
            self.assertNotIn('local_gist',seen[-1])  # first pass: no re-entry yet
            r.cognition.offer('B1_DETAIL',e,0,time.monotonic()+30)
            q=json.loads(r.store.one("SELECT payload FROM packets WHERE kind='QueryPacket' ORDER BY rowid DESC LIMIT 1")['payload'])
            self.assertEqual(q['local_gist']['applied'],False);self.assertNotIn('local_gist',seen[-1])
            G.Gist(r.store).set_mode('ACTIVE','EXPLICIT_HUMAN');r.cognition.offer('B1_DETAIL',e,0,time.monotonic()+30)
            self.assertTrue(any('120 Euro' in x for x in seen[-1]['local_gist']))
        finally:r.close();tmp.cleanup()

if __name__=='__main__':unittest.main()

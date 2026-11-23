"""WP-G G1B: B2 gist grouping (~8 token-equivalents, ~12 slots), Age-flexible resolution, exact back-references."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import gist as G
from v13.age import GIST_FINE,GIST_BASE

TEXT='We move on 2026-11-02. The van is booked for 8:00, and Tom brings boxes. Before that, cancel the internet contract and forward the mail. '*3
def ref(t,start=0):return {'source_id':'s','sha256':'0'*64,'char_start':start,'char_end':start+len(t),'modality':'text'}

class GroupingTests(unittest.TestCase):
    def test_lossless_exact_back_reference(self):
        for mode in ('boundary','fixed'):
            p=G.plan(TEXT,ref(TEXT,100),{'tokens_per_group':8,'slots':12},mode)
            for x in p['slots']:self.assertEqual(TEXT[x['source_ref']['char_start']-100:x['source_ref']['char_end']-100],x['text'])
            joined=''.join(x['text'] for x in p['slots']).replace(' ','');self.assertEqual(joined,TEXT.replace(' ',''))
    def test_boundary_mode_respects_sentences_and_exact_spans(self):
        b=G.group(TEXT,ref(TEXT),8,'boundary');f=G.group(TEXT,ref(TEXT),8,'fixed')
        rate=lambda g:sum(x['boundary']>=.7 for x in g)/len(g)
        self.assertGreaterEqual(rate(b),rate(f));self.assertGreaterEqual(rate(b),.8)
        self.assertTrue(all('2026-11-02' in x['text'] or '2026' not in x['text'] for x in b))
        self.assertFalse(any(x['text'].strip() in '.,;:' for x in b))  # punctuation stays with its word
    def test_slots_fit_and_old_context_coarser(self):
        long=' '.join('Sentence number %d talks about topic %d.'%(i,i%3) for i in range(60))
        p=G.plan(long,ref(long),{'tokens_per_group':8,'slots':12})
        self.assertEqual(len(p['slots']),12);self.assertTrue(p['coarsened'])
        sc=[x['scale'] for x in p['slots']];self.assertGreater(sc[0],sc[-1]);self.assertEqual(sum(sc),p['groups_raw'])

class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        from v13.config import LEGACY_QUOTE_PATH
        self.r.cfg.update(LEGACY_QUOTE_PATH)  # gist slot mechanics on the pre-2026-10-21 quote path
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def age(self):
        from v13.age import controller
        return controller(self.r)
    def test_age_literal_conflict_narrow(self):
        base=G.resolve(self.age(),'plain text here');self.assertEqual(base['tokens_per_group'],GIST_BASE[0])
        self.assertEqual(G.resolve(self.age(),'call `load()` first')['tokens_per_group'],GIST_FINE)
        self.assertLess(G.resolve(self.age(),'plain',conflict=True)['tokens_per_group'],base['tokens_per_group'])
        self.assertLess(G.resolve(self.age(),'plain',novelty=1.)['tokens_per_group'],base['tokens_per_group'])
        self.assertEqual(G.resolve(None,'plain')['tokens_per_group'],GIST_BASE[0])
    def offer(self):
        seen=[]
        def gen(messages,*a,**k):seen.append(json.loads(messages[1]['content']));yield json.dumps({'summary':'moving plan','quotes':['2026-11-02'],'uncertainty':'low','needs_reentry':False})
        self.r.pool.get=lambda role:SimpleNamespace(role=role,last_metrics={},generate=gen)
        e=self.r.store.event(self.r.session,TEXT);p=self.r.cognition.offer('B2_GIST',e,0,time.monotonic()+30)
        q=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='QueryPacket' ORDER BY rowid DESC LIMIT 1")['payload'])
        return p,q,seen[0]
    def test_offer_shadow_then_active(self):
        p,q,sent=self.offer();self.assertFalse(q['gist']['applied']);self.assertIn('source_segments',sent);self.assertNotIn('gist_slots',sent)
        self.assertEqual(q['gist']['tokens_per_group'],GIST_BASE[0]);self.assertEqual(len(p['evidence_refs']),1)
        with self.assertRaises(PermissionError):G.Gist(self.r.store).set_mode('ACTIVE')
        op=Operator(self.r);self.assertIn('ACTIVE',op.run(':gist active'))
        p,q,sent=self.offer();self.assertTrue(q['gist']['applied']);self.assertNotIn('source_segments',sent)
        self.assertLessEqual(len(sent['gist_slots']),12);self.assertEqual(len(p['evidence_refs']),1)
        self.assertIn('preview',op.run(':gist preview Hello there. This is a test.'))

if __name__=='__main__':unittest.main()

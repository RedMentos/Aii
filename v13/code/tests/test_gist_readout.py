"""WP-G2 / G1B: native gist readout consumer (B2 tap -> exact-span gist groups); synthetic vectors, no model."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
from v13 import gist_readout as R
from v13.runtime import Runtime
from v13.operator import Operator

TEXT="The lighthouse on Kerr Island was rebuilt in 1987 after a storm. Maria's bakery opens at 6:30, but on Sundays it stays closed. Größe: 12 cm 🙂 done."
def ref(t,start=0):return {'source_id':'s','sha256':'0'*64,'char_start':start,'char_end':start+len(t),'modality':'text'}

def pieces(text):
    """Word/space/punctuation pieces like a byte BPE, with the emoji split into two byte pieces."""
    import re
    out=[]
    for m in re.finditer(r' ?\w+|[^\w\s]| ',text):
        p=m.group(0)
        if '🙂' in p:b=p.encode('utf-8');out+= [list(b[:2]),list(b[2:])]
        else:out.append(p)
    return out

def topic_vectors(text,ps,dim=16,seed=3):
    """One random direction per sentence plus small noise: a native shift exactly at sentence starts."""
    rng=np.random.default_rng(seed);spans=R.token_spans(text,ps);dirs=[];sentence=0;cur=rng.normal(size=dim)
    for i,(a,b) in enumerate(spans):
        if i and text[spans[i-1][1]-1:spans[i-1][1]] in '.!?':cur=rng.normal(size=dim)
        dirs.append(cur+rng.normal(scale=.05,size=dim))
    return np.asarray(dirs)

class SpanTests(unittest.TestCase):
    def test_pieces_bind_to_exact_chars_including_split_multibyte(self):
        ps=pieces(TEXT);sp=R.token_spans(TEXT,ps)
        self.assertEqual(''.join(TEXT[a:b] for a,b in sp),TEXT)  # zero-width tail of the split emoji adds nothing
        self.assertEqual(sp[-1][1],len(TEXT))
        i=[k for k,p in enumerate(ps) if isinstance(p,list)];self.assertEqual(len(i),2)
        self.assertEqual(TEXT[sp[i[0]][0]:sp[i[1]][1]],'🙂')
    def test_mismatching_pieces_are_refused(self):
        ps=pieces(TEXT);ps[3]=' Kerry'
        with self.assertRaises(R.ReadoutError):R.token_spans(TEXT,ps)
        with self.assertRaises(R.ReadoutError):R.token_spans(TEXT+'!',pieces(TEXT))
    def test_zero_vector_and_count_mismatch_refused(self):
        ps=pieces(TEXT);v=topic_vectors(TEXT,ps);v[4]=0
        with self.assertRaises(R.ReadoutError):R.consume(TEXT,ref(TEXT),list(range(len(ps))),ps,v)
        with self.assertRaises(R.ReadoutError):R.consume(TEXT,ref(TEXT),list(range(len(ps)-1)),ps,topic_vectors(TEXT,ps))

class GroupingTests(unittest.TestCase):
    def setUp(self):
        self.ps=pieces(TEXT);self.v=topic_vectors(TEXT,self.ps);self.ids=list(range(len(self.ps)))
    def test_every_mode_lossless_and_back_referenced(self):
        for m in R.MODES:
            plan,V=R.consume(TEXT,ref(TEXT,50),self.ids,self.ps,self.v,mode=m)
            self.assertTrue(plan['lossless']);self.assertEqual(''.join(s['text'] for s in plan['slots']),TEXT)
            for s in plan['slots']:
                self.assertEqual(TEXT[s['source_ref']['char_start']-50:s['source_ref']['char_end']-50],s['text'])
                a,b=s['native_tokens'];np.testing.assert_allclose(V[s['slot']],self.v[a:b].mean(0))
            self.assertEqual(plan['receiver_injection_authority'],0);self.assertEqual(plan['authority'],'SHADOW')
            self.assertNotIn('vector',json.dumps(plan).replace('vector_sha256',''))
    def test_legal_cuts_never_split_words_numbers_or_punctuation(self):
        for m in ('text','native','hybrid'):
            plan,_=R.consume(TEXT,ref(TEXT),self.ids,self.ps,self.v,mode=m)
            for s in plan['slots']:
                t=s['text'];self.assertFalse(t.strip() and t.strip()[0] in '.,;:',m+': '+t)
            joined=[s['text'] for s in plan['slots']]
            for exact in ('1987','6:30','12'):self.assertTrue(any(exact in t for t in joined))
    def test_native_mode_follows_state_shift(self):
        sp=R.token_spans(TEXT,self.ps);shift=R.native_shift(self.v)
        cuts=R.cut_points(TEXT,sp,shift,8,'native')
        ends={i for i in range(len(sp)-1) if TEXT[sp[i][1]-1] in '.!?'}
        self.assertTrue(set(cuts[:-1])&ends);self.assertGreaterEqual(len(set(cuts[:-1])&ends),2)
    def test_fit_merges_oldest_weighted(self):
        long=' '.join('Sentence %s talks about topic %s.'%(chr(65+i%26),chr(97+i%7)) for i in range(40))
        ps=pieces(long);v=topic_vectors(long,ps);plan,V=R.consume(long,ref(long),list(range(len(ps))),ps,v,size=8,slots=12)
        self.assertEqual(len(plan['slots']),12);self.assertTrue(plan['coarsened'])
        sc=[s['scale'] for s in plan['slots']];self.assertGreater(sc[0],sc[-1])
        a,b=plan['slots'][0]['native_tokens'];np.testing.assert_allclose(V[0],v[a:b].mean(0))
    def test_unknown_mode(self):
        with self.assertRaises(R.ReadoutError):R.consume(TEXT,ref(TEXT),self.ids,self.ps,self.v,mode='magic')

class LiveConsumerTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def stored_tap(self):
        e=self.r.store.event(self.r.session,TEXT);ps=pieces(TEXT);v=topic_vectors(TEXT,ps,dim=8);ids=list(range(100,100+len(ps)))
        runner=MagicMock();runner.tap.return_value={'token_ids':ids,'vectors':v.tolist(),'metrics':{}};runner.tap_id='qwen35.result_norm.final.v1'
        runner._json.return_value={'tokens':[{'id':i,'piece':p} for i,p in zip(ids,ps)]}
        with patch.object(self.r.pool,'get_tap',return_value=runner),patch.object(self.r.learner,'predict_states',return_value=None):
            p=self.r.cognition.tap('B2_GIST',e,e['source_ref'],time.monotonic()+30)
        return p,runner
    def test_operator_consumes_stored_b2_tap(self):
        p,runner=self.stored_tap()
        with patch.object(self.r.pool,'get_tap',return_value=runner):out=json.loads(Operator(self.r).run(':gist readout native'))
        self.assertEqual(out['mode'],'native');self.assertEqual(out['tap_packet_id'],p['packet_id']);self.assertTrue(out['lossless'])
        self.assertEqual(''.join(s['text'] for s in out['slots']),TEXT)
        self.assertIsNotNone(self.r.store.one("SELECT 1 FROM telemetry WHERE kind='gist_readout'"))
    def test_token_mismatch_refused(self):
        p,runner=self.stored_tap();runner._json.return_value={'tokens':[{'id':1,'piece':TEXT}]}
        with patch.object(self.r.pool,'get_tap',return_value=runner),self.assertRaises(R.ReadoutError):R.readout(self.r,p)
    def test_no_tap(self):
        with self.assertRaises(ValueError):Operator(self.r).run(':gist readout')

if __name__=='__main__':unittest.main()

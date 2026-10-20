"""offer_quote_context_chars (STEP2 B2->C3 transport, 2026-10-20): off = old exact verification, on = quote as pointer to exact source sentences."""
import json
from pathlib import Path
import sys
import time
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
from v13.cognition import quote_span

PRIOR='Project Borealis. Budget 90 euros. Deadline 4 days. Local-only requirement: true.'

class QuoteSpan(unittest.TestCase):
    def test_off_is_exact_substring_only(self):
        self.assertEqual(quote_span('Budget 90 euros.',PRIOR),(18,34))
        for q in ('local-only requirement: true.','',None,'Budget  90 euros.'):self.assertIsNone(quote_span(q,PRIOR))
    def test_on_points_at_whole_bounded_sentences(self):
        a,b=quote_span('Project Borealis. Budget 90 euros.',PRIOR,200);self.assertEqual(PRIOR[a:b],PRIOR)
        a,b=quote_span('local-only  requirement: TRUE.',PRIOR,200);self.assertEqual(PRIOR[a:b],PRIOR)
        a,b=quote_span('Deadline 4 days.',PRIOR,40);self.assertIn('Deadline 4 days.',PRIOR[a:b]);self.assertLessEqual(b-a,40)
        self.assertEqual(PRIOR[slice(*quote_span('Budget 90 euros.',PRIOR,20))],'Budget 90 euros.')  # sentence fits, neighbours do not
    def test_on_never_invents_text(self):
        for q in ('Budget 95 euros.','local-only requirement: false.','Deadline 4 days, local'):self.assertIsNone(quote_span(q,PRIOR,200))
        self.assertEqual(PRIOR[slice(*quote_span('true.',PRIOR,200))],'true.')  # < 12 chars: verified, not widened
        self.assertIsNone(quote_span('TRUE.',PRIOR,200))  # < 12 chars: exact only
    def test_case_folding_keeps_offsets_exact(self):
        src='Straße 12. Budget 30 euros. Deadline 2 days.'
        a,b=quote_span('BUDGET 30 EUROS.',src,0) or (None,None);self.assertIsNone(a)
        a,b=quote_span('strasse 12. budget 30 euros.',src,200);self.assertEqual(src[a:b],src)
    def test_long_sentence_beyond_cap_keeps_the_quote(self):
        src='A'*50+' Budget 90 euros and many further words here. Next.'
        a,b=quote_span('Budget 90 euros and many',src,30);self.assertEqual(src[a:b],'Budget 90 euros and many')

class OfferPath(unittest.TestCase):
    def test_offer_evidence_off_vs_on(self):
        from v13.runtime import Runtime
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:
                out={}
                for label,wide in (('off',0),('on',200)):
                    r.cfg['offer_quote_context_chars']=wide
                    reply=json.dumps({'summary':'s','quotes':['project borealis. budget 90 euros.','Budget 90 euros.'],'uncertainty':'u','needs_reentry':False})
                    r.pool.get=Mock(return_value=SimpleNamespace(role='B1_DETAIL',last_metrics={},generate=lambda *a,**k:iter([reply])))
                    e=r.store.event(r.session,PRIOR);p=r.cognition.offer('B1_DETAIL',e,0,time.monotonic()+30)
                    out[label]=([r.store.read_source(x) for x in p['evidence_refs']],p['rejected_quotes'])
                self.assertEqual(out['off'],(['Budget 90 euros.'],1))
                self.assertEqual(out['on'],([PRIOR],0))  # both quotes point at the same sentences: one ref
            finally:r.close()
    def test_config_and_chain_link(self):
        from v13.config import validate,DEFAULTS
        validate(DEFAULTS|{'offer_quote_context_chars':200})
        for bad in (-1,401,True,'200'):
            with self.assertRaises(ValueError):validate(DEFAULTS|{'offer_quote_context_chars':bad})
        sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
        import integrated_candidates as ic, source_handoff_candidate as sh
        live=(ROOT/'v13/cognition.py').read_text()
        baseline,changed=sh.sources();self.assertIn(live,(baseline['v13/cognition.py'],changed['v13/cognition.py']))
        with self.assertRaises(ValueError):ic.quote_context(live)  # applied exactly once
        self.assertIn('quote_context',ic.INTEGRATED)

if __name__=='__main__':unittest.main()

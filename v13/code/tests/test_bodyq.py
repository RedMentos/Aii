"""WP-Z2f: body question derived from the current message (cfg body_question_mode='derived'). No models."""
import json,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from v13 import bodyq as Q
from v13.config import DEFAULTS,validate

class Derive(unittest.TestCase):
    def test_entities_and_pointers(self):
        t='Project Kestrel. Decide between Option A and Option B from the latest supplier data sheet, using the earlier project rules.'
        self.assertEqual(Q.parts(t),(['Project Kestrel','Option A','Option B'],['supplier data sheet','project rules']))
        self.assertIn('exact values of Project Kestrel, Option A and Option B (from the supplier data sheet and project rules)',Q.question('B1_DETAIL',t))
        self.assertTrue(Q.question('B2_GIST',t).startswith('Which earlier supplier data sheet and project rules for Project Kestrel'))
    def test_nothing_found_gives_general_question(self):
        for role in ('B1_DETAIL','B2_GIST'):self.assertEqual(Q.question(role,'what time is it?'),Q.GENERAL[role])
    def test_focus_is_a_question_not_a_fact(self):
        f=Q.focus('B1_DETAIL','Ask Maria Lopez.');self.assertEqual(f['authority'],'EXECUTIVE_QUESTION_NOT_FACT');self.assertLessEqual(len(f['question']),400)
    def test_config(self):
        self.assertEqual(DEFAULTS.get('body_question_mode',''),'')
        with self.assertRaises(ValueError):validate(dict(DEFAULTS,body_question_mode='model'))
        validate(dict(DEFAULTS,body_question_mode='derived'))

class Live(unittest.TestCase):
    def offer(self,r,text):
        reply=json.dumps({'summary':'s','quotes':[],'uncertainty':'u','needs_reentry':False});seen=[]
        def gen(messages,*a,**k):seen.append(messages);return iter([reply])
        r.pool.get=Mock(return_value=SimpleNamespace(role='B1_DETAIL',last_metrics={},generate=gen))
        e=r.store.event(r.session,text);r.cognition.offer('B1_DETAIL',e,0,time.monotonic()+30);return json.loads(seen[0][1]['content'])
    def test_off_by_default_and_switch_text_wins(self):
        from v13.runtime import Runtime
        t='Project Kestrel. Decide between Option A and Option B.'
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:
                self.assertNotIn('jef_query',self.offer(r,t))
                r.cfg['body_question_mode']='derived';q=self.offer(r,t)['jef_query']
                self.assertEqual(q,{'question':Q.question('B1_DETAIL',t),'kind':'FILL_GAP'})
                r.cfg['body_question_b1']='Fixed question?';self.assertEqual(self.offer(r,t)['jef_query']['question'],'Fixed question?')
            finally:r.close()
    def test_chain_link_matches_live(self):
        from scripts.integrated_candidates import INTEGRATED
        self.assertIn('body_question_derived',INTEGRATED)
        live=(Path(__file__).resolve().parents[1]/'v13/cognition.py').read_text();self.assertIn("bodyq.focus(role,text)",live)

if __name__=='__main__':unittest.main()

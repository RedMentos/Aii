"""WP-Z2c: body_question_b1 / body_question_b2 ('' = off = live) give a body the standing executive question measured in WP-Z2b."""
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts'),str(ROOT/'tests')]
from v13.config import DEFAULTS,validate
import step2_z2b_seeds as z2b

TEXT='Project Kestrel. Option A: cost 40 euros, duration 2 days, local true. Option B: cost 70 euros, duration 7 days, local false.'

class Config(unittest.TestCase):
    def test_off_by_default_and_bounded(self):
        for key in ('body_question_b1','body_question_b2'):
            self.assertEqual(DEFAULTS.get(key,''),'')
            validate(DEFAULTS|{key:z2b.QUESTIONS['B1_DETAIL']})
            for bad in (True,1,None,'x'*401):
                with self.assertRaises(ValueError):validate(DEFAULTS|{key:bad})
    def test_chain_link_applied_exactly_once(self):
        import integrated_candidates as ic, source_handoff_candidate as sh
        live=(ROOT/'v13/cognition.py').read_text()
        baseline,changed=sh.sources();self.assertIn(live,(baseline['v13/cognition.py'],changed['v13/cognition.py']))
        with self.assertRaises(ValueError):ic.body_question(live)
        self.assertIn('body_question',ic.INTEGRATED)

class Offer(unittest.TestCase):
    def offer(self,r,role,focus=None):
        reply=json.dumps({'summary':'s','quotes':[],'uncertainty':'u','needs_reentry':False});seen=[]
        def gen(messages,*a,**k):seen.append(messages);return iter([reply])
        r.pool.get=Mock(return_value=SimpleNamespace(role=role,last_metrics={},generate=gen))
        e=r.store.event(r.session,TEXT)
        p=r.cognition.offer(role,e,0,time.monotonic()+30,**({'focus':focus} if focus else {}))
        q=json.loads(r.store.one("SELECT payload FROM packets WHERE id=? AND kind='QueryPacket'",(p['query_packet_id'],))['payload'])
        return json.loads(seen[0][1]['content']),seen[0][0]['content'],q
    def test_off_is_live_on_asks_and_explicit_focus_wins(self):
        from v13.runtime import Runtime
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(Path(d))
            try:
                off={role:self.offer(r,role) for role in ('B1_DETAIL','B2_GIST')}
                r.cfg['body_question_b1']=r.cfg['body_question_b2']=''
                for role in off:  # '' is the same as absent (event ids/prior hypothesis differ per turn, so keys + instructions)
                    query,instr,q=self.offer(r,role)
                    self.assertEqual(set(query),set(off[role][0]));self.assertEqual(instr,off[role][1]);self.assertNotIn('jef_query',q)
                r.cfg['body_question_b1']=z2b.QUESTIONS['B1_DETAIL']
                query,instr,q=self.offer(r,'B1_DETAIL')
                # same fields the WP-Z2b runner patch put on the query (z2b.focus), stored as a question, never a fact
                self.assertEqual(query['jef_query'],{k:z2b.focus('B1_DETAIL')[k] for k in ('question','kind')})
                self.assertIn('jef_query is the executive question',instr)
                self.assertEqual(q['jef_query'],z2b.focus('B1_DETAIL')|{'reason':'CFG_STANDING_QUESTION'})
                query,_,q=self.offer(r,'B2_GIST')
                self.assertNotIn('jef_query',query);self.assertNotIn('jef_query',q)  # per-role switch
                r.cfg['body_question_b2']=z2b.QUESTIONS['B2_GIST']
                query,_,_=self.offer(r,'B2_GIST');self.assertEqual(query['jef_query']['question'],z2b.QUESTIONS['B2_GIST'])
                reentry={'question':'Which duration does Option B have?','kind':'FILL_GAP'}
                query,_,q=self.offer(r,'B1_DETAIL',focus=reentry)
                self.assertEqual(query['jef_query'],reentry);self.assertEqual(q['jef_query'],reentry)  # a re-entry focus is never overwritten
            finally:r.close()

if __name__=='__main__':unittest.main()

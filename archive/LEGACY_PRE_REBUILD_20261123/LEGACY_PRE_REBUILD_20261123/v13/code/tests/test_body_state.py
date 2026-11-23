"""State/provenance regressions; these fixtures are not model-inference proofs."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from v13.contracts import packet
from v13.common import dumps
from v13.runtime import Runtime


class BodyState(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name);self.r=Runtime(self.home)
    def tearDown(self):
        self.r.close();self.tmp.cleanup()
    def event(self,text):return self.r.store.event(self.r.session,text)
    def offer(self,text,role='B2_GIST',event=None):
        e=event or self.event(text)
        p=packet('OfferPacket',role,e['event_id'],e['brain_generation_id'],[e['source_ref']],role=role,based_on_state_version=0,deadline_monotonic_ns=time.monotonic_ns()+10**9,evidence_refs=[e['source_ref']],offer={'summary':'Unit hypothesis, not a fact.'},confidence=0.,model_revision=self.r.models.revision(role))
        self.r.store.add_packet('OfferPacket',p);self.r.cognition.retain_body_offer(p);return p
    def test_gist_multiple_sources_survive_restart_fine_window_is_short(self):
        first=self.offer('Projekt Aurora: Budget 120 Euro.')
        second=self.offer('Projekt Aurora: Nur lokal, keine Cloud.')
        self.r.close();self.r=Runtime(self.home)
        e=self.event('Projekt Aurora: Wie passen Budget und Vorgaben zusammen?')
        ctx=self.r.cognition.body_context('B2_GIST',e)
        self.assertEqual([c['offer_id'] for c in ctx],[second['packet_id'],first['packet_id']])
        self.assertTrue(all(self.r.store.read_source(c['source_ref'])==c['native_context']['exact_source_excerpt'] for c in ctx))
        self.assertLessEqual(len(dumps([c['native_context'] for c in ctx])),self.r.cfg['b2_context_chars'])
        self.assertEqual(self.r.cognition.body_context('B1_DETAIL',e),[])
        self.offer('Projekt Aurora: Detail 1','B1_DETAIL');fine=self.offer('Projekt Aurora: Detail 2','B1_DETAIL')
        state,_=self.r.store.state('B1_DETAIL:'+self.r.session)
        self.assertEqual(state['retained_offer_ids'],[fine['packet_id']])
    def test_scope_generation_model_and_ablation_exclude_context(self):
        self.offer('Projekt Aurora: Budget 120 Euro.')
        self.assertEqual(self.r.cognition.body_context('B2_GIST',self.event('Projekt Borealis: Budget?')),[])
        e=self.event('Projekt Aurora: Budget?')
        self.assertTrue(self.r.cognition.body_context('B2_GIST',e))
        self.assertEqual(self.r.cognition.body_context('B2_GIST',e|{'brain_generation_id':'other'}),[])
        self.r.models.installed['gist']={'exact_revision':'changed'}  # B2 has its own body since WP-V4
        self.assertEqual(self.r.cognition.body_context('B2_GIST',e),[])
        self.r.models.installed.pop('gist');self.r.cfg['b2_state_slots']=0
        self.assertEqual(self.r.cognition.body_context('B2_GIST',e),[])
        self.r.cfg['b2_state_slots']=4;self.r.session=self.r.store.new_session()
        self.assertEqual(self.r.cognition.body_context('B2_GIST',self.event('Projekt Aurora: Budget?')),[])
    def test_capacity_duplicate_event_and_unreadable_source(self):
        offers=[self.offer('Projekt Aurora: Punkt '+str(i)) for i in range(7)]
        state,_=self.r.store.state('B2_GIST:'+self.r.session)
        self.assertEqual(state['retained_offer_ids'],[p['packet_id'] for p in reversed(offers[-4:])])
        e=json.loads(self.r.store.one('SELECT packet FROM events WHERE id=?',(offers[-1]['event_id'],))['packet'])
        replacement=self.offer('',event=e)
        state,_=self.r.store.state('B2_GIST:'+self.r.session)
        self.assertEqual(len(state['retained_offer_ids']),4)
        self.assertNotIn(offers[-1]['packet_id'],state['retained_offer_ids'])
        with self.r.store.tx() as db:db.execute('UPDATE sources SET deleted=1 WHERE id=?',(e['source_ref']['source_id'],))
        ctx=self.r.cognition.body_context('B2_GIST',self.event('Projekt Aurora: Punkte?'))
        self.assertNotIn(replacement['packet_id'],[c['offer_id'] for c in ctx])
        self.r.cfg['b2_context_chars']=1
        self.assertEqual(self.r.cognition.body_context('B2_GIST',self.event('Projekt Aurora: Punkte?')),[])
    def test_legacy_single_offer_state_is_read_without_rewrite(self):
        p=self.offer('Projekt Aurora: Budget 120 Euro.')
        self.r.store.set_state('B2_GIST:'+self.r.session,p)
        e=self.event('Projekt Aurora: Budget?')
        self.assertEqual(self.r.cognition.body_context('B2_GIST',e)[0]['offer_id'],p['packet_id'])
        self.assertEqual(self.r.store.state('B2_GIST:'+self.r.session)[0],p)
    def test_native_probe_failure_is_saved_without_touching_parent_brain(self):
        from v13.proofs import probe_body_state
        before=self.r.store.generation();sid=self.r.session
        result=probe_body_state(self.r)
        self.assertEqual(result['status'],'BODY_STATE_CHECKS_INTERRUPTED')
        proof=json.loads(Path(result['artifact']).read_text())
        self.assertEqual(proof['turns'],[])
        self.assertEqual(self.r.store.generation(),before);self.assertEqual(self.r.session,sid)
        self.assertEqual(self.r.store.rows('SELECT * FROM events'),[])
        self.assertFalse(self.r.cancel_event.is_set())
        self.assertEqual(list((self.home/'tmp').glob('body-state-*')),[])

if __name__=='__main__':unittest.main()

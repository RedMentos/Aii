"""Run274: Sleep A/B must not use revoked F5 human corrections as evidence.

Actual Runtime+SQLite, synthetic text, no native model/Redmi or dream fact writes.
"""
import tempfile
from pathlib import Path
import unittest
from v13.runtime import Runtime


class SleepMemoryAuthorityRun274(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        self.r=Runtime(self.home);self.r.sleep.cycle.set_policy('enabled','off')
        self.s=self.r.store;self.session=self.r.session;self.cy=self.r.sleep.cycle

    def tearDown(self):self.r.close();self.tmp.cleanup()

    def correction(self,key,value,kind='route'):
        e=self.s.event(self.session,key)
        mid=self.r.memory.feedback(e['event_id'],kind,value,key=key)
        sid=self.s.one('SELECT source_id FROM memories WHERE id=?',(mid,))['source_id']
        return e,mid,sid

    def change(self,sql,args=()):
        with self.s.tx() as conn:conn.execute(sql,args)

    def dream(self):
        st,_=self.cy.queue.load()
        return self.cy.sleep_b(st,self.cy.policy(),limit=8)

    def test_valid_route_retention_and_dream_are_still_available(self):
        e,mid,sid=self.correction('Explain Project Orion precisely','detail')
        status,errors,proof=self.cy._probe({'event_id':e['event_id']})
        self.assertEqual(status,'PASS')
        rep=self.dream()
        self.assertTrue(any(h['kind']=='ROUTE_ALTERNATIVE' for h in rep['hypotheses']))
        self.assertEqual(rep['fact_write_authority'],0)
        self.assertEqual(self.s.rows('SELECT * FROM updates'),[])

    def test_deleted_human_decision_invalidates_route_retention_and_dream(self):
        e,mid,sid=self.correction('Explain Project Orion precisely','detail')
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(sid,))
        self.assertNotEqual(self.cy._probe({'event_id':e['event_id']})[0],'PASS')
        self.assertEqual(self.dream()['hypotheses'],[])

    def test_deleted_feedback_invalidates_route_retention_and_dream(self):
        e,mid,sid=self.correction('Explain Project Orion precisely','detail')
        self.change('DELETE FROM feedback WHERE source_id=?',(sid,))
        self.assertNotEqual(self.cy._probe({'event_id':e['event_id']})[0],'PASS')
        self.assertEqual(self.dream()['hypotheses'],[])

    def test_nonhuman_source_kind_or_duplicate_decision_invalidates_dream(self):
        e,mid,sid=self.correction('Explain Project Orion precisely','detail')
        self.change('UPDATE sources SET kind=? WHERE id=?',('REPLAY_HYPOTHESIS',sid))
        self.assertEqual(self.dream()['hypotheses'],[])
        self.change('UPDATE sources SET kind=? WHERE id=?',('HUMAN_DECISION',sid))
        row=self.s.one("SELECT id FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(sid,))
        self.change('INSERT INTO packets SELECT ?,kind,event_id,generation_id,payload,created FROM packets WHERE id=?',('pkt-run274-duplicate',row['id']))
        self.assertEqual(self.dream()['hypotheses'],[])

    def test_revoked_fact_cannot_seed_world_relation_dream(self):
        a,mid,sid=self.correction('Project Aurora budget','120 credits','fact')
        b,mid2,sid2=self.correction('Project Borealis budget','120 credits','fact')
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(sid,))
        rep=self.dream()
        self.assertFalse(any(h['kind']=='WORLD_RELATION' for h in rep['hypotheses']))

    def test_valid_second_route_survives_first_revocation(self):
        e,mid,sid=self.correction('Explain Project Orion precisely','detail')
        e2,mid2,sid2=self.correction('Explain Project Vega precisely','gist')
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(sid,))
        self.assertEqual(self.cy._probe({'event_id':e2['event_id']})[0],'PASS')
        rep=self.dream()
        self.assertTrue(any(h['kind']=='ROUTE_ALTERNATIVE' for h in rep['hypotheses']))
        self.assertTrue(all(mid not in h.get('signature','') for h in rep['hypotheses']))


if __name__=='__main__':unittest.main()

"""Run275: queued Dream B hypotheses and supporting neighbors require live F5 authority.

Actual Runtime+SQLite, synthetic human corrections; no native model or fact writes.
"""
import json
import tempfile
from pathlib import Path
import unittest
from v13.runtime import Runtime


class DreamValidationAuthorityRun275(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.home=Path(self.tmp.name)
        self.r=Runtime(self.home);self.r.sleep.cycle.set_policy('enabled','off')
        self.s=self.r.store;self.session=self.r.session;self.cy=self.r.sleep.cycle

    def tearDown(self):self.r.close();self.tmp.cleanup()

    def correction(self,key,value,kind='route'):
        e=self.s.event(self.session,key)
        mid=self.r.memory.feedback(e['event_id'],kind,value,key=key)
        sid=self.s.one('SELECT source_id FROM memories WHERE id=?',(mid,))['source_id']
        return mid,sid

    def change(self,sql,args=()):
        with self.s.tx() as conn:conn.execute(sql,args)

    def queued(self,kind):
        st,_=self.cy.queue.load();rep=self.cy.sleep_b(st,self.cy.policy(),limit=12)
        for h in rep['hypotheses']:
            if h['kind']==kind:
                rid=h['replay_id']
                row=self.s.one("SELECT payload FROM packets WHERE kind='ReplayItem' AND json_extract(payload,'$.replay_id')=? AND json_extract(payload,'$.stage')='QUEUED'",(rid,))
                return json.loads(row['payload'])
        self.fail('Missing queued '+kind)

    def test_valid_queued_route_hypothesis_stays_nonfactual(self):
        self.correction('Explain Project Orion precisely','detail')
        item=self.queued('ROUTE_ALTERNATIVE')
        self.assertEqual(self.cy.check_hypothesis(item)['verdict'],'UNVERIFIED')
        self.assertEqual(item['fact_write_authority'],0)
        self.assertEqual(self.s.rows('SELECT * FROM updates'),[])

    def test_revoked_route_anchor_is_stale(self):
        mid,sid=self.correction('Explain Project Orion precisely','detail')
        item=self.queued('ROUTE_ALTERNATIVE')
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(sid,))
        self.assertEqual(self.cy.check_hypothesis(item)['verdict'],'STALE')

    def test_revoked_route_feedback_is_stale(self):
        mid,sid=self.correction('Explain Project Orion precisely','detail')
        item=self.queued('ROUTE_ALTERNATIVE')
        self.change('DELETE FROM feedback WHERE source_id=?',(sid,))
        self.assertEqual(self.cy.check_hypothesis(item)['verdict'],'STALE')

    def test_revoked_world_relation_anchor_is_stale(self):
        mid,sid=self.correction('Project Aurora budget','120 credits','fact')
        self.correction('Project Borealis budget','120 credits','fact')
        item=self.queued('WORLD_RELATION')
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(sid,))
        self.assertEqual(self.cy.check_hypothesis(item)['verdict'],'STALE')

    def test_revoked_supporting_neighbor_cannot_support_route(self):
        self.correction('Explain Project Orion precisely','detail')
        item=self.queued('ROUTE_ALTERNATIVE')
        alt=item['hypothesis']['alternative_route']
        mid,sid=self.correction('Explain Project Orion precisely please',alt)
        self.assertEqual(self.cy.check_hypothesis(item)['verdict'],'SUPPORTED')
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(sid,))
        self.assertNotEqual(self.cy.check_hypothesis(item)['verdict'],'SUPPORTED')

    def test_unrelated_valid_queued_route_remains_usable(self):
        mid,sid=self.correction('Explain Project Orion precisely','detail')
        mid2,sid2=self.correction('Explain Project Vega precisely','gist')
        item=self.queued('ROUTE_ALTERNATIVE')
        self.change("DELETE FROM packets WHERE kind='HumanDecision' AND json_extract(payload,'$.source_ref.source_id')=?",(sid,))
        # A stale first anchor may be retired, but no other valid memory is erased.
        self.assertEqual(self.cy._probe({'event_id':self.s.one('SELECT event_id FROM memories WHERE id=?',(mid2,))['event_id']})[0],'PASS')


if __name__=='__main__':unittest.main()

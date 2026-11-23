"""WP-U10 §9.1: one human route correction makes the next very similar request better, before consolidation."""
from pathlib import Path
import tempfile
import time
import unittest
from v13.runtime import Runtime
from v13 import episodic_route as ER

class EpisodicRoute(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off');self.s=self.r.store
        e=self.s.event(self.r.session,'Erkläre Projekt Aurora genau');self.r.memory.feedback(e['event_id'],'route','detail');self.src=e
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_similar_request_gets_the_corrected_route_with_lineage(self):
        s=ER.suggest(self.s,'Erkläre Projekt Aurora bitte genau',self.r.session)
        self.assertEqual((s['route'],s['source'],s['event_id']),('detail','FAST_EPISODIC_ROUTE',self.src['event_id']))
        self.assertIsNone(ER.suggest(self.s,'Erkläre Projekt Borealis genau',self.r.session))  # other entity
        self.assertIsNone(ER.suggest(self.s,'Wie wird das Wetter morgen?',self.r.session))
    def test_shadow_records_active_applies_off_disables(self):
        route,info=ER.for_turn(self.s,'Erkläre Projekt Aurora bitte genau',self.r.session)
        self.assertIsNone(route);self.assertEqual((info['mode'],info['applied']),('shadow',False))
        from v13.episodes import operator_command
        self.assertEqual(operator_command(self.r,['route','active']),{'episodic_route':'active'})
        e=self.s.event(self.r.session,'Erkläre Projekt Aurora bitte genau')
        route,info=self.r._route('Erkläre Projekt Aurora bitte genau',e,time.monotonic()+5)
        self.assertEqual((route,info['source'],info['applied']),('detail','FAST_EPISODIC_ROUTE',True))
        ER.set_mode(self.s,'off');self.assertEqual(ER.for_turn(self.s,'Erkläre Projekt Aurora bitte genau',self.r.session),(None,None))
    def test_forgotten_correction_is_not_reused(self):
        m=self.s.one("SELECT id FROM memories WHERE kind='route'")
        self.r.memory.forget(m['id'])
        self.assertIsNone(ER.suggest(self.s,'Erkläre Projekt Aurora bitte genau',self.r.session))

if __name__=='__main__':unittest.main()

"""Age0d final-answer arithmetic shadow across Runtime restart, not user delivery.

Actual Runtime/SQLite synthetic committed assistant messages; no native model.
"""
import tempfile
import unittest
from pathlib import Path

from v13 import age as agectl
from v13 import neuromod
from v13 import selfmodel
from v13.runtime import Runtime


RING = 'AGE0D_ARITHMETIC_SHADOW'


class Age0dFinalShadowCrossOrgan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.system = selfmodel.SelfSystem(
            self.r, agectl.controller(self.r),
            neuromod.Neuromod(self.r.store), clock=lambda: 1000.)
        self.event = self.r.store.event(self.r.session, 'Compute 6 plus 7.')
        self.offer = {'role': 'B2_GIST', 'event_id': self.event['event_id'],
                      'offer': {'summary': '', 'needs_reentry': False},
                      'evidence_refs': []}

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def commit(self, text):
        mid = self.r.store.message(
            self.r.session, self.event['event_id'], 'assistant')
        self.r.store.append_message(mid, text)
        self.r.store.finish_message(mid, 'FINAL', {'model_generated': False})

    def ring(self):
        return self.r.store.state(RING, [])[0]

    def test_wrong_persisted_final_is_shadow_only_and_survives_restart(self):
        notices = []
        self.r.notice = notices.append
        self.commit('14')
        self.system.late_offer(self.event['event_id'], self.offer, '14')
        rows = self.ring()
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['expected'], rows[0]['claimed']), ('13', '14'))
        self.assertEqual(rows[0]['status'], 'MISMATCH_SHADOW_ONLY')
        self.assertFalse(rows[0]['user_notified'])
        self.assertFalse(rows[0]['learning_authorized'])
        self.assertEqual(notices, [])
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'), [])
        self.r.close()
        self.r = Runtime(self.home)
        self.assertEqual(self.ring(), rows)

    def test_uncommitted_offer_text_cannot_create_shadow_diagnostic(self):
        self.commit('13')
        self.system.late_offer(self.event['event_id'], self.offer, '14')
        self.assertEqual(self.ring(), [])
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'), [])


if __name__ == '__main__':
    unittest.main()

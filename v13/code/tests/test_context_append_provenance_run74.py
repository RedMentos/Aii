"""Run74: append-only Context OS re-entry must bind to prompt actually applied."""
import unittest
from v13.context_os import ContextOS
from tests.test_context_exact_pin_run73 import FakeStore


def make(active=False):
    s=FakeStore()
    c=ContextOS(s,{'context_tokens':4096,'answer_tokens':10})
    c.set_capability('B1_DETAIL','consecutive_user',True)
    if active:c.set_mode('ACTIVE',authority='EXPLICIT_HUMAN')
    return s,c


def vol(n):return [('LATENT_STATE','\nTASK:',{'n':n})]


def prior(c):return c.plan('e1','B1_DETAIL','SYS',vol(1),[],'q1')


def follow(c,text='q1',event='e1'):
    hist=[{'event_id':event,'role':'user','text':text},
          {'event_id':event,'role':'assistant','text':'a1'}]
    return c.plan('e2','B1_DETAIL','SYS',vol(2),hist,'q2')


class ContextAppendProvenance(unittest.TestCase):
    def test_shadow_to_active_must_not_reenter_hypothetical_prompt(self):
        s,c=make();p1=prior(c)
        self.assertFalse(p1['applied'])
        c.set_mode('ACTIVE',authority='EXPLICIT_HUMAN')
        p2=follow(c)
        self.assertNotIn('append_reentry',p2['plan']['decisions'])
        self.assertEqual(p2['plan']['layout'],'stable_prefix')

    def test_shadow_counterfactual_append_remains_available(self):
        s,c=make();prior(c);p2=follow(c)
        self.assertIn('append_reentry',p2['plan']['decisions'])
        self.assertFalse(p2['applied'])

    def test_active_to_active_reentry_still_works(self):
        s,c=make(active=True);p1=prior(c);self.assertTrue(p1['applied'])
        p2=follow(c)
        self.assertIn('append_reentry',p2['plan']['decisions'])
        self.assertTrue(p2['applied'])

    def test_changed_prior_source_must_not_reenter(self):
        s,c=make(active=True);prior(c)
        p2=follow(c,text='tampered q1')
        self.assertNotIn('append_reentry',p2['plan']['decisions'])

    def test_old_transcript_without_applied_proof_fails_closed(self):
        s,c=make(active=True);prior(c)
        s.st['transcripts']['B1_DETAIL'].pop('applied',None)
        p2=follow(c)
        self.assertNotIn('append_reentry',p2['plan']['decisions'])

    def test_unrelated_event_does_not_reenter(self):
        s,c=make(active=True);prior(c)
        self.assertNotIn('append_reentry',follow(c,event='other')['plan']['decisions'])


if __name__=='__main__':unittest.main()

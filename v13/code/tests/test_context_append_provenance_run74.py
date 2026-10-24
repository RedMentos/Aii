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

    def test_reentry_rejects_changed_earlier_turn_text(self):
        _,c=make(active=True);prior(c);follow(c)
        h=[{'event_id':'e1','role':'user','text':'q1'},
           {'event_id':'e1','role':'assistant','text':'a1 tampered'},
           {'event_id':'e2','role':'user','text':'q2'},
           {'event_id':'e2','role':'assistant','text':'a2'}]
        p=c.plan('e3','B1_DETAIL','SYS',vol(3),h,'q3')
        self.assertNotIn('append_reentry',p['plan']['decisions'])

    def test_reentry_rejects_changed_earlier_source_metadata(self):
        _,c=make(active=True);prior(c)
        h1=[{'event_id':'e1','role':'user','text':'q1','metadata':'{"source_ref":{"source_id":"original"}}'},
            {'event_id':'e1','role':'assistant','text':'a1'}]
        c.plan('e2','B1_DETAIL','SYS',vol(2),h1,'q2')
        h2=[dict(h1[0],metadata='{"source_ref":{"source_id":"changed"}}'),h1[1],
            {'event_id':'e2','role':'user','text':'q2'},
            {'event_id':'e2','role':'assistant','text':'a2'}]
        p=c.plan('e3','B1_DETAIL','SYS',vol(3),h2,'q3')
        self.assertNotIn('append_reentry',p['plan']['decisions'])

    def test_reentry_rejects_latest_user_source_ref_mismatch(self):
        _,c=make(active=True)
        ref={'source_id':'source-A','sha256':'a'*64,'char_start':0,'char_end':2,'modality':'text'}
        c.plan('e1','B1_DETAIL','SYS',vol(1),[],'q1',provenance=[ref])
        altered=dict(ref,source_id='source-B')
        h=[{'event_id':'e1','role':'user','text':'q1','metadata':__import__('json').dumps({'source_ref':altered})},
           {'event_id':'e1','role':'assistant','text':'a1'}]
        p=c.plan('e2','B1_DETAIL','SYS',vol(2),h,'q2')
        self.assertNotIn('append_reentry',p['plan']['decisions'])

    def test_reentry_rejects_extra_message_in_latest_event(self):
        _,c=make(active=True);prior(c)
        h=[{'event_id':'e1','role':'user','text':'q1'},
           {'event_id':'e1','role':'assistant','text':'a1'},
           {'event_id':'e1','role':'assistant','text':'extra'}]
        p=c.plan('e2','B1_DETAIL','SYS',vol(2),h,'q2')
        self.assertNotIn('append_reentry',p['plan']['decisions'])

    def test_reentry_rejects_legacy_transcript_without_history_binding(self):
        s,c=make(active=True);prior(c)
        s.st['transcripts']['B1_DETAIL'].pop('history_binding',None)
        p=follow(c)
        self.assertNotIn('append_reentry',p['plan']['decisions'])

    def test_reentry_accepts_unchanged_three_turn_lineage(self):
        _,c=make(active=True);prior(c);p2=follow(c)
        self.assertIn('append_reentry',p2['plan']['decisions'])
        h=[{'event_id':'e1','role':'user','text':'q1'},
           {'event_id':'e1','role':'assistant','text':'a1'},
           {'event_id':'e2','role':'user','text':'q2'},
           {'event_id':'e2','role':'assistant','text':'a2'}]
        p3=c.plan('e3','B1_DETAIL','SYS',vol(3),h,'q3')
        self.assertIn('append_reentry',p3['plan']['decisions'])

    def test_reentry_accepts_matching_real_shape_query_source_ref(self):
        _,c=make(active=True)
        ref={'source_id':'source-A','sha256':'a'*64,'char_start':0,'char_end':2,'modality':'text'}
        c.plan('e1','B1_DETAIL','SYS',vol(1),[],'q1',provenance=[ref])
        h=[{'event_id':'e1','role':'user','text':'q1','metadata':__import__('json').dumps({'source_ref':ref})},
           {'event_id':'e1','role':'assistant','text':'a1'}]
        p=c.plan('e2','B1_DETAIL','SYS',vol(2),h,'q2')
        self.assertIn('append_reentry',p['plan']['decisions'])



class NativeHistoryReentryIntegration(unittest.TestCase):
    """Actual SQLite/source-filter path, not only authored FakeStore dictionaries."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        from v13.runtime import Runtime
        from v13.history import native_history
        self._tmp=tempfile.TemporaryDirectory()
        self._home=Path(self._tmp.name)
        self.r=Runtime(self._home)
        self.session=self.r.session
        self.native_history=native_history
        self.c=ContextOS(self.r.store,self.r.cfg)
        self.c.set_capability('C3_LANGUAGE','consecutive_user',True)
        self.c.set_mode('ACTIVE',authority='EXPLICIT_HUMAN')
        self.e1=self.r.store.event(self.session,'q1')
        self.c.plan(self.e1['event_id'],'C3_LANGUAGE','SYS',vol(1),[],'q1',
                    provenance=[self.e1['source_ref']])
        self.r.store.message(self.session,self.e1['event_id'],'assistant','a1',
                             status='FINAL',metadata={'direct_source_copy':True})
        self.e2=self.r.store.event(self.session,'q2')
        self.h1,_=self.native_history(self.r.store,self.session,self.e2['event_id'],5)

    def tearDown(self):
        self.r.close()
        self._tmp.cleanup()

    def _second(self):
        self.assertEqual([row['role'] for row in self.h1],['user','assistant'])
        p=self.c.plan(self.e2['event_id'],'C3_LANGUAGE','SYS',vol(2),self.h1,'q2',
                      provenance=[self.e2['source_ref']])
        self.r.store.message(self.session,self.e2['event_id'],'assistant','a2',
                             status='FINAL',metadata={'direct_source_copy':True})
        self.e3=self.r.store.event(self.session,'q3')
        return p

    def _third(self):
        hist,_=self.native_history(self.r.store,self.session,self.e3['event_id'],5)
        p=self.c.plan(self.e3['event_id'],'C3_LANGUAGE','SYS',vol(3),hist,'q3',
                      provenance=[self.e3['source_ref']])
        return hist,p

    def test_native_history_source_ref_allows_valid_active_append(self):
        p=self._second()
        self.assertIn('append_reentry',p['plan']['decisions'])
        self.assertTrue(p['applied'])
        self.assertEqual(self.h1[0]['metadata'] and __import__('json').loads(self.h1[0]['metadata'])['source_ref'],
                         self.e1['source_ref'])

    def test_controller_restart_keeps_exact_history_binding(self):
        self._second()
        self.c=ContextOS(self.r.store,self.r.cfg)  # persisted Store, new controller
        hist,p=self._third()
        self.assertEqual(len(hist),4)
        self.assertIn('append_reentry',p['plan']['decisions'])

    def test_deleted_older_source_rebuilds_without_stale_prompt(self):
        self._second()
        with self.r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?',
                       (self.e1['source_ref']['source_id'],))
        hist,p=self._third()
        self.assertEqual([x['event_id'] for x in hist],[self.e2['event_id']]*2)
        self.assertNotIn('append_reentry',p['plan']['decisions'])
        self.assertNotIn('q1',[m['content'] for m in p['planned']])

    def test_corrupt_older_source_metadata_rebuilds_without_stale_prompt(self):
        self._second()
        with self.r.store.tx() as db:
            db.execute("UPDATE messages SET metadata=? WHERE event_id=? AND role='user'",
                       ('{"source_ref":{"source_id":"invalid"}}',self.e1['event_id']))
        hist,p=self._third()
        self.assertEqual([x['event_id'] for x in hist],[self.e2['event_id']]*2)
        self.assertNotIn('append_reentry',p['plan']['decisions'])
        self.assertNotIn('q1',[m['content'] for m in p['planned']])


if __name__=='__main__':unittest.main()

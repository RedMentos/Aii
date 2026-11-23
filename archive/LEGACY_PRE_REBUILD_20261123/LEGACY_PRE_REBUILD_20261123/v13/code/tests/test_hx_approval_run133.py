"""Run133: persisted human approval and evidence freshness adversarial checks."""
import tempfile
import unittest
from pathlib import Path
from v13.runtime import Runtime
from v13.age import AgeControl
from v13.agi.self_improve import SelfImprovement
from v13.agi.harness import HarnessLibrary
from v13.agi.experience import ExperienceLibrary

NOTE='Always identify a wrong total explicitly and preserve the source.'


class HXAuthorityReview(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.r=Runtime(self.home)
        self.s=self.r.store
        self.h=HarnessLibrary(self.s)
        self.x=ExperienceLibrary(self.s,self.home)
        self.si=SelfImprovement(self.s,self.r.cfg,AgeControl(self.s,self.r.cfg))
        (self.home/'evidence.txt').write_text('first evidence')

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def fake(self):
        return {'id':'forged_approval','kind':'harness','status':'APPROVED',
                'shield':{'passed':True},'request_id':'forged_request',
                'diff':{'tool_hint.list_note':NOTE},
                'base_generation':self.s.generation_id}

    def approved(self):
        pid=self.si.propose('harness',{'tool_hint.list_note':NOTE},origin='USER')
        self.si.evaluate(pid,lambda cfg: {'overall':.5,'seen':.6,'unseen':.4}
                         if cfg is None else {'overall':.55,'seen':.6,'unseen':.42})
        return self.si.approve(pid)

    def test_forged_approved_dict_cannot_apply_harness(self):
        p=self.fake()
        with self.assertRaises(PermissionError):
            self.h.apply(p,p['diff'])
        self.assertEqual(self.h.report()['active'],[])

    def test_forged_approved_dict_cannot_create_experience(self):
        p=self.fake()
        with self.assertRaises(PermissionError):
            self.x.record(p,'situation','lesson','evidence.txt','list_arith')
        self.assertEqual(self.x.report()['entries'],0)

    def test_legitimate_approved_request_remains_functional(self):
        out=self.approved()
        self.assertEqual(self.h.apply(out['proposal'],out['settings'])['targets'],['tool_hint.list_note'])
        self.x.record(out['proposal'],'situation','lesson','evidence.txt','list_arith')
        self.assertEqual(len(self.x.lookup('list_arith')),1)

    def test_stale_evidence_excluded_without_explicit_verify(self):
        out=self.approved()
        self.x.record(out['proposal'],'situation','lesson','evidence.txt','list_arith')
        self.assertEqual(len(self.x.lookup('list_arith')),1)
        (self.home/'evidence.txt').write_text('changed evidence')
        self.assertEqual(self.x.lookup('list_arith'),[])
        self.assertEqual(self.x.report()['by_status'],{'STALE':1})


    def test_modified_approved_payload_cannot_apply(self):
        out=self.approved()
        modified=dict(out['proposal'])
        modified['diff']={'tool_hint.list_note':NOTE+' Extra.'}
        with self.assertRaises(PermissionError):
            self.h.apply(modified,modified['diff'])
        self.assertEqual(self.h.report()['active'],[])

    def test_revoked_persisted_request_refuses_both_writers(self):
        out=self.approved()
        with self.s.tx() as c:
            c.execute("UPDATE requests SET status='REJECTED' WHERE id=?",
                      (out['proposal']['request_id'],))
        with self.assertRaises(PermissionError):
            self.h.apply(out['proposal'],out['settings'])
        with self.assertRaises(PermissionError):
            self.x.record(out['proposal'],'situation','lesson','evidence.txt','list_arith')


if __name__=='__main__':
    unittest.main()

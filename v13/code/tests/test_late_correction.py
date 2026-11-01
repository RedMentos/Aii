"""WP-AGE0a: late self-correction of an answer the user already got, without the Age-4 right self_initiative.
Default shadow keeps the live behaviour (HELD finding) and only logs what would be said. No models."""
import tempfile
import unittest
from pathlib import Path
from v13.runtime import Runtime
from v13.operator import Operator
from v13 import selfmodel as S
from v13 import neuromod as N
from v13 import age as agectl

OFFER={'role':'B1_DETAIL','offer':{'summary':'The total is 42.5 not 40','needs_reentry':False},'evidence_refs':['src1']}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.op=Operator(self.r)
        self.t=[1000.];self.s=S.SelfSystem(self.r,agectl.controller(self.r),N.Neuromod(self.r.store),clock=lambda:self.t[0])
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def shadow_rows(self):
        return self.r.store.state(S.SHADOW_KEY,[])[0]


class ModeTests(Base):
    def test_default_shadow_keeps_held_finding_and_logs_what_would_be_said(self):
        self.assertEqual(self.s.correction_mode(),'shadow')
        m=self.s.late_offer('e1',OFFER,'The total is 40.')
        self.assertEqual((m['kind'],m['status']),('finding','HELD'))
        rows=self.shadow_rows();self.assertEqual(len(rows),1)
        self.assertIn('Sicherheit: niedrig',rows[0]['would_say']);self.assertIn('42.5',rows[0]['would_say']);self.assertTrue(rows[0]['right_ok'])

    def test_deliver_at_age0_reaches_the_user_with_uncertainty(self):
        said=[];self.r.notice=said.append;self.s.set_correction_mode('deliver')
        self.assertEqual(agectl.controller(self.r).system_stage(),0)
        m=self.s.late_offer('e1',OFFER,'The total is 40.')
        self.assertEqual((m['kind'],m['status']),('correction','DELIVERED'))
        self.assertTrue(said and 'Möglicher Fehler' in said[0] and 'Sicherheit:' in said[0])

    def test_off_is_the_old_path_without_log(self):
        self.s.set_correction_mode('off');m=self.s.late_offer('e1',OFFER,'The total is 40.')
        self.assertEqual((m['kind'],m['status']),('finding','HELD'));self.assertEqual(self.shadow_rows(),[])

    def test_agreeing_offer_gives_no_correction_in_any_mode(self):
        for mode in S.CORRECTION_MODES:
            self.s.set_correction_mode(mode);self.assertIsNone(self.s.late_offer('e1',OFFER,'The total is 42.5, not 40.'))

    def test_certainty_is_medium_only_with_two_independent_signs(self):
        o={'role':'B2_GIST','offer':{'summary':'Budget is 300','needs_reentry':True},'evidence_refs':[]}
        self.assertIn('Sicherheit: mittel',S.SelfSystem.correction_text('B2_GIST','Budget is 300',True,{'300'}))
        self.assertIn('Sicherheit: niedrig',S.SelfSystem.correction_text('B2_GIST','x',True,set()))
        self.s.set_correction_mode('deliver');self.assertEqual(self.s.late_offer('e2',o,'Budget is 200.')['status'],'DELIVERED')


class GateTests(Base):
    def test_deliver_still_obeys_dedup_rate_limit_and_pause(self):
        self.s.set_correction_mode('deliver');self.r.notice=lambda t:None
        self.assertEqual(self.s.late_offer('e1',OFFER,'The total is 40.')['status'],'DELIVERED')
        self.assertEqual(self.s.late_offer('e1',OFFER,'The total is 40.')['status'],'SUPPRESSED_DUPLICATE')
        o2=dict(OFFER,offer={'summary':'The total is 43 not 40','needs_reentry':False})
        self.t[0]+=10;self.assertEqual(self.s.late_offer('e2',o2,'The total is 40.')['status'],'RATE_LIMITED')
        self.op.run(':pause selfedit');self.t[0]+=700
        o3=dict(OFFER,offer={'summary':'The total is 44 not 40','needs_reentry':False})
        self.assertEqual(self.s.late_offer('e3',o3,'The total is 40.')['status'],'HELD')

    def test_late_correction_right_does_not_open_other_self_messages(self):
        self.s.set_correction_mode('deliver')
        self.assertEqual(self.s.message('finding','unrelated idea',.9)['status'],'HELD')
        self.assertFalse(self.s._allowed('self_initiative'));self.assertTrue(self.s._allowed('late_correction'))

    def test_unreadable_mode_falls_back_to_off(self):
        self.r.store.set_state(S.CORRECTION_KEY,'loud');self.assertEqual(self.s.correction_mode(),'off')
        with self.assertRaises(ValueError):self.s.set_correction_mode('loud')

    def test_operator_command(self):
        self.assertIn('"shadow"',self.op.run(':self correction'))
        self.assertIn('"deliver"',self.op.run(':self correction deliver'))
        self.assertEqual(S.controller(self.r).correction_mode(),'deliver')


if __name__=='__main__':unittest.main()

import unittest
from v13.context_append_guard import can_reenter


def previous(applied=False, layout='stable_prefix', seed=True):
    return {'event_id':'e1','system':'SYSTEM','messages':[{'role':'user','content':'q'}],
            'applied':applied,'layout':layout,'append_seed':seed}

LAST=('e1',[{'role':'user','content':'q'},{'role':'assistant','content':'a'}])


class AppendGuard(unittest.TestCase):
    def test_shadow_to_active_refused(self):
        self.assertFalse(can_reenter(previous(False),LAST,'SYSTEM',True))

    def test_active_to_shadow_refused(self):
        self.assertFalse(can_reenter(previous(True),LAST,'SYSTEM',False))

    def test_same_mode_append_allowed(self):
        self.assertTrue(can_reenter(previous(True,'append_only'),LAST,'SYSTEM',True))

    def test_same_mode_stable_prefix_seed_allowed(self):
        self.assertTrue(can_reenter(previous(True,'stable_prefix'),LAST,'SYSTEM',True))

    def test_unqualified_stable_prefix_refused(self):
        self.assertFalse(can_reenter(previous(True,'stable_prefix',False),LAST,'SYSTEM',True))

    def test_legacy_layout_refused(self):
        self.assertFalse(can_reenter(previous(True,'legacy'),LAST,'SYSTEM',True))

    def test_missing_legacy_applied_marker_refused(self):
        p=previous(True);del p['applied']
        self.assertFalse(can_reenter(p,LAST,'SYSTEM',True))

    def test_mismatched_event_refused(self):
        self.assertFalse(can_reenter(previous(True),('e2',LAST[1]),'SYSTEM',True))

    def test_mismatched_system_refused(self):
        self.assertFalse(can_reenter(previous(True),LAST,'OTHER',True))

    def test_last_not_assistant_refused(self):
        self.assertFalse(can_reenter(previous(True),('e1',[{'role':'user','content':'q'}]),'SYSTEM',True))

    def test_no_previous_messages_refused(self):
        p=previous(True);p['messages']=None
        self.assertFalse(can_reenter(p,LAST,'SYSTEM',True))

    def test_none_previous_refused(self):
        self.assertFalse(can_reenter(None,LAST,'SYSTEM',True))


if __name__=='__main__':unittest.main()

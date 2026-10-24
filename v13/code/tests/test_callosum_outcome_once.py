import copy
import unittest
from v13.callosum_outcome_once import apply_once


def m(msg, scored=False):
    return {'msg':msg,'direction':'B1_TO_B2','channel':'SOURCE_EXACT','scored':scored}


class OutcomeOnce(unittest.TestCase):
    def setUp(self):
        self.updates=[]
        self.update=lambda item,utility,parts:self.updates.append((item['msg'],utility,parts))

    def test_single_update(self):
        pending=[m('p1')]
        applied=apply_once(pending,[(m('p1'),.7,{'task_gain':1})],self.update)
        self.assertEqual(applied,[('p1',.7)]);self.assertTrue(pending[0]['scored'])
        self.assertEqual(len(self.updates),1)

    def test_replay_idempotence(self):
        pending=[m('p1')];score=[(m('p1'),.7,{})]
        self.assertEqual(apply_once(pending,score,self.update),[('p1',.7)])
        self.assertEqual(apply_once(pending,score,self.update),[])
        self.assertEqual(len(self.updates),1)

    def test_duplicate_packet_id(self):
        pending=[m('p1'),m('p1')]
        score=[(m('p1'),.7,{}),(m('p1'),.9,{})]
        self.assertEqual(apply_once(pending,score,self.update),[('p1',.7)])
        self.assertEqual(len(self.updates),1)
        self.assertTrue(all(x['scored'] for x in pending))

    def test_only_matching_messages_marked(self):
        pending=[m('p1'),m('p2')]
        apply_once(pending,[(m('p1'),.2,{})],self.update)
        self.assertTrue(pending[0]['scored']);self.assertFalse(pending[1]['scored'])

    def test_missing_pending_noop(self):
        self.assertEqual(apply_once([],[(m('p1'),.2,{})],self.update),[])
        self.assertEqual(self.updates,[])

    def test_stale_precomputed_score_noop(self):
        pending=[m('p1',True)]
        self.assertEqual(apply_once(pending,[(m('p1'),.9,{})],self.update),[])
        self.assertEqual(self.updates,[])

    def test_previous_utility_not_mutated_on_replay(self):
        pending=[m('p1')];q={'v':0.,'n':0}
        def updater(item,u,comp):q['n']+=1;q['v']+=.2*(u-q['v'])
        apply_once(pending,[(m('p1'),1.,{})],updater)
        before=copy.deepcopy(q)
        apply_once(pending,[(m('p1'),0.,{})],updater)
        self.assertEqual(q,before)

    def test_duplicate_with_one_already_scored_repairs_flags_without_update(self):
        pending=[m('p1',True),m('p1')]
        self.assertEqual(apply_once(pending,[(m('p1'),.9,{})],self.update),[])
        self.assertTrue(all(x['scored'] for x in pending))
        self.assertEqual(self.updates,[])

    def test_scored_other_packet_not_reused(self):
        pending=[m('p1',True),m('p2')]
        self.assertEqual(apply_once(pending,[(m('p1'),1.,{}),(m('p2'),.5,{})],self.update),[('p2',.5)])

    def test_empty_scores_no_marks(self):
        pending=[m('p1')]
        self.assertEqual(apply_once(pending,[],self.update),[])
        self.assertFalse(pending[0]['scored'])


if __name__=='__main__':unittest.main()

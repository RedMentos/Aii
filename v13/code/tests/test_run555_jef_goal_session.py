"""Run555: event-backed USER goal auto-completion requires originating session.

Software-only provenance checks; lexical relevance does not prove answer quality.
"""
import json
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.agi import hub, live, operator_command

TOPIC = 'Explain the fictional Project RUN555-ORBIT plan briefly.'


class Run555JefGoalSession(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.s1 = self.r.session
        self.e1 = self.r.store.event(self.s1, TOPIC)
        live.goal_turn(self.r, self.e1, {}, 'ERROR')
        self.gid = hub(self.r).goals.tree('OPEN')[0]['id']

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def reply(self, session=None, text=TOPIC, answer='A delivered answer', status='FINAL', meta=None):
        session = session or self.r.session
        event = self.r.store.event(session, text)
        mid = self.r.store.message(session, event['event_id'], 'assistant', answer)
        self.r.store.finish_message(mid, status, meta or {})
        live.goal_turn(self.r, event, {}, status)
        return event, mid

    def goal(self):
        return hub(self.r).goals.get(self.gid)

    def test_same_session_receipt_closes_and_restart_retains(self):
        e, mid = self.reply()
        self.assertEqual(self.goal()['status'], 'DONE')
        self.assertIn('message '+str(mid), self.goal()['notes'][-1])
        self.r.close()
        self.r = Runtime(self.home)
        self.assertEqual(self.goal()['status'], 'DONE')
        self.assertFalse(self.r.store.integrity(True))

    def test_identical_final_other_session_cannot_close_origin_goal(self):
        s2 = self.r.store.new_session('Other independent chat')
        self.r.session = s2
        self.reply()
        self.assertEqual(self.goal()['status'], 'OPEN')
        self.r.session = self.s1
        self.reply()
        self.assertEqual(self.goal()['status'], 'DONE')

    def test_two_same_title_goals_each_close_only_in_own_session(self):
        s2 = self.r.store.new_session('Second chat')
        self.r.session = s2
        e2 = self.r.store.event(s2, TOPIC)
        live.goal_turn(self.r, e2, {}, 'ERROR')
        other = next(g for g in hub(self.r).goals.tree('OPEN') if g['id'] != self.gid)
        self.reply()
        self.assertEqual(self.goal()['status'], 'OPEN')
        self.assertEqual(hub(self.r).goals.get(other['id'])['status'], 'DONE')

    def test_mixed_and_dangling_event_evidence_fail_closed(self):
        s2 = self.r.store.new_session('Second chat')
        foreign = self.r.store.event(s2, TOPIC)
        for extra in ('event:'+foreign['event_id'], 'event:does_not_exist', 'event:'):
            with self.subTest(extra=extra):
                gs = hub(self.r).goals
                gs.box.mutate(lambda st: st['goals'][self.gid].update(
                    evidence=['event:'+self.e1['event_id'], extra]))
                self.reply()
                self.assertEqual(self.goal()['status'], 'OPEN')

    def test_wrong_runtime_session_does_not_mutate_goals(self):
        s2 = self.r.store.new_session('Other chat')
        self.r.session = s2
        # Calling the hook with an event from A while Runtime points at B
        # must not create a second unresolved goal or close the first.
        before = [(g['id'],g['status']) for g in hub(self.r).goals.tree()]
        live.goal_turn(self.r, self.e1, {}, 'ERROR')
        self.assertEqual(before, [(g['id'],g['status']) for g in hub(self.r).goals.tree()])

    def test_manual_user_operator_completion_remains_global(self):
        self.r.session = self.r.store.new_session('Operator chat')
        result = json.loads(operator_command(self.r, ['goal','done',self.gid]))
        self.assertEqual(result['status'], 'DONE')
        self.assertEqual(json.loads(operator_command(self.r, ['goal','reopen',self.gid]))['status'], 'OPEN')
        self.assertEqual(self.goal()['progress'], 0.)

    def test_reference_only_nonfinal_and_unrelated_remain_open(self):
        self.reply(answer='Teacher answer', meta={'reference_only':True})
        self.assertEqual(self.goal()['status'], 'OPEN')
        self.reply(status='ERROR')
        self.assertEqual(self.goal()['status'], 'OPEN')
        self.reply(text='How is the weather today?')
        self.assertEqual(self.goal()['status'], 'OPEN')


if __name__ == '__main__':
    unittest.main()

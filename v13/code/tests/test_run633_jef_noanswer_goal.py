"""Run633: explicit no-answer/abstention is not a JEF USER goal completion receipt.

Model-free SQLite integration. This does not prove semantic task success.
"""
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.agi import hub, live, operator_command

TOPIC = 'Plan the fictional Aurora budget for May'
FOLLOWUP = 'Plan the fictional Aurora budget for May please'


class Run633GoalNoAnswer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.first = self.r.store.event(self.r.session, TOPIC)
        live.goal_turn(self.r, self.first, {}, 'ERROR')
        self.gid = hub(self.r).goals.tree('OPEN')[0]['id']

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def goal(self):
        return hub(self.r).goals.get(self.gid)

    def reply(self, answer, metadata=None, turn_metadata=None):
        e = self.r.store.event(self.r.session, FOLLOWUP)
        mid = self.r.store.message(self.r.session, e['event_id'], 'assistant', answer)
        self.r.store.finish_message(mid, 'FINAL', metadata or {})
        live.goal_turn(self.r, e, turn_metadata or {}, 'FINAL')
        return mid

    def test_explicit_no_answer_variants_cannot_close_goal(self):
        replies = (
            "I don't know.",
            "I don’t know the answer.",
            "Sorry, I can't answer this.",
            "I cannot answer that question.",
            "I'm not sure.",
            "Not enough information to answer.",
            "No answer available.",
            "Unknown.",
            "Ich weiß es nicht.",
            "Leider, ich weiss es nicht.",
            "Keine Ahnung.",
            "Das weiß ich nicht.",
            "Ich kann die Frage nicht beantworten.",
            "Unbekannt.",
        )
        for reply in replies:
            with self.subTest(reply=reply):
                self.reply(reply)
                self.assertEqual(self.goal()['status'], 'OPEN')

    def test_explicit_abstention_metadata_on_persisted_final_is_authoritative(self):
        self.reply('Aurora budget: 100 units.', metadata={'metacog_abstain': True})
        self.assertEqual(self.goal()['status'], 'OPEN')

    def test_current_turn_abstention_does_not_close_without_persisted_flag(self):
        self.reply('Aurora budget: 100 units.', turn_metadata={'metacog_abstain': True})
        self.assertEqual(self.goal()['status'], 'OPEN')

    def test_mid_answer_quote_does_not_trigger_leading_refusal_guard(self):
        self.reply('Aurora budget: 100 units. The note says "I don\'t know" but this is a quotation.')
        self.assertEqual(self.goal()['status'], 'DONE')

    def test_normal_same_session_final_receipt_and_restart_still_work(self):
        mid = self.reply('Aurora budget plan: allocate 100 units to May.')
        self.assertEqual(self.goal()['status'], 'DONE')
        self.assertIn('message ' + str(mid), self.goal()['notes'][-1])
        self.r.close()
        self.r = Runtime(self.home)
        self.assertEqual(self.goal()['status'], 'DONE')

    def test_explicit_user_goal_completion_still_available_after_abstention(self):
        self.reply("I don't know.")
        self.assertEqual(self.goal()['status'], 'OPEN')
        result = operator_command(self.r, ['goal', 'done', self.gid])
        self.assertIn('"DONE"', result)
        self.assertEqual(self.goal()['status'], 'DONE')


if __name__ == '__main__':
    unittest.main()

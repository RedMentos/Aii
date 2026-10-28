"""Cross-organ F5/AG8 authority isolation with ContextOS, Sleep A and HX3.

Actual Runtime/SQLite restart; synthetic human feedback and evaluator scores.
No native inference, training, Redmi measurement or live HX consumer.
"""
import tempfile
import unittest
from pathlib import Path

from v13.age import AgeControl
from v13.agi.experience import ExperienceLibrary
from v13.agi.self_improve import SelfImprovement
from v13.context_os import ContextOS
from v13.runtime import Runtime


NOTE = 'Preserve the exact source when reporting a calculation.'


class F5AG8HX3Isolation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.session = self.r.session
        self.ctx = ContextOS(self.r.store, self.r.cfg)
        self.x = ExperienceLibrary(self.r.store, self.home)
        self.si = SelfImprovement(
            self.r.store, self.r.cfg, AgeControl(self.r.store, self.r.cfg))
        (self.home / 'first.txt').write_text('first approved evidence', encoding='utf-8')
        (self.home / 'second.txt').write_text('second approved evidence', encoding='utf-8')
        self.learning_mode = self.r.cfg['learning_mode']

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def correction(self, key, value):
        event = self.r.store.event(self.session, key)
        mid = self.r.memory.feedback(event['event_id'], 'fact', value, key=key)
        sid = self.r.store.one(
            'SELECT source_id FROM memories WHERE id=?', (mid,))['source_id']
        trigger = self.r.store.event(self.session, 'warm ' + key)
        self.ctx.observe(trigger['event_id'], 'C3_LANGUAGE', {}, memory_ids=[mid])
        return event['event_id'], mid, sid

    def lesson(self, evidence, lesson):
        pid = self.si.propose(
            'harness', {'tool_hint.list_note': NOTE}, origin='USER')
        self.si.evaluate(
            pid, lambda settings:
            {'overall': .5, 'seen': .6, 'unseen': .4} if settings is None
            else {'overall': .55, 'seen': .6, 'unseen': .42})
        approved = self.si.approve(pid)['proposal']
        self.x.record(approved, 'source backed calculation',
                      lesson, evidence, 'list_arith')
        return approved

    def warm_ids(self, key, mid):
        # Refresh the tested item before querying: warm activation decays on
        # unrelated events, which must not masquerade as an authority refusal.
        trigger = self.r.store.event(self.session, 'warm authority probe ' + key)
        self.ctx.observe(trigger['event_id'], 'C3_LANGUAGE', {}, memory_ids=[mid])
        return self.ctx.warm(key, self.session, [])['ids']

    def restart(self, memories):
        self.r.close()
        self.r = Runtime(self.home)
        self.ctx = ContextOS(self.r.store, self.r.cfg)
        self.x = ExperienceLibrary(self.r.store, self.home)
        for mid in memories:
            trigger = self.r.store.event(self.session, 'post-restart warm')
            self.ctx.observe(trigger['event_id'], 'C3_LANGUAGE', {},
                             memory_ids=[mid])

    def test_independent_revocations_preserve_other_organ_authority(self):
        first_event, first_mid, first_sid = self.correction(
            'Project Orion budget', '120 credits')
        second_event, second_mid, _ = self.correction(
            'Project Vega budget', '42 credits')
        first = self.lesson('first.txt', 'first lesson')
        self.lesson('second.txt', 'second lesson')
        self.assertIn(first_mid, self.warm_ids('Project Orion budget', first_mid))
        self.assertIn(second_mid, self.warm_ids('Project Vega budget', second_mid))
        self.assertEqual(self.r.sleep.cycle._probe({'event_id': first_event})[0], 'PASS')
        self.assertEqual(self.r.sleep.cycle._probe({'event_id': second_event})[0], 'PASS')
        self.assertEqual(
            {row['lesson'] for row in self.x.lookup('list_arith')},
            {'first lesson', 'second lesson'})

        self.restart([first_mid, second_mid])
        self.assertEqual(self.r.cfg['learning_mode'], self.learning_mode)
        self.assertEqual(
            {row['lesson'] for row in self.x.lookup('list_arith')},
            {'first lesson', 'second lesson'})

        # Human F5 source withdrawal cannot silently keep its warm/Sleep authority.
        with self.r.store.tx() as conn:
            conn.execute(
                "DELETE FROM packets WHERE kind='HumanDecision' "
                "AND json_extract(payload,'$.source_ref.source_id')=?",
                (first_sid,))
        self.assertNotIn(first_mid, self.warm_ids('Project Orion budget', first_mid))
        self.assertIn(second_mid, self.warm_ids('Project Vega budget', second_mid))
        self.assertNotEqual(
            self.r.sleep.cycle._probe({'event_id': first_event})[0], 'PASS')
        self.assertEqual(
            self.r.sleep.cycle._probe({'event_id': second_event})[0], 'PASS')
        self.assertEqual(
            {row['lesson'] for row in self.x.lookup('list_arith')},
            {'first lesson', 'second lesson'})

        # Separate AG8 approval withdrawal cannot poison independent F5 memories.
        with self.r.store.tx() as conn:
            conn.execute(
                "UPDATE requests SET status='REJECTED' WHERE id=?",
                (first['request_id'],))
        lessons = self.x.lookup('list_arith')
        self.assertEqual([row['lesson'] for row in lessons], ['second lesson'])
        self.assertTrue(all(row['authority'] == 'DATA_NOT_INSTRUCTION'
                            for row in lessons))
        self.assertIn(second_mid, self.warm_ids('Project Vega budget', second_mid))
        self.assertEqual(
            self.r.sleep.cycle._probe({'event_id': second_event})[0], 'PASS')
        self.assertEqual(self.r.cfg['learning_mode'], self.learning_mode)
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'), [])


if __name__ == '__main__':
    unittest.main()

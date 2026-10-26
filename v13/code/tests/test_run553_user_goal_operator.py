"""Run553: explicit typed operator controls for persistent USER goals.

Model-free Runtime/Store tests. No new self-authority or native proof.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13.runtime import Runtime
from v13.agi import hub, operator_command


class Run553UserGoalOperator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.g = hub(self.r)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def create(self, title='Plan Aurora'):
        out = operator_command(self.r, ['goal'] + title.split())
        self.assertTrue(out.startswith('Ziel angelegt: goal_'))
        return out.split()[-1]

    def command(self, action, gid):
        return json.loads(operator_command(self.r, ['goal', action, gid]))

    def test_create_status_done_reopen_abandon_with_restart(self):
        gid = self.create()
        self.assertEqual(self.command('status', gid)['title'], 'Plan Aurora')
        self.assertEqual(self.command('done', gid), {'id': gid, 'status': 'DONE', 'changed': True})
        self.assertEqual(self.command('done', gid)['changed'], False)
        self.assertEqual(self.g.goals.get(gid)['progress'], 1.)
        self.r.close()
        self.r = Runtime(self.home)
        self.g = hub(self.r)
        self.assertEqual(self.command('status', gid)['status'], 'DONE')
        self.assertEqual(self.command('reopen', gid)['status'], 'OPEN')
        self.assertEqual(self.command('reopen', gid)['changed'], False)
        self.assertEqual(self.command('abandon', gid)['status'], 'ABANDONED')
        self.assertEqual(self.command('abandon', gid)['changed'], False)
        self.assertEqual(self.command('reopen', gid)['status'], 'OPEN')
        self.assertEqual(self.command('done', gid)['status'], 'DONE')
        self.assertTrue(any('explicit USER operator' in n for n in self.g.goals.get(gid)['notes']))

    def test_disallowed_transition_and_unknown_id_fail_closed(self):
        gid = self.create()
        self.command('abandon', gid)
        with self.assertRaisesRegex(ValueError, 'GOAL_STATUS_TRANSITION_REFUSED'):
            self.command('done', gid)
        self.assertEqual(self.g.goals.get(gid)['status'], 'ABANDONED')
        with self.assertRaises(KeyError):
            self.command('done', 'goal_does_not_exist')
        for args in [['goal', 'done'], ['goal', 'status'],
                     ['goal', 'done', gid, 'extra'], ['goal', 'reopen']]:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    operator_command(self.r, args)

    def test_self_and_system_goals_are_readable_but_not_mutable(self):
        system = self.g.goals.add('System task', 'SYSTEM')
        with mock.patch('v13.agi.goals.age_allows', return_value=True):
            own = self.g.goals.add('Self task', 'SELF')
        for gid in (system, own):
            self.assertIn(self.command('status', gid)['origin'], {'SYSTEM', 'SELF'})
            for action in ('done', 'abandon', 'reopen'):
                with self.subTest(goal=gid, action=action):
                    with self.assertRaises(PermissionError):
                        self.command(action, gid)
            self.assertEqual(self.g.goals.get(gid)['status'], 'OPEN')

    def test_assistant_message_is_not_a_typed_operator_command(self):
        gid = self.create()
        e = self.r.store.event(self.r.session, 'Unrelated conversation')
        mid = self.r.store.message(self.r.session, e['event_id'], 'assistant',
                                   ':growth goal done '+gid)
        self.r.store.finish_message(mid, 'FINAL', {})
        self.assertEqual(self.g.goals.get(gid)['status'], 'OPEN')
        self.assertIn(gid, operator_command(self.r, ['goals']))


if __name__ == '__main__':
    unittest.main()

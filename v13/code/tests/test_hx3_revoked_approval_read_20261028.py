"""HX3 read-side human approval revocation across restart (actual Runtime/SQLite).

Synthetic evidence and AG8 evaluator; no live HX consumer, native inference or learning.
"""
import tempfile
import unittest
from pathlib import Path

from v13.age import AgeControl
from v13.agi.experience import ExperienceLibrary
from v13.agi.self_improve import SelfImprovement
from v13.runtime import Runtime


NOTE = 'Always preserve the exact source when reporting a calculation.'


class HX3RevokedApprovalRead(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.si = SelfImprovement(
            self.r.store, self.r.cfg, AgeControl(self.r.store, self.r.cfg))
        self.x = ExperienceLibrary(self.r.store, self.home)
        (self.home / 'one.txt').write_text('first source', encoding='utf-8')
        (self.home / 'two.txt').write_text('second source', encoding='utf-8')

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def approved(self):
        pid = self.si.propose(
            'harness', {'tool_hint.list_note': NOTE}, origin='USER')
        self.si.evaluate(
            pid, lambda settings: {'overall': .5, 'seen': .6, 'unseen': .4}
            if settings is None else {'overall': .55, 'seen': .6, 'unseen': .42})
        return self.si.approve(pid)['proposal']

    def seed(self):
        first = self.approved()
        second = self.approved()
        self.x.record(first, 'first situation', 'first lesson',
                      'one.txt', 'list_arith')
        self.x.record(second, 'second situation', 'second lesson',
                      'two.txt', 'list_arith')
        self.assertEqual(
            {r['lesson'] for r in self.x.lookup('list_arith')},
            {'first lesson', 'second lesson'})
        return first, second

    def restart(self):
        self.r.close()
        self.r = Runtime(self.home)
        self.x = ExperienceLibrary(self.r.store, self.home)

    def test_revoked_request_excludes_only_its_persisted_lesson(self):
        first, second = self.seed()
        self.restart()
        with self.r.store.tx() as conn:
            conn.execute("UPDATE requests SET status='REJECTED' WHERE id=?",
                         (first['request_id'],))
        lessons = self.x.lookup('list_arith')
        self.assertEqual([x['lesson'] for x in lessons], ['second lesson'])
        self.assertTrue(all(x['authority'] == 'DATA_NOT_INSTRUCTION'
                            for x in lessons))
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'), [])

    def test_both_independently_valid_lessons_survive_restart(self):
        self.seed()
        self.restart()
        self.assertEqual(
            {r['lesson'] for r in self.x.lookup('list_arith')},
            {'first lesson', 'second lesson'})
        self.assertEqual(self.r.store.rows('SELECT * FROM updates'), [])


if __name__ == '__main__':
    unittest.main()

"""Run532: local read-only Age0d arithmetic shadow diagnostic command."""
import json
import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.operator import Operator
from v13.selfmodel import ARITH_SHADOW_KEY


class ReadOnlyArithmeticOperator(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.r = Runtime(Path(self.temp.name))
        self.addCleanup(self.r.close)
        self.op = Operator(self.r)

    def test_empty_and_help(self):
        data = json.loads(self.op.run(':self arithmetic'))
        self.assertEqual((data['status'], data['total'], data['recent']),
                         ('SHADOW_ONLY', 0, []))
        self.assertFalse(data['learning_authorized'])
        self.assertIn('arithmetic', self.op.run(':help'))

    def test_last_eight_only_and_no_state_write(self):
        rows = [{'event_id': f'evt{i}', 'status': 'MISMATCH_SHADOW_ONLY'}
                for i in range(12)]
        self.r.store.set_state(ARITH_SHADOW_KEY, rows)
        before, version = self.r.store.state(ARITH_SHADOW_KEY, [])
        data = json.loads(self.op.run(':self arithmetic'))
        after, new_version = self.r.store.state(ARITH_SHADOW_KEY, [])
        self.assertEqual((data['total'], data['recent']), (12, rows[-8:]))
        self.assertEqual((after, new_version), (before, version))
        self.assertFalse(data['user_notified'])
        self.assertFalse(data['age_reopen_authorized'])

    def test_non_operator_cannot_read(self):
        with self.assertRaisesRegex(ValueError, 'Nur lokale Operator'):
            self.op.run(':self arithmetic', origin='API')

    def test_corrupt_state_fails_closed(self):
        self.r.store.set_state(ARITH_SHADOW_KEY, {'not': 'list'})
        with self.assertRaisesRegex(ValueError, 'invalid'):
            self.op.run(':self arithmetic')

    def test_other_self_command_unchanged(self):
        data = json.loads(self.op.run(':self correction'))
        self.assertIn('mode', data)
        self.assertNotIn('recent', data)


if __name__ == '__main__':
    unittest.main()

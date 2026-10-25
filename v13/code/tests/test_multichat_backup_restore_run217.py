"""Run217: real Runtime+Operator multi-chat backup/restore journey.

Deterministic C3 seam, actual SQLite, source-backed session memory and offline
restore. Software only; no native model, Redmi, training or gate promotion.
"""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from v13.backup import restore
from v13.operator import Operator
from v13.runtime import Runtime


class MultiChatBackupRestoreRun217(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.wire()

    def tearDown(self):
        if self.r is not None:
            self.r.close()
        self.tmp.cleanup()

    def wire(self):
        self.op = Operator(self.r)
        self.op.run(':observers off')
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.cfg.update(route_override='simple', history_turns=0)
        fake = SimpleNamespace(
            role='C3_LANGUAGE', last_metrics={'test_seam': True},
            generate=lambda messages, *args, **kwargs: iter(['RUN217_FAKE_C3']),
        )
        self.r.pool.get = Mock(return_value=fake)
        self.r.learner.output_delta = Mock(return_value=None)

    def ask(self, text):
        eid = self.op.run(text)
        deadline = time.monotonic() + 20
        while not self.r.idle() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(self.r.idle(), 'Runtime test turn did not finish')
        row = self.r.last_answer()
        self.assertEqual(row['event_id'], eid)
        self.assertEqual(row['status'], 'FINAL', row)
        self.assertEqual(row['text'], 'RUN217_FAKE_C3')
        return eid

    def restart(self):
        if self.r is not None:
            self.r.close()
        self.r = Runtime(self.home)
        self.wire()

    def test_two_chat_operator_exports_and_session_memory_survive_offline_restore(self):
        a = self.r.session
        ae = self.ask('RUN217_ALPHA original')
        mid = self.r.memory.feedback(ae, 'fact', 'RUN217_ALPHA_VALUE',
                                     key='RUN217_ALPHA_KEY', scope='session')
        b = self.op.run(':new')
        self.ask('RUN217_BETA original')
        self.assertEqual(self.r.memory.recall('RUN217_ALPHA_KEY', b), [])
        snapshot = Path(self.op.run(':backup'))
        self.assertTrue(snapshot.is_file())

        # A third chat and its data were created AFTER the snapshot.
        c = self.op.run(':new')
        self.ask('RUN217_GAMMA post-snapshot')
        self.assertIn(c, {row['id'] for row in json.loads(self.op.run(':chats'))})
        self.r.close()
        self.r = None
        safety = restore(self.home, snapshot)
        self.assertTrue(safety.is_file())
        self.restart()

        self.assertEqual(self.r.session, b)
        chats = {row['id'] for row in json.loads(self.op.run(':chats'))}
        self.assertIn(a, chats)
        self.assertIn(b, chats)
        self.assertNotIn(c, chats)
        self.assertEqual(json.loads(self.op.run(':search RUN217_GAMMA')), [])
        self.assertEqual(self.r.memory.recall('RUN217_ALPHA_KEY', b), [])
        self.assertEqual(self.op.run(':open ' + a), a)
        self.assertEqual([m['id'] for m in self.r.memory.recall('RUN217_ALPHA_KEY', a)], [mid])
        export_a = json.loads(Path(self.op.run(':export chat json')).read_text())
        self.assertIn('RUN217_ALPHA original', json.dumps(export_a))
        self.assertNotIn('RUN217_BETA original', json.dumps(export_a))
        self.assertNotIn('RUN217_GAMMA', json.dumps(export_a))
        self.assertEqual(self.op.run(':open ' + b), b)
        export_b = json.loads(Path(self.op.run(':export chat json')).read_text())
        self.assertIn('RUN217_BETA original', json.dumps(export_b))
        self.assertNotIn('RUN217_ALPHA original', json.dumps(export_b))
        self.assertEqual(self.r.cfg['learning_mode'], 'RECORD_ONLY')
        self.assertFalse((self.home/'restore_pending.json').exists())

    def test_backup_restores_selected_chat_and_exact_export_after_restart(self):
        a = self.r.session
        self.ask('RUN217_PERSISTED first')
        b = self.op.run(':new')
        self.ask('RUN217_PERSISTED second')
        self.op.run(':open ' + a)
        original_a = Path(self.op.run(':export chat json')).read_bytes()
        self.op.run(':open ' + b)
        original_b = Path(self.op.run(':export chat json')).read_bytes()
        snapshot = Path(self.op.run(':backup'))
        self.r.close()
        self.r = None
        restore(self.home, snapshot)
        self.restart()
        self.assertEqual(self.r.session, b)
        self.op.run(':open ' + a)
        self.assertEqual(Path(self.op.run(':export chat json')).read_bytes(), original_a)
        self.op.run(':open ' + b)
        self.assertEqual(Path(self.op.run(':export chat json')).read_bytes(), original_b)


if __name__ == '__main__':
    unittest.main()

"""Run214: actual Runtime/Operator multi-chat persistence and export journey.

Uses a deterministic C3 test double. Software integration only: no native model,
Redmi, JEPA learning, new authority, or acceptance-gate promotion.
"""
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from v13.operator import Operator
from v13.runtime import Runtime


class ChatOperatorPersistenceRun214(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.wire()

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def wire(self):
        self.op = Operator(self.r)
        self.op.run(':observers off')
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.cfg.update(route_override='simple', history_turns=0)
        fake = SimpleNamespace(
            role='C3_LANGUAGE',
            last_metrics={'test_seam': True},
            generate=lambda messages, *args, **kwargs: iter(['RUN214_FAKE_C3_REPLY']),
        )
        self.r.pool.get = Mock(return_value=fake)
        self.r.learner.output_delta = Mock(return_value=None)

    def ask(self, text):
        eid = self.op.run(text)
        deadline = time.monotonic() + 20
        while not self.r.idle() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(self.r.idle(), 'Runtime did not finish test turn')
        row = self.r.last_answer()
        self.assertIsNotNone(row)
        self.assertEqual(row['event_id'], eid)
        self.assertEqual(row['status'], 'FINAL', row)
        self.assertEqual(row['text'], 'RUN214_FAKE_C3_REPLY')
        return eid

    def restart(self):
        self.r.close()
        self.r = Runtime(self.home)
        self.wire()

    def test_multichat_roundtrip_and_separate_json_exports_after_restart(self):
        a = self.r.session
        ae = self.ask('RUN214_ALPHA question')
        b = self.op.run(':new')
        self.assertNotEqual(a, b)
        be = self.ask('RUN214_BETA question')
        chats = json.loads(self.op.run(':chats'))
        self.assertTrue({a, b}.issubset({row['id'] for row in chats}))
        self.assertEqual(self.r.session, b)

        self.restart()
        self.assertEqual(self.r.session, b)
        self.assertEqual(self.op.run(':open ' + a), a)
        self.assertEqual(self.r.session, a)
        history_a = json.loads(Path(self.op.run(':export chat json')).read_text())
        self.assertEqual([x['event_id'] for x in history_a if x['role'] == 'user'], [ae])
        self.assertIn('RUN214_ALPHA question', json.dumps(history_a))
        self.assertNotIn('RUN214_BETA question', json.dumps(history_a))

        self.assertEqual(self.op.run(':open ' + b), b)
        history_b = json.loads(Path(self.op.run(':export chat json')).read_text())
        self.assertEqual([x['event_id'] for x in history_b if x['role'] == 'user'], [be])
        self.assertIn('RUN214_BETA question', json.dumps(history_b))
        self.assertNotIn('RUN214_ALPHA question', json.dumps(history_b))
        self.assertEqual(self.r.cfg['learning_mode'], 'RECORD_ONLY')

    def test_literal_search_across_chats_after_restart(self):
        self.ask('RUN214 needle_42 and 100%')
        a = self.r.session
        b = self.op.run(':new')
        self.ask('RUN214 needleX42 and 100 percent')
        self.restart()
        results = json.loads(self.op.run(':search needle_42'))
        self.assertEqual([x['session_id'] for x in results if x['role'] == 'user'], [a])
        results = json.loads(self.op.run(':search 100%'))
        self.assertEqual([x['session_id'] for x in results if x['role'] == 'user'], [a])
        self.assertEqual(self.r.session, b)

    def test_invalid_open_does_not_change_selected_chat_or_export(self):
        a = self.r.session
        self.ask('RUN214_KEEP_SELECTED')
        with self.assertRaises(ValueError):
            self.op.run(':open chat_nonexistent_run214')
        self.assertEqual(self.r.session, a)
        exported = json.loads(Path(self.op.run(':export chat json')).read_text())
        self.assertIn('RUN214_KEEP_SELECTED', json.dumps(exported))


if __name__ == '__main__':
    unittest.main()

"""Run443: real Age-0 offline chat -> human correction -> restart -> revoke/export.

No installed models, no downloads, no simulated model answer. Tests the real
SQLite state path and deliberately expects a source-bound ERROR abstention.
"""
import json
import tempfile
import time
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.operator import Operator
from v13.verification import doctor


class Run443OfflineHumanMemoryLifecycle(unittest.TestCase):
    def test_missing_model_abstention_human_memory_and_forget_after_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            r = Runtime(home)
            session = r.session
            try:
                r.cfg['observer_mode'] = 'off'
                eid = r.submit('What is my chosen offline color?')
                end = time.monotonic() + 12
                while not r.idle() and time.monotonic() < end:
                    time.sleep(.02)
                self.assertTrue(r.idle(), 'model-free request failed to finish')
                answer = r.last_answer()
                self.assertEqual(answer['event_id'], eid)
                self.assertEqual(answer['status'], 'ERROR')
                self.assertIn('Modell fehlt', answer['text'])
                op = Operator(r)
                generation = r.store.generation_id
                mid = op.run(':remember Chosen offline color | saffron-owl-993')
                self.assertTrue(mid.startswith('mem_'))
                memories = json.loads(op.run(':memory'))
                self.assertEqual([(m['key_text'], m['value']) for m in memories],
                                 [('Chosen offline color', 'saffron-owl-993')])
                self.assertEqual(r.store.generation_id, generation)
                self.assertEqual(r.store.one('SELECT permission FROM feedback WHERE event_id=?', (eid,))['permission'], 'record')
                self.assertTrue(any(row['id'] == session for row in json.loads(op.run(':chats'))))
                self.assertTrue(any('chosen offline color' in row['text'].lower()
                                    for row in json.loads(op.run(':search chosen offline color'))))
                chat_export = Path(op.run(':export chat json'))
                self.assertIn('What is my chosen offline color?', chat_export.read_text())
                new_session = op.run(':new')
                self.assertNotEqual(new_session, session)
                self.assertEqual(json.loads(op.run(':memory')), [])
                op.run(':open ' + session)
                self.assertEqual(json.loads(op.run(':memory'))[0]['id'], mid)
                self.assertEqual(doctor(r, False)['data_integrity_errors'], [])
            finally:
                r.close()
            r = Runtime(home)
            try:
                op = Operator(r)
                self.assertEqual(r.session, session)
                self.assertEqual(json.loads(op.run(':memory'))[0]['id'], mid)
                self.assertIn('gelöscht', op.run(':forget ' + mid + ' --confirm'))
                self.assertEqual(json.loads(op.run(':memory')), [])
                exported = json.loads(op.run(':export dataset session'))
                data = Path(exported['dataset']).read_text()
                self.assertEqual(exported['records'], 1)
                self.assertNotIn('saffron-owl-993', data)
                self.assertEqual(doctor(r, False)['data_integrity_errors'], [])
                self.assertEqual(r.store.generation_id, generation)
            finally:
                r.close()


if __name__ == '__main__':
    unittest.main()

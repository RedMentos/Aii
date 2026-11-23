"""F1/F5 semantic cache revocation while a slow embedding encoder is in flight.

Real SQLite Store and synthetic deterministic embeddings only. No model/native/Redmi proof.
"""
import tempfile
import threading
import time
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.semantic_memory import SemanticKeys, status
from tests.test_semantic_memory import Fake


class CallbackEncoder(Fake):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.fired = False

    def __call__(self, texts, cancel, deadline):
        if not self.fired:
            self.fired = True
            self.callback()
        return super().__call__(texts, cancel, deadline)


class ForgetDuringEncoder(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.temp.name))
        self.r.cfg['memory_embedding'] = 'on'
        self.keys = SemanticKeys(self.r.store, self.r.cfg, Fake())
        self.r.memory.semantic_keys = self.keys

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def remember(self, key='What is the budget of Project Alpha?', value='120 Euro'):
        event = self.r.store.event(self.r.session, key)
        return self.r.memory.feedback(event['event_id'], 'fact', value, key=key)

    def row(self, mid):
        return dict(self.r.store.one('SELECT * FROM memories WHERE id=?', (mid,)))

    def query(self, text='What is the budget of Project Alpha?'):
        return self.r.memory.recall(text, self.r.session, cancel=threading.Event())

    def similarities(self, rows):
        return self.keys.similarities(
            'What is the budget of Project Alpha?', rows,
            threading.Event(), time.monotonic() + 30)

    def test_forget_during_new_key_encode_never_resurrects_cache_or_answer(self):
        mid = self.remember()
        self.keys.encoder = CallbackEncoder(lambda: self.r.memory.forget(mid))
        self.assertEqual(self.query(), [])
        self.assertEqual(status(self.r)['cached_keys'], 0)
        self.assertIsNone(self.keys.last_query)
        self.assertEqual(self.keys.last['revoked_rows'], 1)

    def test_forget_during_cached_query_encode_filters_stale_cached_vector(self):
        mid = self.remember()
        row = self.row(mid)
        self.assertIn(mid, self.similarities([row]))
        self.assertEqual(status(self.r)['cached_keys'], 1)
        self.keys.encoder = CallbackEncoder(lambda: self.r.memory.forget(mid))
        self.assertEqual(self.similarities([row]), {})
        self.assertEqual(status(self.r)['cached_keys'], 0)
        self.assertIsNone(self.keys.last_query)

    def test_direct_stale_row_after_forget_is_never_cached(self):
        mid = self.remember()
        row = self.row(mid)
        self.r.memory.forget(mid)
        self.assertEqual(self.similarities([row]), {})
        self.assertEqual(status(self.r)['cached_keys'], 0)
        self.assertIsNone(self.keys.last_query)

    def test_batch_keeps_live_row_but_not_revoked_row(self):
        gone = self.remember()
        keep = self.remember('What is the budget of Project Beta?', '80 Euro')
        rows = [self.row(gone), self.row(keep)]
        self.keys.encoder = CallbackEncoder(lambda: self.r.memory.forget(gone))
        got = self.similarities(rows)
        self.assertEqual(set(got), {keep})
        self.assertEqual(status(self.r)['cached_keys'], 1)
        self.assertIsNotNone(self.keys.last_query)

    def test_live_source_corruption_after_encoder_still_fails_closed(self):
        mid = self.remember()
        row = self.row(mid)
        source = self.r.store.one('SELECT hash FROM sources WHERE id=?', (row['source_id'],))
        path = self.r.home / 'data/blobs' / source['hash']
        self.assertTrue(path.is_file())
        self.keys.encoder = CallbackEncoder(lambda: path.write_bytes(b'wrong'))
        with self.assertRaises(ValueError):
            self.query()
        self.assertEqual(self.r.store.one('SELECT deleted FROM sources WHERE id=?',
                                          (row['source_id'],))['deleted'], 0)


if __name__ == '__main__':
    unittest.main()

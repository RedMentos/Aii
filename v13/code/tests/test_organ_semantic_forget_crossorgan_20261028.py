"""Cross-organ Age0: organ restore cannot resurrect F1/F5 forgotten sources or embeddings.

Real Store SQLite + synthetic fake encoder, no model inference or native device evidence.
"""
import threading
import unittest

from tests.test_organ import Base
from tests.test_semantic_memory import Fake
from v13 import organ
from v13.semantic_memory import SemanticKeys, status


class PausedEncoder(Fake):
    def __init__(self):
        super().__init__()
        self.entered = threading.Event()
        self.release = threading.Event()

    def __call__(self, texts, cancel, deadline):
        self.entered.set()
        if not self.release.wait(8):
            raise RuntimeError('Timed out waiting for test forget interleaving')
        return super().__call__(texts, cancel, deadline)


class OrganSemanticForgetCrossOrgan(Base):
    QUESTION = 'What is the budget of Project Alpha?'

    def active(self, name):
        entry = self.r.store.components()[name]
        return (self.r.home / entry['path']).read_bytes()

    def remember(self):
        event = self.r.store.event(self.r.session, self.QUESTION)
        return self.r.memory.feedback(event['event_id'], 'fact', '120 Euro',
                                      key=self.QUESTION)

    def attach(self, encoder):
        self.r.cfg['memory_embedding'] = 'on'
        self.keys = SemanticKeys(self.r.store, self.r.cfg, encoder)
        self.r.memory.semantic_keys = self.keys

    def recall(self):
        return self.r.memory.recall(self.QUESTION, self.r.session,
                                    cancel=threading.Event())

    def test_restoring_b1_component_never_restores_forgotten_memory(self):
        self.put('b1_predictor', 'B1_DETAIL', b'b1-good')
        saved_hash = self.active('b1_predictor')
        snapshot = organ.snapshot(self.r, 'B1_DETAIL')
        mid = self.remember()
        self.attach(Fake())
        self.assertEqual([m['id'] for m in self.recall()], [mid])
        self.assertEqual(status(self.r)['cached_keys'], 1)

        self.r.memory.forget(mid)
        self.assertEqual(status(self.r)['cached_keys'], 0)
        self.put('b1_predictor', 'B1_DETAIL', b'b1-newer')
        self.assertNotEqual(self.active('b1_predictor'), saved_hash)
        result = organ.restore(self.r, snapshot['id'])
        self.assertEqual(result['status'], 'RESTORED')
        self.assertEqual(self.active('b1_predictor'), saved_hash)
        self.r.store.validate_artifacts(self.r.store.generation())

        row = self.r.store.one('SELECT active,source_id FROM memories WHERE id=?', (mid,))
        self.assertEqual(row['active'], 0)
        self.assertEqual(self.r.store.one('SELECT deleted FROM sources WHERE id=?',
                                          (row['source_id'],))['deleted'], 1)
        self.assertEqual(self.recall(), [])
        self.assertEqual(status(self.r)['cached_keys'], 0)
        self.assertIsNone(self.keys.last_query)

    def test_actual_threaded_forget_during_encoder_does_not_resurrect(self):
        mid = self.remember()
        encoder = PausedEncoder()
        self.attach(encoder)
        outcome = {}

        def worker():
            try:
                outcome['memories'] = self.recall()
            except Exception as exc:
                outcome['error'] = type(exc).__name__ + ': ' + str(exc)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        try:
            self.assertTrue(encoder.entered.wait(5), 'encoder did not start')
            self.r.memory.forget(mid)
        finally:
            encoder.release.set()
            thread.join(8)
        self.assertFalse(thread.is_alive(), 'recall thread did not finish')
        self.assertNotIn('error', outcome, outcome.get('error'))
        self.assertEqual(outcome.get('memories'), [])
        self.assertEqual(status(self.r)['cached_keys'], 0)
        self.assertIsNone(self.keys.last_query)


if __name__ == '__main__':
    unittest.main()

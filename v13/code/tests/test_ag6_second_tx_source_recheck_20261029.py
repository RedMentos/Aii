"""AG6 approval must not activate after external revocation between its two transactions.

Isolated real SQLite + authored FakeLora only; no native model or user adapter.
"""
from contextlib import contextmanager
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13.inputs import record_rating
from v13.agi.weights import WeightConsolidation, KEY
from v13.lora_trainer import AdapterRegistry
from tests.test_lora_trainer import FakeLora


class AG6SecondTransactionSourceRecheck(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.r = Runtime(self.home)
        self.addCleanup(self.r.close)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.s = self.r.store
        for n in range(9):
            event = self.s.event(self.r.session, 'Who owns project ' + str(n) + '?')
            self.r.memory.feedback(event['event_id'], 'fact', 'Human' + str(n))
        event = self.s.event(self.r.session, 'What is the approved budget?')
        self.dep = self.s.source('Supporting human context: budget is 120 EUR.',
                                 'HUMAN_FACT')
        self.s.message(self.r.session, event['event_id'], 'assistant',
                       'The budget is 120 EUR.', 'FINAL',
                       {'model_generated': True,
                        'context_source_refs': [event['source_ref'], self.dep]})
        record_rating(self.s, event['event_id'], 9, 'EXPLICIT_NOTE')
        self.cfg = self.r.cfg | {'learning_mode': 'SHADOW_UPDATE'}
        model = self.home / 'model.gguf'
        model.write_bytes(b'authored fake model fixture')
        self.trainer = FakeLora(self.home, model, cand={
            'overall': .8, 'unseen': .75, 'forgetting': {'rate': 0.}})

    def test_external_revocation_after_activating_commit_vetoes_registry_and_approval(self):
        w = WeightConsolidation(self.s, self.cfg, trainer=self.trainer)
        staged = w.stage(require_replay_pass=False, include_rated=True)
        self.assertEqual(staged['status'], 'STAGED')
        bid = staged['batch_id']
        gated = w.train_and_gate(bid)
        self.assertEqual(gated['status'], 'PENDING_USER')
        rid = gated['request_id']
        original_tx = self.s.tx
        tx_count = 0

        @contextmanager
        def revoke_between_transactions():
            nonlocal tx_count
            tx_count += 1
            if tx_count == 2:
                # This independent SQLite writer commits AFTER the durable
                # ACTIVATING intent but BEFORE approval's second transaction.
                with sqlite3.connect(self.home / 'data/db/brain.sqlite3') as other:
                    other.execute('UPDATE sources SET deleted=1 WHERE id=?',
                                  (self.dep['source_id'],))
            with original_tx() as c:
                yield c

        with patch.object(self.s, 'tx', revoke_between_transactions):
            with self.assertRaisesRegex(ValueError, 'Quelle|Source'):
                w.approve(bid)
        self.assertGreaterEqual(tx_count, 2)
        self.assertEqual(self.s.one('SELECT deleted FROM sources WHERE id=?',
                                    (self.dep['source_id'],))['deleted'], 1)
        self.assertEqual(w.batch(bid)['status'], 'PENDING_USER')
        self.assertEqual(self.s.one('SELECT status FROM requests WHERE id=?',
                                    (rid,))['status'], 'PENDING')
        self.assertEqual(self.s.state(KEY)[0]['consolidated'], [])
        self.assertNotIn('C3_LANGUAGE', AdapterRegistry(self.s).report()['active'])


    def test_external_final_change_after_activating_commit_vetoes_approval(self):
        w = WeightConsolidation(self.s, self.cfg, trainer=self.trainer)
        staged = w.stage(require_replay_pass=False, include_rated=True)
        self.assertEqual(staged['status'], 'STAGED')
        bid = staged['batch_id']
        gated = w.train_and_gate(bid)
        self.assertEqual(gated['status'], 'PENDING_USER')
        rid = gated['request_id']
        original_tx = self.s.tx
        tx_count = 0

        # The event ID is captured by the staged rated item, and the external
        # writer must alter that same FINAL, not an unrelated answer.
        rated = next(i for i in w.batch(bid)['items']
                     if i['kind'] == 'rated_answer')
        event_id = rated['event_id']

        @contextmanager
        def targeted_change():
            nonlocal tx_count
            tx_count += 1
            if tx_count == 2:
                with sqlite3.connect(self.home / 'data/db/brain.sqlite3') as other:
                    other.execute(
                        "UPDATE messages SET text=? WHERE event_id=? "
                        "AND role='assistant' AND status='FINAL'",
                        ('Changed externally', event_id))
            with original_tx() as c:
                yield c

        with patch.object(self.s, 'tx', targeted_change):
            with self.assertRaisesRegex(ValueError, 'Quelle|Source'):
                w.approve(bid)
        self.assertGreaterEqual(tx_count, 2)
        self.assertEqual(self.s.one(
            "SELECT text FROM messages WHERE event_id=? AND role='assistant' "
            "AND status='FINAL'", (event_id,))['text'], 'Changed externally')
        self.assertEqual(w.batch(bid)['status'], 'PENDING_USER')
        self.assertEqual(self.s.one('SELECT status FROM requests WHERE id=?',
                                    (rid,))['status'], 'PENDING')
        self.assertNotIn('C3_LANGUAGE', AdapterRegistry(self.s).report()['active'])


if __name__ == '__main__':
    unittest.main()

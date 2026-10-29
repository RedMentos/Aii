"""Preregistered Context OS warm-memory FINAL delivery lifecycle regression.

No model inference. Uses real Runtime/Store/Memory state and source-valid F1
feedback. The non-FINAL status is an API-level injected outcome, not a claimed
native model observation or production learning event.
"""
import unittest

from test_context_os import Base


class WarmMemoryFinalStatusTests(Base):
    def remember(self, key, value):
        event = self.ev(key)
        self.r.memory.feedback(event, 'fact', value, key=key)
        return self.r.store.one(
            'SELECT id FROM memories ORDER BY id DESC LIMIT 1'
        )['id']

    def test_cancelled_observation_does_not_warm_but_final_does(self):
        mid = self.remember('garden shed passphrase', 'indigo owl')
        event = self.ev('cancelled memory answer')
        cancelled = self.c.observe(event, 'C3_LANGUAGE', {},
                                   status='CANCELLED', memory_ids=[mid])
        self.assertEqual(cancelled['warm'], [])
        self.assertEqual(self.c._load()[0]['warm'], {})
        self.assertEqual(self.c.warm('garden shed passphrase',
                                     self.r.session, [])['ids'], [])

        # A successful answer can still warm an authorized memory without a
        # ContextPlan (e.g. a conservative plan fallback).
        delivered = self.c.observe(event, 'C3_LANGUAGE', {},
                                   status='FINAL', memory_ids=[mid])
        self.assertEqual(delivered['warm'], [mid])
        self.assertEqual(self.c.warm('garden shed passphrase',
                                     self.r.session, [])['ids'], [mid])

    def test_error_and_provisional_observations_never_warm(self):
        mid = self.remember('blue mailbox label', 'seven')
        for status in ('ERROR', 'PROVISIONAL'):
            with self.subTest(status=status):
                event = self.ev('nonfinal ' + status)
                self.c.observe(event, 'C3_LANGUAGE', {}, status=status,
                               memory_ids=[mid])
                self.assertEqual(self.c._load()[0]['warm'], {})

    def test_cancelled_reuse_cannot_refresh_decayed_memory(self):
        mid = self.remember('red garden bicycle', 'parked')
        event = self.ev('initial final')
        self.c.observe(event, 'C3_LANGUAGE', {}, status='FINAL',
                       memory_ids=[mid])
        self.assertEqual(self.c.warm('red garden bicycle',
                                     self.r.session, [])['ids'], [mid])
        for i in range(6):
            self.ev('later event %d' % i)
        self.assertEqual(self.c.warm('red garden bicycle',
                                     self.r.session, [])['ids'], [])
        self.c.observe(self.ev('interrupted revisit'), 'C3_LANGUAGE', {},
                       status='CANCELLED', memory_ids=[mid])
        self.assertEqual(self.c.warm('red garden bicycle',
                                     self.r.session, [])['ids'], [])


if __name__ == '__main__':
    unittest.main()

"""Run44 cross-check offline CLI against actual V13 Runtime-created Store.

Software only. Runtime is closed before the immutable read-only diagnostic.
"""
import hashlib
from pathlib import Path
import tempfile
import time
import unittest

from v13.runtime import Runtime
from v13.contracts import packet
from scripts import run44_b2_shadow_readonly_cli as offline

RULE = ('Project Orion kickoff note. ' + 'Administrative background only. ' * 12 +
        'Binding rules: Budget 160 euros. Deadline 8 days. Local-only requirement: true.')
SHEET = ('Project Orion supplier sheet. Option A: cost 115 euros, duration 6 days, local true. '
         'Option B: cost 90 euros, duration 5 days, local false.')
CURRENT = 'Project Orion: decide using the earlier binding project rules and latest supplier sheet.'


class ActualStoreOfflineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / 'installed'
        self.runtime = Runtime(self.home)
        self.revision = self.runtime.models.revision('B2_GIST')
        self.closed = False

    def tearDown(self):
        if not self.closed:
            self.runtime.close()
        self.temp.cleanup()

    def offer(self, text):
        e = self.runtime.store.event(self.runtime.session, text)
        p = packet('OfferPacket', 'B2_GIST', e['event_id'], e['brain_generation_id'],
                   [e['source_ref']], role='B2_GIST', based_on_state_version=0,
                   deadline_monotonic_ns=time.monotonic_ns() + 10**9,
                   evidence_refs=[e['source_ref']],
                   offer={'summary': 'Untrusted hypothesis.', 'quotes': [],
                          'uncertainty': '', 'needs_reentry': False},
                   confidence=0.0, model_revision=self.revision)
        self.runtime.store.add_packet('OfferPacket', p)
        self.runtime.cognition.retain_body_offer(p)
        return e

    def test_actual_store_closed_home_immutable_diagnostic(self):
        note = self.offer(RULE)
        for _ in range(5):
            self.offer(SHEET)
        current = self.runtime.store.event(self.runtime.session, CURRENT)
        self.runtime.close()
        self.closed = True
        def snapshot():
            return {str(p.relative_to(self.home)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.home.rglob('*') if p.is_file()}
        before = snapshot()
        result = offline.diagnose(self.home, current['event_id'], self.revision)
        self.assertEqual(result['decision']['action'], 'A')
        self.assertEqual(result['decision']['options'][0]['remaining'], 45)
        self.assertEqual(result['source_refs'][0]['source_id'], note['source_ref']['source_id'])
        self.assertEqual(snapshot(), before)
        self.assertEqual(result['authority'], 'SHADOW_NO_AUTHORITY')
        self.assertFalse(result['canonical_gate_pass'])

    def test_running_runtime_cannot_be_opened_immutably(self):
        current = self.runtime.store.event(self.runtime.session, CURRENT)
        with self.assertRaisesRegex(ValueError,
                                    'RUN44_ACTIVE_COORDINATOR|RUN44_NOT_QUIESCENT_OR_INVALID_HOME'):
            offline.diagnose(self.home, current['event_id'], self.revision)


if __name__ == '__main__':
    unittest.main()

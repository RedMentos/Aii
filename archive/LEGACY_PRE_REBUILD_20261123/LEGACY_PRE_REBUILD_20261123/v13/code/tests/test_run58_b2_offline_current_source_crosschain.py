"""Run58: real offline SQLite/blob integration regression for Run57 guard.

Review-only SHADOW: never starts Runtime/Store constructors against an installed
home, never authorizes an answer, and does not test native inference.
"""
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from scripts import run44_b2_shadow_readonly_cli as offline
from tests.test_run40_b2_store_history_readonly import Store
from tests.test_run42_b2_eligibility_source_shadow import RULE, SHEET, CURRENT
from v13.agi import eligibility


class Run58OfflineCurrentSourceRace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / 'installed'
        (self.home / 'data/db').mkdir(parents=True)
        (self.home / 'data/blobs').mkdir(parents=True)
        (self.home / 'data/coordinator.lock').touch()
        self.s = Store()
        self.addCleanup(self.s.db.close)
        rule = self.s.event(RULE)
        self.s.offer(rule)
        for _ in range(5):
            self.s.offer(self.s.event(SHEET))
        self.current = self.s.event(CURRENT)
        self.s.db.commit()
        with sqlite3.connect(self.home / 'data/db/brain.sqlite3') as disk:
            self.s.db.backup(disk)
        for text in self.s.sources.values():
            h = hashlib.sha256(text.encode('utf-8')).hexdigest()
            (self.home / 'data/blobs' / h).write_bytes(text.encode('utf-8'))

    def test_disk_backed_current_blob_tamper_after_selection_abstains(self):
        """Without Run57's final reread, Run42 incorrectly returns action A."""
        current_sha = self.current['source_ref']['sha256']
        blob = self.home / 'data/blobs' / current_sha
        original_fixed_rule = eligibility.fixed_rule
        seen = []

        def tamper_during_rule_parse(name, text):
            if not seen:
                blob.write_bytes(b'changed-after-option-selection')
            seen.append(name)
            return original_fixed_rule(name, text)

        with mock.patch.object(eligibility, 'fixed_rule',
                               side_effect=tamper_during_rule_parse):
            result = offline.diagnose(
                self.home, self.current['event_id'], 'm')
        self.assertEqual(seen, ['budget', 'deadline', 'local_only'])
        self.assertEqual(result['status'], 'ABSTAIN_CURRENT_SOURCE_CHANGED')
        self.assertIsNone(result['decision'])
        self.assertEqual(result['source_refs'], [])
        self.assertEqual(result['authority'], 'SHADOW_NO_AUTHORITY')
        self.assertFalse(result['canonical_gate_pass'])
        self.assertFalse(result['native_executed'])
        self.assertFalse(result['whole_system_complete'])

    def test_unmodified_offline_path_still_returns_shadow_action_a(self):
        result = offline.diagnose(self.home, self.current['event_id'], 'm')
        self.assertEqual(result['status'],
                         'SHADOW_DETERMINISTIC_DECISION_NO_OUTPUT')
        self.assertEqual(result['decision']['action'], 'A')
        self.assertEqual(result['decision']['options'][0]['remaining'], 45)
        self.assertEqual(result['authority'], 'SHADOW_NO_AUTHORITY')
        self.assertFalse(result['canonical_gate_pass'])


if __name__ == '__main__':
    unittest.main()

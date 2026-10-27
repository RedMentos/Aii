"""Sleep commit acknowledgment: durable CAS is required before reporting DONE.

Software/SQLite-only evidence; no model/native/Redmi or gate promotion.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13.runtime import Runtime
from v13.sleep import LAST_KEY, SCHEDULE_KEY


class SleepCommitAckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.cy = self.r.sleep.cycle

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def run_full(self):
        with mock.patch.object(self.cy, 'sleep_a', return_value={'phase':'SLEEP_A','status':'DONE'}), \
             mock.patch('v13.sleep_offline.run', return_value={'phase':'SLEEP_OFFLINE','status':'DONE'}), \
             mock.patch.object(self.cy, 'sleep_b', return_value={'phase':'SLEEP_B','status':'DONE'}), \
             mock.patch.object(self.cy, 'sleep_c', return_value={'phase':'SLEEP_C','status':'DONE'}):
            return self.cy.run('full', origin='USER', resource=lambda:'NORMAL')

    def test_full_cas_conflict_does_not_claim_done_or_advance_durable_clock(self):
        before = self.cy.queue.load()[0]['last_full']
        with mock.patch.object(self.cy.queue, 'save', side_effect=ValueError('CAS conflict')) as save:
            report = self.run_full()
        save.assert_called_once()
        self.assertEqual(report['status'], 'INTERRUPTED')
        self.assertEqual(report['reason'], 'SCHEDULE_CAS_CONFLICT')
        self.assertIs(report['schedule_saved'], False)
        self.assertEqual(self.cy.queue.load()[0]['last_full'], before)
        self.assertEqual(self.r.store.state(LAST_KEY, None)[0]['status'], 'INTERRUPTED')
        persisted = json.loads((self.home / 'exports/sleep-last.json').read_text())
        self.assertEqual(persisted['status'], 'INTERRUPTED')
        self.assertEqual(persisted['reason'], 'SCHEDULE_CAS_CONFLICT')
        self.assertEqual(len(report['phases']), 4)

    def test_successful_full_reports_commit_and_persists_clock_across_restart(self):
        before = self.cy.queue.load()[0]['last_full']
        report = self.run_full()
        self.assertEqual(report['status'], 'DONE')
        self.assertIs(report['schedule_saved'], True)
        committed = self.cy.queue.load()[0]['last_full']
        self.assertGreater(committed, before)
        self.r.close()
        self.r = Runtime(self.home)
        self.cy = self.r.sleep.cycle
        self.assertEqual(self.cy.queue.load()[0]['last_full'], committed)

    def test_real_sqlite_cas_race_preserves_external_schedule_after_restart(self):
        before, _ = self.cy.queue.load()
        original_save = self.cy.queue.save

        def competing_save(st, version):
            external = dict(before)
            external['cycles'] = before['cycles'] + 10
            self.r.store.set_state(SCHEDULE_KEY, external, expected=version)
            return original_save(st, version)

        with mock.patch.object(self.cy, 'sleep_a', return_value={'phase':'SLEEP_A','status':'DONE'}), \
             mock.patch('v13.sleep_offline.run', return_value={'phase':'SLEEP_OFFLINE','status':'DONE'}), \
             mock.patch.object(self.cy, 'sleep_b', return_value={'phase':'SLEEP_B','status':'DONE'}), \
             mock.patch.object(self.cy, 'sleep_c', return_value={'phase':'SLEEP_C','status':'DONE'}), \
             mock.patch.object(self.cy.queue, 'save', side_effect=competing_save):
            report = self.cy.run('full', origin='USER', resource=lambda:'NORMAL')
        self.assertEqual(report['status'], 'INTERRUPTED')
        self.assertIs(report['schedule_saved'], False)
        self.assertEqual(self.cy.queue.load()[0]['last_full'], before['last_full'])
        self.assertEqual(self.cy.queue.load()[0]['cycles'], before['cycles'] + 10)
        self.r.close()
        self.r = Runtime(self.home)
        self.cy = self.r.sleep.cycle
        self.assertEqual(self.cy.queue.load()[0]['cycles'], before['cycles'] + 10)
        self.assertEqual(self.cy.queue.load()[0]['last_full'], before['last_full'])

    def test_nonfull_commit_conflict_cannot_claim_done(self):
        with mock.patch.object(self.cy, 'sleep_c', return_value={'phase':'SLEEP_C','status':'DONE'}), \
             mock.patch.object(self.cy.queue, 'save', side_effect=ValueError('CAS conflict')):
            report = self.cy.run('c', origin='USER', resource=lambda:'NORMAL')
        self.assertEqual(report['status'], 'INTERRUPTED')
        self.assertIs(report['schedule_saved'], False)

    def test_existing_error_status_not_masked_by_cas_conflict(self):
        with mock.patch.object(self.cy, 'sleep_a', side_effect=RuntimeError('phase failed')), \
             mock.patch.object(self.cy.queue, 'save', side_effect=ValueError('CAS conflict')):
            with self.assertRaisesRegex(RuntimeError, 'phase failed'):
                self.cy.run('full', origin='USER', resource=lambda:'NORMAL')
        self.assertEqual(self.r.store.state(LAST_KEY, None)[0]['status'], 'ERROR')
        persisted = json.loads((self.home / 'exports/sleep-last.json').read_text())
        self.assertEqual(persisted['status'], 'ERROR')
        self.assertIs(persisted['schedule_saved'], False)


if __name__ == '__main__':
    unittest.main()

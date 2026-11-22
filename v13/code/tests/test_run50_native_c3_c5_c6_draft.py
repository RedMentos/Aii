"""Run50 software preflight with a clearly synthetic C3 stub and real SQLite Store."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts import run50_native_c3_c5_c6_draft as run50
from v13.store import Store

FIXTURE = Path(__file__).resolve().parents[1] / 'docs/fixtures/run50_native_c3_c5_c6_draft_seed443.json'


class FakeRunner:
    def __init__(self, wrong=False):
        self.wrong = wrong
        self.last_metrics = {'status': 'FINAL'}

    def generate(self, msgs, cancel, deadline, tokens, schema, seed):
        payload = json.loads(msgs[1]['content'])
        candidate = payload['typed_jef_candidate']
        if self.wrong:
            candidate = {'choice': 'B' if candidate['choice'] != 'B' else 'A', 'remaining': 999}
        return [json.dumps(candidate, separators=(',', ':'))]


class FakePool:
    def __init__(self, wrong=False):
        self.runner = FakeRunner(wrong)
        self.release_history = []

    def get(self, role):
        if role != 'C3_LANGUAGE':
            raise AssertionError('only synthetic C3 stub allowed')
        return self.runner

    def unload(self):
        if not self.release_history:
            self.release_history.append({'process_reaped': True, 'synthetic': True})


class FakeRuntime:
    wrong = False

    def __init__(self, home):
        self.store = Store(home)
        self.session = self.store.new_session()
        self.cancel_event = threading.Event()
        self.pool = FakePool(self.wrong)

    def close(self):
        self.pool.unload()
        self.store.close()


class Run50PreflightTests(unittest.TestCase):
    def test_frozen_fixture_and_disjoint_oracles(self):
        f = run50.load_fixture(FIXTURE)
        self.assertEqual([x['id'] for x in f['fixtures']], list(run50.PROJECTS))
        self.assertEqual([x['oracle']['choice'] for x in f['fixtures']], ['A', 'B', 'NONE', 'UNKNOWN'])

    def test_fixture_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'fixture.json'
            p.write_bytes(FIXTURE.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'RUN50_FIXTURE_SHA'):
                run50.load_fixture(p)

    def test_four_real_store_rows_with_synthetic_receiver_only(self):
        fixtures = run50.load_fixture(FIXTURE)['fixtures']
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run50, 'Runtime', FakeRuntime), \
                patch.object(run50, 'installed_links', lambda *args: None):
            for f in fixtures:
                with self.subTest(project=f['id']):
                    row = run50.run_row(Path(d) / f['id'], Path(d), f)
                    self.assertEqual(row['status'], 'RECORDED')
                    self.assertEqual(row['score']['correct'], 1)
                    self.assertEqual(row['draft_result']['result'], 'DRAFT_BOUND_SHADOW_NO_COMMIT')
                    self.assertEqual(row['draft_preflight_writes'], 0)
                    self.assertEqual(row['c6_draft_row']['status'], 'DRAFT')
                    self.assertTrue(row['processes_reaped'])
                    self.assertEqual(row['draft_result']['delivery_authority'], 0)

    def test_wrong_synthetic_receiver_is_scientific_red(self):
        f = run50.load_fixture(FIXTURE)['fixtures'][0]
        class WrongRuntime(FakeRuntime):
            wrong = True
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run50, 'Runtime', WrongRuntime), \
                patch.object(run50, 'installed_links', lambda *args: None):
            row = run50.run_row(Path(d) / 'bad', Path(d), f)
            self.assertEqual(row['status'], 'STRUCTURAL_FAIL')
            self.assertEqual(row['score']['correct'], 0)
            self.assertEqual(row['draft_result']['result'], 'FINAL_AGREEMENT_RED')

    def test_report_raw_rows_and_hashes_synthetic_only(self):
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run50, 'Runtime', FakeRuntime), \
                patch.object(run50, 'installed_links', lambda *args: None), \
                patch.object(run50, 'installed_artifacts', lambda *args: {'fake': True}):
            out = Path(d) / 'pilot'
            report = run50.run(Path(d), out, FIXTURE)
            self.assertEqual(len(report['rows']), 4)
            self.assertTrue(report['native_draft_copy_signal'])
            self.assertEqual(report['status'], 'NATIVE_DRAFT_COPY_SIGNAL_ONLY')
            for row in report['rows']:
                self.assertEqual(report['row_sha256'][row['fixture']],
                                 run50.sha(run50.dumps(row).encode('utf-8')))
            self.assertEqual(json.loads((out / 'report.json').read_text())['seed'], 443)


if __name__ == '__main__':
    unittest.main()
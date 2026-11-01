import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import tool_forecast_bound_learning_candidate as bound


class BindingAndJournal(unittest.TestCase):
    def test_second_attempt_is_rejected_and_original_claim_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            path = bound.claim_cohort(home, 'a'*64, home / 'attempt-one')
            original = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'PREREGISTRATION_ALREADY_CONSUMED'):
                bound.claim_cohort(home, 'a'*64, home / 'attempt-two')
            self.assertEqual(path.read_bytes(), original)
            self.assertTrue(json.loads(original)['consumed_even_if_interrupted'])

    def test_source_change_or_new_executable_source_refuses_continuation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'v13').mkdir()
            src = root / 'v13/forecast.py'
            src.write_text('first source')
            prereg = {'sources': bound.source_binding(root)}
            bound.verify_sources(prereg, root)
            src.write_text('second source')
            with self.assertRaisesRegex(ValueError, 'SOURCE_BINDING_CHANGED'):
                bound.verify_sources(prereg, root)
            src.write_text('first source')
            (root / 'v13/new_path.py').write_text('new execution path')
            with self.assertRaisesRegex(ValueError, 'SOURCE_BINDING_CHANGED'):
                bound.verify_sources(prereg, root)

    def test_progress_failure_keeps_complete_last_row_on_disk(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'rows.jsonl'
            def failed_progress(*args):
                raise RuntimeError('interrupt after row')
            rows = bound.Journal(path, 'preregistered-hash', failed_progress)
            with self.assertRaisesRegex(RuntimeError, 'interrupt after row'):
                rows.append({'arm': 'calc_shift_exp', 'action': 'double', 'state': 1234})
            saved = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]['ordinal'], 0)
            self.assertEqual(saved[0]['preregistration_sha256'], 'preregistered-hash')
            self.assertEqual(saved, rows)

    def test_stale_rule_fails_before_native_install(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            home = root / 'installed'; (home / 'data').mkdir(parents=True)
            prereg = root / 'prereg.json'
            prereg.write_text(json.dumps({'schema': bound.SCHEMA, 'gates': bound.original.GATES, 'rule': 'old-rule'}))
            with patch.object(bound.installer, 'install') as install:
                rc = bound.worker(home, prereg, root / 'out')
            self.assertEqual(rc, 1)
            install.assert_not_called()
            report = json.loads((root / 'out/report.json').read_text())
            self.assertEqual(report['status'], 'ERROR')
            self.assertEqual(report['verdict'], 'CONTINUAL_LEARNING_NOT_CONFIRMED')
            self.assertFalse(report['canonical_gate_pass'])


if __name__ == '__main__':
    unittest.main()

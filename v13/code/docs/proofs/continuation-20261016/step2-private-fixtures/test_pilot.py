"""Pilot geometry/registration tests only. No native processes or inference."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('private_pilot_adapter_test', HERE / 'runtime_adapter.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
P = A.P


class DiagnosticPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full = A.G.generate()
        cls.pilot = P.select_pilot(cls.full)

    def test_geometry_selects_one_fixed_case_per_action_before_any_outcome(self):
        self.assertEqual(self.pilot['selected_ids'], ['private_bfzwzwww', 'private_eztsxxpt', 'private_amvcghct'])
        self.assertEqual([f['oracle']['action'] for f in self.pilot['fixtures']], ['A', 'B', 'NONE'])
        for fixture in self.pilot['fixtures']:
            self.assertEqual(fixture['kind'], 'complementary')
            candidates = [f['id'] for f in self.full['fixtures'] if f['kind'] == 'complementary'
                          and f['oracle']['action'] == fixture['oracle']['action']]
            self.assertEqual(fixture['id'], min(candidates))
        self.assertEqual(len(self.full['fixtures']), 39)
        self.assertEqual(self.pilot['full_benchmark_rows'], 234)
        self.assertEqual(self.pilot['native_runs'], 0)
        self.assertFalse(self.pilot['gate_promotion'])

    def test_saved_selection_manifest_matches_exact_file_and_source_bytes(self):
        pilot_path = HERE / 'pilot/pilot-fixtures.json'
        manifest = json.loads((HERE / 'pilot/pilot-selection-manifest.json').read_text())
        self.assertEqual(json.loads(pilot_path.read_text()), self.pilot)
        expected_sources = {'generate_fixtures.py': HERE / 'generate_fixtures.py',
                            'prepare_pilot.py': HERE / 'prepare_pilot.py',
                            'full-fixtures.json': HERE / 'generated/fixtures.json',
                            'pilot-fixtures.json': pilot_path}
        self.assertEqual(manifest['source_sha256'], {k: P.sha(v) for k, v in expected_sources.items()})
        self.assertEqual(manifest['status'], 'SELECTED_BEFORE_NATIVE_OUTCOMES')
        self.assertFalse(manifest['cohort_registration'])
        self.assertFalse(manifest['gate_promotion'])

    def test_selection_export_is_reproducible_refuses_overwrite_and_rejects_changes(self):
        with tempfile.TemporaryDirectory() as d:
            first, second = Path(d) / 'first', Path(d) / 'second'
            P.export(HERE / 'generated/fixtures.json', first)
            P.export(HERE / 'generated/fixtures.json', second)
            for name in ('pilot-fixtures.json', 'pilot-selection-manifest.json'):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            with self.assertRaises(FileExistsError):
                P.export(HERE / 'generated/fixtures.json', first)
        changed = copy.deepcopy(self.full)
        changed['fixtures'][0]['oracle']['action'] = 'CHANGED'
        with self.assertRaises(ValueError):
            P.select_pilot(changed)

    def test_pilot_registration_has_exact_eighteen_row_forty_two_call_diagnostic_scope(self):
        with patch.object(A, 'installed_bindings', return_value={'fixture': 'SOFTWARE_NOT_NATIVE'}):
            pilot = A.registration(Path('/unused'), self.pilot)
            full = A.registration(Path('/unused'), self.full)
            self.assertEqual((pilot['max_rows'], pilot['max_native_calls']), (18, 42))
            self.assertEqual((full['max_rows'], full['max_native_calls']), (234, 546))
            self.assertEqual(pilot['fixture_ids'], self.pilot['selected_ids'])
            self.assertEqual(pilot['variant_order'], list(A.VARIANTS))
            self.assertEqual(pilot['scope'], 'THREE_COMPLEMENTARY_CASE_DIAGNOSTIC_NOT_FULL_STEP2')
            self.assertEqual(pilot['numeric_utility_gate'], 'NO_UTILITY_PROMOTION_FOR_DIAGNOSTIC_PILOT')
            self.assertFalse(pilot['gate_promotion'])
            changed = copy.deepcopy(self.pilot)
            changed['scope'] = 'FULL_STEP2_PASS'
            with self.assertRaises(ValueError):
                A.registration(Path('/unused'), changed)

    def test_actual_registration_cli_binds_saved_pilot_with_only_installation_probe_replaced(self):
        # Exercise argparse, file read, validation, hashing and output creation.
        # The only replacement is artifact lookup: the pilot has deliberately
        # not received B2/runner assets yet, and no native process may start.
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'software-cli-registration.json'
            argv = ['runtime_adapter.py', 'register', '--installed', '/unused', '--fixtures',
                    str(HERE / 'pilot/pilot-fixtures.json'), '--out', str(output)]
            with patch.object(A, 'installed_bindings', return_value={'fixture': 'SOFTWARE_NOT_NATIVE'}), \
                 patch.object(sys, 'argv', argv), contextlib.redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(A.main(), 0)
            written = json.loads(output.read_text())
            printed = json.loads(stream.getvalue())
            self.assertEqual(written['fixtures_sha256'], A.digest(A.dumps(self.pilot)))
            self.assertEqual((printed['max_rows'], printed['max_native_calls']), (18, 42))
            self.assertEqual(printed['scope'], self.pilot['scope'])
            self.assertEqual(printed['registration_sha256'], A.digest(A.dumps(written)))


if __name__ == '__main__':
    unittest.main()

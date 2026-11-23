"""Blueprint STEP2 harness/exit separation: original native RED stays binding."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v13 import gates
from v13.common import APP


class Step2ExitGate(unittest.TestCase):
    def test_legacy_harness_key_preserved_but_not_canonical_exit(self):
        spec = gates.spec()
        self.assertIn('STEP2', spec['gates'])
        self.assertIn('STEP2_EXIT', spec['gates'])
        self.assertIn('STEP2_HARNESS', spec['gates']['STEP2']['title'])
        self.assertEqual(spec['gates']['STEP2_EXIT']['deps'], ['STEP2'])
        self.assertNotEqual(spec['gates']['STEP2']['verdict'],
                            spec['gates']['STEP2_EXIT']['verdict'])

    def test_original_negative_native_verdicts_remain_false(self):
        exit_gate = gates.spec()['gates']['STEP2_EXIT']
        self.assertEqual(len(exit_gate['verdict']), 2)
        for rule in exit_gate['verdict']:
            self.assertEqual(rule['path'], 'gate.canonical_gate_pass')
            self.assertEqual((rule['op'], rule['value']), ('==', True))
            original = json.loads((APP / rule['file']).read_text())
            self.assertIs(original['gate']['canonical_gate_pass'], False)
        failures = gates.verdicts(exit_gate)
        self.assertEqual(len(failures), 2)
        self.assertTrue(all(x['actual'] is False for x in failures))

    def test_exit_is_explicitly_red_and_all_graph_deps_remain_known(self):
        spec = gates.spec()
        for key in ('STEP6', 'G-B-TIMESCALE-DIVERGENCE-001',
                    'G-FOCAL-CAPACITY-003'):
            self.assertIn('STEP2', spec['gates'][key]['deps'])
            self.assertIn('STEP2_EXIT', spec['gates'][key]['deps'])
        for gate in spec['gates'].values():
            self.assertTrue(set(gate['deps']) <= set(spec['gates']))
        state = gates.evaluate()
        self.assertEqual(state['STEP2_EXIT']['status'], 'EVIDENCE_NOT_PASSING')
        self.assertEqual(len(state['STEP2_EXIT']['verdict_failures']), 2)
        for key in ('STEP6', 'G-B-TIMESCALE-DIVERGENCE-001',
                    'G-FOCAL-CAPACITY-003'):
            self.assertNotEqual(state[key]['status'], 'GREEN')

    def test_in_tree_bench_results_are_real_data_not_unit_tests(self):
        exit_gate = gates.spec()['gates']['STEP2_EXIT']
        checked = gates.check(exit_gate)
        self.assertTrue(checked['real_data']['present'])
        self.assertTrue(checked['ablation']['present'])
        self.assertFalse(checked['real_data']['missing'])
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp)
            (app / 'bench-results/native').mkdir(parents=True)
            (app / 'tests').mkdir()
            (app / 'bench-results/native/report.json').write_text('{}')
            (app / 'tests/fake.json').write_text('{}')
            blank = {k: None for k in gates.spec()['criteria']}
            schema = gates.spec()
            with patch.object(gates, 'APP', app), patch.object(gates, 'spec', return_value=schema):
                good = gates.check(blank | {'real_data': ['bench-results/native/report.json']},
                                   logged=set())
                bad = gates.check(blank | {'real_data': ['tests/fake.json']},
                                  logged=set())
            self.assertTrue(good['real_data']['present'])
            self.assertFalse(bad['real_data']['present'])

    def test_missing_or_corrupt_verdict_cannot_promote_exit(self):
        gate = gates.spec()['gates']['STEP2_EXIT']
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(gates, 'APP', Path(tmp)):
                failures = gates.verdicts(gate)
        self.assertEqual(len(failures), 2)
        self.assertTrue(all(x['actual'] == 'FileNotFoundError' for x in failures))

    def test_boolean_verdict_type_is_binding_and_unused_ops_are_not_evaluated(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp)
            report = app / 'report.json'
            bool_rule = {'file': 'report.json', 'path': 'gate.canonical_gate_pass',
                         'op': '==', 'value': True}
            with patch.object(gates, 'APP', app):
                for value in (1, 1.0, 'true', False):
                    report.write_text(json.dumps({'gate': {'canonical_gate_pass': value}}))
                    self.assertEqual(len(gates.verdicts({'verdict': [bool_rule]})), 1)
                report.write_text(json.dumps({'gate': {'canonical_gate_pass': True}}))
                self.assertEqual(gates.verdicts({'verdict': [bool_rule]}), [])
                report.write_text(json.dumps({'gate': {'canonical_gate_pass': None}}))
                null_rule = dict(bool_rule, value=None)
                self.assertEqual(gates.verdicts({'verdict': [null_rule]}), [])
                report.write_text(json.dumps({'gate': {'canonical_gate_pass': 3}}))
                numeric_rule = dict(bool_rule, op='>=', value=2)
                self.assertEqual(gates.verdicts({'verdict': [numeric_rule]}), [])
                report.write_text(json.dumps({'gate': {'canonical_gate_pass': True}}))
                self.assertEqual(len(gates.verdicts({'verdict': [numeric_rule]})), 1)

    def test_summary_exposes_both_without_any_completion_claim(self):
        summary = gates.summary()
        self.assertIn('STEP2', summary['gates'])
        self.assertEqual(summary['gates']['STEP2_EXIT'], 'EVIDENCE_NOT_PASSING')
        self.assertNotEqual(summary['gates']['STEP2_EXIT'], 'GREEN')


if __name__ == '__main__':
    unittest.main()

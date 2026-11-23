"""Offline diagnostic contract checks; no model, server or STEP2 fixture is invoked."""
import importlib.util
import json
from pathlib import Path
import unittest

path = Path(__file__).parents[1]/'scripts/schema_action_probe.py'
spec = importlib.util.spec_from_file_location('schema_action_probe', path)
probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)


class SchemaProbe(unittest.TestCase):
    def test_actual_wire_changes_order_without_changing_schema_semantics(self):
        _, action_wire = probe.payload_for('same template', 'schema_action_first')
        _, facts_wire = probe.payload_for('same template', 'schema_facts_first')
        action = json.loads(action_wire); facts = json.loads(facts_wire)
        self.assertEqual(action, facts)
        self.assertEqual(list(action['json_schema']['properties']), ['action', 'eligible', 'remaining'])
        self.assertEqual(list(facts['json_schema']['properties']), ['remaining', 'eligible', 'action'])
        self.assertEqual(action['prompt'], facts['prompt'])
        self.assertEqual(action['seed'], facts['seed'])
        self.assertEqual(action['n_predict'], facts['n_predict'])

    def test_schema_free_control_keeps_same_sampling_and_has_no_grammar(self):
        free, _ = probe.payload_for('same template', 'free_json')
        forced, _ = probe.payload_for('same template', 'schema_action_first')
        forced.pop('json_schema')
        self.assertEqual(free, forced)
        self.assertNotIn('grammar', free)

    def test_all_actions_in_both_direct_and_arithmetic_cohorts(self):
        rows = probe.cases()
        self.assertEqual(len(rows), 8)
        self.assertEqual({r['expected']['action'] for r in rows[:4]}, set(probe.LABELS))
        self.assertEqual({r['expected']['action'] for r in rows[4:]}, set(probe.LABELS))
        self.assertEqual(len({r['id'] for r in rows}), 8)

    def test_action_only_is_disclosed_and_not_full_arithmetic_proof(self):
        expected = probe.cases()[-1]['expected']
        raw = json.dumps({'action': 'UNKNOWN'})
        self.assertTrue(probe.score(raw, expected, 'action_only')['all_requested_fields_exact'])
        self.assertFalse(probe.score(raw, expected, 'schema_action_first')['all_requested_fields_exact'])

    def test_invalid_output_is_retained_as_failure_without_text_label_guess(self):
        expected = probe.cases()[0]['expected']
        for raw in ('Action A', '```json\n{"action":"A"}\n```', 'null', '{"action":"NONE"}'):
            self.assertFalse(probe.score(raw, expected, 'free_json')['action_exact'])

    def test_wrong_arithmetic_does_not_pass_full_output(self):
        expected = probe.cases()[4]['expected']
        output = dict(expected, remaining=[20, 20])
        result = probe.score(json.dumps(output), expected, 'schema_facts_first')
        self.assertTrue(result['action_exact'])
        self.assertFalse(result['all_requested_fields_exact'])


if __name__ == '__main__':
    unittest.main()

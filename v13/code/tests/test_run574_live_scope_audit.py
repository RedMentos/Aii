"""Run574 source-only AST scope proof and adversarial tamper tests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import run574_live_scope_audit as audit


class LiveScopeAuditTests(unittest.TestCase):
    def sources(self):
        return {k: p.read_text() for k, p in audit.PATHS.items()}

    def test_original_source_call_graph_is_not_live_runtime(self):
        result = audit.audit()
        self.assertEqual(result['status'], 'BODY_OFFER_PLUS_FROZEN_C3_REPLAY_ONLY')
        self.assertIs(result['upstream_body_quote_comparison_possible'], True)
        self.assertIs(result['live_end_to_end_verified'], False)
        self.assertIs(result['eligibility_reader_final_effect_isolated'], False)
        self.assertIs(result['tool_answer_first_final_effect_isolated'], False)
        self.assertIs(result['native_executed'], False)
        self.assertIs(result['canonical_gate_pass'], False)
        self.assertEqual(result['step2_exit'], 'UTILITY_FAIL')
        self.assertEqual(result['jepa_weight'], 0)
        self.assertIs(result['redmi_measured'], False)
        self.assertEqual(set(result['source_sha256']), set(audit.PATHS))

    def test_producer_no_longer_calls_frozen_replay_refused(self):
        src = self.sources()
        self.assertIn('replay.run(', src['producer'])
        src['producer'] = src['producer'].replace('replay.run(', 'replay.other(', 1)
        with self.assertRaisesRegex(ValueError, 'PRODUCER_NOT_FROZEN_TOOL_REPLAY'):
            audit.audit(src)

    def test_executor_not_using_z2b_refused(self):
        src = self.sources()
        self.assertIn('z2b.run_one(', src['executor'])
        src['executor'] = src['executor'].replace('z2b.run_one(', 'z2b.other(', 1)
        with self.assertRaisesRegex(ValueError, 'EXECUTOR_NOT_FROZEN_Z2B'):
            audit.audit(src)

    def test_c3_frozen_generation_removed_refused(self):
        src = self.sources()
        self.assertIn('runner.generate(', src['replay'])
        src['replay'] = src['replay'].replace('runner.generate(', 'runner.other(', 1)
        with self.assertRaisesRegex(ValueError, 'C3_FROZEN_REPLAY_CALL_GRAPH_CHANGED'):
            audit.audit(src)

    def test_tool_answer_not_fixed_guard_refused(self):
        src = self.sources()
        self.assertIn('E.decide(', src['replay'])
        src['replay'] = src['replay'].replace('E.decide(', 'E.other(', 1)
        with self.assertRaisesRegex(ValueError, 'FIXED_ELIGIBILITY_TOOL_CHANGED'):
            audit.audit(src)

    def test_replay_actual_live_submit_change_refused(self):
        src = self.sources()
        needle='    report = recorded(report_path); fixtures = '
        self.assertIn(needle, src['replay'])
        src['replay'] = src['replay'].replace(needle, '    r.submit("not allowed")\n'+needle, 1)
        with self.assertRaisesRegex(ValueError, 'FROZEN_REPLAY_NOW_CALLS_LIVE_RUNTIME'):
            audit.audit(src)

    def test_actual_runtime_answer_first_removed_refused(self):
        src = self.sources()
        self.assertIn('tool_answer_first', src['runtime'])
        src['runtime'] = src['runtime'].replace('tool_answer_first', 'some_other_control')
        with self.assertRaisesRegex(ValueError, 'LIVE_RUNTIME_ANSWER_FIRST_BINDING_MISSING'):
            audit.audit(src)

    def test_exclusive_report_and_no_model_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'scope.json'
            with patch.object(sys, 'argv', ['run574', '--output', str(out)]):
                audit.main()
            original = out.read_bytes()
            report = json.loads(original)
            self.assertEqual(report['status'], 'BODY_OFFER_PLUS_FROZEN_C3_REPLAY_ONLY')
            with patch.object(sys, 'argv', ['run574', '--output', str(out)]):
                with self.assertRaises(FileExistsError):
                    audit.main()
            self.assertEqual(out.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()

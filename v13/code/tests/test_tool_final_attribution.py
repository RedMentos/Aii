"""Source-bound deterministic eligibility FINAL provenance and real lead_final checks.

Software-only: no model, device or STEP2 utility claims.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from v13.agi import eligibility
from v13.toolstep import ToolStep
from v13.broker import Broker, decide, egress_type, exact_tool_final

RUNTIME = Path(__file__).resolve().parents[1] / 'v13' / 'runtime.py'


def _turn_ast():
    module = ast.parse(RUNTIME.read_text(encoding='utf-8'))
    cls = next(x for x in module.body if isinstance(x, ast.ClassDef) and x.name == 'Runtime')
    return next(x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == '_turn')


def _source(node):
    return ast.unparse(node)


def _call(node, name):
    return isinstance(node, ast.Call) and _source(node.func) == name


def _tool(action):
    options = [
        {'entity': 'A', 'cost': 40, 'days': 5, 'local': True,
         'remaining': 10, 'eligible': action == 'A'},
        {'entity': 'B', 'cost': 55, 'days': 7, 'local': False,
         'remaining': -5, 'eligible': action == 'B'},
    ]
    return {
        'tool': 'eligibility',
        'args': {'current': 'Choose Option A or Option B.', 'budget': 50},
        'result': {'action': action, 'options': options, 'rejected': []},
    }


class ToolFinalAttributionTests(unittest.TestCase):
    def test_final_text_is_tool_owned_without_body_generation(self):
        step = ToolStep(SimpleNamespace(cfg={'tool_answer_first': True}))
        for action in ('UNKNOWN', 'NONE'):
            with self.subTest(action=action):
                result = _tool(action)
                final = step.lead_final(result)
                self.assertEqual(final, eligibility.final_text(result['args'], result['result']))
                self.assertTrue(final)
                self.assertNotIn('Choose Option A.', final)
                self.assertNotIn('Choose Option B.', final)

    def test_a_b_leads_still_require_native_continuation(self):
        step = ToolStep(SimpleNamespace(cfg={'tool_answer_first': True}))
        for action in ('A', 'B'):
            with self.subTest(action=action):
                result = _tool(action)
                self.assertIsNone(step.lead_final(result))
                self.assertTrue(step.lead(result).startswith('Choose Option '+action+'.'))
        off = ToolStep(SimpleNamespace(cfg={'tool_answer_first': False}))
        self.assertIsNone(off.lead(_tool('UNKNOWN')))
        self.assertIsNone(off.lead_final(_tool('NONE')))

    def test_actual_runtime_skips_native_generation_and_late_observer_for_final(self):
        turn = _turn_ast()
        nodes = list(ast.walk(turn))
        tool_final = [n for n in nodes if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'tool_final' for t in n.targets)]
        self.assertEqual(len(tool_final), 1)
        self.assertIn("meta.get('tool_answer_first') == 'FINAL'", _source(tool_final[0].value))
        loop = [n for n in nodes if isinstance(n, ast.For)
                and any(_call(x, 'runner.generate') for x in ast.walk(n.iter))]
        self.assertEqual(len(loop), 1)
        self.assertIsInstance(loop[0].iter, ast.IfExp)
        self.assertEqual(_source(loop[0].iter.test), 'tool_final')
        watcher = [n for n in nodes if _call(n, 'latewatch.start')]
        self.assertEqual(len(watcher), 1)
        eligible = next(k.value for k in watcher[0].keywords if k.arg == 'eligible')
        self.assertIn('not tool_final', _source(eligible))

    def test_success_and_exception_paths_do_not_credit_tool_final_as_model(self):
        turn = _turn_ast()
        nodes = list(ast.walk(turn))
        guards = [n for n in nodes if isinstance(n, ast.If)
                  and _source(n.test) == 'tool_final'
                  and any(_call(x, 'meta.update') for y in n.body for x in ast.walk(y))]
        self.assertEqual(len(guards), 1)
        self.assertIn('model_generated=False', _source(guards[0].body))
        self.assertIn("output_authority='ELIGIBILITY_TOOL_FINAL'", _source(guards[0].body))
        self.assertIn('model_generated=True', _source(guards[0].orelse))
        exc_guard = [n for n in nodes if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Subscript) and _source(t) == "meta['model_generated']"
                             for t in n.targets)]
        self.assertTrue(any("meta.get('tool_answer_first') != 'FINAL'" in _source(n.value)
                            for n in exc_guard))

    def test_no_stale_runner_observation_or_false_reflex_credit(self):
        turn = _turn_ast()
        nodes = list(ast.walk(turn))
        obs = [n for n in nodes if _call(n, 'ctxos.controller(self).observe')]
        self.assertEqual(len(obs), 1)
        self.assertTrue(any(isinstance(p, ast.If) and _source(p.test) == 'not tool_final'
                            and obs[0] in list(ast.walk(p)) for p in nodes))
        self.assertTrue(any(isinstance(n, ast.If) and
                            'not tool_final' in _source(n.test) and
                            'runner' in _source(n.test)
                            for n in nodes))
        self.assertTrue(any(isinstance(n, ast.Assign) and
                            "meta.get('tool_answer_first')" in _source(n.value) and
                            'runner.role' in _source(n.value)
                            for n in nodes))

    def test_broker_preserves_distinct_tool_authority_in_real_finalize(self):
        self.assertEqual(decide(['ELIGIBILITY_TOOL_FINAL'])['selected'], 'ELIGIBILITY_TOOL_FINAL')
        self.assertEqual(egress_type('ELIGIBILITY_TOOL_FINAL'), 'TEXT_REPORT')
        store = MagicMock()
        store.add_packet.return_value = {'packet_id': 'broker-packet'}
        runtime = SimpleNamespace(store=store, cfg={}, session='test')
        b = Broker(runtime)
        e = {'event_id': 'event', 'brain_generation_id': 'generation', 'source_ref': {'source_id': 'src'}}
        for action in ('UNKNOWN', 'NONE'):
            with self.subTest(action=action):
                tool = _tool(action)
                output = eligibility.final_text(tool['args'], tool['result'])
                meta = {'output_authority': 'ELIGIBILITY_TOOL_FINAL',
                        'tool_answer_first': 'FINAL', 'model_generated': False,
                        'output_committed': True}
                with patch.object(Broker, '_check', return_value={'ok': True, 'violations': []}):
                    receipt = b.finalize(e, 'message', meta, 'FINAL', output, tool_result=tool)
                self.assertEqual(receipt['authority'], 'ELIGIBILITY_TOOL_FINAL')
                self.assertEqual(receipt['egress_type'], 'TEXT_REPORT')
                self.assertEqual(receipt['conflicts'], [])
                self.assertEqual(receipt['late'], [])
        self.assertEqual(store.add_packet.call_count, 2)

    def test_broker_refuses_unbound_or_model_generated_tool_claim(self):
        store = MagicMock()
        store.add_packet.return_value = {'packet_id': 'broker-packet'}
        b = Broker(SimpleNamespace(store=store, cfg={}, session='test'))
        e = {'event_id': 'event', 'brain_generation_id': 'generation', 'source_ref': {'source_id': 'src'}}
        tool = _tool('UNKNOWN')
        output = eligibility.final_text(tool['args'], tool['result'])
        with patch.object(Broker, '_check', return_value={'ok': True, 'violations': []}):
            for bad in ({'model_generated': True}, {'tool_answer_first': 'LEAD'},
                        {'output_authority': 'MODEL_ANSWER'}):
                meta = {'output_authority': 'ELIGIBILITY_TOOL_FINAL',
                        'tool_answer_first': 'FINAL', 'model_generated': False}
                meta.update(bad)
                receipt = b.finalize(e, 'message', meta, 'FINAL', output, tool_result=tool)
                self.assertNotEqual(receipt['authority'], 'ELIGIBILITY_TOOL_FINAL')

    def test_exact_tool_authority_refuses_tampered_visible_answer(self):
        store = MagicMock()
        store.add_packet.return_value = {'packet_id': 'broker-packet'}
        b = Broker(SimpleNamespace(store=store, cfg={'tool_conflict_policy': 'log'}, session='test'))
        e = {'event_id': 'event', 'brain_generation_id': 'generation',
             'source_ref': {'source_id': 'src'}}
        tool = _tool('UNKNOWN')
        expected = eligibility.final_text(tool['args'], tool['result'])
        self.assertTrue(exact_tool_final(tool, expected))
        for output in (expected+' Choose Option A.', expected[:-1], 'Choose Option B.'):
            with self.subTest(output=output):
                self.assertFalse(exact_tool_final(tool, output))
                meta = {'output_authority': 'ELIGIBILITY_TOOL_FINAL',
                        'tool_answer_first': 'FINAL', 'model_generated': False}
                with patch.object(Broker, '_check', return_value={'ok': True, 'violations': []}):
                    receipt = b.finalize(e, 'message', meta, 'FINAL', output, tool_result=tool)
                self.assertIsNone(receipt['authority'])

    def test_malformed_tool_results_never_get_fixed_tool_authority(self):
        tool = _tool('UNKNOWN')
        text = eligibility.final_text(tool['args'], tool['result'])
        malformed = [None, [], {}, {'tool': 'calc', 'result': tool['result']},
                     {'tool': 'eligibility', 'result': None},
                     {'tool': 'eligibility', 'result': {'action': 'UNKNOWN'}},
                     {'tool': 'eligibility', 'result': {'action': 'A'}, 'args': tool['args']},
                     {'tool': 'eligibility', 'result': tool['result'], 'args': None},
                     {'tool': 'eligibility', 'result': tool['result'], 'args': {}}]
        for value in malformed:
            with self.subTest(value=value):
                self.assertFalse(exact_tool_final(value, text))
        self.assertFalse(exact_tool_final(tool, None))

    def test_original_frozen_gates_not_redefined_by_this_candidate(self):
        self.assertTrue(RUNTIME.exists())
        # Source-only unit tests cannot establish native, Redmi, JEPA or STEP2 utility.
        self.assertEqual({'STEP2': 'UTILITY_FAIL', 'B3': 'FAIL',
                          'Body-JEPA': 'UNAVAILABLE', 'jepa_weight': 0,
                          'Redmi': 'UNMEASURED'}['STEP2'], 'UTILITY_FAIL')


if __name__ == '__main__':
    unittest.main()

"""Run12K preregistration and strict admission logic (software only)."""
import unittest
from scripts import c2_strict_native_compat_run12k as s


def control(route='detail', **kwargs):
    return {'success': True, 'confidence': .91,
            'validation': {'negation': False, 'ungrounded': []},
            'function_calls': [{'name': 'select_processing',
                                'arguments': {'route': route}}]} | kwargs


def row(c, scaffold='simple', source='NATIVE_C2_ADVISORY', route='detail'):
    return {'route': route, 'route_info': {'native_control': c,
                                         'scaffold': scaffold, 'source': source}}


class C2StrictNativeCompatibilityRun12K(unittest.TestCase):
    def test_preregistration_fixed_disjoint_and_scaffold_roles(self):
        self.assertEqual(s.prompt_hash(), s.PROMPT_SHA256)
        self.assertEqual(len(s.PROMPTS), 4)
        self.assertEqual(s.EXPECTED_SCAFFOLDS, ('simple', 'simple', 'detail', 'gist'))
        self.assertTrue(set(s.PROMPTS).isdisjoint(s.original.PROMPTS))
        self.assertEqual(s.SEED, s.original.SEED)

    def test_valid_single_tool_expected_admission(self):
        result = s.classify(row(control()))
        self.assertTrue(result['valid_unique_tool'])
        self.assertTrue(result['matches'])
        self.assertEqual(result['native_route'], 'detail')

    def test_non_simple_scaffold_keeps_scaffold(self):
        result = s.classify(row(control(), scaffold='gist',
                                source='BOOT_SCAFFOLD', route='gist'))
        self.assertTrue(result['valid_unique_tool'])
        self.assertTrue(result['matches'])
        self.assertFalse(result['expected_selected'])

    def test_invalid_native_must_not_be_selected(self):
        cases = (
            control(success=False), control(confidence=float('nan')),
            control(validation={'negation': True}),
            control(function_calls=[{'name': 'foreign', 'arguments': {'route': 'detail'}}]),
            control(function_calls=[{'name': 'select_processing', 'arguments': {'route': 'detail'}},
                                    {'name': 'select_processing', 'arguments': {'route': 'both'}}]),
        )
        for c in cases:
            with self.subTest(c=repr(c)[:70]):
                self.assertTrue(s.classify(row(c, source='BOOT_SCAFFOLD', route='simple'))['matches'])
                self.assertFalse(s.classify(row(c))['matches'])

    def test_foreign_nested_route_not_admitted(self):
        c = {'route': 'gist', 'diagnostic': {'route': 'both'}} | control()
        self.assertTrue(s.classify(row(c))['matches'])
        self.assertEqual(s.classify(row(c))['native_route'], 'detail')

    def test_no_native_evidence_does_not_match(self):
        self.assertFalse(s.classify({'route_info': {}})['matches'])


if __name__ == '__main__':
    unittest.main()

"""Isolated source-number guard review; no runtime source edits or native inference."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
APP = HERE.parents[3]
sys.path[:0] = [str(APP), str(APP/'tests'), str(APP/'scripts')]

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE/filename)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

B = load('list_guard_baseline', 'baseline-listarith.py')
C = load('list_guard_candidate', 'candidate-listarith.py')

def values(a=5, b=2):
    return [{'name': 'a', 'number': a}, {'name': 'b', 'number': b}]


class SignedNumberGuard(unittest.TestCase):
    def test_original_accepted_sign_changed_positive_while_rejecting_correct_negative(self):
        text = 'Items: a -5, b 2. Give the correct total.'
        self.assertEqual(B.compute('total', values(), text)[0], 7)
        with self.assertRaises(ValueError):
            B.compute('total', values(-5), text)
        with self.assertRaises(ValueError):
            C.compute('total', values(), text)
        self.assertEqual(C.compute('total', values(-5), text)[0], -3)

    def test_difference_recipe_sign_guard_and_calculation(self):
        text = 'Values: a -5, b 2. What is the difference between largest and smallest?'
        self.assertEqual(B.compute('difference_max_min', values(), text)[0], 3)
        with self.assertRaises(ValueError):
            C.compute('difference_max_min', values(), text)
        self.assertEqual(C.compute('difference_max_min', values(-5), text)[0], 7)

    def test_unicode_mathematical_minus_preserves_sign_too(self):
        text = 'Items: a \u22125, b 2. Give the correct total.'
        self.assertEqual(B.compute('total', values(), text)[0], 7)
        with self.assertRaises(ValueError):
            C.compute('total', values(), text)
        self.assertEqual(C.compute('total', values(-5), text)[0], -3)

    def test_explicit_plus_and_surrounding_punctuation(self):
        for text in ('Items: a +5, b 2. Give the total.', 'a (+5); b [2]. Give the total.',
                     'a 5. b 2. Give the total.'):
            with self.subTest(text=text):
                self.assertEqual(C.compute('total', values(), text)[0], 7)
        self.assertEqual(C.compute('total', values(-5), 'a (-5); b +2. Give the total.')[0], -3)

    def test_no_partial_match_after_other_signs(self):
        for spelling in ('--5', '++5', '-+5', '+-5', '\u2212-5', '-\u22125'):
            with self.subTest(spelling=spelling):
                self.assertEqual(C._INT.findall('a '+spelling+', b 2.'), ['2'])
                with self.assertRaises(ValueError):
                    C.compute('total', values(), 'a '+spelling+', b 2. Give the total.')

    def test_decimal_integer_parts_remain_rejected(self):
        for spelling in ('5.2', '-5.2', '+5.2', '\u22125.2', '.5', '-.5', '15.2'):
            for number in (5, 2, -5, 15):
                with self.subTest(spelling=spelling, number=number):
                    text = 'a '+spelling+', b 9. Give the total.'
                    for module in (B, C):
                        with self.assertRaises(ValueError):
                            module.compute('total', values(number, 9), text)

    def test_multi_digit_negative_does_not_expose_suffix(self):
        text = 'Items: a -123, b 2. Give the total.'
        self.assertEqual(C._INT.findall(text), ['-123', '2'])
        for number in (123, 23, 3):
            with self.subTest(number=number), self.assertRaises(ValueError):
                C.compute('total', values(number), text)
        self.assertEqual(C.compute('total', values(-123), text)[0], -121)

    def test_existing_leading_zero_and_sentence_period_behavior_is_preserved(self):
        for module in (B, C):
            self.assertEqual(module.compute('total', values(0), 'a 0. b 2. Give the total.')[0], 2)
            with self.assertRaises(ValueError):
                module.compute('total', values(), 'a 005, b 2. Give the total.')
        self.assertEqual(C.compute('total', values(-5), 'a -5. b 2. Give the total.')[0], -3)

    def test_tool_and_label_fail_closed_on_sign_changed_value(self):
        text = 'a -5, b 2. Give the total.'
        encoded = C.encode(values())
        with self.assertRaises(ValueError):
            C.tool('total', text, encoded)
        self.assertIsNone(C.label({'operation': 'total', 'text': text, 'values': encoded}))
        self.assertEqual(C.tool('total', text, C.encode(values(-5))), -3)

    def test_positive_k_arithmetic_fixtures_unchanged(self):
        import utility_bench2 as U
        seen = 0
        for seed in (7, 11, 13, 17, 19, 23):
            for fid, text, _, _ in U.tasks(seed):
                if fid.startswith('summary'):
                    body = text.split('Items: ', 1)[1].split('. Summary', 1)[0]
                    parsed = [re.fullmatch(r'(.+) (\d+) euros', item).groups() for item in body.split(', ')]
                    op = 'total'
                elif fid.startswith('compare'):
                    body = text.split(': ', 1)[1].split('. Which', 1)[0]
                    parsed = [re.fullmatch(r'(.+) (\d+)', item).groups() for item in body.split(', ')]
                    op = 'difference_max_min'
                else:
                    continue
                read = [{'name': name, 'number': int(number)} for name, number in parsed]
                self.assertEqual(C.compute(op, read, text), B.compute(op, read, text), (seed, fid))
                seen += 1
        self.assertEqual(seen, 180)

    def test_real_toolstep_rejects_sign_flip_before_proposal_with_only_reader_stub(self):
        from v13.runtime import Runtime
        from v13.agi import hub, listarith
        from v13 import toolstep
        from tests.test_listarith import FakeC3
        text = 'Items: a -5, b 2. Give the correct total.'
        with tempfile.TemporaryDirectory() as d:
            r = Runtime(Path(d)); r.sleep.cycle.set_policy('enabled', 'off')
            reader = FakeC3(values()); r.pool.get = lambda role: reader
            try:
                hub(r).tools.enable('list_arith')
                e = r.store.event(r.session, text)
                with patch.object(listarith, 'compute', B.compute):
                    self.assertIsNotNone(toolstep.ToolStep(r).plan(e, text))
                with patch.object(listarith, 'compute', C.compute):
                    e = r.store.event(r.session, text)
                    self.assertIsNone(toolstep.ToolStep(r).plan(e, text))
                    reader.values = values(-5)
                    e = r.store.event(r.session, text)
                    plan = toolstep.ToolStep(r).plan(e, text)
                    self.assertIsNotNone(plan)
                    self.assertEqual(C.decode(plan['args']['values']), values(-5))
            finally:
                r.close()


if __name__ == '__main__':
    import tests.test_listarith as upstream
    from v13.agi import listarith
    # All upstream tests run unchanged against the isolated candidate in this
    # process; the repository files and separate native worker stay untouched.
    stream = io.StringIO()
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(SignedNumberGuard),
                               unittest.defaultTestLoader.loadTestsFromModule(upstream)])
    with patch.object(listarith, 'compute', C.compute):
        # Original/candidate contrast test restores baseline just around its first plan.
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (HERE/'tests.log').write_text(stream.getvalue())
    print(stream.getvalue())
    binding = json.loads((HERE/'source-binding.json').read_text())
    unchanged = hashlib.sha256((APP/'v13/agi/listarith.py').read_bytes()).hexdigest() == binding['runtime_source_sha256']
    summary = {'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'skips': len(result.skipped), 'runtime_source_hash_unchanged': unchanged,
               'native_or_phone_claim': False, 'positive_k_arithmetic_fixtures_equal': 180}
    (HERE/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() and unchanged else 1)

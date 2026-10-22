from pathlib import Path
import tempfile
import unittest

from v13.agi import hub, listarith as L
from v13.runtime import Runtime
from v13.toolstep import ToolStep
from tests.test_listarith import FakeC3


def values(first):
    return [{'name': 'a', 'number': first}, {'name': 'b', 'number': 2}]


class SignedSource(unittest.TestCase):
    def test_sign_flip_rejected_and_exact_negative_computes(self):
        for minus in ('-', '\u2212'):
            text = 'Items: a '+minus+'5, b 2. Give the correct total.'
            with self.subTest(minus=minus):
                with self.assertRaises(ValueError): L.compute('total', values(5), text)
                self.assertEqual(L.compute('total', values(-5), text)[0], -3)
                self.assertEqual(L.compute('difference_max_min', values(-5), text)[0], 7)

    def test_decimal_and_double_sign_parts_never_become_values(self):
        for spelling in ('-5.2', '\u22125.2', '+5.2', '--5', '-+5', '+-5'):
            with self.subTest(spelling=spelling), self.assertRaises(ValueError):
                L.compute('total', values(5), 'Items: a '+spelling+', b 2. Give the total.')

    def test_positive_sign_and_sentence_period(self):
        self.assertEqual(L.compute('total', values(5), 'a +5. b 2. Give the total.')[0], 7)

    def test_wrong_reader_sign_is_blocked_before_tool_proposal(self):
        text = 'Items: a -5, b 2. Give the correct total.'
        with tempfile.TemporaryDirectory() as d:
            r = Runtime(Path(d)); r.sleep.cycle.set_policy('enabled', 'off')
            reader = FakeC3(values(5)); r.pool.get = lambda role: reader
            try:
                hub(r).tools.enable('list_arith')
                self.assertIsNone(ToolStep(r).plan(r.store.event(r.session, text), text))
                reader.values = values(-5)
                proposal = ToolStep(r).plan(r.store.event(r.session, text), text)
                self.assertIsNotNone(proposal)
                self.assertEqual(L.decode(proposal['args']['values']), values(-5))
            finally:
                r.close()

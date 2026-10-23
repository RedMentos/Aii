"""Software-only adversarial tests. These are NOT native model/Redmi evidence."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import torch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'lp3_memory_key_candidate.py'

# The repository's LP2 fixture import is supplied by a lightweight test fixture
# when running this standalone package; integration must use real LP2 source.
import sys
import types
fixture = types.ModuleType('lp2_assignment_objective')
fixture.FACTS = [(f'Q{i}', f'A{i}', [f'a{i}']) for i in range(16)]
fixture.HELDOUT = [(i, f'H{i}') for i in range(16)]
fixture.NEAR_MISS = [('N', ['x'])]
prior = sys.modules.get('lp2_assignment_objective')
sys.modules['lp2_assignment_objective'] = fixture
try:
    spec = importlib.util.spec_from_file_location('lp3_memory_key_candidate', SCRIPT)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
finally:
    if prior is None: sys.modules.pop('lp2_assignment_objective', None)
    else: sys.modules['lp2_assignment_objective'] = prior


class TestLP3(unittest.TestCase):
    def setUp(self):
        self.bank = torch.eye(16)
        self.values = tuple(f'A{i}' for i in range(16))

    def test_correct_and_shifted_values_are_different(self):
        raw = mod.retrieve(self.bank, self.bank, self.values)
        shifted = mod.retrieve(self.bank, self.bank, self.values[1:] + self.values[:1])
        self.assertEqual(raw, list(self.values))
        self.assertEqual(shifted[0], 'A1')
        self.assertNotEqual(raw, shifted)

    def test_zero_query_abstains(self):
        self.assertEqual(mod.retrieve(torch.zeros(1,16), self.bank, self.values), [None])

    def test_bad_latents_and_ambiguous_banks_rejected(self):
        with self.assertRaises(ValueError): mod.retrieve(torch.ones(1,16), self.bank*float('nan'), self.values)
        with self.assertRaises(ValueError): mod.retrieve(torch.ones(1,15), self.bank, self.values)
        with self.assertRaises(ValueError): mod.retrieve(self.bank, self.bank, ('x',)*16)
        duplicate = self.bank.clone(); duplicate[1] = duplicate[0]
        self.assertIsNone(mod.retrieve(self.bank[:1], duplicate, self.values)[0])

    def test_predictor_receives_gradient_and_shift_control_is_wrong(self):
        torch.set_num_threads(1)
        p, metrics = mod.fit_predictor(self.bank, self.bank, 31, steps=10)
        self.assertEqual(metrics['steps'], 10)
        self.assertGreater(sum(float(x.detach().abs().sum()) for x in p.parameters()), 0)
        self.assertEqual(mod.retrieve(self.bank + p(self.bank), self.bank, self.values), list(self.values))
        r = mod.evaluate(self.bank, self.bank, self.bank, list(self.values), self.bank[:1], seed=31)
        self.assertEqual(r['zero_intervention']['abstain'], 16)
        self.assertEqual(r['value_shift']['correct'], 0)
        self.assertEqual(r['predicted']['correct'], 16)

    def test_incomplete_never_passes(self):
        self.assertEqual(mod.verdict([]), 'LP3_INCOMPLETE')


    def test_state_scaling_does_not_change_prediction(self):
        torch.set_num_threads(1)
        a = mod.evaluate(self.bank, self.bank, self.bank, list(self.values), self.bank[:1], seed=31)
        b = mod.evaluate(self.bank * 5, self.bank * 3, self.bank * 17,
                         list(self.values), self.bank[:1] * 11, seed=31)
        self.assertEqual(a['outputs'], b['outputs'])

    def test_audit_detects_tampered_aggregate(self):
        torch.set_num_threads(1)
        row = mod.evaluate(self.bank, self.bank, self.bank, list(self.values), self.bank[:1], seed=31)
        mod.audit_rows([row])
        row['predicted']['correct'] += 1
        with self.assertRaises(ValueError): mod.audit_rows([row])

    def test_zero_intervention_is_required_by_verdict(self):
        torch.set_num_threads(1)
        import copy
        one = mod.evaluate(self.bank, self.bank, self.bank, list(self.values), self.bank[:1], seed=31)
        rows = [dict(copy.deepcopy(one), seed=seed) for seed in mod.SEEDS]
        rows[0]['outputs']['zero_intervention'][0] = self.values[0]
        rows[0]['zero_intervention'] = mod.score(rows[0]['expected'], rows[0]['outputs']['zero_intervention'])
        self.assertEqual(mod.verdict(rows), 'LP3_ZERO_INTERVENTION_FAILED')

    def test_chat_template_used_for_prompt_encoding(self):
        class Tok:
            def apply_chat_template(self, messages, add_generation_prompt, tokenize):
                self.last = messages
                return 'TEMPLATE:' + messages[0]['content']
            def __call__(self, text, add_special_tokens, return_tensors):
                assert text.startswith('TEMPLATE:')
                return {'input_ids': torch.tensor([[1, 2]])}
        class Model:
            def __call__(self, input_ids, output_hidden_states):
                return types.SimpleNamespace(hidden_states=[torch.tensor([[[3., 4.], [5., 6.]]])])
        tok = Tok()
        out = mod.encode(Model(), tok, ['hello'])
        self.assertEqual(tok.last[0]['content'], 'hello')
        self.assertEqual(out.tolist(), [[5., 6.]])

    def test_closed_report_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'report.json'
            h = mod.write_atomic(path, {'a': 1})
            self.assertEqual(h, __import__('hashlib').sha256(path.read_bytes()).hexdigest())
            with self.assertRaises(FileExistsError): mod.write_atomic(path, {'a': 2})
            self.assertEqual(json.loads(path.read_text()), {'a': 1})


if __name__ == '__main__': unittest.main()

"""Synthetic admission regressions. NOT native Android measurements."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "scripts" / "prefill_envelope.py"
spec = importlib.util.spec_from_file_location("prefill_envelope", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class PrefillEnvelopeTests(unittest.TestCase):
    def test_no_tiny_prompt_extrapolation(self):
        x = [{"role":"C3","prompt_tokens":30,"prefill_ms":200,"status":"OK"}]
        self.assertFalse(m.estimate(x,"C3",617,30000)["admit"])
    def test_real_failure_never_promoted(self):
        x = [{"role":"C3","prompt_tokens":617,"prefill_ms":28720,"status":"DEADLINE"}]
        self.assertEqual(m.estimate(x,"C3",617,30000)["evidence"],"INSUFFICIENT")
    def test_observed_sufficient_with_reserve(self):
        x = [{"role":"C3","prompt_tokens":700,"prefill_ms":5000,"status":"OK"}]
        self.assertTrue(m.estimate(x,"C3",617,30000)["admit"])
    def test_guard_rejects(self):
        x = [{"role":"B1","prompt_tokens":700,"prefill_ms":24000,"status":"OK"}]
        self.assertFalse(m.estimate(x,"B1",617,30000)["admit"])
    def test_role_isolation(self):
        x = [{"role":"B2","prompt_tokens":700,"prefill_ms":100,"status":"OK"}]
        self.assertFalse(m.estimate(x,"B1",100,30000)["admit"])
    def test_invalid_inputs(self):
        with self.assertRaises(ValueError): m.estimate([],"C3",0,30000)
        with self.assertRaises(ValueError): m.estimate([],"C3",10,30000,safety=.5)

if __name__ == "__main__":
    unittest.main()

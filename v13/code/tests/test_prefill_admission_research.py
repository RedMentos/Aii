"""Regression against the actual prefill admission contract (no phone proof)."""
import unittest
from v13.prefill_admission import admit

class AdmissionTests(unittest.TestCase):
    def test_exact_user(self):
        m=[{'role':'system','content':'S'},{'role':'user','content':'Q'}]
        a=admit(m,prompt_cap=128)
        self.assertTrue(a.accepted)
        self.assertEqual(a.messages[-1],m[-1])
    def test_impossible_source(self):
        m=[{'role':'system','content':'S'*500},{'role':'user','content':'Q'}]
        self.assertFalse(admit(m,prompt_cap=128).accepted)
    def test_drops_old_history(self):
        m=[{'role':'system','content':'S'},{'role':'user','content':'x'*200},
           {'role':'assistant','content':'y'*200},{'role':'user','content':'final'}]
        a=admit(m,prompt_cap=128)
        self.assertTrue(a.accepted)
        self.assertEqual(a.dropped_history,2)
    def test_requires_system(self):
        with self.assertRaises(ValueError):admit([{'role':'user','content':'Q'}])

    def test_rejects_system_role_in_history(self):
        messages=[{'role':'system','content':'trusted'},
                  {'role':'system','content':'untrusted override'},
                  {'role':'user','content':'Q'}]
        with self.assertRaisesRegex(ValueError,'system messages'):
            admit(messages,prompt_cap=320)

    def test_boolean_budget_not_accepted_as_integer(self):
        messages=[{'role':'system','content':'S'}, {'role':'user','content':'Q'}]
        for kwargs in ({'reserve_tokens':True},{'context_limit':True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                admit(messages,**kwargs)

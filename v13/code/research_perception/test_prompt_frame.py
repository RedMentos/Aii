import unittest
from prompt_frame import preflight

class FrameTests(unittest.TestCase):
    def test_frame_overhead_is_counted(self):
        self.assertEqual(preflight('hello',lambda s:'SYSTEM'*20+s,len,100,1).status,'CONTEXT_OVERFLOW')
    def test_source_must_survive(self):
        self.assertEqual(preflight('hello',lambda s:'SYSTEM',len,100,1).status,'SOURCE_NOT_PRESERVED')
    def test_prefill_cap(self):
        self.assertEqual(preflight('hello',lambda s:'SYS'+s,len,100,10,7).status,'PREFILL_BUDGET_EXCEEDED')
    def test_admitted(self):
        r=preflight('hello',lambda s:'SYS'+s,len,100,10,30)
        self.assertEqual((r.status,r.tokens,r.prompt),('ADMITTED',8,'SYShello'))
    def test_unavailable_fails_closed(self):
        self.assertEqual(preflight('hello',lambda s:s,lambda s:1/0,100,0).status,'FRAME_OR_TOKENIZER_UNAVAILABLE')
    def test_invalid_counter(self):
        self.assertEqual(preflight('hello',lambda s:s,lambda s:True,100,0).status,'INVALID_TOKEN_COUNT')
    def test_budget_validation(self):
        for cap,res in [(True,0),(10,10),(10,-1),(0,0)]:
            with self.subTest(cap=cap,res=res),self.assertRaises(ValueError):
                preflight('hi',lambda s:s,len,cap,res)
if __name__=='__main__': unittest.main()

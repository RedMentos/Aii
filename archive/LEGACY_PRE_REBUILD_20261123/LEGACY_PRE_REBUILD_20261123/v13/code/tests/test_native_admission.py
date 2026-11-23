import unittest
from v13.native_admission import admit, admit_coalition

class AdmissionTests(unittest.TestCase):
    def test_prefill_is_budgeted_not_only_decode(self):
        x=admit("C3_LANGUAGE",prompt_tokens=630,output_tokens=10,
                remaining_seconds=30,prefill_tokens_per_second=20,
                decode_tokens_per_second=10)
        self.assertFalse(x.accepted)
        self.assertEqual(x.reason,"PREFILL_DECODE_BUDGET")

    def test_measured_short_prompt(self):
        x=admit("C3_LANGUAGE",prompt_tokens=40,output_tokens=10,
                remaining_seconds=30,prefill_tokens_per_second=100,
                decode_tokens_per_second=10)
        self.assertTrue(x.accepted)

    def test_unknown_rate_fails_closed(self):
        x=admit("B1_DETAIL",prompt_tokens=300,output_tokens=20,
                remaining_seconds=50,prefill_tokens_per_second=None,
                decode_tokens_per_second=10)
        self.assertEqual(x.reason,"NO_MEASURED_RATE")

    def test_coalition_preserves_order_and_refusal(self):
        requests=[("B1_DETAIL",600,20),("B2_GIST",300,20),("C3_LANGUAGE",200,20)]
        rates={r:{"prefill_tps":100,"decode_tps":10} for r,_,_ in requests}
        result=admit_coalition(requests,remaining_seconds=10,rates=rates)
        self.assertEqual(len(result),2)
        self.assertTrue(result[0].accepted)
        self.assertFalse(result[1].accepted)

    def test_rejects_invalid_or_unmeasured_inputs(self):
        for value in (0,-1,float("nan"),float("inf")):
            with self.assertRaises(ValueError):
                admit("B1_DETAIL",prompt_tokens=10,output_tokens=1,
                      remaining_seconds=30,prefill_tokens_per_second=value,
                      decode_tokens_per_second=5)
        with self.assertRaises(ValueError):
            admit("B1_DETAIL",prompt_tokens=True,output_tokens=1,
                  remaining_seconds=30,prefill_tokens_per_second=5,
                  decode_tokens_per_second=5)

if __name__=="__main__":unittest.main()

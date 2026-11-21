"""Synthetic negative/positive tests; no Android hardware claims."""
import unittest
from redmi_receipt_gate import evaluate

def turn(i):
    return dict(scenario=("greeting", "arithmetic", "ambiguity", "memory_recall", "cross_organ")[i%5], turn_id=str(i), receipt_id="private-receipt-"+str(i),
                installed_sha="a"*40, evidence="OWNER_CONSENTED_REDMI",
                status="FINAL", correct=True, source_bound=True,
                total_ms=200, first_token_ms=100,
                b1_attempted=1,b1_delivered=1,b1_consumed=1,
                b2_attempted=1,b2_delivered=1,b2_consumed=1)

def rows():
    return [turn(i) for i in range(20)]

class GateTests(unittest.TestCase):
    def test_consistent_is_not_phone_verified(self):
        result=evaluate({"turns":rows()})
        self.assertEqual(result["status"],"METADATA_CONSISTENT")
        self.assertFalse(result["device_independently_verified"])
    def test_fewer_than_twenty(self):
        self.assertEqual(evaluate({"turns":rows()[:19]})["status"],"BLOCKED")
    def test_wrong_answer(self):
        x=rows();x[0]["correct"]=False
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_missing_b2_consumer(self):
        x=rows()
        for r in x:r["b2_consumed"]=0
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_offers_only_on_greetings_do_not_prove_cross_organ(self):
        x=rows()
        for r in x:
            if r["scenario"]=="cross_organ":
                r["b1_consumed"]=0
                r["b2_consumed"]=0
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_one_organ_missing_in_cross_organ_turns(self):
        x=rows()
        for r in x:
            if r["scenario"]=="cross_organ":
                r["b2_consumed"]=0
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_synthetic_is_not_redmi(self):
        x=rows();x[0]["evidence"]="SYNTHETIC"
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_private_text_rejected(self):
        x=rows();x[0]["prompt"]="secret"
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_duplicate_receipt_rejected(self):
        x=rows();x[1]["receipt_id"]=x[0]["receipt_id"]
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_latency_and_accounting(self):
        x=rows();x[0]["first_token_ms"]=201;x[1]["b1_consumed"]=2
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_missing_diversity(self):
        x=rows()
        for r in x:r["scenario"]="greeting"
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_nested_private_metadata(self):
        x=rows();x[0]["telemetry"]={"payload":[{"transcript":"private"}]}
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_invalid_root(self):
        self.assertEqual(evaluate([])["status"],"INVALID")
    def test_unhashable_identifiers_are_blocked_not_crash(self):
        x=rows();x[0]["turn_id"]=["malformed"];x[1]["receipt_id"]={"bad":"id"}
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_reject_unknown_fields_even_without_private_key_names(self):
        x=rows(); x[0]["notes"]="private chat content under innocent field"
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
        self.assertEqual(evaluate({"turns":rows(),"debug":"private"})["status"],"INVALID")
    def test_both_organs_must_be_consumed_in_same_cross_organ_turn(self):
        x=rows()
        cross=[r for r in x if r["scenario"]=="cross_organ"]
        for r in cross: r["b2_consumed"]=0
        cross[0]["b1_consumed"]=0
        cross[0]["b2_consumed"]=1
        self.assertEqual(evaluate({"turns":x})["status"],"BLOCKED")
    def test_missing_input(self):
        self.assertEqual(evaluate({"turns":None})["status"],"INVALID")

if __name__=="__main__":
    unittest.main()

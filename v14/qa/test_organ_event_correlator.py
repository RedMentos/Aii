"""Synthetic only: no device/native acceptance claim."""
import unittest
from organ_event_correlator import correlate

def trace():
    out=[]
    for role in ("B1","B2"):
        for i,kind in enumerate(("offer_created","offer_delivered","offer_consumed")):
            out.append(dict(turn_id="t1",event_id=f"{role}{i}",kind=kind,role=role,offer_id=f"{role}o",source_id="src1",consumer=("BUS","C4","C4")[i],timestamp_ms=i+1))
        out.append(dict(turn_id="t1",event_id=f"{role}i",kind="c3_input",role=role,offer_id=f"{role}o",source_id="src1",consumer="C3",timestamp_ms=4))
    out.append(dict(turn_id="t1",event_id="final",kind="final",role="C3",offer_id="none",source_id="src1",consumer="USER",timestamp_ms=5))
    return out

class CorrelationTests(unittest.TestCase):
    def test_valid_trace_not_device_proof(self):
        r=correlate(trace())
        self.assertEqual(r["status"],"TRACE_CONSISTENT")
        self.assertTrue(r["turns"]["t1"]["cross_organ_trace"])
        self.assertFalse(r["independent_device_proof"])
    def test_missing_delivery(self):
        self.assertEqual(correlate([e for e in trace() if e["event_id"]!="B11"])["status"],"BLOCKED")
    def test_changed_source(self):
        x=trace();x[2]["source_id"]="other"
        self.assertEqual(correlate(x)["status"],"BLOCKED")
    def test_duplicate(self):
        x=trace();x.append(x[0].copy())
        self.assertEqual(correlate(x)["status"],"BLOCKED")
    def test_early_final(self):
        x=trace();x[-1]["timestamp_ms"]=3
        self.assertEqual(correlate(x)["status"],"BLOCKED")
    def test_unproven_c3_reference(self):
        x=trace();next(e for e in x if e["event_id"]=="B2i")["offer_id"]="wrong"
        self.assertEqual(correlate(x)["status"],"BLOCKED")
    def test_bad_timestamp(self):
        x=trace();x[0]["timestamp_ms"]="now"
        self.assertEqual(correlate(x)["status"],"BLOCKED")
    def test_private_fields_rejected(self):
        x=trace();x[0]["prompt"]="private"
        self.assertEqual(correlate(x)["status"],"BLOCKED")
    def test_out_of_order(self):
        x=trace();x[1]["timestamp_ms"]=0
        self.assertEqual(correlate(x)["status"],"BLOCKED")

if __name__=="__main__":unittest.main()

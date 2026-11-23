import unittest
from v13.a5_ui_admission_bridge import ui_to_admission, admit_ui

def fixture():
    return {"modality":"ui","source_ref":{"source_id":"ui-1","sha256":"a"*64},"segments":[{"start_ms":10,"end_ms":40,"consent_receipt_ref":"receipt-1","finality":"FINAL","event_kind":"window_changed","learning_authority":False,"action_authority":False}]}

class TestUI(unittest.TestCase):
    def test_final(self):
        p=ui_to_admission(fixture(),consent_active=True)
        self.assertEqual(p.modality,"ui")
        self.assertNotIn("receipt",p.summary)
    def test_consent(self):
        for c in (False,None,1,"true"):
            with self.subTest(c=c),self.assertRaises(PermissionError): ui_to_admission(fixture(),consent_active=c)
    def test_receipt(self):
        p=fixture();p["segments"][0]["consent_receipt_ref"]=""
        with self.assertRaises(PermissionError):ui_to_admission(p,consent_active=True)
    def test_authority(self):
        for key in ("learning_authority","action_authority"):
            p=fixture();p["segments"][0][key]=True
            with self.assertRaises(PermissionError):ui_to_admission(p,consent_active=True)
    def test_provisional(self):
        p=fixture();p["segments"][0]["finality"]="PROVISIONAL"
        self.assertFalse(ui_to_admission(p,consent_active=True).final)
        self.assertFalse(admit_ui(p,consent_active=True,token_budget=500).selected)
    def test_time(self):
        for val in (-1,1.2,True,100000):
            p=fixture();p["segments"][0]["end_ms"]=val
            with self.subTest(val=val),self.assertRaises(ValueError):ui_to_admission(p,consent_active=True)
    def test_untrusted_text(self):
        p=fixture();p["segments"][0]["event_kind"]="password entered"
        with self.assertRaises(ValueError):ui_to_admission(p,consent_active=True)
    def test_source(self):
        p=fixture();p["source_ref"]["sha256"]="oops"
        with self.assertRaises(ValueError):ui_to_admission(p,consent_active=True)
    def test_priority(self):
        with self.assertRaises(ValueError):ui_to_admission(fixture(),consent_active=True,priority=True)
    def test_budget(self):
        self.assertFalse(admit_ui(fixture(),consent_active=True,token_budget=0).selected)
        self.assertEqual(len(admit_ui(fixture(),consent_active=True,token_budget=500).selected),1)

if __name__=="__main__":unittest.main()

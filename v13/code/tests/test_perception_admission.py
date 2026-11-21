import unittest
from v13.perception_admission import Evidence, admit

class AdmissionTests(unittest.TestCase):
    def test_preserves_user_and_reports_omission(self):
        a=admit([Evidence("user","exact",60,"user",required=True),Evidence("memory","old",80,"memory")],100,10)
        self.assertEqual((tuple(e.source_id for e in a.accepted),a.omitted,a.status),(("user",),("memory",),"PARTIAL_SOURCE_BOUND"))
    def test_required_over_budget(self):
        self.assertEqual(admit([Evidence("user","exact",100,"user",required=True)],99).status,"REQUIRED_OVER_BUDGET")
    def test_consent_blocked(self):
        self.assertEqual(admit([Evidence("mic","raw",1,"audio",False,True)],50).status,"CONSENT_BLOCKED")
    def test_optional_consent(self):
        self.assertEqual(admit([Evidence("u","hi",1,"user",True,True),Evidence("screen","secret",2,"ui",False)],20).omitted,("screen",))
    def test_duplicate_source(self):
        with self.assertRaises(ValueError): admit([Evidence("x","a",1,"a"),Evidence("x","b",1,"b")],10)
    def test_native_count_required(self):
        with self.assertRaises(ValueError): admit([Evidence("x","hello",0,"a")],10)
    def test_order_and_reserve(self):
        a=admit([Evidence("a","a",2,"audio"),Evidence("u","u",3,"user",required=True),Evidence("b","b",2,"ui")],8,1)
        self.assertEqual((tuple(e.source_id for e in a.accepted),a.token_count),(("a","u","b"),7))
if __name__=="__main__": unittest.main()

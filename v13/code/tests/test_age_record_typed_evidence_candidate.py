"""Direct AgeControl.record evidence admission, RED-first Store tests."""
import tempfile
import unittest
from pathlib import Path
from v13 import age
from v13.config import initialize
from v13.store import Store

GOOD = {"experience":10000,"competence":.95,"stability":.95,
        "retention":.98,"calibration":.9,"memory_health":.97,
        "safe_self_control":.999,"regression_pass":True}

class AgeRecordTypedEvidenceCandidate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.cfg=initialize(self.home)|{"user_stage_cap":5}
        self.store=Store(self.home)
        self.ctl=age.AgeControl(self.store,self.cfg)
    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()
    def assert_rejects_without_write(self,metrics,evidence_id=None):
        before=self.ctl.state()
        telemetry=self.store.rows("SELECT * FROM telemetry")
        with self.assertRaisesRegex(ValueError,"AGE_EVIDENCE"):
            self.ctl.record("system",metrics,evidence_id=evidence_id)
        self.assertEqual(self.ctl.state(),before)
        self.assertEqual(self.store.rows("SELECT * FROM telemetry"),telemetry)
    def test_nonfinite_boolean_out_of_range_quality_rejected(self):
        for value in (True,False,float("nan"),float("inf"),-float("inf"),-.01,1.01,"0.9"):
            with self.subTest(value=repr(value)):
                self.assert_rejects_without_write(dict(GOOD,competence=value))
    def test_experience_and_regression_flag_types_rejected(self):
        for value in (True,-1,2.0,"100",float("inf")):
            with self.subTest(experience=repr(value)):
                self.assert_rejects_without_write(dict(GOOD,experience=value))
        for value in (1,0,"true"):
            with self.subTest(regression_pass=repr(value)):
                self.assert_rejects_without_write(dict(GOOD,regression_pass=value))
    def test_explicit_evidence_id_must_be_nonempty_exact_string(self):
        for value in (True,False,1,0,1.0,"",[],{},b"evidence"):
            with self.subTest(evidence_id=repr(value)):
                self.assert_rejects_without_write(GOOD,evidence_id=value)
    def test_invalid_metrics_container_rejected(self):
        for value in (None,[],"metrics",5):
            with self.subTest(metrics=repr(value)):
                self.assert_rejects_without_write(value)
    def test_valid_partial_evidence_remains_nonpromoting(self):
        result=self.ctl.record("system",{"competence":.4},evidence_id="partial-1")
        self.assertEqual(result["stage"],0)
        self.assertNotIn("proposal",result)
        self.assertEqual(self.ctl.state()[0]["system"]["evidence_count"],1)
        self.assertFalse(self.ctl.allowed("short_dream"))
    def test_unmeasured_none_metrics_are_recorded_without_gate_credit(self):
        incomplete=dict(GOOD,competence=None,retention=None,calibration=None,
                        stability=None,safe_self_control=None,regression_pass=None)
        result=self.ctl.record("system",incomplete,evidence_id="unmeasured-1")
        self.assertEqual(result["stage"],0)
        self.assertNotIn("proposal",result)
        self.assertEqual(self.ctl.state()[0]["system"]["evidence_count"],1)
        self.assertEqual(self.ctl.state()[0]["system"]["maturity"]["competence"],0.)
        self.assertFalse(self.ctl.allowed("short_dream"))
        # False regression with unavailable retention is a maintenance miss,
        # not evidence of severe retention collapse.
        a=age.AgeControl(self.store,self.cfg,build_ceiling=5)
        for i in range(3):a.record("language",GOOD,evidence_id="warm-"+str(i))
        self.assertEqual(a.state()[0]["capabilities"]["language"]["stage"],1)
        a.record("language",dict(GOOD,retention=None,regression_pass=False),
                 evidence_id="missing-retention")
        self.assertEqual(a.state()[0]["capabilities"]["language"]["stage"],1)

    def test_valid_full_evidence_and_restart_remain_age_zero(self):
        for i in range(4):
            self.ctl.record("system",GOOD,evidence_id="good-"+str(i))
        self.assertEqual(self.ctl.system_stage(),0)
        self.assertFalse(self.ctl.allowed("short_dream"))
        with self.assertRaises(ValueError):
            self.ctl.record("system",GOOD,evidence_id="good-0")
        before=self.ctl.state()
        self.store.close()
        self.store=Store(self.home)
        self.ctl=age.AgeControl(self.store,self.cfg)
        self.assertEqual(self.ctl.state(),before)
        self.assertFalse(self.ctl.allowed("short_dream"))

if __name__=="__main__":
    unittest.main()

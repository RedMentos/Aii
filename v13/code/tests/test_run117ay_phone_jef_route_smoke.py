"""Run117AY optional phone installer smoke without modifying registered cohorts."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import install_selftest as original
from scripts import install_selftest_run117ay as smoke

class Run117AYPhoneJefRouteSmoke(unittest.TestCase):
    def test_original_registered_cohorts_and_default_are_immutable(self):
        smoke._cohorts_unchanged()
        self.assertEqual(set(original.COHORTS),set(smoke.ORIGINAL))
        self.assertEqual(original.run_bounded.__defaults__,(120,"legacy_run97"))
        self.assertEqual(len(original.COHORTS["legacy_run97"]),18)
        self.assertEqual(len(original.COHORTS["run102_c3"]),18)
        self.assertEqual(len(original.COHORTS["run104_c3_c5_exit"]),21)
        for name,h in smoke.ORIGINAL.items():
            self.assertEqual(sha256(json.dumps(original.COHORTS[name],
                separators=(",",":")).encode()).hexdigest(),h)
        self.assertIn('scripts/install_selftest.py" --cohort run102_c3',
                      (smoke.APP/"setup.sh").read_text())

    def test_exact_25_method_allowlist_and_file_origins(self):
        self.assertEqual(len(smoke.CASES),25)
        self.assertEqual(len(set(smoke.CASES)),25)
        self.assertEqual(smoke.CASES[:21],
                         original.SMOKE_CASES_RUN104_C3_C5_EXIT)
        self.assertEqual(smoke.CASES[21:],smoke.EXTRA)
        self.assertEqual(original.load_exact_suite(smoke.CASES).countTestCases(),25)

    def test_real_bounded_25_case_worker(self):
        self.assertEqual(smoke.run_bounded(120),0)

    def test_timeout_types_and_bounds_fail_before_worker(self):
        for seconds in (0,121,True,False,0.5,None,"120"):
            with self.subTest(seconds=seconds):
                with self.assertRaisesRegex(ValueError,"RUN117AY_TIMEOUT"):
                    smoke.run_bounded(seconds)

    def test_missing_or_substituted_method_fails_closed(self):
        with patch.object(smoke,"CASES",smoke.CASES[:-1]+(
                "test_missing_fake.Forged.test_missing",)):
            with self.assertRaisesRegex(ValueError,
                                        "RUN117AY_REGISTERED_COHORT_OR_EXTENSION_RED"):
                smoke.run_bounded(120)
        with patch.object(smoke,"ORIGINAL",
                          dict(smoke.ORIGINAL,run102_c3="0"*64)):
            with self.assertRaisesRegex(ValueError,
                                        "RUN117AY_ORIGINAL_COHORT_HASH_RED"):
                smoke.run_bounded(120)

    def test_timeout_kills_and_reaps_child_process_group(self):
        fake=Mock(pid=32177)
        fake.wait.side_effect=[subprocess.TimeoutExpired("worker",1),-9]
        with patch.object(smoke.subprocess,"Popen",return_value=fake), \
             patch.object(smoke.os,"killpg") as kill:
            self.assertEqual(smoke.run_bounded(1),124)
        kill.assert_called_once_with(32177,smoke.signal.SIGKILL)
        self.assertEqual(fake.wait.call_count,2)

    def test_worker_import_error_is_red_not_success(self):
        with patch.object(smoke.smoke,"load_exact_suite",
                          side_effect=ImportError("missing original")):
            self.assertEqual(smoke.worker(),2)

if __name__=="__main__":
    unittest.main()

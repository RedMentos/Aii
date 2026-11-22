"""Run117CS exact original Run12J C2 route hardening in reviewed source chain."""
import hashlib
from pathlib import Path
import unittest

from scripts import integrated_candidates as I
from scripts import run117cr_source_chain_drift_audit as A
from scripts.source_handoff_candidate import sources


EXPECTED = {
    "v13/runners.py": "87312169d871bcb1498ad028df058b0ab6e100f6e51c011ead4b9ecfb1b831c5",
    "v13/memory_server.py": "78b1eb46b11a55c8ba1a37fabd99bdf480d33f62a2c0d7a97822abc68e5a4672",
    "v13/runtime.py": "8a403bffd1c2b14d9caa798cf17ea3c299cea5796115bad40cbaf9a2054072ed",
    "v13/store.py": "fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980",
}


class Run12JReviewedChain(unittest.TestCase):
    def test_exact_complete_four_file_chain_matches_live_bytes(self):
        self.assertEqual(set(I.NAMES), set(EXPECTED))
        self.assertIn("c2_unique_native_route_run12j", I.INTEGRATED)
        before = {name: (I.ROOT / name).read_bytes() for name in I.NAMES}
        reviewed = I.integrated_sources()
        for name in I.NAMES:
            self.assertEqual(reviewed[name].encode("utf-8"), before[name], name)
            self.assertEqual(hashlib.sha256(before[name]).hexdigest(),
                             EXPECTED[name], name)
        self.assertEqual(before, {name: (I.ROOT / name).read_bytes()
                                  for name in I.NAMES})
        self.assertIn("observed=observation(control)", reviewed["v13/runtime.py"])
        self.assertIn("observed['proposal_count']==1", reviewed["v13/runtime.py"])
        self.assertIn("observed['ambiguous'] is False", reviewed["v13/runtime.py"])
        self.assertNotIn("def routes(obj):", reviewed["v13/runtime.py"])

    def test_original_guard_accepts_only_complete_live_chain(self):
        original, candidate = sources()
        self.assertTrue(original)
        self.assertTrue(candidate)
        self.assertIn("v13/runtime.py", original)
        self.assertIn("v13/runtime.py", candidate)
        self.assertEqual(I.integrated_sources()["v13/runtime.py"],
                         (I.ROOT / "v13/runtime.py").read_text())

    def test_reapplying_transform_or_changing_anchor_fails_closed(self):
        exact = I.integrated_sources()
        with self.assertRaisesRegex(ValueError, "Integrated anchor changed"):
            I.run12j_native_route_admission(exact)
        mixed = dict(exact)
        mixed["v13/runtime.py"] = mixed["v13/runtime.py"].replace(
            "observed['proposal_count']==1",
            "observed['proposal_count']>=1")
        with self.assertRaisesRegex(ValueError, "Integrated anchor changed"):
            I.run12j_native_route_admission(mixed)

    def test_prior_read_only_drift_audit_now_reports_exact_chain(self):
        report, _, _ = A.audit()
        self.assertEqual(report["status"], "EXACT_REVIEWED_CHAIN", report)
        self.assertEqual(report["changed_files"], [])
        self.assertEqual(report["checked_files"], 4)
        self.assertFalse(report["acceptance_modified"])
        self.assertFalse(report["full_suite_promoted"])
        self.assertEqual(report["jepa_weight"], 0)


if __name__ == "__main__":
    unittest.main()

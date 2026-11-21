import unittest
from v13.a5_timed_fusion import fuse_timed_a5, FusionError

def packet(modality, start, end, status="FINAL"):
    return dict(schema="v13.a5.fixture/1", source=dict(id="fixture", authorized=True, modality=modality),
                start_ms=start, end_ms=end, status=status, action_authority=False,
                learning_authority=False, payload="private observation")

class TestFusion(unittest.TestCase):
    def setUp(self):
        self.a, self.u = packet("audio", 100, 200), packet("ui", 180, 260)
    def test_no_consent(self):
        with self.assertRaises(PermissionError): fuse_timed_a5(self.a, self.u)
    def test_hash_only(self):
        x = fuse_timed_a5(self.a, self.u, consent=True)
        self.assertNotIn("private observation", str(x))
        self.assertEqual(x["route"], "SHADOW")
        self.assertEqual(x["temporal_gap_ms"], 0)
    def test_provisional(self):
        self.a["status"] = "PROVISIONAL"
        self.assertEqual(fuse_timed_a5(self.a, self.u, consent=True)["status"], "PROVISIONAL")
    def test_skew(self):
        self.u["start_ms"], self.u["end_ms"] = 500, 600
        with self.assertRaisesRegex(FusionError, "OUTSIDE_TEMPORAL_WINDOW"):
            fuse_timed_a5(self.a, self.u, consent=True)
    def test_authority(self):
        self.a["learning_authority"] = True
        with self.assertRaisesRegex(FusionError, "AUTHORITY_ESCALATION"):
            fuse_timed_a5(self.a, self.u, consent=True)
    def test_invalid_timestamp(self):
        self.a["start_ms"] = float("nan")
        with self.assertRaisesRegex(FusionError, "INVALID_TIME"):
            fuse_timed_a5(self.a, self.u, consent=True)
    def test_invalid_budget(self):
        with self.assertRaisesRegex(FusionError, "INVALID_BUDGET"):
            fuse_timed_a5(self.a, self.u, consent=True, max_bytes=1)
    def test_unapproved_ui(self):
        self.u["source"]["authorized"] = False
        with self.assertRaisesRegex(FusionError, "UNAUTHORIZED_SOURCE"):
            fuse_timed_a5(self.a, self.u, consent=True)
    def test_budget_too_small(self):
        with self.assertRaisesRegex(FusionError, "ENVELOPE_OVER_BUDGET"):
            fuse_timed_a5(self.a, self.u, consent=True, max_bytes=256)

if __name__ == "__main__":
    unittest.main()

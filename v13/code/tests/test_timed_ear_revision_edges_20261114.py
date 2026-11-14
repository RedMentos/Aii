"""Synthetic RAW EAR reconciliation edge regressions; no native microphone evidence."""
import unittest
from v13.timed_ear_contract import AcousticFrame, TimedEarPacket
from v13.timed_ear_revision import EarRevision, reconcile_ear_revisions


def revision(seq, frames, source="synthetic", scope="synthetic_test", provenance="fixture"):
    return EarRevision(TimedEarPacket(source=source, consent_scope=scope,
                                     frames=tuple(frames), provenance=provenance), seq)


def frame(t, provisional=True):
    return AcousticFrame(t, t + 10, .2, None, .3, provisional=provisional)


class EarRevisionEdgeCases(unittest.TestCase):
    def test_live_and_synthetic_sources_never_join(self):
        with self.assertRaises(PermissionError):
            reconcile_ear_revisions((
                revision(0, [frame(0)]),
                revision(1, [frame(10)], "authorized_feed", "audio_observation")))

    def test_out_of_order_provisional_after_final_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_ear_revisions((
                revision(2, [frame(0)]),
                revision(1, [frame(0, False)])))

    def test_frame_limit_is_enforced_across_revisions(self):
        valid = tuple(revision(i, [frame(i * 10, False)]) for i in range(32))
        self.assertEqual(len(reconcile_ear_revisions(valid).frames), 32)
        oversized = tuple(revision(i, [frame(i * 50 + j * 10)
                                       for j in range(5)]) for i in range(32))
        with self.assertRaises(ValueError):
            reconcile_ear_revisions(oversized)


if __name__ == "__main__":
    unittest.main()

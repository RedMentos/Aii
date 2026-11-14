import unittest
from v13.timed_ear_contract import AcousticFrame, TimedEarPacket
from v13.timed_ear_revision import EarRevision, reconcile_ear_revisions


def packet(frames, source="synthetic", consent="synthetic_test", provenance="fixture", transcript=None, teacher=None):
    return TimedEarPacket(source=source, consent_scope=consent, frames=tuple(frames),
                          provenance=provenance, transcript=transcript, teacher_revision=teacher)


def frame(start, provisional=True, rms=.2):
    return AcousticFrame(start_ms=start, end_ms=start+10, rms=rms,
                         pitch_hz=None, speech_probability=.3, provisional=provisional)


class EarRevisionTests(unittest.TestCase):
    def test_final_replaces_provisional_and_retains_other_frame(self):
        result = reconcile_ear_revisions((
            EarRevision(packet([frame(0),frame(10)]), 0),
            EarRevision(packet([frame(0,False)]), 1)))
        self.assertEqual(len(result.frames),2)
        self.assertFalse(result.frames[0].provisional)
        self.assertTrue(result.frames[1].provisional)
        self.assertFalse(result.percept_packet()["action_authority"])

    def test_no_provisional_regression(self):
        with self.assertRaises(ValueError):
            reconcile_ear_revisions((EarRevision(packet([frame(0,False)]),0),
                                     EarRevision(packet([frame(0)]),1)))

    def test_conflicting_final_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_ear_revisions((EarRevision(packet([frame(0,False)]),0),
                                     EarRevision(packet([frame(0,False,.9)]),1)))

    def test_source_provenance_boundary(self):
        with self.assertRaises(PermissionError):
            reconcile_ear_revisions((EarRevision(packet([frame(0)]),0),
                                     EarRevision(packet([frame(10)],provenance="other"),1)))

    def test_overlap_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_ear_revisions((EarRevision(packet([frame(0)]),0),
                                     EarRevision(packet([AcousticFrame(5,15,.2,None,.3)]),1)))

    def test_duplicate_sequence_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_ear_revisions((EarRevision(packet([frame(0)]),0),
                                     EarRevision(packet([frame(10)]),0)))

    def test_teacher_conflict_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_ear_revisions((
                EarRevision(packet([frame(0)],transcript="a",teacher="teacher-1"),0),
                EarRevision(packet([frame(0,False)],transcript="b",teacher="teacher-2"),1)))

    def test_out_of_order_revisions_sorted(self):
        result = reconcile_ear_revisions((
            EarRevision(packet([frame(10,False)]),2),
            EarRevision(packet([frame(0,False)]),1)))
        self.assertEqual([f.start_ms for f in result.frames],[0,10])


if __name__ == "__main__":
    unittest.main()

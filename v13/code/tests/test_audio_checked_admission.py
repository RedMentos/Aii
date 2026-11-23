"""Synthetic checked A5->C3 route; not a native Redmi benchmark."""
import unittest

from v13.audio_percept_contract import audio_percept_packet
from v13.audio_checked_admission import admit_checked_audio_percept

ARGS = dict(event_id="synthetic-event", generation_id="synthetic-generation",
            source_id="synthetic-source", source_sha256="a"*64,
            start_ms=0, end_ms=20, rms=0.2, zcr=0.1,
            consent_receipt="synthetic-consent")
STORE = {"sha256": "a"*64, "revoked": False, "modality": "audio"}


class CheckedAdmissionTests(unittest.TestCase):
    def packet(self, **changes):
        return audio_percept_packet(**(ARGS | changes))

    def test_valid_source_and_explicit_shadow(self):
        seen = []
        def reader(source_id):
            seen.append(source_id)
            return STORE
        out = admit_checked_audio_percept(self.packet(), reader, max_utf8_bytes=1024)
        self.assertEqual(seen, ["synthetic-source"])
        self.assertEqual(out["status"], "FULL")
        self.assertEqual(out["finality"], "FINAL")
        self.assertEqual(out["source_sha256"], "a"*64)
        self.assertFalse(out["action_authority"])
        self.assertFalse(out["learning_authority"])

    def test_revoked_source_fails_before_admission(self):
        with self.assertRaises(PermissionError):
            admit_checked_audio_percept(self.packet(), lambda _: {**STORE, "revoked": True})

    def test_hash_mismatch_fails_before_admission(self):
        with self.assertRaises(PermissionError):
            admit_checked_audio_percept(self.packet(), lambda _: {**STORE, "sha256": "b"*64})

    def test_missing_source_fails_before_admission(self):
        with self.assertRaises(PermissionError):
            admit_checked_audio_percept(self.packet(), lambda _: None)

    def test_provisional_remains_provisional(self):
        out = admit_checked_audio_percept(self.packet(finality="PROVISIONAL"), lambda _: STORE,
                                          max_utf8_bytes=1024)
        self.assertEqual(out["finality"], "PROVISIONAL")
        self.assertIn("PROVISIONAL", out["prompt_text"])

    def test_tiny_budget_explicit_omission_with_lineage(self):
        out = admit_checked_audio_percept(self.packet(), lambda _: STORE, max_utf8_bytes=0)
        self.assertEqual(out["status"], "OMITTED_BUDGET")
        self.assertEqual(out["prompt_text"], "")
        self.assertEqual(out["omitted_windows"], 1)
        self.assertEqual(out["source_sha256"], "a"*64)

    def test_no_raw_consent_leak(self):
        out = admit_checked_audio_percept(self.packet(), lambda _: STORE, max_utf8_bytes=1024)
        self.assertNotIn("synthetic-consent", str(out))
        self.assertNotIn("synthetic-event", str(out))

    def test_forged_packet_authority_rejected(self):
        packet = self.packet()
        packet["segments"][0]["learning_authority"] = True
        with self.assertRaises(PermissionError):
            admit_checked_audio_percept(packet, lambda _: STORE)

    def test_invalid_budget_rejected(self):
        with self.assertRaises(ValueError):
            admit_checked_audio_percept(self.packet(), lambda _: STORE, max_utf8_bytes=True)

    def test_source_rechecked_on_each_call(self):
        state = {"revoked": False}
        def reader(_):
            return {**STORE, "revoked": state["revoked"]}
        packet = self.packet()
        admit_checked_audio_percept(packet, reader)
        state["revoked"] = True
        with self.assertRaises(PermissionError):
            admit_checked_audio_percept(packet, reader)


if __name__ == "__main__":
    unittest.main()

"""Tests for actual Store.read_source-backed A3 observation contract."""
import json
import unittest
from unittest.mock import Mock

from v13.a3_online_projector import A3Projector
from v13.a3_store_source import observe_stored_features


class TestStoreSource(unittest.TestCase):
    def setUp(self):
        self.payload = json.dumps({"features": [.25, .5], "final": True})
        self.ref = {"source_id": "src_fixture", "sha256": "a"*64,
                    "char_start": 0, "char_end": len(self.payload), "modality": "text"}
        self.store = Mock()
        self.store.read_source.return_value = self.payload
        self.runtime = Mock(store=self.store)
        self.projector = A3Projector(2, 1)

    def test_store_backed_feature_route(self):
        result = observe_stored_features(self.runtime, self.projector, self.ref,
                                        modality="synthetic_audio")
        self.assertEqual(result["a5"]["status"], "SHADOW_STORE_BACKED")
        self.assertEqual(result["a5"]["store_source_sha256"], self.ref["sha256"])
        self.assertFalse(result["jef"]["android_action_allowed"])
        self.assertGreaterEqual(self.store.read_source.call_count, 2)

    def test_reject_provisional_and_partial(self):
        self.store.read_source.return_value = json.dumps({"features": [.25, .5], "final": False})
        with self.assertRaises(PermissionError):
            observe_stored_features(self.runtime, self.projector, self.ref,
                                    modality="synthetic_audio")
        self.store.read_source.return_value = self.payload
        with self.assertRaises(ValueError):
            observe_stored_features(self.runtime, self.projector,
                                    dict(self.ref, char_start=1), modality="synthetic_audio")

    def test_revoked_between_reads(self):
        self.store.read_source.side_effect = [self.payload, ValueError("revoked")]
        with self.assertRaises(PermissionError):
            observe_stored_features(self.runtime, self.projector, self.ref,
                                    modality="synthetic_ui")

    def test_invalid_source_or_action_modality(self):
        with self.assertRaises(ValueError):
            observe_stored_features(self.runtime, self.projector,
                                    dict(self.ref, modality="audio"), modality="synthetic_audio")
        with self.assertRaises(ValueError):
            observe_stored_features(self.runtime, self.projector, self.ref,
                                    modality="android_action")


if __name__ == "__main__":
    unittest.main()

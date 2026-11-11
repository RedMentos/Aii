"""Synthetic-only Android UI observation source admission regression."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from v13.config import initialize
from v13.store import Store
from v13.android_ui_source_candidate import persist_ui_shadow_source, ui_snapshot_text


def fixture():
    return {
        "schema": "v13.android.ui_observation/1",
        "source": "ACCESSIBILITY_APPROVED",
        "capture_authorized": True,
        "redacted": True,
        "consent_receipt_id": "synthetic-consent-1",
        "observation_id": "synthetic-observation-1",
        "nodes": [
            {"class_name": "android.widget.TextView", "text": "Settings"},
            {"content_description": "Back"},
        ],
    }


class AndroidUISourceTests(unittest.TestCase):
    def test_source_roundtrip_and_no_authority(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            initialize(home)
            store = Store(home)
            try:
                result = persist_ui_shadow_source(store, fixture())
                self.assertEqual(store.read_source(result["source_ref"]), ui_snapshot_text(fixture()))
                self.assertFalse(result["percept_packet_created"])
                self.assertEqual(result["action_authority"], 0)
                self.assertIsNone(store.one("SELECT id FROM packets WHERE kind='PerceptPacket' LIMIT 1"))
            finally:
                store.close()
            reopened = Store(home)
            try:
                self.assertEqual(reopened.read_source(result["source_ref"]), ui_snapshot_text(fixture()))
            finally:
                reopened.close()

    def test_fail_closed_without_writing_source(self):
        with TemporaryDirectory() as tmp:
            home = Path(tmp)
            initialize(home)
            store = Store(home)
            try:
                for key, value in (
                    ("capture_authorized", False),
                    ("redacted", False),
                    ("source", "MEDIA_PROJECTION_UNVERIFIED"),
                    ("consent_receipt_id", "../bad"),
                    ("nodes", [{"password": "secret"}]),
                    ("nodes", [{"text": "x" * 241}]),
                    ("nodes", [{}] * 129),
                    ("nodes", []),
                ):
                    with self.subTest(key=key, value=str(value)[:30]):
                        snap = fixture()
                        snap[key] = value
                        with self.assertRaises(ValueError):
                            persist_ui_shadow_source(store, snap)
                self.assertIsNone(store.one("SELECT id FROM sources LIMIT 1"))
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()

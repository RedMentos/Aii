"""A5 UI observation lease, Runtime ingress and revocation regressions."""
import contextlib
import copy
import pickle
import tempfile
import threading
import time
import unittest
from pathlib import Path

from v13.attention import Attention
from v13.runtime import Runtime
from v13.store import Store
from v13.a5_ui_admission_bridge import A5UIRuntimeAdapter, validate_ui_observation


class Provider:
    """Synthetic OS provider: a non-reentrant guard shared with revocation."""
    def __init__(self):
        self.lock = threading.Lock()
        self.active = True
        self.callbacks = {}
        self.sequence = 0

    def check(self, *args):
        with self.lock:
            return self.active

    def guard(self, *args):
        @contextlib.contextmanager
        def held():
            self.lock.acquire()
            try:
                yield self.active
            finally:
                self.lock.release()
        return held()

    def subscribe(self, source_id, receipt, session_id, callback):
        self.sequence += 1
        key = self.sequence
        self.callbacks[key] = callback

        def unsubscribe():
            self.callbacks.pop(key, None)

        return unsubscribe

    def revoke(self):
        with self.lock:
            self.active = False
        for callback in tuple(self.callbacks.values()):
            callback()


def observation(**overrides):
    value = {
        "schema": "v14.a5.ui-observation/1",
        "modality": "ui",
        "source_id": "src_ui_lease_test",
        "capture_session_id": "ui_session_test",
        "consent_receipt_ref": "receipt_ui_test",
        "capture_method": "APP_INTENT",
        "capture_scope": "APP_DATA",
        "api_level": 33,
        "clock": "ELAPSED_REALTIME",
        "event_kind": "APP_INTENT_RESULT",
        "start_ms": 100,
        "end_ms": 120,
        "finality": "FINAL",
        "action_authority": False,
        "learning_authority": False,
        "raw_capture_persisted": False,
    }
    value.update(overrides)
    return value


class A5UIObservationLeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        (self.home / "data/db").mkdir(parents=True)
        (self.home / "data/blobs").mkdir(parents=True)
        self.store = Store(self.home)
        session = self.store.new_session("A5 UI lease test")
        self.event = self.store.event(session, "synthetic UI observation test")
        self.runtime = Runtime.__new__(Runtime)
        self.runtime.store = self.store
        self.runtime.turn_event = self.event
        self.runtime.attention = Attention(self.store)
        self.runtime.closed = False
        self.adapter = A5UIRuntimeAdapter(self.runtime)
        self.provider = Provider()

    def tearDown(self):
        self.adapter.close()
        self.store.close()
        self.temp.cleanup()

    def lease(self, observation_packet=None):
        return self.adapter.lease(
            observation_packet or observation(),
            self.provider.check,
            self.provider.guard,
            self.provider.subscribe,
        )

    def test_runtime_ingress_drives_store_a4_and_admission(self):
        obs = observation()
        with self.lease(obs) as grant:
            result = self.adapter.ingest(obs, grant, goal="open app")
            self.assertEqual(result["status"], "WIRED_SYNTHETIC")
            self.assertEqual(result["admission"].status, "ADMITTED")
            self.assertEqual(result["packet"]["modality"], "ui")
            self.assertEqual(result["packet"]["action_authority"], False)
            self.assertEqual(result["packet"]["learning_authority"], False)
            self.assertFalse(result["raw_capture_persisted"])
            self.assertEqual(result["a4"]["truth_authority"], 0)
            self.assertEqual(len(result["a4"]["segments"]), 1)
            self.assertTrue(result["a4"]["highres"])
            expected = (
                "ui event=APP_INTENT_RESULT method=APP_INTENT scope=APP_DATA "
                "api=33 clock=ELAPSED_REALTIME interval_ms=20"
            )
            self.assertEqual(self.store.read_source(result["source_ref"]), expected)
            self.assertEqual(
                self.adapter.context(self.event["event_id"]),
                (result["packet"],),
            )
            segment = result["packet"]["segments"][0]
            self.assertEqual(segment["text"], expected)
            for forbidden in ("screenshot", "node_tree", "window_text", "package_name", "notification_text"):
                self.assertNotIn(forbidden, result["packet"])
                self.assertNotIn(forbidden, segment)

    def test_revocation_waits_for_lease_then_tombstones_packets_cache_and_blob(self):
        obs = observation()
        with self.lease(obs) as grant:
            result = self.runtime.ingest_ui_observation(obs, grant)
            revoker = threading.Thread(target=self.provider.revoke)
            revoker.start()
            time.sleep(0.04)
            self.assertTrue(revoker.is_alive(), "revocation must wait for the held provider guard")
            source = self.store.one("SELECT deleted FROM sources WHERE id=?", (obs["source_id"],))
            self.assertEqual(source["deleted"], 0)
        revoker.join(timeout=2)
        self.assertFalse(revoker.is_alive(), "revocation callback did not complete after lease release")
        source = self.store.one("SELECT deleted,hash FROM sources WHERE id=?", (obs["source_id"],))
        self.assertEqual(source["deleted"], 1)
        self.assertEqual(self.runtime.ui_observation_context(self.event["event_id"]), ())
        self.assertNotIn(obs["source_id"], self.runtime._a5_ui_context_cache)
        self.assertNotIn(obs["source_id"], self.runtime._a5_ui_unsubscribe)
        remaining = self.store.rows("SELECT id,payload FROM packets")
        self.assertFalse(any(obs["source_id"] in row["payload"] for row in remaining))
        with self.assertRaises(ValueError):
            self.store.read_source(result["source_ref"])
        self.assertFalse((self.home / "data/blobs" / source["hash"]).exists())

    def test_provisional_is_persisted_but_not_admitted_or_requested(self):
        obs = observation(finality="PROVISIONAL")
        with self.lease(obs) as grant:
            result = self.runtime.ingest_ui_observation(obs, grant)
        self.assertEqual(result["admission"].status, "EMPTY_OR_UNAUTHORIZED")
        self.assertEqual(result["admission"].omitted, (obs["source_id"],))
        self.assertFalse(result["a4"]["requests"])
        self.assertEqual(self.runtime.ui_observation_context(self.event["event_id"]), ())
        self.assertTrue(self.store.read_source(result["source_ref"]))

    def test_receipt_generation_and_runtime_binding_are_mandatory(self):
        obs = observation()
        with self.lease(obs) as grant:
            altered = dict(obs, consent_receipt_ref="receipt_other")
            with self.assertRaises(PermissionError):
                self.runtime.ingest_ui_observation(altered, grant)
            original = self.runtime.turn_event["brain_generation_id"]
            self.runtime.turn_event["brain_generation_id"] = "generation_other"
            try:
                with self.assertRaises(PermissionError):
                    self.runtime.ingest_ui_observation(obs, grant)
            finally:
                self.runtime.turn_event["brain_generation_id"] = original
        self.assertIsNone(self.store.one("SELECT id FROM sources WHERE id=?", (obs["source_id"],)))

    def test_lease_is_thread_bound_and_not_copyable_or_serializable(self):
        obs = observation()
        with self.lease(obs) as grant:
            with self.assertRaises(TypeError):
                copy.copy(grant)
            with self.assertRaises(TypeError):
                pickle.dumps(grant)
            failures = []

            def wrong_thread():
                try:
                    self.runtime.ingest_ui_observation(obs, grant)
                except Exception as exc:
                    failures.append(exc)

            thread = threading.Thread(target=wrong_thread)
            thread.start()
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
            self.assertTrue(failures)
            self.assertIsInstance(failures[0], PermissionError)

    def test_missing_revocation_subscription_fails_closed(self):
        with self.assertRaises(PermissionError):
            with self.runtime.ui_observation_lease(
                observation(), self.provider.check, self.provider.guard, None
            ):
                self.fail("lease unexpectedly acquired")

    def test_duplicate_source_id_cannot_overwrite_prior_observation(self):
        obs = observation()
        with self.lease(obs) as grant:
            self.runtime.ingest_ui_observation(obs, grant)
        second = dict(obs, capture_session_id="ui_session_second", consent_receipt_ref="receipt_second")
        with self.assertRaises(ValueError):
            with self.lease(second) as grant:
                self.runtime.ingest_ui_observation(second, grant)

    def test_no_active_runtime_turn_rejects_ui_observation(self):
        self.runtime.turn_event = None
        with self.assertRaises(ValueError):
            with self.lease(observation()):
                self.fail("lease unexpectedly acquired")

    def test_media_projection_api33_is_display_only_api34_can_be_app_window(self):
        self.assertTrue(validate_ui_observation(observation(
            capture_method="MEDIA_PROJECTION", capture_scope="FULL_DISPLAY",
            event_kind="SCREEN_FRAME_AVAILABLE", api_level=33,
        )))
        with self.assertRaises(ValueError):
            validate_ui_observation(observation(
                capture_method="MEDIA_PROJECTION", capture_scope="APP_WINDOW",
                event_kind="SCREEN_FRAME_AVAILABLE", api_level=33,
            ))
        self.assertTrue(validate_ui_observation(observation(
            capture_method="MEDIA_PROJECTION", capture_scope="APP_WINDOW",
            event_kind="SCREEN_FRAME_AVAILABLE", api_level=34,
        )))

    def test_accessibility_service_requires_disability_assistance_purpose(self):
        base = observation(
            capture_method="ACCESSIBILITY_ASSISTIVE",
            capture_scope="ACCESSIBILITY_TREE",
            event_kind="WINDOW_CONTENT_CHANGED",
        )
        with self.assertRaises(PermissionError):
            validate_ui_observation(base)
        self.assertTrue(validate_ui_observation(dict(base, accessibility_purpose="DISABILITY_ASSISTANCE")))

    def test_notification_listener_requires_api18_and_notification_scope(self):
        with self.assertRaises(ValueError):
            validate_ui_observation(observation(
                capture_method="NOTIFICATION_LISTENER", capture_scope="NOTIFICATION",
                event_kind="NOTIFICATION_POSTED", api_level=17,
            ))
        self.assertTrue(validate_ui_observation(observation(
            capture_method="NOTIFICATION_LISTENER", capture_scope="NOTIFICATION",
            event_kind="NOTIFICATION_POSTED", api_level=33,
        )))

    def test_raw_content_and_authority_escalation_are_rejected(self):
        for field in ("screenshot", "node_tree", "window_text", "package_name", "notification_text"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_ui_observation(observation(**{field: "private"}))
        with self.assertRaises(PermissionError):
            validate_ui_observation(observation(action_authority=True))
        with self.assertRaises(PermissionError):
            validate_ui_observation(observation(learning_authority=True))
        with self.assertRaises(PermissionError):
            validate_ui_observation(observation(raw_capture_persisted=True))

    def test_invalid_intervals_clock_and_unbounded_priority_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_ui_observation(observation(end_ms=100))
        with self.assertRaises(ValueError):
            validate_ui_observation(observation(end_ms=6000))
        with self.assertRaises(ValueError):
            validate_ui_observation(observation(clock="WALL_TIME"))
        with self.lease(observation()) as grant:
            with self.assertRaises(ValueError):
                self.runtime.ingest_ui_observation(observation(), grant, priority=101)


if __name__ == "__main__":
    unittest.main()

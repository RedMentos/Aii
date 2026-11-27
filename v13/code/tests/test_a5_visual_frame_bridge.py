"""A5 MediaProjection frame -> RAW-EYE -> A4 PerceptPacket regressions."""
import contextlib
import hashlib
import io
import tempfile
import threading
import unittest
from pathlib import Path

from PIL import Image

from v13.attention import Attention
from v13.store import Store
from v13.a5_visual_frame_bridge import A5VisualFrameAdapter
from v13.a5_ui_admission_bridge import UIObservationLease


class Provider:
    def __init__(self):
        self.lock = threading.RLock()
        self.active = True
        self.callbacks = {}
        self.sequence = 0

    def check(self, *args):
        with self.lock:
            return self.active

    def guard(self, *args):
        @contextlib.contextmanager
        def held():
            with self.lock:
                yield self.active
        return held()

    def subscribe(self, source_id, receipt, session_id, on_revoke_requested, on_revoked):
        self.sequence += 1
        key = self.sequence
        self.callbacks[key] = (on_revoke_requested, on_revoked)

        def unsubscribe():
            self.callbacks.pop(key, None)

        return unsubscribe

    def revoke(self):
        callbacks = tuple(self.callbacks.values())
        for request_cancel, _cleanup in callbacks:
            request_cancel()
        with self.lock:
            self.active = False
        for _request_cancel, cleanup in callbacks:
            cleanup()


def observation(**overrides):
    value = {
        "schema": "v14.a5.ui-observation/1",
        "modality": "ui",
        "source_id": "src_visual_frame_test",
        "capture_session_id": "session_visual_frame_test",
        "consent_receipt_ref": "receipt_visual_frame_test",
        "capture_method": "MEDIA_PROJECTION",
        "capture_scope": "FULL_DISPLAY",
        "api_level": 34,
        "clock": "ELAPSED_REALTIME",
        "event_kind": "SCREEN_FRAME_AVAILABLE",
        "start_ms": 100,
        "end_ms": 120,
        "finality": "FINAL",
        "action_authority": False,
        "learning_authority": False,
        "raw_capture_persisted": False,
    }
    value.update(overrides)
    return value


def png_bytes(width=32, height=24):
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = ((x * 7) % 256, (y * 11) % 256, ((x + y) * 5) % 256)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def flat_png(value=120):
    image = Image.new("RGB", (32, 24), (value, value, value))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class A5VisualFrameBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        (self.home / "data" / "db").mkdir(parents=True)
        (self.home / "data" / "blobs").mkdir(parents=True)
        (self.home / "data" / "vision").mkdir(parents=True)
        self.store = Store(self.home)
        session = self.store.new_session("A5 visual frame test")
        self.event = dict(self.store.event(session, "synthetic visual frame"))
        self.event["brain_generation_id"] = "gen_visual_frame_test"
        self.runtime = type("RuntimeStub", (), {})()
        self.runtime.home = self.home
        self.runtime.store = self.store
        self.runtime.turn_event = self.event
        self.runtime.current = "turn"
        self.runtime.cancel_event = threading.Event()
        self.runtime.attention = Attention(self.store)
        self.adapter = A5VisualFrameAdapter(self.runtime)
        self.provider = Provider()

    def tearDown(self):
        self.runtime.current = None
        self.runtime.turn_event = None
        if self.provider.active:
            self.provider.revoke()
        self.adapter.close()
        self.store.close()
        self.temp.cleanup()

    def lease(self, obs=None):
        return self.adapter.lease(
            obs or observation(),
            self.provider.check,
            self.provider.guard,
            self.provider.subscribe,
        )

    def test_media_projection_frame_reaches_raw_eye_a4_and_admission_without_disk_capture(self):
        obs = observation()
        frame = png_bytes()
        with self.lease(obs) as grant:
            result = self.adapter.ingest(
                frame, obs, grant, goal="find the control", token_budget=512, priority=8
            )
            self.assertEqual(result["status"], "WIRED_SYNTHETIC")
            self.assertEqual(result["packet"]["modality"], "visual")
            self.assertEqual(result["packet"]["producer_component"], "A5_VISUAL")
            self.assertEqual(result["packet"]["source_ref"]["source_id"], obs["source_id"])
            self.assertEqual(result["packet"]["source_ref"]["sha256"], hashlib.sha256(frame).hexdigest())
            self.assertEqual(result["packet"]["raw_capture_persisted"], False)
            self.assertEqual(result["packet"]["action_authority"], False)
            self.assertEqual(result["packet"]["learning_authority"], False)
            self.assertEqual(result["a4"]["truth_authority"], 0)
            self.assertEqual(result["admission"].status, "ADMITTED")
            self.assertGreater(result["feature_count"], 0)
            self.assertEqual(len(result["feature_sha256"]), 64)
            self.assertEqual(result["student_authority"], "NO_PROJECTOR")
            self.assertEqual(self.adapter.context(self.event["event_id"], grant), (result["packet"],))
            features = self.adapter.features(self.event["event_id"], grant)[obs["source_id"]]
            self.assertEqual(len(features), result["feature_count"])
            self.assertTrue(all(isinstance(value, float) for value in features))
            self.assertIsNone(self.store.one("SELECT id FROM sources WHERE id=?", (obs["source_id"],)))
            frame_sha = hashlib.sha256(frame).hexdigest()
            self.assertIsNone(self.store.one("SELECT id FROM sources WHERE hash=?", (frame_sha,)))
            blob_names = {path.name for path in (self.home / "data" / "blobs").iterdir()}
            self.assertNotIn(frame_sha, blob_names)
            self.assertNotIn(frame.hex(), str(result["packet"]))
        self.assertEqual(self.adapter._packets, {})
        self.assertEqual(self.adapter._features, {})
        self.assertEqual(self.adapter._owned_sources, set())


    def test_raw_eye_structure_reaches_a4_as_a_separate_bounded_signal(self):
        obs = observation()
        with self.lease(obs) as grant:
            result = self.adapter.ingest(png_bytes(), obs, grant, goal="find the control")
            packet_value = result["packet"]
            segment = packet_value["segments"][0]
            self.assertEqual(segment["producer_component"], "A5_VISUAL")
            self.assertEqual(segment["modality"], "visual")
            self.assertGreater(packet_value["raw_eye_structure"], 0.0)
            self.assertEqual(segment["raw_eye_structure"], packet_value["raw_eye_structure"])
            row = result["a4"]["segments"][0]
            self.assertEqual(row["raw_eye_structure"], packet_value["raw_eye_structure"])
            self.assertGreater(row["raw_eye_contribution"], 0.0)
            without_signal = dict(segment)
            without_signal.pop("raw_eye_structure")
            without_signal.pop("raw_eye_components")
            baseline = self.runtime.attention.perceive(
                self.event["event_id"], [without_signal], goal="find the control"
            )["segments"][0]["score"]
            self.assertGreater(row["score"], baseline)
            self.assertEqual(result["a4"]["truth_authority"], 0)
            self.assertFalse(packet_value["action_authority"])
            self.assertFalse(packet_value["learning_authority"])

    def test_uniform_visual_frame_has_zero_raw_eye_structure_after_noise_floor(self):
        obs = observation()
        with self.lease(obs) as grant:
            result = self.adapter.ingest(flat_png(), obs, grant)
            self.assertEqual(result["packet"]["raw_eye_structure"], 0.0)
            self.assertEqual(result["a4"]["segments"][0]["raw_eye_contribution"], 0.0)

    def test_a4_rejects_raw_eye_signal_without_visual_media_projection_provenance(self):
        from v13.a4_visual_salience import apply_raw_eye_structure
        segment = {
            "text": "visual frame observed",
            "source_ref": {
                "source_id": "src_untrusted_visual_signal", "sha256": "a" * 64,
                "char_start": 0, "char_end": 0, "modality": "text",
            },
            "modality": "text",
            "capture_method": "MEDIA_PROJECTION",
            "producer_component": "A5_VISUAL",
            "raw_eye_structure": 0.8,
        }
        a4_result = {"segments": [{"source_ref": segment["source_ref"], "score": 0.1}]}
        with self.assertRaises(ValueError):
            apply_raw_eye_structure(a4_result, segment, 0.8, {"global_contrast": 0.8})

    def test_a4_rejects_non_finite_or_out_of_range_raw_eye_signal(self):
        from v13.a4_visual_salience import apply_raw_eye_structure
        valid = {
            "text": "visual frame observed",
            "source_ref": {
                "source_id": "src_visual_signal_bounds", "sha256": "b" * 64,
                "char_start": 0, "char_end": 0, "modality": "visual",
            },
            "modality": "visual",
            "capture_method": "MEDIA_PROJECTION",
            "producer_component": "A5_VISUAL",
            "raw_eye_structure": 0.5,
        }
        components = {
            "global_contrast": 0.5,
            "global_edge_energy": 0.5,
            "cell_edge_energy": 0.5,
            "spatial_color": 0.5,
            "luminance_range": 0.5,
        }
        for invalid in (1.01, float("nan"), True):
            a4_result = {"segments": [{"source_ref": valid["source_ref"], "score": 0.1}]}
            with self.subTest(invalid=repr(invalid)), self.assertRaises(ValueError):
                apply_raw_eye_structure(a4_result, valid, invalid, components)

    def test_provisional_frame_is_ignored_before_image_decode(self):
        obs = observation(finality="PROVISIONAL")
        with self.lease(obs) as grant:
            result = self.adapter.ingest(b"not-an-image", obs, grant)
            self.assertEqual(result["status"], "PROVISIONAL_IGNORED")
            self.assertIsNone(result["packet"])
            self.assertEqual(result["feature_count"], 0)
            self.assertEqual(self.adapter.context(self.event["event_id"], grant), ())
            self.assertEqual(self.adapter.features(self.event["event_id"], grant), {})

    def test_only_media_projection_screen_frames_are_accepted(self):
        obs = observation(
            capture_method="ACCESSIBILITY_ASSISTIVE",
            capture_scope="ACCESSIBILITY_TREE",
            event_kind="WINDOW_CONTENT_CHANGED",
            accessibility_purpose="DISABILITY_ASSISTANCE",
        )
        with self.assertRaises(PermissionError):
            with self.lease(obs):
                pass
        with self.assertRaises(ValueError):
            with self.lease(observation(api_level=20)):
                pass
        with self.assertRaises(ValueError):
            with self.lease(observation(capture_scope="APP_WINDOW", api_level=33)):
                pass

    def test_provider_revocation_cancels_turn_and_drops_ephemeral_features(self):
        obs = observation()
        frame = png_bytes()
        with self.lease(obs) as grant:
            self.adapter.ingest(frame, obs, grant)
            self.assertTrue(self.adapter._features)
            self.provider.revoke()
            self.assertTrue(self.runtime.cancel_event.is_set())
            self.assertEqual(self.adapter._packets, {})
            self.assertEqual(self.adapter._features, {})
            with self.assertRaises(PermissionError):
                self.adapter.context(self.event["event_id"], grant)
            with self.assertRaises(PermissionError):
                self.adapter.features(self.event["event_id"], grant)


    def test_a4_targets_base_visual_row_when_student_hypotheses_share_source_ref(self):
        from unittest.mock import patch
        from v13 import a5_visual_frame_bridge as bridge

        obs = observation()
        candidate = {
            "region_id": "r00",
            "caption": "red square",
            "cosine": 0.9,
            "authority": "STUDENT_ESTIMATE",
            "reference_authority": "REFERENCE_NOT_FACT",
        }
        with patch.object(
            bridge,
            "_student_hypotheses",
            return_value=("STUDENT_ESTIMATE", (candidate,)),
        ):
            with self.lease(obs) as grant:
                result = self.adapter.ingest(png_bytes(), obs, grant)

        rows = result["a4"]["segments"]
        self.assertEqual(len(result["packet"]["segments"]), 2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["source_ref"], rows[1]["source_ref"])
        self.assertIn("raw_eye_structure", rows[0])
        self.assertNotIn("raw_eye_structure", rows[1])
        self.assertGreater(rows[0]["score"], rows[0]["base_score"])
        self.assertAlmostEqual(sum(row["weight"] for row in rows), 1.0, places=5)
        self.assertTrue(all(0.0 <= row["suppression"] <= 0.70 for row in rows))
        expected_highres = [
            row["index"]
            for row in sorted(
                (row for row in rows if row["score"] >= 0.35),
                key=lambda row: (-row["score"], row["index"]),
            )[:3]
        ]
        self.assertEqual(result["a4"]["highres"], expected_highres)

    def test_student_projector_candidates_are_hypotheses_not_facts(self):
        import numpy as np
        from unittest.mock import patch
        from v13 import a5_visual_frame_bridge as bridge

        projector_file = self.home / "data" / "vision" / "projector.npz"
        projector_file.write_bytes(b"synthetic-projector-placeholder")

        class FakeProjector:
            W = np.zeros((4, 3), dtype=np.float32)

            def __call__(self, values):
                return np.asarray([[1.0, 0.0, 0.0]], dtype=np.float32)

        state = {
            "projector": {
                "path": "data/vision/projector.npz",
                "sha256": "a" * 64,
                "encoder": "hashed_bow",
                "captions": {"r00": "red square", "r01": "blue circle"},
            }
        }

        def embed(caption, dimension):
            return np.asarray(
                [1.0, 0.0, 0.0] if caption == "red square" else [0.0, 1.0, 0.0],
                dtype=np.float32,
            )

        with (
            patch.object(bridge.vision, "load", return_value=state),
            patch.object(bridge.vision.Projector, "load", return_value=FakeProjector()),
            patch.object(bridge.vision, "hashed_embed", side_effect=embed),
        ):
            status, candidates = bridge._student_hypotheses(
                self.runtime, np.asarray([0.2, 0.4, 0.6], dtype=np.float32)
            )

        self.assertEqual(status, "STUDENT_ESTIMATE")
        self.assertEqual(candidates[0]["caption"], "red square")
        self.assertEqual(candidates[0]["authority"], "STUDENT_ESTIMATE")
        self.assertEqual(candidates[0]["reference_authority"], "REFERENCE_NOT_FACT")

    def test_wrong_or_expired_lease_cannot_read_visual_context(self):
        obs = observation()
        with self.lease(obs) as grant:
            self.adapter.ingest(png_bytes(), obs, grant)
            forged = observation(consent_receipt_ref="different_receipt")
            with self.assertRaises(PermissionError):
                self.adapter.ingest(png_bytes(), forged, grant)
        with self.assertRaises(PermissionError):
            self.adapter.context(self.event["event_id"], grant)


if __name__ == "__main__":
    unittest.main()

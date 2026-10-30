"""Source-only guards for isolated Needle/C2 route provenance; synthetic only."""
import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime

from scripts import c2_native_route_provenance_20261030 as pilot


class C2NativeRouteProvenanceSoftware(unittest.TestCase):
    def setUp(self):
        self.ref = {"source_id": "src_test", "sha256": "0"*64,
                    "char_start": 0, "char_end": 3, "modality": "text"}
        self.event = {"event_id": "evt_test", "session_id": "session_test",
                      "source_ref": self.ref}
        self.context = {"packet_id": "pkt_test", "session_id": "session_test",
                        "event_id": "evt_test", "query_ref": self.ref,
                        "external_action_authority": False}
        self.info = {
            "source": "BOOT_SCAFFOLD",
            "executive_control_policy": "LOCAL_PROCESSING_ONLY",
            "executive_control_context_id": "pkt_test",
            "native_control": {"route": "both"},
            "native_control_metrics": {
                "role": "C2_CONTROL", "operation": "C", "status": "FINAL",
                "duration_s": 0.6,
                "memory": {"measurement_status": "MEASURED", "pid": 42},
            },
        }

    def valid(self, info=None, context=None, event=None):
        return pilot.valid_control_evidence(
            event or self.event, "hello", "simple",
            self.info if info is None else info,
            context_packet=self.context if context is None else context)

    def test_frozen_prompt_identity_and_no_original_fixture_reuse(self):
        self.assertEqual(pilot.SEED, 43)
        self.assertEqual(pilot.prompt_hash(),
                         "c952103c6f36bff983659977783f2b6447264bc72e93f76412a69f91ca1fde25")
        self.assertEqual(len(pilot.PROMPTS), 3)
        self.assertEqual(len(set(pilot.PROMPTS)), 3)
        self.assertFalse(any("Solace" in p or "Tundra" in p for p in pilot.PROMPTS))

    def test_synthetic_shape_positive_is_not_native_proof(self):
        self.assertTrue(self.valid())
        advisory = copy.deepcopy(self.info)
        advisory["source"] = "NATIVE_C2_ADVISORY"
        self.assertTrue(self.valid(info=advisory))
        # A unit stub cannot assert that a real process ever ran.
        self.assertEqual(pilot.SCHEMA, "v13.c2.native_route_provenance_pilot.v1")

    def test_override_and_unverified_native_route_refused(self):
        for source in ("OPERATOR_ROUTE_OVERRIDE", "APPROVED_EXTERNAL_HEAD",
                       "EXPLICIT_EXACT_COPY", None):
            with self.subTest(source=source):
                x = copy.deepcopy(self.info)
                x["source"] = source
                self.assertFalse(self.valid(info=x))
        for route in ("wrong", "", None):
            with self.subTest(route=route):
                self.assertFalse(pilot.valid_control_evidence(
                    self.event, "hello", route, self.info,
                    context_packet=self.context))

    def test_no_metrics_or_failed_process_refused(self):
        for field, value in (("role", "C3_LANGUAGE"),
                             ("operation", "E"),
                             ("status", "ERROR"),
                             ("duration_s", -1),
                             ("duration_s", 31)):
            with self.subTest(field=field, value=value):
                x = copy.deepcopy(self.info)
                x["native_control_metrics"][field] = value
                self.assertFalse(self.valid(info=x))
        x = copy.deepcopy(self.info)
        x["native_control_metrics"]["memory"]["measurement_status"] = "UNKNOWN"
        self.assertFalse(self.valid(info=x))
        x = copy.deepcopy(self.info)
        del x["native_control"]
        self.assertFalse(self.valid(info=x))

    def test_packet_session_source_and_action_binding(self):
        for field, value in (("session_id", "foreign"),
                             ("event_id", "foreign"),
                             ("query_ref", {"source_id": "foreign"}),
                             ("external_action_authority", True),
                             ("packet_id", "wrong")):
            with self.subTest(field=field):
                x = copy.deepcopy(self.context)
                x[field] = value
                self.assertFalse(self.valid(context=x))
        x = copy.deepcopy(self.info)
        x["executive_control_policy"] = "EXTERNAL_TOOLS"
        self.assertFalse(self.valid(info=x))

    def test_real_store_route_boundary_with_synthetic_needle_stub(self):
        # This test is explicitly SOFTWARE/SYNTHETIC, never native evidence.
        with tempfile.TemporaryDirectory() as td:
            r = Runtime(Path(td))
            try:
                r.sleep.cycle.set_policy("enabled", "off")
                r.cfg["route_override"] = "auto"
                text = "Hello. Is this a simple greeting?"
                event = r.store.event(r.session, text)
                def fake_control(*args):
                    r.needle.last_metrics = copy.deepcopy(
                        self.info["native_control_metrics"])
                    return {"route": "both"}
                with (patch.object(r.learner, "propose", return_value=None),
                      patch.object(r.needle, "control",
                                   side_effect=fake_control),
                      patch.object(r.pool, "get",
                                   side_effect=AssertionError("C3_CALLED"))):
                    route, info = r._route(
                        text, event, time.monotonic() + 20)
                ctx_id = info.get("executive_control_context_id")
                stored = r.store.one(
                    "SELECT payload FROM packets WHERE id=? AND kind='ExecutiveControlContext'",
                    (ctx_id,))
                self.assertIsNotNone(stored)
                context = json.loads(stored["payload"])
                self.assertTrue(pilot.valid_control_evidence(
                    {**event, "session_id": r.session}, text, route,
                    info, context_packet=context))
                self.assertEqual(r.store.read_source(event["source_ref"]), text)
                self.assertIsNone(r.store.one(
                    "SELECT id FROM messages WHERE role='assistant'"))
            finally:
                r.close()

    def test_missing_native_control_and_no_context_refused(self):
        x = copy.deepcopy(self.info)
        x["control_unavailable"] = "timeout"
        self.assertFalse(self.valid(info=x))
        self.assertFalse(pilot.valid_control_evidence(
            self.event, "hello", "simple", self.info, context_packet=None))


if __name__ == "__main__":
    unittest.main()

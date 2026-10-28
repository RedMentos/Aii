"""C5 attached manifest availability, including AG0 missing-base and learned ACTIVE controls.

Software control-flow only. Native C2+C3 rerun and source-handoff re-registration
are separate gates; this test never claims model quality or real native execution.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13.actionlearn import C5Learning, context
from v13.common import Unavailable
from v13.focal import ActionGate, available_model_roles
from v13.runtime import Runtime


class C5AttachedManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled", "off")
        self.gate = ActionGate(self.r.store)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self):
        source = self.r.store.source("Inspect this plan.", "USER")
        eid = self.r.store.event(self.r.session, "Inspect this plan.")["event_id"]
        return {"event_id": eid, "brain_generation_id": self.r.store.generation_id,
                "source_ref": source}

    def choose(self, route="detail", direct=False):
        return self.gate.select(self.event(), route=route, direct=direct,
                                resource_state="NORMAL",
)

    def test_no_b_manifest_selects_c3_without_fallback(self):
        self.r.models.installed = {"language": {"download_complete": True}}
        self.assertEqual(available_model_roles(self.r.models), {"C3_LANGUAGE"})
        for route in ("detail", "gist", "both", "simple"):
            result = self.choose(route)
            self.assertEqual(result["role"], "C3_LANGUAGE")
            self.assertNotIn("B1_DETAIL", result["alternates"])
            self.assertNotIn("B2_GIST", result["alternates"])
            reasons = {x["action_id"]: x["reason"] for x in result["suppressed"]}
            self.assertEqual(reasons["B1_DETAIL"], "MODEL_MANIFEST_UNAVAILABLE")
            self.assertEqual(reasons["B2_GIST"], "MODEL_MANIFEST_UNAVAILABLE")
            p = json.loads(self.r.store.one(
                "SELECT payload FROM packets WHERE id=?", (result["packet_id"],))["payload"])
            self.assertEqual(p["selected"]["action_id"], "C3_LANGUAGE")

    def test_full_manifest_preserves_boot_prior(self):
        self.r.models.installed = {k: {"download_complete": True}
                                   for k in ("body", "gist", "language")}
        for route, role in (("detail", "B1_DETAIL"), ("gist", "B2_GIST"),
                            ("both", "B1_DETAIL"), ("simple", "C3_LANGUAGE")):
            self.assertEqual(self.choose(route)["role"], role)

    def test_shared_body_maps_b2_to_body_manifest(self):
        self.r.models.b2_control = "shared_body_dual_state"
        self.r.models.installed = {"body": {"download_complete": True},
                                   "language": {"download_complete": True}}
        self.assertEqual(available_model_roles(self.r.models),
                         {"B1_DETAIL", "B2_GIST", "C3_LANGUAGE"})
        self.assertEqual(self.choose("gist")["role"], "B2_GIST")

    def test_disabled_manifest_fails_closed(self):
        self.r.models.installed = {"body": {"download_complete": False},
                                   "language": {"download_complete": True}}
        self.assertEqual(self.choose("detail")["role"], "C3_LANGUAGE")
        self.r.models.installed["language"]["download_complete"] = False
        with self.assertRaises(Unavailable):
            self.choose("detail")
        self.assertEqual(self.choose("detail", direct=True)["role"], "SOURCE_COPY")

    def test_active_learning_cannot_unsuppress_absent_b(self):
        self.r.models.installed = {"language": {"download_complete": True}}
        c5 = C5Learning(self.r.store)
        ctx = context("detail", .5)
        for _ in range(5):
            c5.learn(ctx, "B1_DETAIL", task_success=1., human_approval=1.)
            c5.learn(ctx, "C3_LANGUAGE", rule_violation=1., cost_error=1.)
        c5.set_mode("ACTIVE", "EXPLICIT_HUMAN")
        result = self.gate.select(self.event(), route="detail", direct=False,
                                  resource_state="NORMAL", effort=.5,
)
        self.assertEqual(result["role"], "C3_LANGUAGE")
        self.assertIn({"action_id": "B1_DETAIL", "reason": "MODEL_MANIFEST_UNAVAILABLE"},
                      result["suppressed"])

    def test_attached_capability_is_transient_and_missing_manager_uses_test_seam(self):
        self.assertIs(self.r.store._model_manager, self.r.models)
        self.r.models.installed = {"language": {"download_complete": True}}
        self.assertEqual(self.choose("detail")["role"], "C3_LANGUAGE")
        self.r.store._model_manager = None
        self.assertEqual(self.choose("detail")["role"], "B1_DETAIL")

    def test_empty_installed_software_seam_is_not_native_proof(self):
        self.r.models.installed = {}
        self.assertIsNone(available_model_roles(self.r.models))
        self.assertEqual(self.choose("detail")["role"], "B1_DETAIL")


if __name__ == "__main__":
    unittest.main()

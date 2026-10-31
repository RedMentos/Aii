"""Independent Run115K post-assembly source/authority adversarial review.

These are deliberately synthetic collaborator probes of the exact bridge
function, not native B1/B2/JEF/C3 inference or source-quote evidence.
The inherited real SQLite/Context OS tests remain separate.
"""
import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from v13 import b1b2_jef_c3_source_role_bridge_candidate as bridge


class PostAssemblyAuthorityReview(unittest.TestCase):
    def setUp(self):
        self.runtime = SimpleNamespace(store=object())
        self.prior = {"source_ref": {"source_id": "prior"}}
        self.current = {"source_ref": {"source_id": "current"}}
        self.ids = {"B1_DETAIL": "offer-b1", "B2_GIST": "offer-b2"}
        self.sources = [
            {"lane": "B2_PRIOR_USER_SOURCE",
             "source_ref": self.prior["source_ref"],
             "text": "Project Kairo. Budget 200 euros. Deadline 5 days.",
             "origin": "STORE_EXACT_USER_NOT_MODEL_QUOTE"},
            {"lane": "B1_CURRENT_USER_SOURCE",
             "source_ref": self.current["source_ref"],
             "text": "Project Kairo. Option A costs 190 euros, takes 4 days. "
                     "Option B costs 170 euros, takes 7 days.",
             "origin": "STORE_EXACT_USER_NOT_MODEL_QUOTE"},
        ]
        self.bound = {"status": "SHADOW_TWO_SOURCE_POINTER_VERIFIED",
                      "sources": self.sources}
        self.candidate = {"choice": "A", "remaining": 10}
        self.hashes = ["hash-prior", "hash-current"]
        self.observations = [
            {"role": role, "hypothesis_authority": "MODEL_HYPOTHESIS_NOT_FACT",
             "hypothesis": {"summary": "possibly wrong", "uncertainty": "high",
                            "needs_reentry": True}, "verified_quotes": []}
            for role in ("B1_DETAIL", "B2_GIST")
        ]
        self.body = {
            "status": "C3_SOURCE_ENVELOPE_SHADOW_NO_MODEL_CALL",
            "delivery_authority": 0, "learning_authority": 0,
            "output_committed": False, "source_ref": self.current["source_ref"],
            "verified_quote_count": 0,
            "messages": [{"role": "system", "content": "untrusted legacy"},
                         {"role": "user", "content": json.dumps({
                             "current_source": {"text": self.sources[1]["text"],
                                                "source_ref": self.current["source_ref"]},
                             "body_hypotheses_are_facts": False,
                             "body_observations": self.observations})}],
        }
        self.payload = {
            "sources": self.sources,
            "typed_jef_candidate": self.candidate,
            "typed_candidate_origin":
                "DETERMINISTIC_EXACT_USER_SOURCE_RECIPE_NOT_MODEL",
            "typed_jef_source_ref_sha256": self.hashes,
            "typed_candidate_authority": 0,
        }
        self.typed = {
            "status": "SHADOW_TYPED_JEF_ROLE_FORMATTER_VERIFIED",
            "context_plan_packet_id": "plan-1",
            "source_refs": [self.prior["source_ref"], self.current["source_ref"]],
            "applied": False, "delivery_authority": 0, "learning_authority": 0,
            "typed_jef_candidate": self.candidate,
            "typed_jef_source_ref_sha256": self.hashes,
            "messages": [{"role": "system", "content": "not forwarded"},
                         {"role": "user", "content": json.dumps(self.payload)}],
        }
        self.jef = {
            "status": "SHADOW_NO_AUTHORITY",
            "reason": "EXACT_USER_SOURCE_RECIPE_SHADOW",
            "authority": 0, "model_called": False, "native_calls": 0,
            "store_writes": 0, "tool_dispatches": 0,
            "candidate": self.candidate, "source_ref_sha256": self.hashes,
        }

    def build(self, *, typed=None, jef=None):
        with patch.object(bridge, "controller",
                          return_value=SimpleNamespace(
                              _load=lambda: ({"mode": "SHADOW"}, None))), \
             patch.object(bridge, "bind_two_source",
                          return_value=copy.deepcopy(self.bound)), \
             patch.object(bridge, "build_c3_source_envelope",
                          return_value=copy.deepcopy(self.body)), \
             patch.object(bridge, "build_typed_jef_role_formatter",
                          return_value=copy.deepcopy(typed or self.typed)), \
             patch.object(bridge, "propose",
                          return_value=copy.deepcopy(jef or self.jef)):
            return bridge.build_b1b2_jef_c3_source_role_bridge(
                self.runtime, self.prior, self.current, self.ids,
                operator_opt_in=True)

    def assert_refused(self, result):
        self.assertNotEqual(result["status"],
                            "SHADOW_B1B2_JEF_C3_ROLE_BRIDGE_VERIFIED")
        self.assertNotIn("messages", result)
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertEqual(result["tool_dispatches"], 0)

    def test_positive_role_separated_zero_authority_control(self):
        result = self.build()
        self.assertEqual(result["status"],
                         "SHADOW_B1B2_JEF_C3_ROLE_BRIDGE_VERIFIED")
        self.assertEqual([m["role"] for m in result["messages"]],
                         ["system", "user"])
        payload = json.loads(result["messages"][1]["content"])
        self.assertEqual(payload["typed_jef_candidate"], self.candidate)
        self.assertEqual(payload["body_observations"], self.observations)
        self.assertFalse(payload["body_hypotheses_are_facts"])
        self.assertFalse(result["body_model_quote_verified"])
        self.assertNotIn(self.sources[0]["text"], result["messages"][0]["content"])
        self.assertNotIn(self.sources[1]["text"], result["messages"][0]["content"])

    def test_typed_payload_candidate_divergence_fails_closed(self):
        typed = copy.deepcopy(self.typed)
        payload = copy.deepcopy(self.payload)
        payload["typed_jef_candidate"] = {"choice": "B", "remaining": 30}
        typed["messages"][1]["content"] = json.dumps(payload)
        self.assert_refused(self.build(typed=typed))

    def test_typed_payload_authority_or_hash_divergence_fails_closed(self):
        for key, bad in (
            ("typed_candidate_authority", 1),
            ("typed_jef_source_ref_sha256", ["other-prior", "other-current"]),
            ("typed_candidate_origin", "MODEL_INFERRED_POLICY"),
        ):
            with self.subTest(field=key):
                typed = copy.deepcopy(self.typed)
                payload = copy.deepcopy(self.payload)
                payload[key] = bad
                typed["messages"][1]["content"] = json.dumps(payload)
                self.assert_refused(self.build(typed=typed))

    def test_postassembly_jef_authority_or_side_effect_drift_fails_closed(self):
        for key, bad in (
            ("status", "APPROVED_COMMIT"),
            ("authority", 1),
            ("model_called", True),
            ("native_calls", 1),
            ("store_writes", 1),
            ("tool_dispatches", 1),
        ):
            with self.subTest(field=key):
                jef = copy.deepcopy(self.jef)
                jef[key] = bad
                self.assert_refused(self.build(jef=jef))


if __name__ == "__main__":
    unittest.main()

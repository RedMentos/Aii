"""Run14T synthetic schema preflight only; forged receipts are NOT native evidence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run13j_c3_jef_native as j
from scripts import run13j_c3_jef_native_verify as jverify
from scripts import run14t_c3_schema_native as pilot
from scripts import run14t_c3_schema_native_verify as replay
from v13.agi.c3_source_fidelity_shadow_run13m import TRUSTED

FIXTURE = (Path(__file__).resolve().parents[1]
           / "docs/fixtures/run14t_c3_schema_seed311_20261030.json")


class Run14TSourcePreflight(unittest.TestCase):
    def setUp(self):
        self.cases = pilot.load_fixture(FIXTURE)

    def test_disjoint_frozen_fixture_and_order(self):
        self.assertEqual(len(self.cases), 8)
        self.assertEqual(self.cases[0]["project"], "Atlas311")
        self.assertEqual(self.cases[-1]["project"], "Haven311")
        self.assertEqual(len({c["project"] for c in self.cases}), 8)
        self.assertEqual(pilot.arm_order(0), pilot.ARMS)
        self.assertEqual(pilot.arm_order(1), tuple(reversed(pilot.ARMS)))

    def test_fixture_tamper_and_nonfinite_rejected(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "fixture.json"
            data["cases"][0]["budget"] += 1
            p.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                pilot.load_fixture(p)
            p.write_text(FIXTURE.read_text().replace("15200", "NaN", 1))
            with self.assertRaises(ValueError):
                pilot.load_fixture(p)

    def test_identical_prompts_schema_order_and_strict_source_score(self):
        case = self.cases[0]
        answer = jverify.expected_answer(case)
        linked = replay.linked_answer(answer)
        plain_system, plain_user = pilot.prompts(linked, "PROMPT_ONLY")
        schema_system, schema_user = pilot.prompts(linked, "JSON_SCHEMA")
        self.assertEqual((plain_system, plain_user), (schema_system, schema_user))
        self.assertIn("VERIFIED_FACTS", schema_user)
        self.assertEqual(tuple(pilot.JSON_SCHEMA["properties"]), pilot.FIELDS)
        self.assertEqual(tuple(pilot.JSON_SCHEMA["required"]), pilot.FIELDS)
        self.assertIs(pilot.JSON_SCHEMA["additionalProperties"], False)
        m = TRUSTED.fullmatch(answer)
        self.assertIsNotNone(m)
        fields = {"project": m.group("project"), "option_a": m.group("a"),
                  "remaining_a": int(m.group("na")), "option_b": m.group("b"),
                  "remaining_b": int(m.group("nb")), "faster": m.group("faster")}
        exact = json.dumps(fields)
        self.assertTrue(pilot.score(linked, case, "JSON_SCHEMA",
                                    exact, True)["strict_six_slots_exact"])
        self.assertTrue(pilot.typed_json(exact))
        self.assertFalse(pilot.typed_json("```json\\n" + exact + "\\n```"))
        fields["remaining_b"] += 1
        wrong = pilot.score(linked, case, "JSON_SCHEMA", json.dumps(fields), True)
        self.assertTrue(wrong["valid_json_six_fields"])
        self.assertFalse(wrong["strict_six_slots_exact"])
        self.assertFalse(pilot.score(linked, case, "JSON_SCHEMA",
                                     exact, False)["strict_six_slots_exact"])
        with self.assertRaises(ValueError):
            pilot.prompts(linked, "UNREGISTERED_ARM")

    def build_synthetic_raw(self, out):
        raw = out / "raw"
        raw.mkdir(parents=True)
        rows = []
        for i, case in enumerate(self.cases):
            answer = jverify.expected_answer(case)
            linked = replay.linked_answer(answer)
            m = TRUSTED.fullmatch(answer)
            fields = {"project": m.group("project"), "option_a": m.group("a"),
                      "remaining_a": int(m.group("na")), "option_b": m.group("b"),
                      "remaining_b": int(m.group("nb")), "faster": m.group("faster")}
            for aidx, arm in enumerate(pilot.ARMS):
                system, user = pilot.prompts(linked, arm)
                output = ("```json\\n" + json.dumps(fields) + "\\n```"
                          if arm == "PROMPT_ONLY" else json.dumps(fields))
                row = {
                    "schema": pilot.SCHEMA, "seed": pilot.SEED, "index": i,
                    "project": case["project"], "arm": arm,
                    "source_event_id": f"synthetic-source-{i}",
                    "query_event_id": f"synthetic-query-{i}",
                    "context_plan_packet_id": f"synthetic-plan-{i}",
                    "source_sha256": pilot.sha(j.frozen.prompt(case)),
                    "answer_sha256": pilot.sha(answer),
                    "prompt_sha256": pilot.sha(user),
                    "system_sha256": pilot.sha(system),
                    "model_sha256": pilot.MODEL_SHA,
                    "model_revision": pilot.MODEL_REVISION,
                    "schema_sha256": pilot.SCHEMA_SHA256,
                    "schema_applied": arm == "JSON_SCHEMA",
                    "c3_sampling": "legacy", "offer_logprobs": False,
                    "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
                    "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
                    "body_jepa_status": "UNAVAILABLE", "redmi_measured": False,
                    "whole_system_complete": False, "native_role": "C3_LANGUAGE",
                    "native_calls": 1, "native_status": "FINAL",
                    "native_pid": 10000 + 2 * i + aidx,
                    "native_reaped": True,
                    "native_release": {"process_reaped": True},
                    "native_metrics": {"status": "FINAL", "role": "C3_LANGUAGE",
                                       "actual_model": "LFM2.5-350M-QAD-Q4_0.gguf"},
                    "final_output": output, "native_output_sha256": pilot.sha(output),
                    "native_output_bytes": len(output.encode("utf-8")),
                    "score": replay.expected_score(linked, case, arm, output),
                }
                (raw / f"{i:02d}_{arm}.json").write_text(json.dumps(row) + "\n")
                rows.append(row)
        totals = pilot.totals_for(rows)
        report = {
            "schema": pilot.SCHEMA, "seed": pilot.SEED,
            "fixture_sha256": pilot.FIXTURE_SHA256, "rows": 16,
            "totals": totals, "all_native_final_and_reaped": True,
            "status": pilot.verdict(totals, True),
            "learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
            "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
            "jepa_weight": 0, "redmi_measured": False,
            "utility_gate_promoted": False, "semantic_quality_proven": False,
            "production_activation": False, "whole_system_complete": False,
        }
        (out / "report.json").write_text(json.dumps(report) + "\n")

    def test_independent_synthetic_replay_and_counterexamples(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "pilot"
            self.build_synthetic_raw(out)
            self.assertEqual(replay.verify(out, FIXTURE)["rows"], 16)
            rowfile = out / "raw/00_COPY_BASELINE.json"
            original = rowfile.read_text()
            row = json.loads(original)
            for field, bad in (
                ("system_sha256", "0" * 64),
                ("model_sha256", "0" * 64),
                ("schema_sha256", "0" * 64),
                ("schema_applied", True),
                ("c3_sampling", "anti_echo"),
                ("offer_logprobs", True),
                ("native_pid", 10001),
                ("jepa_weight", 1),
                ("native_reaped", False),
            ):
                altered = copy.deepcopy(row)
                altered[field] = bad
                rowfile.write_text(json.dumps(altered))
                with self.subTest(field=field), self.assertRaises(ValueError):
                    replay.verify(out, FIXTURE)
            rowfile.write_text(original)
            (out / "raw/extra.json").write_text("{}")
            with self.assertRaises(ValueError):
                replay.verify(out, FIXTURE)
            (out / "raw/extra.json").unlink()
            report = out / "report.json"
            report.write_text(report.read_text().replace('"rows": 16', '"rows": 15'))
            with self.assertRaises(ValueError):
                replay.verify(out, FIXTURE)


if __name__ == "__main__":
    unittest.main()

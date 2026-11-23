"""Run13J independent verifier synthetic controls; not native evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts import run13j_c3_jef_native as j
from scripts import run13j_c3_jef_native_verify as v
from scripts import c2_body_disjoint_paired181_run11v as frozen
from v13.agi.jef_c3_shadow_prompt_run13i import PREFIX

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run13j_c3_jef_native_seed227_20261030.json"


def _sha(s):
    return hashlib.sha256(s.encode()).hexdigest()


def make_synthetic(pilot):
    pilot = Path(pilot); (pilot / "raw").mkdir(parents=True)
    cases = j.load_fixture(FIXTURE)
    rows = []
    for i, case in enumerate(cases):
        answer = v.expected_answer(case)
        source = frozen.prompt(case)
        for arm in j.ARMS:
            prompt = source + "\n" + j.query(case) if arm == "RAW_C3" else PREFIX + answer
            row = {
                "index": i, "project": case["project"], "arm": arm,
                "seed": j.SEED, "native_role": "C3_LANGUAGE",
                "model_sha256": v.MODEL_SHA, "model_revision": v.MODEL_REVISION,
                "source_sha256": _sha(source), "prompt_sha256": _sha(prompt),
                "jef_answer_sha256": _sha(answer),
                "source_event_id": f"source-{i}",
                "query_event_id": f"query-{i}",
                "context_plan_packet_id": f"plan-{i}",
                "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
                "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
                "body_jepa_status": "UNAVAILABLE",
                "redmi_measured": False, "whole_system_complete": False,
                "native_calls": 0, "native_status": "ERROR",
                "final_output": None, "native_pid": None, "native_reaped": True,
                "native_release": {"process_reaped": True},
                "score": j.score(case, "", False),
                "exact_copy": "NOT_APPLICABLE",
            }
            (pilot / "raw" / f"{i:02d}_{arm}.json").write_text(json.dumps(row))
            rows.append(row)
    totals = {arm: {
        "n": 6, "native_final": 0, "numeric_correct": 0,
        "faster_correct": 0, "strict_full": 0,
    } for arm in j.ARMS}
    report = {
        "schema": j.SCHEMA, "seed": j.SEED,
        "fixture_sha256": j.FIXTURE_SHA256, "rows": 12,
        "totals": totals, "jef_exact_copy": 0,
        "all_native_reaped": True, "all_native_final": False,
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
        "body_jepa_status": "UNAVAILABLE",
        "redmi_measured": False, "whole_system_complete": False,
        "utility_gate_promoted": False, "semantic_quality_proven": False,
    }
    (pilot / "report.json").write_text(json.dumps(report))
    return rows


class Run13JVerifierSynthetic(unittest.TestCase):
    def test_complete_honest_failed_native_rows_are_replayable_not_promoted(self):
        with TemporaryDirectory() as td:
            make_synthetic(td)
            got = v.verify(td, FIXTURE)
            self.assertEqual(got["status"], "RAW_REPLAY_VALID")
            self.assertFalse(got["all_native_final"])
            self.assertFalse(got["utility_gate_promoted"])
            self.assertEqual(got["step2_status"], "UTILITY_FAIL")

    def test_missing_row_and_source_or_score_tamper_rejected(self):
        for tamper in ("missing", "source", "score", "report"):
            with self.subTest(tamper=tamper), TemporaryDirectory() as td:
                make_synthetic(td)
                path = Path(td) / "raw" / "00_RAW_C3.json"
                if tamper == "missing":
                    path.unlink()
                elif tamper in ("source", "score"):
                    row = json.loads(path.read_text())
                    if tamper == "source":
                        row["source_sha256"] = "0" * 64
                    else:
                        row["score"]["numeric"]["correct"] = 2
                    path.write_text(json.dumps(row))
                else:
                    report = Path(td) / "report.json"
                    obj = json.loads(report.read_text())
                    obj["utility_gate_promoted"] = True
                    report.write_text(json.dumps(obj))
                with self.assertRaises(ValueError):
                    v.verify(td, FIXTURE)


if __name__ == "__main__":
    unittest.main()

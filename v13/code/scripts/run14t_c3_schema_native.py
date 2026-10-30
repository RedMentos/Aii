"""Run14T preregistered seed311 C3 prompt-only vs JSON-schema constrained Linux-native SHADOW pilot.

A paired protocol experiment, not a model/age/utility promotion. All source,
model, prompt, seed and native process receipts are preserved as raw JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time

from scripts import run13j_c3_jef_native as j
from scripts import run13j_c3_jef_native_verify as jverify
from scripts import run13k_c3_copy_native as k
from scripts import run13l_c3_system_native as l
from v13.agi.c3_source_fidelity_shadow_run13m import audit_source_facts
from v13.agi.c3_structured_source_shadow_run14k import (
    audit_slots, prompt_for as structured_prompt,
)
from v13.common import file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime

SCHEMA = "v13.run14t.c3_schema_native.v1"
FIXTURE_SCHEMA = "v13.run14t.c3_schema_constraint.fixture.v1"
FIXTURE_SHA256 = "a46ca596386fc2ea75d2779c2a08982cc50fb5e119b4b9990168dfed26450d5a"
SEED = 311
ARMS = ("PROMPT_ONLY", "JSON_SCHEMA")
MODEL_SHA = jverify.MODEL_SHA
MODEL_REVISION = jverify.MODEL_REVISION
FIELDS = ("project", "option_a", "remaining_a", "option_b", "remaining_b", "faster")
JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "project": {"type": "string"},
        "option_a": {"type": "string"},
        "remaining_a": {"type": "integer"},
        "option_b": {"type": "string"},
        "remaining_b": {"type": "integer"},
        "faster": {"type": "string"},
    },
    "required": list(FIELDS),
    "additionalProperties": False,
}
SCHEMA_SHA256 = hashlib.sha256(json.dumps(JSON_SCHEMA, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("RUN14T_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("RUN14T_NONFINITE_JSON")


def typed_json(output):
    try:
        parsed = json.loads(output, object_pairs_hook=_unique,
                            parse_constant=_reject_constant)
    except (TypeError, ValueError, OverflowError):
        return False
    return (type(parsed) is dict and set(parsed) == set(FIELDS)
            and all(type(parsed[k]) is (int if k in ("remaining_a", "remaining_b") else str)
                    for k in FIELDS))



def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_fixture(path):
    def reject(_):
        raise ValueError("RUN14T_NONFINITE_FIXTURE")
    data = json.loads(Path(path).read_text(encoding="utf-8"),
                      parse_constant=reject)
    cases = data.get("cases")
    if (type(data) is not dict or data.get("schema") != FIXTURE_SCHEMA
            or type(data.get("seed")) is not int or data["seed"] != SEED
            or type(cases) is not list or len(cases) != 8
            or data.get("cases_sha256") != FIXTURE_SHA256
            or j.fixture_hash(cases) != FIXTURE_SHA256):
        raise ValueError("RUN14L_FROZEN_FIXTURE_RED")
    seen = set()
    for case in cases:
        if (type(case) is not dict
                or set(case) != {"project", "budget", "a", "a_cost", "a_days",
                                 "b", "b_cost", "b_days"}
                or type(case["project"]) is not str
                or not case["project"].endswith("311")
                or case["project"] in seen
                or any(type(case[name]) is not str or not case[name]
                       for name in ("a", "b"))
                or case["a"] == case["b"]
                or any(type(case[name]) is not int
                       for name in ("budget", "a_cost", "a_days",
                                    "b_cost", "b_days"))
                or not (0 < case["a_cost"] < case["budget"] <= 999999
                        and 0 < case["b_cost"] < case["budget"]
                        and 0 < case["a_days"] <= 365
                        and 0 < case["b_days"] <= 365
                        and case["a_days"] != case["b_days"])):
            raise ValueError("RUN14L_CASE_SCHEMA_RED")
        seen.add(case["project"])
    return cases


def arm_order(index):
    return ARMS if index % 2 == 0 else tuple(reversed(ARMS))


def prompts(linked, arm):
    if arm not in ARMS:
        raise ValueError("RUN14T_UNKNOWN_ARM")
    return structured_prompt(linked)


def score(linked, case, arm, output, valid):
    if arm not in ARMS:
        raise ValueError("RUN14T_UNKNOWN_ARM")
    slots = audit_slots(linked, output)
    exact = bool(valid and slots["result"] == "SLOTS_EXACT")
    return {"valid_json_six_fields": bool(valid and typed_json(output)),
            "strict_six_slots_exact": exact,
            "fidelity_reason": slots["reason"],
            "fenced_markdown": output.lstrip().startswith("```")}


def fresh_case(base_home, base_cfg, case, index, out):
    (base_home / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base_home / "tmp", prefix="run14l-") as td:
        home = Path(td)
        cfg = initialize(home)
        cfg.update(base_cfg)
        cfg.update(learning_mode="RECORD_ONLY", system_stage=0,
                   user_stage_cap=0, teacher_enabled=False,
                   latents_enabled=False, jepa_weight=0,
                   observer_mode="off", history_turns=0,
                   route_override="simple", seed=SEED,
                   temperature=0.0, answer_tokens=128,
                   context_tokens=1024, deadline_seconds=180)
        save_config(home, cfg)
        for name in ("models", "bin"):
            shutil.rmtree(home / name)
            (home / name).symlink_to(base_home / name, target_is_directory=True)
        shutil.copyfile(base_home / "config/models.json", home / "config/models.json")
        runtime = Runtime(home)
        rows = []
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            data = j.prepare_case(runtime, case)
            linked = data["linked"]
            answer = jverify.expected_answer(case)
            if linked["answer"] != answer:
                raise ValueError("RUN14L_JEF_ANSWER_BINDING_RED")
            model_sha = file_hash(runtime.models.path_for("C3_LANGUAGE"))
            revision = runtime.models.revision("C3_LANGUAGE")
            if model_sha != MODEL_SHA or revision != MODEL_REVISION:
                raise ValueError("RUN14L_MODEL_PIN_RED")
            before = runtime.store.one(
                "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
            for arm in arm_order(index):
                system, user = prompts(linked, arm)
                row = {
                    "schema": SCHEMA, "seed": SEED, "index": index,
                    "project": case["project"], "arm": arm,
                    "source_event_id": data["source_event_id"],
                    "query_event_id": data["query_event_id"],
                    "context_plan_packet_id": data["plan_packet_id"],
                    "source_sha256": sha(data["source_text"]),
                    "answer_sha256": sha(answer),
                    "prompt_sha256": sha(user), "system_sha256": sha(system),
                    "model_sha256": model_sha, "model_revision": revision,
                    "schema_sha256": SCHEMA_SHA256,
                    "schema_applied": arm == "JSON_SCHEMA",
                    "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
                    "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
                    "body_jepa_status": "UNAVAILABLE", "redmi_measured": False,
                    "whole_system_complete": False, "native_role": "C3_LANGUAGE",
                    "native_calls": 0, "native_status": "NOT_RUN",
                    "native_pid": None, "native_reaped": False,
                    "final_output": None,
                }
                try:
                    runner = runtime.pool.get("C3_LANGUAGE")
                    if runner.role != "C3_LANGUAGE":
                        raise ValueError("RUN14L_NATIVE_ROLE_RED")
                    chunks = []
                    row["native_calls"] = 1
                    for chunk in runner.generate(
                            [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                            runtime.cancel_event, time.monotonic() + 170,
                            max_tokens=128, seed=SEED,
                            schema=JSON_SCHEMA if arm == "JSON_SCHEMA" else None):
                        if type(chunk) is not str:
                            raise ValueError("RUN14L_NATIVE_NON_TEXT")
                        chunks.append(chunk)
                    row["final_output"] = "".join(chunks)
                    row["native_status"] = runner.last_metrics.get("status", "UNKNOWN")
                    row["native_metrics"] = dict(runner.last_metrics)
                    row["native_pid"] = runner.proc.pid if runner.proc else None
                except Exception as exc:
                    row["native_status"] = "ERROR"
                    row["error_type"] = type(exc).__name__
                finally:
                    release = runtime.pool.unload("C3_LANGUAGE")
                    row["native_release"] = release
                    row["native_reaped"] = release.get("process_reaped") is True
                valid = (row["native_status"] == "FINAL"
                         and row["native_calls"] == 1 and row["native_reaped"]
                         and type(row["final_output"]) is str)
                output = row["final_output"] or ""
                row["native_output_sha256"] = sha(output)
                row["native_output_bytes"] = len(output.encode("utf-8"))
                row["score"] = score(linked, case, arm, output, valid)
                (out / "raw" / f"{index:02d}_{arm}.json").write_text(
                    json.dumps(row, sort_keys=True, ensure_ascii=False,
                               allow_nan=False) + "\n", encoding="utf-8")
                rows.append(row)
            after = runtime.store.one(
                "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
            if before != after:
                raise ValueError("RUN14L_AUTONOMOUS_EGRESS_RED")
        finally:
            runtime.close()
        return rows


def totals_for(rows):
    return {arm: {
        "n": sum(r["arm"] == arm for r in rows),
        "native_final": sum(r["arm"] == arm and r["native_status"] == "FINAL"
                            and r["native_reaped"] for r in rows),
        "valid_json_six_fields": sum(r["arm"] == arm
                                     and r["score"]["valid_json_six_fields"] for r in rows),
        "strict_six_slots_exact": sum(r["arm"] == arm
                                      and r["score"]["strict_six_slots_exact"] for r in rows),
        "fenced_markdown": sum(r["arm"] == arm
                               and r["score"]["fenced_markdown"] for r in rows),
    } for arm in ARMS}


def verdict(totals, complete):
    if not complete:
        return "NATIVE_INCOMPLETE"
    plain = totals["PROMPT_ONLY"]
    constrained = totals["JSON_SCHEMA"]
    if (constrained["valid_json_six_fields"] >= plain["valid_json_six_fields"] + 4
            and constrained["strict_six_slots_exact"] >= plain["strict_six_slots_exact"]):
        return "BOUNDED_SCHEMA_SYNTAX_SIGNAL_NOT_UTILITY_GATE"
    if (constrained["valid_json_six_fields"] < plain["valid_json_six_fields"]
            or constrained["strict_six_slots_exact"] < plain["strict_six_slots_exact"]):
        return "SCHEMA_HURT"
    return "NO_BOUNDED_SCHEMA_SIGNAL"


def run(home, out, fixture):
    cases = load_fixture(fixture)
    home, out = Path(home), Path(out)
    if out.exists() or out.is_symlink():
        raise ValueError("RUN14L_REFUSE_OVERWRITE")
    (out / "raw").mkdir(parents=True)
    base_cfg = initialize(home)
    rows = []
    for index, case in enumerate(cases):
        rows.extend(fresh_case(home, base_cfg, case, index, out))
    totals = totals_for(rows)
    complete = (len(rows) == 16
                and all(r["native_status"] == "FINAL" and r["native_reaped"]
                        for r in rows))
    report = {
        "schema": SCHEMA, "seed": SEED, "fixture_sha256": FIXTURE_SHA256,
        "rows": len(rows), "totals": totals, "all_native_final_and_reaped": complete,
        "status": verdict(totals, complete),
        "learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
        "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "utility_gate_promoted": False, "semantic_quality_proven": False,
        "production_activation": False, "whole_system_complete": False,
    }
    (out / "report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--execute-native", action="store_true")
    args = parser.parse_args(argv)
    if not args.execute_native:
        parser.error("Explicit --execute-native required")
    report = run(args.home, args.out, args.fixture)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["all_native_final_and_reaped"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

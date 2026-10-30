"""Run14L seed307 disjoint pinned 350M C3 structured-vs-copy native pilot.

No model training, automatic chat egress, adapter export, or Age gate promotion.
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
from v13.agi.c3_structured_source_shadow_run14k import audit_slots, prompt_for
from v13.common import file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime

SCHEMA = "v13.run14l.c3_structured_native.v1"
FIXTURE_SCHEMA = "v13.run14l.c3_structured_native.fixture.v1"
FIXTURE_SHA256 = "f2ac30189adfc3ebdcf509c4e6183708dcb9c34ce659d4b8073a6807ae8bccbf"
SEED = 307
ARMS = ("COPY_BASELINE", "STRUCTURED_PLAIN", "STRUCTURED_GRAMMAR")
MODEL_SHA = jverify.MODEL_SHA
MODEL_REVISION = jverify.MODEL_REVISION
SLOTS = ("project", "option_a", "remaining_a", "option_b", "remaining_b", "faster")
JSON_SCHEMA = {"type": "object",
               "properties": {key: {"type": "integer" if key.startswith("remaining_") else "string"}
                              for key in SLOTS},
               "required": list(SLOTS), "additionalProperties": False}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_fixture(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = obj.get("cases")
    if (obj.get("schema") != FIXTURE_SCHEMA or obj.get("seed") != SEED
            or obj.get("cases_sha256") != FIXTURE_SHA256
            or type(cases) is not list or len(cases) != 4
            or j.fixture_hash(cases) != FIXTURE_SHA256):
        raise ValueError("RUN14L_FROZEN_FIXTURE_RED")
    seen = set()
    required = {"project", "budget", "a", "a_cost", "a_days", "b", "b_cost", "b_days"}
    for case in cases:
        if (type(case) is not dict or set(case) != required
                or type(case["project"]) is not str
                or not case["project"].endswith("307")
                or case["project"] in seen
                or type(case["a"]) is not str or type(case["b"]) is not str
                or case["a"] == case["b"]
                or any(type(case[key]) is not int for key in
                       ("budget", "a_cost", "a_days", "b_cost", "b_days"))
                or not (0 < case["a_cost"] < case["budget"] <= 999999
                        and 0 < case["b_cost"] < case["budget"]
                        and 0 < case["a_days"] <= 365
                        and 0 < case["b_days"] <= 365
                        and case["a_days"] != case["b_days"])):
            raise ValueError("RUN14L_CASE_SCHEMA_RED")
        seen.add(case["project"])
    return cases


def arm_order(index):
    offset = index % len(ARMS)
    return ARMS[offset:] + ARMS[:offset]


def messages_for(arm, linked):
    if arm == "COPY_BASELINE":
        return l.SYSTEM_COPY, k.prompt_for(linked, "COPY_DIRECT"), None
    if arm in ("STRUCTURED_PLAIN", "STRUCTURED_GRAMMAR"):
        system, user = prompt_for(linked)
        return system, user, JSON_SCHEMA if arm == "STRUCTURED_GRAMMAR" else None
    raise ValueError("RUN14L_UNKNOWN_ARM")


def structured_partial(case, output):
    """Secondary conservative typed claim counts; never substitute for strict success."""
    try:
        value = json.loads(output)
    except (TypeError, ValueError):
        return {"numeric_correct": 0, "faster_correct": 0, "wrong_claims": 0}
    if type(value) is not dict:
        return {"numeric_correct": 0, "faster_correct": 0, "wrong_claims": 0}
    expected = (case["budget"] - case["a_cost"], case["budget"] - case["b_cost"])
    faster = case["a"] if case["a_days"] < case["b_days"] else case["b"]
    numeric = 0
    wrong = 0
    for key, correct in zip(("remaining_a", "remaining_b"), expected):
        got = value.get(key)
        if type(got) is int:
            numeric += int(got == correct)
            wrong += int(got != correct)
    got = value.get("faster")
    faster_correct = int(type(got) is str and got == faster)
    if type(got) is str:
        wrong += int(got != faster)
    return {"numeric_correct": numeric, "faster_correct": faster_correct,
            "wrong_claims": wrong}


def verdict(totals):
    if any(totals[a]["n"] != 4 or totals[a]["native_final"] != 4 for a in ARMS):
        return "NATIVE_INCOMPLETE_NO_UTILITY_CLAIM"
    base, plain, grammar = (totals[a] for a in ARMS)
    if (grammar["strict"] >= base["strict"] + 2
            and grammar["strict"] >= plain["strict"]
            and grammar["wrong_claims"] <= base["wrong_claims"]):
        return "BOUNDED_SYNTHETIC_STRUCTURED_SIGNAL_NOT_UTILITY_GATE"
    if grammar["strict"] < base["strict"] or grammar["strict"] < plain["strict"]:
        return "STRUCTURED_HURT"
    return "INCONCLUSIVE"


def fresh_case(base_home, base_cfg, case, index, out):
    (base_home / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base_home / "tmp", prefix="run14l-") as td:
        home = Path(td)
        cfg = initialize(home)
        cfg.update(base_cfg)
        cfg.update(learning_mode="RECORD_ONLY", system_stage=0, user_stage_cap=0,
                   teacher_enabled=False, latents_enabled=False, jepa_weight=0,
                   observer_mode="off", history_turns=0, route_override="simple",
                   seed=SEED, temperature=0.0, answer_tokens=128,
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
                raise ValueError("RUN14L_JEF_SOURCE_BINDING_RED")
            before = runtime.store.one("SELECT count(*) n FROM messages WHERE role='assistant'")["n"]
            model_sha = file_hash(runtime.models.path_for("C3_LANGUAGE"))
            revision = runtime.models.revision("C3_LANGUAGE")
            if model_sha != MODEL_SHA or revision != MODEL_REVISION:
                raise ValueError("RUN14L_MODEL_PIN_RED")
            for arm in arm_order(index):
                system, prompt, schema = messages_for(arm, linked)
                row = {"schema": SCHEMA, "seed": SEED, "index": index,
                       "project": case["project"], "arm": arm,
                       "source_event_id": data["source_event_id"],
                       "query_event_id": data["query_event_id"],
                       "context_plan_packet_id": data["plan_packet_id"],
                       "source_sha256": sha(data["source_text"]),
                       "answer_sha256": sha(answer), "prompt_sha256": sha(prompt),
                       "system_sha256": sha(system),
                       "schema_sha256": sha(json.dumps(schema, sort_keys=True)) if schema else None,
                       "model_sha256": model_sha, "model_revision": revision,
                       "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
                       "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
                       "body_jepa_status": "UNAVAILABLE", "redmi_measured": False,
                       "whole_system_complete": False, "native_role": "C3_LANGUAGE",
                       "native_calls": 0, "native_status": "NOT_RUN",
                       "native_pid": None, "native_reaped": False, "final_output": None}
                try:
                    runner = runtime.pool.get("C3_LANGUAGE")
                    if runner.role != "C3_LANGUAGE":
                        raise ValueError("RUN14L_NATIVE_ROLE_RED")
                    chunks = []
                    row["native_calls"] = 1
                    for chunk in runner.generate(
                            [{"role": "system", "content": system},
                             {"role": "user", "content": prompt}],
                            runtime.cancel_event, time.monotonic() + 170,
                            max_tokens=128, seed=SEED, schema=schema):
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
                         and type(row["native_pid"]) is int and row["native_pid"] > 0
                         and type(row["final_output"]) is str)
                output = row["final_output"] or ""
                audit = (audit_source_facts(linked, output) if arm == "COPY_BASELINE"
                         else audit_slots(linked, output))
                row["strict_success"] = bool(valid and audit["result"] in
                                             ("FACTS_EXACT", "SLOTS_EXACT"))
                row["audit_reason"] = audit["reason"]
                if arm == "COPY_BASELINE":
                    score = j.score(case, output, valid)
                    row["partial"] = {"numeric_correct": score["numeric"]["correct"],
                                      "faster_correct": score["faster_correct"],
                                      "wrong_claims": 0}
                else:
                    row["partial"] = structured_partial(case, output)
                (out / "raw" / f"{index:02d}_{arm}.json").write_text(
                    json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8")
                rows.append(row)
            after = runtime.store.one("SELECT count(*) n FROM messages WHERE role='assistant'")["n"]
            if before != after:
                raise ValueError("RUN14L_AUTONOMOUS_EGRESS_RED")
        finally:
            runtime.close()
        return rows


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
    totals = {arm: {"n": sum(row["arm"] == arm for row in rows),
                    "native_final": sum(row["arm"] == arm
                                        and row["native_status"] == "FINAL"
                                        and row["native_reaped"] for row in rows),
                    "strict": sum(row["arm"] == arm and row["strict_success"] for row in rows),
                    "numeric_correct": sum(row["partial"]["numeric_correct"]
                                           for row in rows if row["arm"] == arm),
                    "faster_correct": sum(row["partial"]["faster_correct"]
                                          for row in rows if row["arm"] == arm),
                    "wrong_claims": sum(row["partial"]["wrong_claims"]
                                        for row in rows if row["arm"] == arm)}
              for arm in ARMS}
    report = {"schema": SCHEMA, "seed": SEED, "fixture_sha256": FIXTURE_SHA256,
              "rows": len(rows), "totals": totals,
              "all_native_final": all(r["native_status"] == "FINAL" for r in rows),
              "all_native_reaped": all(r["native_reaped"] for r in rows),
              "learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
              "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
              "jepa_weight": 0, "redmi_measured": False,
              "utility_gate_promoted": False, "production_activation": False,
              "whole_system_complete": False, "semantic_quality_proven": False,
              "status": verdict(totals)}
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True,
                                               allow_nan=False) + "\n")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--execute-native", action="store_true")
    args = p.parse_args(argv)
    if not args.execute_native:
        p.error("Explicit --execute-native required")
    report = run(args.home, args.out, args.fixture)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["all_native_final"] and report["all_native_reaped"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

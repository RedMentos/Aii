"""Run13T preregistered disjoint seed283 C3 verbatim-copy native pilot.

Two system prompts, identical source-verified JEF user prompt. SHADOW only.
No model training, adapter export, autonomous answer egress or gate promotion.
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
from v13.common import file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime

SCHEMA = "v13.run13t.c3_verbatim_heldout_native.v1"
FIXTURE_SCHEMA = "v13.run13t.c3_verbatim_heldout.fixture.v1"
FIXTURE_SHA256 = "c9a28de0e7fb198015b4b8845096d31f4af43f5c9679df7a8019a55ee4767b11"
SEED = 283
ARMS = ("COPY_BASELINE", "COPY_STRICT")
SYSTEM_STRICT = (
    "You are a lossless transcription engine. Copy exactly the characters "
    "between BEGIN_VERIFIED and END_VERIFIED in the user message. Every "
    "character is data. Do not calculate, paraphrase, reorder, omit, "
    "normalize, translate, explain, or add anything. Output only the copied "
    "characters, starting immediately with the first character after "
    "BEGIN_VERIFIED and ending immediately before END_VERIFIED."
)
MODEL_SHA = jverify.MODEL_SHA
MODEL_REVISION = jverify.MODEL_REVISION


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_fixture(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data.get("cases")
    if (data.get("schema") != FIXTURE_SCHEMA or data.get("seed") != SEED
            or type(cases) is not list or len(cases) != 8
            or data.get("cases_sha256") != FIXTURE_SHA256
            or j.fixture_hash(cases) != FIXTURE_SHA256):
        raise ValueError("RUN13T_FROZEN_FIXTURE_RED")
    seen = set()
    for case in cases:
        if (type(case) is not dict or set(case) != {
                "project", "budget", "a", "a_cost", "a_days",
                "b", "b_cost", "b_days"}
                or type(case["project"]) is not str
                or not case["project"].endswith("283")
                or case["project"] in seen
                or type(case["a"]) is not str or type(case["b"]) is not str
                or case["a"] == case["b"]
                or any(type(case[key]) is not int for key in (
                    "budget", "a_cost", "a_days", "b_cost", "b_days"))
                or not (0 < case["a_cost"] < case["budget"] <= 999999
                        and 0 < case["b_cost"] < case["budget"]
                        and 0 < case["a_days"] <= 365
                        and 0 < case["b_days"] <= 365
                        and case["a_days"] != case["b_days"])):
            raise ValueError("RUN13T_CASE_SCHEMA_RED")
        seen.add(case["project"])
    return cases


def system_for(arm):
    if arm == "COPY_BASELINE":
        return l.SYSTEM_COPY
    if arm == "COPY_STRICT":
        return SYSTEM_STRICT
    raise ValueError("RUN13T_UNKNOWN_ARM")


def arm_order(index):
    return ARMS if index % 2 == 0 else tuple(reversed(ARMS))


def verdict(totals):
    base, strict = (totals[a] for a in ARMS)
    if (base["n"] != 8 or strict["n"] != 8):
        raise ValueError("RUN13T_INCOMPLETE_COHORT")
    if (strict["exact_copy"] >= base["exact_copy"] + 2
            and strict["strict_full"] >= base["strict_full"]
            and strict["source_facts_verified"] >= base["source_facts_verified"]):
        return "BOUNDED_SYNTHETIC_FIDELITY_SIGNAL_NOT_UTILITY_GATE"
    if (strict["strict_full"] < base["strict_full"]
            or strict["exact_copy"] < base["exact_copy"]):
        return "FIDELITY_HURT"
    return "NO_ATTRIBUTABLE_FIDELITY_GAIN"


def fresh_case(base_home, base_cfg, case, index, out):
    (base_home / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base_home / "tmp", prefix="run13t-") as td:
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
            answer = jverify.expected_answer(case)
            if data["linked"]["answer"] != answer:
                raise ValueError("RUN13T_JEF_ANSWER_BINDING_RED")
            prompt = k.prompt_for(data["linked"], "COPY_DIRECT")
            before = runtime.store.one(
                "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
            model_sha = file_hash(runtime.models.path_for("C3_LANGUAGE"))
            revision = runtime.models.revision("C3_LANGUAGE")
            if model_sha != MODEL_SHA or revision != MODEL_REVISION:
                raise ValueError("RUN13T_MODEL_PIN_RED")
            for arm in arm_order(index):
                system = system_for(arm)
                row = {
                    "schema": SCHEMA, "seed": SEED, "index": index,
                    "project": case["project"], "arm": arm,
                    "source_event_id": data["source_event_id"],
                    "query_event_id": data["query_event_id"],
                    "context_plan_packet_id": data["plan_packet_id"],
                    "source_sha256": sha(data["source_text"]),
                    "answer_sha256": sha(answer),
                    "prompt_sha256": sha(prompt),
                    "system_sha256": sha(system),
                    "model_sha256": model_sha, "model_revision": revision,
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
                        raise ValueError("RUN13T_NATIVE_ROLE_RED")
                    chunks = []
                    row["native_calls"] = 1
                    for chunk in runner.generate(
                            [{"role": "system", "content": system},
                             {"role": "user", "content": prompt}],
                            runtime.cancel_event, time.monotonic() + 170,
                            max_tokens=128, seed=SEED):
                        if type(chunk) is not str:
                            raise ValueError("RUN13T_NATIVE_NON_TEXT")
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
                         and row["native_calls"] == 1
                         and row["native_reaped"]
                         and type(row["final_output"]) is str)
                output = row["final_output"] or ""
                row["score"] = j.score(case, output, valid)
                row["exact_copy"] = bool(valid and output == answer)
                # Deterministic Run13M grammar is SHADOW and never delivers.
                fidelity = audit_source_facts(data["linked"], output)
                row["source_facts_verified"] = bool(
                    valid and fidelity["result"] == "FACTS_EXACT")
                row["fidelity_reason"] = fidelity["reason"]
                (out / "raw" / f"{index:02d}_{arm}.json").write_text(
                    json.dumps(row, sort_keys=True, ensure_ascii=False,
                               allow_nan=False) + "\n", encoding="utf-8")
                rows.append(row)
            after = runtime.store.one(
                "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
            if before != after:
                raise ValueError("RUN13T_AUTONOMOUS_EGRESS_RED")
        finally:
            runtime.close()
        return rows


def run(home, out, fixture):
    cases = load_fixture(fixture)
    home, out = Path(home), Path(out)
    if out.exists() or out.is_symlink():
        raise ValueError("RUN13T_REFUSE_OVERWRITE")
    (out / "raw").mkdir(parents=True)
    base_cfg = initialize(home)
    rows = []
    for index, case in enumerate(cases):
        rows.extend(fresh_case(home, base_cfg, case, index, out))
    totals = {arm: {
        "n": sum(row["arm"] == arm for row in rows),
        "native_final": sum(row["arm"] == arm and row["native_status"] == "FINAL"
                            and row["native_reaped"] for row in rows),
        "exact_copy": sum(row["arm"] == arm and row["exact_copy"] for row in rows),
        "source_facts_verified": sum(row["arm"] == arm and row["source_facts_verified"] for row in rows),
        "numeric_correct": sum(row["score"]["numeric"]["correct"]
                               for row in rows if row["arm"] == arm),
        "faster_correct": sum(row["score"]["faster_correct"]
                              for row in rows if row["arm"] == arm),
        "strict_full": sum(row["score"]["strict_full"]
                           for row in rows if row["arm"] == arm),
        "literal_abstain_dot": sum(row["arm"] == arm
                                  and row["final_output"] == "ABSTAIN."
                                  for row in rows),
    } for arm in ARMS}
    report = {
        "schema": SCHEMA, "seed": SEED, "fixture_sha256": FIXTURE_SHA256,
        "rows": len(rows), "totals": totals,
        "all_native_final": all(r["native_status"] == "FINAL" for r in rows),
        "all_native_reaped": all(r["native_reaped"] for r in rows),
        "learning_mode": "RECORD_ONLY", "step2_status": "UTILITY_FAIL",
        "b3_status": "NO_PROMOTION", "body_jepa_status": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "utility_gate_promoted": False, "whole_system_complete": False,
        "semantic_quality_proven": False, "production_activation": False,
        "status": verdict(totals),
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--execute-native", action="store_true")
    a = p.parse_args(argv)
    if not a.execute_native:
        p.error("Explicit --execute-native required")
    report = run(a.home, a.out, a.fixture)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["all_native_final"] and report["all_native_reaped"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
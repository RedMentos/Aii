"""Run13J: exploratory real native C3 fidelity on source-verified JEF prompts.

Six frozen seed227 cases x RAW_C3/JEF_C3, native C3 only, no chat egress.
Not a STEP2, B3, JEPA, Redmi, semantic generalization or Age promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time

from scripts import c2_body_disjoint_paired181_run11v as frozen
from scripts.c2_body_run12n_fulltask_readonly import explicit_faster_claim
from v13 import context_os as context
from v13.agi.jef_c3_shadow_prompt_run13i import propose_c3_context, audit_c3_text
from v13.common import file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime

SCHEMA = "v13.run13j.c3_jef_prompt_native.v1"
FIXTURE_SCHEMA = "v13.run13j.c3_jef_prompt_native.fixture.v1"
FIXTURE_SHA256 = "d43a65572d85a3f3c1b2ef81d2903c19de880e643887c9bae96f0facbc1b6712"
SEED = 227
ARMS = ("RAW_C3", "JEF_C3")
SYSTEM = ("Give a concise factual answer about remaining budgets and the faster "
          "option. Do not invent values. If you cannot answer, say ABSTAIN.")
LONG = "A long unrelated note about garden soil and weather. " * 8


def fixture_hash(cases):
    return hashlib.sha256(json.dumps(tuple(cases), sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def load_fixture(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data.get("cases")
    if (data.get("schema") != FIXTURE_SCHEMA or data.get("seed") != SEED
            or type(cases) is not list or len(cases) != 6
            or data.get("cases_sha256") != FIXTURE_SHA256
            or fixture_hash(cases) != FIXTURE_SHA256):
        raise ValueError("RUN13J_FROZEN_FIXTURE_RED")
    seen = set()
    for case in cases:
        if (type(case) is not dict or set(case) != {
                "project", "budget", "a", "a_cost", "a_days",
                "b", "b_cost", "b_days"}
                or type(case["project"]) is not str
                or not case["project"].endswith("227")
                or case["project"] in seen
                or type(case["a"]) is not str or type(case["b"]) is not str
                or case["a"] == case["b"]
                or any(type(case[k]) is not int for k in (
                    "budget", "a_cost", "a_days", "b_cost", "b_days"))
                or not (0 < case["a_cost"] < case["budget"] <= 999999
                        and 0 < case["b_cost"] < case["budget"]
                        and 0 < case["a_days"] <= 365
                        and 0 < case["b_days"] <= 365
                        and case["a_days"] != case["b_days"])):
            raise ValueError("RUN13J_CASE_SCHEMA_RED")
        seen.add(case["project"])
    return cases


def query(case):
    return ("Calculate both remaining budgets and faster option for Project "
            + case["project"] + ".")


def prepare_case(runtime, case):
    """Actual Store events and Context OS plan; no native model call."""
    store = runtime.store
    text = frozen.prompt(case)
    source = store.event(runtime.session, text)["event_id"]
    history = [
        {"event_id": source, "role": "user", "text": text},
        {"event_id": source, "role": "assistant", "text": "Not yet answered."},
    ]
    for i in range(5):
        note = f"Garden note {i}. " + LONG
        eid = store.event(runtime.session, note)["event_id"]
        history.extend([
            {"event_id": eid, "role": "user", "text": note},
            {"event_id": eid, "role": "assistant", "text": "No answer. " + LONG},
        ])
    q = query(case)
    qevent = store.event(runtime.session, q)["event_id"]
    cfg = dict(runtime.cfg, context_tokens=600, answer_tokens=64)
    plan = context.ContextOS(store, cfg).plan(
        qevent, "C3_LANGUAGE", "SYS", [], history, q)
    linked = propose_c3_context(store, plan["packet_id"], qevent, source)
    if linked["candidate_prompt"] is None:
        raise ValueError("RUN13J_JEF_SOURCE_LINK_UNAVAILABLE")
    if linked["delivery_authority"] != 0 or linked["native_calls"] != 0:
        raise ValueError("RUN13J_SHADOW_AUTHORITY_RED")
    return {
        "source_event_id": source, "query_event_id": qevent,
        "plan_packet_id": plan["packet_id"],
        "source_text": text, "query_text": q, "linked": linked,
    }


def arm_order(index):
    return ARMS if index % 2 == 0 else tuple(reversed(ARMS))


def score(case, answer, valid_native):
    numeric = (frozen.score_pair(case, answer) if valid_native
               else {"a": False, "b": False, "correct": 0, "out_of": 2})
    faster = (explicit_faster_claim(answer, case["a"], case["b"])
              if valid_native else "ABSTAIN")
    expected = case["a"] if case["a_days"] < case["b_days"] else case["b"]
    return {
        "numeric": numeric, "faster_claim": faster,
        "faster_expected": expected, "faster_correct": faster == expected,
        "strict_full": bool(valid_native and numeric["correct"] == 2
                            and faster == expected),
    }


def fresh_case(base_home, base_cfg, case, index, out):
    """Fresh Store per case; model unloaded/reaped between counterbalanced arms."""
    (base_home / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
            dir=base_home / "tmp", prefix="run13j-c3-") as td:
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
            (home / name).symlink_to(
                base_home / name, target_is_directory=True)
        shutil.copyfile(base_home / "config/models.json",
                        home / "config/models.json")
        runtime = Runtime(home)
        results = []
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            case_data = prepare_case(runtime, case)
            before = runtime.store.one(
                "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
            revision = runtime.models.revision("C3_LANGUAGE")
            model_sha = file_hash(runtime.models.path_for("C3_LANGUAGE"))
            for arm in arm_order(index):
                prompt = (case_data["source_text"] + "\n" + case_data["query_text"]
                          if arm == "RAW_C3" else
                          case_data["linked"]["candidate_prompt"])
                result = {
                    "index": index, "project": case["project"], "arm": arm,
                    "seed": SEED, "source_event_id": case_data["source_event_id"],
                    "query_event_id": case_data["query_event_id"],
                    "context_plan_packet_id": case_data["plan_packet_id"],
                    "source_sha256": hashlib.sha256(
                        case_data["source_text"].encode()).hexdigest(),
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    "jef_answer_sha256": case_data["linked"]["answer_sha256"],
                    "model_revision": revision, "model_sha256": model_sha,
                    "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
                    "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
                    "body_jepa_status": "UNAVAILABLE",
                    "redmi_measured": False, "whole_system_complete": False,
                    "native_role": "C3_LANGUAGE", "native_calls": 0,
                    "final_output": None, "native_status": "NOT_RUN",
                    "native_pid": None, "native_reaped": False,
                }
                runner = None
                try:
                    runner = runtime.pool.get("C3_LANGUAGE")
                    if runner.role != "C3_LANGUAGE":
                        raise ValueError("RUN13J_WRONG_NATIVE_ROLE")
                    deadline = time.monotonic() + 170
                    chunks = []
                    result["native_calls"] = 1
                    for part in runner.generate(
                            [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": prompt}],
                            runtime.cancel_event, deadline,
                            max_tokens=128, seed=SEED):
                        if type(part) is not str:
                            raise ValueError("RUN13J_NON_TEXT_NATIVE_CHUNK")
                        chunks.append(part)
                    result["final_output"] = "".join(chunks)
                    result["native_status"] = runner.last_metrics.get("status", "UNKNOWN")
                    result["native_metrics"] = dict(runner.last_metrics)
                    result["native_pid"] = runner.proc.pid if runner.proc else None
                except Exception as exc:
                    result["native_status"] = "ERROR"
                    result["error_type"] = type(exc).__name__
                finally:
                    release = runtime.pool.unload("C3_LANGUAGE")
                    result["native_release"] = release
                    result["native_reaped"] = release.get("process_reaped") is True
                valid = (result["native_status"] == "FINAL"
                         and result["native_calls"] == 1
                         and result["native_reaped"]
                         and type(result["final_output"]) is str)
                result["score"] = score(case, result["final_output"] or "", valid)
                result["exact_copy"] = (
                    audit_c3_text(case_data["linked"],
                                  result["final_output"] or "")["status"]
                    if arm == "JEF_C3" and valid else "NOT_APPLICABLE")
                (out / "raw" / f"{index:02d}_{arm}.json").write_text(
                    json.dumps(result, sort_keys=True,
                               ensure_ascii=False, allow_nan=False) + "\n")
                results.append(result)
            after = runtime.store.one(
                "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
            if before != after:
                raise ValueError("RUN13J_AUTONOMOUS_CHAT_EGRESS_RED")
        finally:
            runtime.close()
        return results


def run(home, out, fixture):
    cases = load_fixture(fixture)
    out = Path(out); (out / "raw").mkdir(parents=True, exist_ok=True)
    home = Path(home)
    base_cfg = initialize(home)
    rows = []
    for i, case in enumerate(cases):
        rows.extend(fresh_case(home, base_cfg, case, i, out))
    totals = {arm: {
        "n": sum(r["arm"] == arm for r in rows),
        "native_final": sum(r["arm"] == arm and r["native_status"] == "FINAL"
                            and r["native_reaped"] for r in rows),
        "numeric_correct": sum(r["score"]["numeric"]["correct"]
                               for r in rows if r["arm"] == arm),
        "faster_correct": sum(r["score"]["faster_correct"]
                              for r in rows if r["arm"] == arm),
        "strict_full": sum(r["score"]["strict_full"]
                           for r in rows if r["arm"] == arm),
    } for arm in ARMS}
    report = {
        "schema": SCHEMA, "seed": SEED, "fixture_sha256": FIXTURE_SHA256,
        "rows": len(rows), "totals": totals,
        "jef_exact_copy": sum(r["exact_copy"] == "EXACT_COPY" for r in rows),
        "all_native_reaped": all(r["native_reaped"] for r in rows),
        "all_native_final": all(r["native_status"] == "FINAL" for r in rows),
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
        "body_jepa_status": "UNAVAILABLE", "redmi_measured": False,
        "whole_system_complete": False,
        "utility_gate_promoted": False, "semantic_quality_proven": False,
    }
    (out / "report.json").write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run(args.home, args.out, args.fixture)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["all_native_final"] and report["all_native_reaped"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Run13K preregistered disjoint seed239 native C3 exact-copy intervention.

Two source-verified JEF fact prompts; no active Runtime turn, training or gate promotion.
Original Run13J seed227 source, prompt, scorer and native raw remain unchanged.
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
from v13.agi.jef_c3_shadow_prompt_run13i import PREFIX
from v13.common import file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime

SCHEMA = "v13.run13k.c3_copy_native.v1"
FIXTURE_SCHEMA = "v13.run13k.c3_copy_instruction.fixture.v1"
FIXTURE_SHA256 = "c2e98d20730ec653678bac0ee7393fa143b08508ee684b6f87b6d875ee0b0796"
SEED = 239
ARMS = ("ORIGINAL_SHADOW", "COPY_DIRECT")
COPY_PREFIX = ("Reproduce the text between BEGIN_VERIFIED and END_VERIFIED exactly, "
               "including line breaks. Output only that text.\nBEGIN_VERIFIED\n")
COPY_SUFFIX = "\nEND_VERIFIED"
MODEL_SHA = jverify.MODEL_SHA
MODEL_REVISION = jverify.MODEL_REVISION


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_fixture(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data.get("cases")
    if (data.get("schema") != FIXTURE_SCHEMA or data.get("seed") != SEED
            or type(cases) is not list or len(cases) != 6
            or data.get("cases_sha256") != FIXTURE_SHA256
            or j.fixture_hash(cases) != FIXTURE_SHA256):
        raise ValueError("RUN13K_FROZEN_FIXTURE_RED")
    seen = set()
    for case in cases:
        if (type(case) is not dict or set(case) != {
                "project", "budget", "a", "a_cost", "a_days", "b", "b_cost", "b_days"}
                or type(case["project"]) is not str
                or not case["project"].endswith("239")
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
            raise ValueError("RUN13K_CASE_SCHEMA_RED")
        seen.add(case["project"])
    return cases


def prompt_for(linked, arm):
    if (type(linked) is not dict
            or linked.get("reason") != "VERIFIED_JEF_TO_C3_SHADOW_CANDIDATE"
            or linked.get("status") != "SHADOW_NO_AUTHORITY"
            or linked.get("delivery_authority") != 0
            or linked.get("context_authority") != 0
            or linked.get("native_calls") != 0
            or linked.get("weight_updates") is not False
            or type(linked.get("answer")) is not str
            or type(linked.get("candidate_prompt")) is not str
            or linked.get("answer_sha256") != sha(linked["answer"])
            or linked["candidate_prompt"] != PREFIX + linked["answer"]
            or linked.get("prompt_sha256") != sha(linked["candidate_prompt"])):
        raise ValueError("RUN13K_SOURCE_BINDING_RED")
    if arm == "ORIGINAL_SHADOW":
        prompt = linked["candidate_prompt"]
    elif arm == "COPY_DIRECT":
        prompt = COPY_PREFIX + linked["answer"] + COPY_SUFFIX
    else:
        raise ValueError("RUN13K_ARM_RED")
    if len(prompt.encode("utf-8")) > 768:
        raise ValueError("RUN13K_PROMPT_BUDGET_RED")
    return prompt


def arm_order(index):
    return ARMS if index % 2 == 0 else tuple(reversed(ARMS))


def fresh_case(base_home, base_cfg, case, index, out):
    (base_home / "tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base_home / "tmp", prefix="run13k-") as td:
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
            before = runtime.store.one(
                "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
            model_sha = file_hash(runtime.models.path_for("C3_LANGUAGE"))
            revision = runtime.models.revision("C3_LANGUAGE")
            if model_sha != MODEL_SHA or revision != MODEL_REVISION:
                raise ValueError("RUN13K_MODEL_PIN_RED")
            answer = data["linked"]["answer"]
            for arm in arm_order(index):
                prompt = prompt_for(data["linked"], arm)
                row = {
                    "schema": SCHEMA, "seed": SEED, "index": index,
                    "project": case["project"], "arm": arm,
                    "source_event_id": data["source_event_id"],
                    "query_event_id": data["query_event_id"],
                    "context_plan_packet_id": data["plan_packet_id"],
                    "source_sha256": sha(data["source_text"]),
                    "answer_sha256": sha(answer),
                    "prompt_sha256": sha(prompt),
                    "model_sha256": model_sha, "model_revision": revision,
                    "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
                    "step2_status": "UTILITY_FAIL", "b3_status": "NO_PROMOTION",
                    "body_jepa_status": "UNAVAILABLE", "redmi_measured": False,
                    "whole_system_complete": False, "native_role": "C3_LANGUAGE",
                    "native_calls": 0, "native_status": "NOT_RUN",
                    "native_pid": None, "native_reaped": False, "final_output": None,
                }
                try:
                    runner = runtime.pool.get("C3_LANGUAGE")
                    if runner.role != "C3_LANGUAGE":
                        raise ValueError("RUN13K_NATIVE_ROLE_RED")
                    chunks = []
                    row["native_calls"] = 1
                    for chunk in runner.generate(
                            [{"role": "system", "content": j.SYSTEM},
                             {"role": "user", "content": prompt}],
                            runtime.cancel_event, time.monotonic() + 170,
                            max_tokens=128, seed=SEED):
                        if type(chunk) is not str:
                            raise ValueError("RUN13K_NATIVE_NON_TEXT")
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
                row["score"] = j.score(case, row["final_output"] or "", valid)
                row["exact_copy"] = bool(valid and row["final_output"] == answer)
                (out / "raw" / f"{index:02d}_{arm}.json").write_text(
                    json.dumps(row, sort_keys=True, ensure_ascii=False,
                               allow_nan=False) + "\n", encoding="utf-8")
                rows.append(row)
            after = runtime.store.one(
                "SELECT count(*) AS n FROM messages WHERE role='assistant'")["n"]
            if before != after:
                raise ValueError("RUN13K_AUTONOMOUS_EGRESS_RED")
        finally:
            runtime.close()
        return rows


def run(home, out, fixture):
    cases = load_fixture(fixture)
    home, out = Path(home), Path(out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    base_cfg = initialize(home)
    rows = []
    for index, case in enumerate(cases):
        rows.extend(fresh_case(home, base_cfg, case, index, out))
    totals = {arm: {
        "n": sum(row["arm"] == arm for row in rows),
        "native_final": sum(row["arm"] == arm and row["native_status"] == "FINAL"
                            and row["native_reaped"] for row in rows),
        "exact_copy": sum(row["arm"] == arm and row["exact_copy"] for row in rows),
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
        "semantic_quality_proven": False,
    }
    (out / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    a = p.parse_args(argv)
    report = run(a.home, a.out, a.fixture)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["all_native_final"] and report["all_native_reaped"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

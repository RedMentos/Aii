#!/usr/bin/env python3
"""Run40 fresh seed19 Linux-native AG12 null-span subtype triple-vote SHADOW.

No raw answers/prompts/token metrics exported. Original frozen models and
runner, one generation per role/item, aggregate-only evidence and no promotion.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import time

from scripts.run27_ag12_three_organ_native import (
    install, ROLES, RUNNER_SHA, RUNNER_BINARY_SHA, BODIES, C3_SHA,
)
from v13.agi.generality import GeneralityEval
from v13.agi.solver_confidence_null_span_native_candidate import (
    TripleConfidenceBodySolver, REVISION,
)
from v13.common import file_hash
from v13.runtime import Runtime

SEED = 19
DEADLINE_S = 1200


def hypotheses(per_language):
    if set(per_language) != {"de", "en"}:
        raise ValueError("RUN40_LANGUAGE_IDENTITY")
    none_count = changed = finite_correct = null_correct = 0
    for lang in ("de", "en"):
        a = per_language[lang]["aggregate"]
        if a["items"] != 88 or a["role_calls"] != 264:
            raise ValueError("RUN40_AGGREGATE_COUNT")
        for role in ROLES:
            by = a["by_role"][role]
            if (by["native_calls"] != 88
                    or sum(by["native_field_min_types"].values()) != 88
                    or sum(by["finite_source_counts"].values()) != 88
                    or sum(by["null_source_counts"].values()) != 88):
                raise ValueError("RUN40_SOURCE_COUNT")
            none_count += by["native_field_min_types"].get("field_min_none_span", 0)
        changed += a["changed_votes"].get("finite_null_all", 0)
        finite_correct += a["correct"].get("finite_all", 0)
        null_correct += a["correct"].get("null_all", 0)
    if not 0 <= changed <= 176 or not 0 <= finite_correct <= 176 or not 0 <= null_correct <= 176:
        raise ValueError("RUN40_PAIRED_COUNT")
    return {
        "none_span_role_calls": none_count,
        "finite_null_changed_votes": changed,
        "finite_correct_all": finite_correct,
        "null_correct_all": null_correct,
        "H1_native_none_span_present": none_count >= 1,
        "H2_null_finite_vote_change": changed >= 1,
        "H3_null_not_worse_than_finite": null_correct >= finite_correct,
    }


def run(home, out):
    home, out = Path(home), Path(out)
    if (platform.system() != "Linux"
            or platform.machine().lower() not in ("x86_64", "amd64")):
        raise ValueError("RUN40_LINUX_X86_64_ONLY")
    if home.exists() or out.exists():
        raise FileExistsError("RUN40_FRESH_PATHS_REQUIRED")
    out.mkdir(parents=True)
    report = {
        "schema": "v13.run40.ag12_native_null_span_triple_vote.v1",
        "evidence_kind": "LINUX_NATIVE_AG12_SAME_OUTPUT_NULL_SPAN_SHADOW",
        "revision": REVISION, "suite_seed": SEED, "generation_seed": SEED,
        "roles": list(ROLES), "language_order": ["de", "en"],
        "model_sha256": {}, "runner_tar_sha256": None,
        "runner_binary_sha256": None, "per_language": {},
        "native_role_calls": 0, "voted_items": 0,
        "runtime_closed": False, "process_reaped": False,
        "exclusive_native_residency": False, "no_events": False,
        "no_messages": False, "status": "INCOMPLETE",
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "world_jepa_authority": "SHADOW",
        "redmi_measured": False, "learned_german_transfer_proven": False,
        "live_jef_fusion_proven": False, "whole_system_complete": False,
    }
    runtime = None
    began = time.monotonic()
    try:
        paths, archive, binary = install(home)
        report["model_sha256"] = {role: file_hash(path)
                                  for role, path in paths.items()}
        report["runner_tar_sha256"] = file_hash(archive)
        report["runner_binary_sha256"] = file_hash(binary)
        if (report["model_sha256"] != {
                "C3_LANGUAGE": C3_SHA,
                "B1_DETAIL": BODIES["b1"]["sha"],
                "B2_GIST": BODIES["b2"]["sha"]}
                or report["runner_tar_sha256"] != RUNNER_SHA
                or report["runner_binary_sha256"] != RUNNER_BINARY_SHA):
            raise ValueError("RUN40_NATIVE_MODEL_OR_RUNNER_PIN_RED")
        runtime = Runtime(home)
        runtime.sleep.cycle.set_policy("enabled", "off")
        cfg = runtime.cfg
        if (cfg["learning_mode"] != "RECORD_ONLY" or cfg["system_stage"] != 0
                or cfg.get("jepa_weight", 0) != 0 or cfg["latents_enabled"]):
            raise ValueError("RUN40_AGE0_GATE_RED")
        for role, path in paths.items():
            if runtime.models.path_for(role) != path:
                raise ValueError("RUN40_ROLE_BINDING_RED")
        runtime.pool.unload()
        runtime.pool.fabric = None
        report["exclusive_native_residency"] = True
        before_events = runtime.store.one("SELECT COUNT(*) n FROM events")["n"]
        before_messages = runtime.store.one("SELECT COUNT(*) n FROM messages")["n"]
        for lang in ("de", "en"):
            evaluation = GeneralityEval(runtime.store, home, seed=SEED, lang=lang)
            solver = TripleConfidenceBodySolver(
                runtime.pool, ROLES, cfg, name="run40-three-organ-null-aware",
                seed=SEED)
            started = time.monotonic()
            result = evaluation.run(
                solver, label="run40-native-null-span", solver_name="v13",
                deadline=time.monotonic() + DEADLINE_S, include_results=True)
            if result["status"] != "DONE" or result["items"] != 88:
                raise ValueError("RUN40_" + lang.upper() + "_INCOMPLETE")
            aggregate = solver.aggregate(evaluation.suite, result["_results"])
            report["per_language"][lang] = {
                "suite_hash": evaluation.suite["hash"],
                "elapsed_s": round(time.monotonic() - started, 3),
                "native_roles": list(ROLES),
                "aggregate": aggregate,
            }
        report["hypotheses"] = hypotheses(report["per_language"])
        report["no_events"] = runtime.store.one(
            "SELECT COUNT(*) n FROM events")["n"] == before_events
        report["no_messages"] = runtime.store.one(
            "SELECT COUNT(*) n FROM messages")["n"] == before_messages
        report["native_role_calls"] = sum(
            x["aggregate"]["role_calls"] for x in report["per_language"].values())
        report["voted_items"] = sum(
            x["aggregate"]["items"] for x in report["per_language"].values())
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)[:300]
    finally:
        if runtime is not None:
            try:
                runtime.close()
                report["runtime_closed"] = runtime.closed is True
                report["process_reaped"] = not runtime.pool.pids()
            except Exception as exc:
                report["close_error"] = type(exc).__name__ + ": " + str(exc)[:200]
        report["elapsed_s"] = round(time.monotonic() - began, 3)
        report["status"] = (
            "DONE" if (report.get("error") is None
                       and report["runtime_closed"] and report["process_reaped"]
                       and report["exclusive_native_residency"]
                       and report["no_events"] and report["no_messages"]
                       and report["native_role_calls"] == 528
                       and report["voted_items"] == 176
                       and set(report["per_language"]) == {"de", "en"})
            else "RED")
        (out / "REPORT.json").write_text(
            json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n",
            encoding="utf-8")
    if report["status"] != "DONE":
        raise RuntimeError("RUN40_NATIVE_RED_OR_INCOMPLETE; aggregate raw retained")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    result = run(args.home, args.out)
    print(json.dumps({"native_role_calls": result["native_role_calls"],
                      "voted_items": result["voted_items"],
                      "hypotheses": result["hypotheses"],
                      "evidence_kind": result["evidence_kind"]}, sort_keys=True))


if __name__ == "__main__":
    main()

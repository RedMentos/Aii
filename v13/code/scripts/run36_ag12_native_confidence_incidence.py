#!/usr/bin/env python3
"""Run36 disjoint Linux-native AG12 finite-confidence incidence; aggregate only."""
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
from v13.agi.solver_confidence_native_incidence_candidate import (
    PairedConfidenceBodySolver, REVISION,
)
from v13.common import file_hash
from v13.runtime import Runtime

SEED = 17
DEADLINE_S = 1200


def run(home, out):
    home, out = Path(home), Path(out)
    if (platform.system() != "Linux" or
            platform.machine().lower() not in ("x86_64", "amd64")):
        raise ValueError("RUN36_LINUX_X86_64_ONLY")
    if home.exists() or out.exists():
        raise FileExistsError("RUN36_FRESH_PATHS_REQUIRED")
    out.mkdir(parents=True)
    report = {
        "schema": "v13.run36.ag12_native_finite_confidence_incidence.v1",
        "evidence_kind": "LINUX_NATIVE_AG12_SAME_OUTPUT_CONFIDENCE_SHADOW",
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
            raise ValueError("RUN36_NATIVE_MODEL_OR_RUNNER_PIN_RED")
        runtime = Runtime(home)
        runtime.sleep.cycle.set_policy("enabled", "off")
        cfg = runtime.cfg
        if (cfg["learning_mode"] != "RECORD_ONLY" or cfg["system_stage"] != 0
                or cfg.get("jepa_weight", 0) != 0 or cfg["latents_enabled"]):
            raise ValueError("RUN36_AGE0_GATE_RED")
        for role, path in paths.items():
            if runtime.models.path_for(role) != path:
                raise ValueError("RUN36_ROLE_BINDING_RED")
        runtime.pool.unload()
        runtime.pool.fabric = None
        report["exclusive_native_residency"] = True
        before_events = runtime.store.one("SELECT COUNT(*) n FROM events")["n"]
        before_messages = runtime.store.one("SELECT COUNT(*) n FROM messages")["n"]
        for lang in ("de", "en"):
            evaluation = GeneralityEval(runtime.store, home, seed=SEED, lang=lang)
            solver = PairedConfidenceBodySolver(
                runtime.pool, ROLES, cfg, name="run36-three-organ-finite",
                seed=SEED)
            started = time.monotonic()
            result = evaluation.run(
                solver, label="run36-native-incidence", solver_name="v13",
                deadline=time.monotonic() + DEADLINE_S, include_results=True)
            if result["status"] != "DONE" or result["items"] != 88:
                raise ValueError("RUN36_" + lang.upper() + "_INCOMPLETE")
            aggregate = solver.aggregate(evaluation.suite, result["_results"])
            report["per_language"][lang] = {
                "suite_hash": evaluation.suite["hash"],
                "elapsed_s": round(time.monotonic() - started, 3),
                "native_roles": list(ROLES),
                "aggregate": aggregate,
            }
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
        raise RuntimeError("RUN36_NATIVE_RED_OR_INCOMPLETE; aggregate raw retained")
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args(argv)
    result = run(args.home, args.out)
    print(json.dumps({"native_role_calls": result["native_role_calls"],
                      "voted_items": result["voted_items"],
                      "evidence_kind": result["evidence_kind"]}, sort_keys=True))


if __name__ == "__main__":
    main()

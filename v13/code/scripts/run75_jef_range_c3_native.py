#!/usr/bin/env python3
"""Run75 pinned Linux-native C3 JSON formatting of authenticated JEF range.

Six registered synthetic human-source tasks. The typed answer IS visible to
C3; this is formatter fidelity, not independent source reasoning or output.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import os
import time

from v13.common import atomic_write, dumps, file_hash
from v13.config import initialize, save_config
from v13.store import audit_closed
from v13.jef_range_c3_typed_envelope_shadow import build, STATUS
from scripts import jef_range_native_fixture_773 as f
from scripts import jef_c3_c5_c6_operator_cli as cli
from scripts.run63_jef_c3_native import RUN_CONFIG

REPORT_SCHEMA = "v13.run75.jef_range_c3_native_formatter.v1"
C3_FILE = "LFM2.5-350M-QAD-Q4_0.gguf"


def _save(path, value):
    atomic_write(path, dumps(value))


def _record(runtime, key, value):
    e = runtime.store.event(runtime.session, "Record: " + key)
    mid = runtime.memory.feedback(
        e["event_id"], "fact", value, permission="record",
        key=key, scope="session")
    runtime.memory.candidate(mid, runtime.session)
    return mid


def run(home, out):
    home, out = Path(home), Path(out)
    if out.exists():
        raise FileExistsError("RUN75_OUTPUT_EXISTS")
    rows = f.fixtures()
    out.mkdir(parents=True)
    report_path = out / "report.json"
    report = {
        "schema": REPORT_SCHEMA,
        "evidence_kind": "LINUX_NATIVE_C3_TYPED_JEF_RANGE_FORMATTER_SMALL_SYNTHETIC",
        "status": "INCOMPLETE",
        "seed": f.SEED, "temperature": 0.0, "max_tokens": 32,
        "table_sha256": f.TABLE_SHA256,
        "model_sha256_required": f.MODEL_SHA256,
        "runner_sha256_required": f.RUNNER_SHA256,
        "formatter_only": True, "typed_answer_visible": True,
        "independent_source_reasoning_proven": False,
        "cases": [],
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "delivery_authority": 0, "tool_dispatches": 0,
        "learning_authority": 0, "tty_approved": False,
        "output_committed": False,
    }
    _save(report_path, report)
    runtime = None
    try:
        initialize(home)
        save_config(home, RUN_CONFIG | {
            "seed": f.SEED, "temperature": 0.0, "answer_tokens": 32})
        runtime = cli.Runtime(home)
        model_sha = file_hash(runtime.models.path_for("C3_LANGUAGE"))
        runner_path = Path(os.environ.get(
            "V13_LLAMA_SERVER", str(home / "bin/llama-server")))
        runner_sha = file_hash(runner_path)
        report["model_sha256_observed"] = model_sha
        report["runner_sha256_observed"] = runner_sha
        if model_sha != f.MODEL_SHA256 or runner_sha != f.RUNNER_SHA256:
            raise ValueError("RUN75_NATIVE_PINS_RED")
        for row in rows:
            project = row["project"]
            ids = [
                _record(runtime, f"Project {project} archived "
                        f"{f.TABLE[row['index']][1]} policy",
                        row["policy_source"]),
                _record(runtime, f"Project {project} latest "
                        f"{f.TABLE[row['index']][1]} option sheet",
                        row["sheet_source"]),
            ]
            event = runtime.store.event(runtime.session, row["current"])
            env = build(runtime.memory, runtime.session,
                        event["event_id"], event["source_ref"], ids,
                        operator_opt_in=True)
            if (env.get("status") != STATUS
                    or env.get("typed_jef_action") != row["expected"]
                    or env.get("human_source_lineage_verified") is not True
                    or env.get("formatter_only") is not True):
                raise ValueError("RUN75_AUTHENTICATED_SOURCE_RED")
            messages = env["messages"]
            if any(row[k] in dumps(messages)
                   for k in ("current", "policy_source", "sheet_source")):
                raise ValueError("RUN75_RAW_SOURCE_PROMPT_LEAK_RED")
            case = {
                "index": row["index"],
                "project_sha256": f.sha(project.encode()),
                "expected": row["expected"],
                "typed_jef_action": env["typed_jef_action"],
                "input_sha256": f.sha(dumps(messages).encode()),
                "source_sha256": {
                    k: f.sha(row[k].encode("utf-8"))
                    for k in ("current", "policy_source", "sheet_source")},
                "native_final": False, "process_reaped": False,
                "post_source_rechecked": False,
                "status": "INCOMPLETE", "strict": 0,
            }
            report["cases"].append(case)
            _save(report_path, report)
            before = len(runtime.pool.release_history)
            try:
                runner = runtime.pool.get("C3_LANGUAGE")
                output = "".join(runner.generate(
                    messages, runtime.cancel_event,
                    time.monotonic() + 90, 32, f.SCHEMA, seed=f.SEED))
                metrics = dict(runner.last_metrics)
                case["output"] = output
                case["output_sha256"] = f.sha(output.encode("utf-8"))
                case["output_bytes"] = len(output.encode("utf-8"))
                case["parsed_action"] = f.run68.decode_schema(output)
                case["strict"] = f.score(output, row["expected"])
                case["native_final"] = metrics.get("status") == "FINAL"
                case["actual_model"] = metrics.get("actual_model")
                case["generated_tokens"] = metrics.get("generated_tokens")
            except Exception as exc:
                case["error_type"] = type(exc).__name__
            finally:
                try:
                    runtime.pool.unload()
                except Exception as exc:
                    case["release_error_type"] = type(exc).__name__
                releases = runtime.pool.release_history[before:]
                case["process_reaped"] = (
                    bool(releases)
                    and any(x.get("before") is not None for x in releases)
                    and all(x.get("process_reaped") is True for x in releases))
                after = build(runtime.memory, runtime.session,
                              event["event_id"], event["source_ref"], ids,
                              operator_opt_in=True)
                case["post_source_rechecked"] = (
                    after.get("status") == STATUS
                    and after.get("messages_sha256") == env["messages_sha256"]
                    and after.get("typed_jef_action") == row["expected"])
                case["status"] = (
                    "RECORDED" if case["native_final"]
                    and case.get("actual_model") == C3_FILE
                    and case["process_reaped"]
                    and case["post_source_rechecked"]
                    and 0 < case.get("output_bytes", 0) <= 1024
                    else "STRUCTURAL_RED")
                _save(report_path, report)
            if case["status"] != "RECORDED":
                raise RuntimeError("RUN75_NATIVE_ROW_RED")
        report["no_live_output"] = (
            runtime.store.one(
                "SELECT COUNT(*) AS n FROM messages WHERE role='assistant' "
                "AND status IN ('FINAL','OUTPUT_COMMITTED')")["n"] == 0
            and runtime.store.one("SELECT COUNT(*) AS n FROM actions")["n"] == 0)
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        report["status"] = "STRUCTURAL_RED"
    finally:
        if runtime is not None:
            try:
                runtime.close()
            except Exception as exc:
                report["close_error_type"] = type(exc).__name__
                report["status"] = "STRUCTURAL_RED"
        try:
            report["closed_store_ok"] = bool(audit_closed(home)["ok"])
        except Exception:
            report["closed_store_ok"] = False
        cases = report["cases"]
        report["native_call_count"] = len(cases)
        report["strict"] = sum(c.get("strict", 0) for c in cases)
        structural = (
            len(cases) == 6
            and all(c["status"] == "RECORDED" for c in cases)
            and report.get("no_live_output") is True
            and report["closed_store_ok"]
            and report["status"] != "STRUCTURAL_RED")
        report["status"] = (
            "FORMATTER_SMALL_SYNTHETIC_PASS" if structural
            and report["strict"] == 6
            else "FORMATTER_FIDELITY_RED" if structural
            else "STRUCTURAL_RED")
        _save(report_path, report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    r = run(args.home, args.out)
    print(dumps({"status": r["status"], "strict": r["strict"],
                 "native_call_count": r["native_call_count"]}))
    raise SystemExit(0 if r["status"] in (
        "FORMATTER_SMALL_SYNTHETIC_PASS", "FORMATTER_FIDELITY_RED") else 1)


if __name__ == "__main__":
    main()

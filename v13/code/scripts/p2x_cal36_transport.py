#!/usr/bin/env python3
"""P2X CAL36 source-transport diagnostic; isolated LoRA, no gate promotion.

Only the pre-registered calibration partition is used. The 72 validation
rows and all training rows are deliberately excluded.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import time

from scripts import p2x_candidate360_standalone as candidate
from scripts import p2x_disjoint_receiver_trainset as fixture
from scripts import p2x_native_receiver_eval_scorer as scorer
from scripts import p2x_c3_lora_pilot as resources
from v13.common import atomic_write

SCHEMA = "v13.p2x.cal36_transport.v1"
ADAPTER_SHA = "062c20d796c59169579529f4a069f77693a847123f599d00f374bd01a8618e92"
ARMS = ("both_exact", "c3_only")
EXPECTED = 72
CALL_SECONDS = candidate.CALL_SECONDS
OVERALL_SECONDS = 1800


def need(ok, reason):
    if not ok:
        raise ValueError("P2X_CAL36_" + reason)


def canonical(obj):
    return scorer.canonical(obj)


def sha(data):
    return scorer.sha(data)


def plan():
    rows = fixture.fixtures()
    fixture.validate(rows)
    need(sha(fixture.canonical(rows)) == scorer.FIXTURE_SHA, "FROZEN_FIXTURE_RED")
    calibration = sorted((r for r in rows if r["partition"] == "calibration"),
                         key=lambda r: r["id"])
    need(len(calibration) == 36
         and len({r["id"] for r in calibration}) == 36
         and all(sum(r["oracle_action"] == a for r in calibration) == 12
                 for a in ("A", "B", "NONE")), "CALIBRATION_BALANCE_RED")
    prompts, answers = [], []
    for row in calibration:
        rendered = fixture.views(row, rows)
        answers.append({"id": row["id"], "oracle_action": row["oracle_action"]})
        for arm in ARMS:
            prompts.append({"id": row["id"], "arm": arm,
                            "messages": [{"role": "user", "content": rendered[arm]}]})
    need(len(prompts) == EXPECTED and len(answers) == 36, "PLAN_COUNT_RED")
    for prompt in prompts:
        need(type(prompt["messages"][0]["content"]) is str
             and not any(x in prompt["messages"][0]["content"] for x in
                         ("oracle_action", "target_action", "max_first", "max_second")),
             "MODEL_INPUT_LEAK_RED")
    return prompts, answers


def score(records, prompts, answers):
    expected_prompts, expected_answers = plan()
    need(prompts == expected_prompts and answers == expected_answers,
         "FROZEN_PLAN_RED")
    need(type(records) is list and len(records) == EXPECTED, "RAW_COVERAGE_RED")
    oracle = {a["id"]: a["oracle_action"] for a in answers}
    counts = {arm: {key: 0 for key in
              ("correct", "wrong_committed", "unknown", "unparseable")} for arm in ARMS}
    details = []
    positive_correct = negative_abstained = paired_source_sensitive = none_correct = 0
    for i, (rec, prompt) in enumerate(zip(records, prompts)):
        need(type(rec) is dict and set(rec) ==
             {"id", "arm", "input_sha256", "model_sha256", "runtime_sha256",
              "adapter_sha256", "seed", "status", "model_called", "native_calls",
              "duration_s", "output", "metrics"}, "RAW_SHAPE_RED")
        duration = rec["duration_s"]
        need((rec["id"], rec["arm"]) == (prompt["id"], prompt["arm"])
             and rec["input_sha256"] == sha(canonical(prompt["messages"]))
             and rec["model_sha256"] == scorer.MODEL_SHA
             and rec["runtime_sha256"] == scorer.RUNTIME_SHA
             and rec["adapter_sha256"] == ADAPTER_SHA
             and type(rec["seed"]) is int and rec["seed"] == scorer.SEED
             and rec["status"] == "FINAL" and rec["model_called"] is True
             and type(rec["native_calls"]) is int and rec["native_calls"] == 1
             and type(duration) in (int, float) and math.isfinite(duration)
             and 0 <= duration <= CALL_SECONDS
             and type(rec["output"]) is str
             and type(rec["metrics"]) is dict
             and rec["metrics"].get("status") == "FINAL",
             "RAW_BINDING_RED")
        parsed = scorer.strict_action(rec["output"])
        expected = oracle[prompt["id"]] if prompt["arm"] == "both_exact" else "UNKNOWN"
        kind = ("correct" if parsed == expected else
                "wrong_committed" if parsed in ("A", "B", "NONE") else
                "unknown" if parsed == "UNKNOWN" else "unparseable")
        counts[prompt["arm"]][kind] += 1
        details.append({"id_sha256": sha(prompt["id"].encode("utf-8")),
                        "arm": prompt["arm"], "expected": expected,
                        "parsed": parsed, "kind": kind})
        if prompt["arm"] == "both_exact":
            if expected in ("A", "B") and parsed == expected:
                positive_correct += 1
            if expected == "NONE" and parsed == "NONE":
                none_correct += 1
        elif parsed == "UNKNOWN":
            negative_abstained += 1
        if i % 2 == 1:
            before, after = details[-2:]
            if (before["expected"] in ("A", "B")
                    and before["parsed"] == before["expected"]
                    and after["parsed"] == "UNKNOWN"):
                paired_source_sensitive += 1
    need(all(sum(k.values()) == 36 for k in counts.values()),
         "ARM_COVERAGE_RED")
    return {"schema": SCHEMA + ".score.v1",
            "status": "P2X_CAL36_DIAGNOSTIC_NO_GATE",
            "fixture_sha256": scorer.FIXTURE_SHA,
            "model_sha256": scorer.MODEL_SHA,
            "runtime_sha256": scorer.RUNTIME_SHA,
            "runner_binary_sha256": candidate.BINARY_SHA,
            "adapter_sha256": ADAPTER_SHA, "seed": scorer.SEED,
            "rows": 36, "native_calls": EXPECTED, "per_arm": counts,
            "positive_correct": positive_correct,
            "negative_abstained": negative_abstained,
            "paired_source_sensitive": paired_source_sensitive,
            "none_correct": none_correct, "details": details,
            "calibration_only": True, "validation_rows_used": 0,
            "train_rows_used": 0, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
            "jepa_weight": 0, "ag6_approved": False,
            "redmi_measured": False, "whole_system_complete": False}


def preflight(server_binary, runtime_archive, model, adapter, out):
    out = Path(out)
    need(not out.exists() and not out.is_symlink()
         and out.parent.is_dir(), "FRESH_OUTPUT_RED")
    binary = candidate.admit_file(server_binary, candidate.BINARY_SHA, "BINARY")
    candidate.admit_file(runtime_archive, scorer.RUNTIME_SHA, "RUNTIME")
    model = candidate.admit_file(model, scorer.MODEL_SHA, "MODEL")
    adapter = candidate.admit_file(adapter, ADAPTER_SHA, "ADAPTER")
    need(len({str(binary), str(model), str(adapter),
              str(Path(runtime_archive).resolve())}) == 4,
         "DISTINCT_ASSETS_RED")
    prompts, answers = plan()
    admission = resources.resource_admission(out.parent)
    return binary, model, adapter, prompts, answers, admission


def run_native(server_binary, runtime_archive, model, adapter, out,
               server_factory=candidate.LocalServer):
    binary, model, adapter, prompts, answers, admission = preflight(
        server_binary, runtime_archive, model, adapter, out)
    out = Path(out)
    out.mkdir(mode=0o700)
    receipt = {"schema": SCHEMA, "status": "RUNNING",
               "evidence_kind": "LINUX_NATIVE_CALIBRATION_PARTITION_ONLY",
               "fixture_sha256": scorer.FIXTURE_SHA,
               "model_sha256": scorer.MODEL_SHA,
               "runtime_sha256": scorer.RUNTIME_SHA,
               "runner_binary_sha256": candidate.BINARY_SHA,
               "adapter_sha256": ADAPTER_SHA, "seed": scorer.SEED,
               "expected_calls": EXPECTED, "recorded_calls": 0,
               "age_authority": 0, "weight_updates": False,
               "ag6_approved": False, "production_activation": False,
               "jepa_weight": 0, "redmi_measured": False,
               "canonical_gate_pass": False, "whole_system_complete": False,
               "validation_rows_used": 0, "train_rows_used": 0,
               "resources": admission}
    records = []

    def persist():
        atomic_write(out / "RAW.json", canonical(records).decode("utf-8"))
        atomic_write(out / "RECEIPT.json", canonical(receipt).decode("utf-8"))

    atomic_write(out / "INPUTS.json", canonical(prompts).decode("utf-8"))
    atomic_write(out / "ANSWERS.json", canonical(answers).decode("utf-8"))
    persist()
    server = None
    started = time.monotonic()
    try:
        server = server_factory(binary, model, adapter, out / "SERVER_RAW.log")
        for prompt in prompts:
            remaining = OVERALL_SECONDS - (time.monotonic() - started)
            need(remaining > 10, "OVERALL_DEADLINE_RED")
            begun = time.monotonic()
            output, metrics = server.generate(
                prompt["messages"], min(CALL_SECONDS - 2, remaining))
            records.append(candidate.record_call(
                prompt, output, time.monotonic() - begun, metrics, ADAPTER_SHA))
            receipt["recorded_calls"] = len(records)
            persist()
        server.close()
        server = None
        for path, expected, label in ((server_binary, candidate.BINARY_SHA, "BINARY"),
                                      (runtime_archive, scorer.RUNTIME_SHA, "RUNTIME"),
                                      (model, scorer.MODEL_SHA, "MODEL"),
                                      (adapter, ADAPTER_SHA, "ADAPTER")):
            candidate.admit_file(path, expected, label)
        snapshot = score(records, prompts, answers)
        atomic_write(out / "SCORE.json", canonical(snapshot).decode("utf-8"))
        receipt["status"] = "P2X_CAL36_NATIVE_DIAGNOSTIC_NO_GATE"
        receipt["process_reaped"] = True
        for name, key in (("INPUTS.json", "inputs_sha256"),
                          ("ANSWERS.json", "answers_sha256"),
                          ("RAW.json", "raw_sha256"),
                          ("SCORE.json", "score_sha256")):
            receipt[key] = resources.file_sha(out / name)
        persist()
    except BaseException as exc:
        receipt["status"] = "FAIL_RETAIN_RAW"
        receipt["error_type"] = type(exc).__name__
        receipt["error_message"] = str(exc)[:320]
        persist()
        raise
    finally:
        if server is not None:
            server.close()
            receipt["process_reaped_on_exit"] = True
            persist()
    return receipt


def verify(evidence):
    evidence = Path(evidence)
    need(evidence.is_dir() and not evidence.is_symlink(), "EVIDENCE_DIR_RED")
    for name in ("INPUTS.json", "ANSWERS.json", "RAW.json", "SCORE.json",
                 "RECEIPT.json"):
        need((evidence / name).is_file() and not (evidence / name).is_symlink(),
             "EVIDENCE_FILE_RED")
    prompts = json.loads((evidence / "INPUTS.json").read_bytes())
    answers = json.loads((evidence / "ANSWERS.json").read_bytes())
    records = json.loads((evidence / "RAW.json").read_bytes())
    snapshot = json.loads((evidence / "SCORE.json").read_bytes())
    receipt = json.loads((evidence / "RECEIPT.json").read_bytes())
    replay = score(records, prompts, answers)
    need(snapshot == replay and canonical(snapshot) == canonical(replay),
         "SCORE_REPLAY_RED")
    need(receipt.get("schema") == SCHEMA
         and receipt.get("status") == "P2X_CAL36_NATIVE_DIAGNOSTIC_NO_GATE"
         and type(receipt.get("recorded_calls")) is int
         and receipt["recorded_calls"] == EXPECTED
         and receipt.get("expected_calls") == EXPECTED
         and receipt.get("process_reaped") is True
         and receipt.get("fixture_sha256") == scorer.FIXTURE_SHA
         and receipt.get("model_sha256") == scorer.MODEL_SHA
         and receipt.get("runtime_sha256") == scorer.RUNTIME_SHA
         and receipt.get("runner_binary_sha256") == candidate.BINARY_SHA
         and receipt.get("adapter_sha256") == ADAPTER_SHA
         and receipt.get("seed") == scorer.SEED
         and receipt.get("age_authority") == 0
         and receipt.get("weight_updates") is False
         and receipt.get("ag6_approved") is False
         and receipt.get("production_activation") is False
         and receipt.get("jepa_weight") == 0
         and receipt.get("canonical_gate_pass") is False
         and receipt.get("redmi_measured") is False
         and receipt.get("whole_system_complete") is False
         and receipt.get("validation_rows_used") == 0
         and receipt.get("train_rows_used") == 0,
         "RECEIPT_GATE_RED")
    for name, key in (("INPUTS.json", "inputs_sha256"),
                      ("ANSWERS.json", "answers_sha256"),
                      ("RAW.json", "raw_sha256"),
                      ("SCORE.json", "score_sha256")):
        need(receipt.get(key) == resources.file_sha(evidence / name),
             "RECEIPT_SHA_RED")
    return replay


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-check", action="store_true")
    parser.add_argument("--verify", type=Path)
    for name in ("server-binary", "runtime-archive", "model", "adapter", "out"):
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    if args.plan_check:
        prompts, answers = plan()
        print(json.dumps({"status": "SOURCE_ONLY_NO_NATIVE", "calls": len(prompts),
                          "rows": len(answers), "fixture_sha256": scorer.FIXTURE_SHA,
                          "step2_status": "UTILITY_FAIL"}, sort_keys=True))
        return 0
    if args.verify is not None:
        print(json.dumps(verify(args.verify), sort_keys=True))
        return 0
    for name in ("server_binary", "runtime_archive", "model", "adapter", "out"):
        if getattr(args, name) is None:
            parser.error("--" + name.replace("_", "-") + " required")
    result = run_native(args.server_binary, args.runtime_archive, args.model,
                        args.adapter, args.out)
    print(json.dumps({"status": result["status"],
                      "recorded_calls": result["recorded_calls"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

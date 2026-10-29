#!/usr/bin/env python3
"""P2X 16 training-row x 2 adapter JSON-schema inference; NO heldout utility."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

from scripts import p2x_candidate360_standalone as candidate
from scripts import p2x_c3_json_target_fourstep as jsonpilot
from scripts import p2x_c3_lora_pilot as resources
from scripts import p2x_disjoint_receiver_trainset as fixture
from scripts import p2x_native_receiver_eval_scorer as scorer
from v13.common import atomic_write

SCHEMA = "v13.p2x.json_train16_adapter_comparison.v1"
ADAPTERS = {
    "bare": "062c20d796c59169579529f4a069f77693a847123f599d00f374bd01a8618e92",
    "json": "7a9e04377607045e86ce8d45260caa762648745260ffacad853626353c408ca6",
}
EXPECTED = 32
CALL_SECONDS = candidate.CALL_SECONDS
OVERALL_SECONDS = 1800


def need(ok, reason):
    if not ok:
        raise ValueError("P2X_TRAIN16_" + reason)


def canonical(obj):
    return scorer.canonical(obj)


def sha(raw):
    return scorer.sha(raw)


def plan():
    rows = fixture.fixtures()
    fixture.validate(rows)
    need(sha(fixture.canonical(rows)) == resources.FIXTURE_SHA,
         "FROZEN_FIXTURE_RED")
    train, validation, _ = fixture.training_and_validation(rows)
    train_bytes = b"".join(canonical(r) + b"\n" for r in train)
    need(sha(train_bytes) == resources.EXPORT_SHA["train.jsonl"],
         "FROZEN_TRAIN_EXPORT_RED")
    selected = jsonpilot.select_balanced({
        "train.jsonl": train, "validation_inputs.jsonl": validation})
    need(len(selected) == 16 and len({r["id"] for r in selected}) == 16,
         "TRAIN16_SELECTION_RED")
    need(all(sum(r["target_action"] == label for r in selected) == 4
             for label in resources.LABELS), "TRAIN16_BALANCE_RED")
    answers = [{"id": r["id"], "target_action": r["target_action"]}
               for r in selected]
    prompts = [{"id": r["id"], "arm": variant, "messages": r["messages"]}
               for variant in ADAPTERS for r in selected]
    need(len(prompts) == EXPECTED, "TRAIN16_COUNT_RED")
    for p in prompts:
        need(type(p["messages"][0]["content"]) is str
             and not any(t in p["messages"][0]["content"] for t in
                         ("oracle_action", "target_action", "max_first", "max_second")),
             "TRAIN16_TARGET_LEAK_RED")
    return prompts, answers


def score(records, prompts, answers):
    fixed_prompts, fixed_answers = plan()
    need(prompts == fixed_prompts and answers == fixed_answers,
         "FROZEN_PLAN_RED")
    need(type(records) is list and len(records) == EXPECTED,
         "RAW_COVERAGE_RED")
    oracle = {a["id"]: a["target_action"] for a in answers}
    counts = {arm: {label: {"correct": 0, "wrong": 0, "unparseable": 0}
                    for label in resources.LABELS} for arm in ADAPTERS}
    outputs = {arm: {} for arm in ADAPTERS}
    details = []
    for rec, prompt in zip(records, prompts):
        need(type(rec) is dict and set(rec) ==
             {"id", "arm", "input_sha256", "model_sha256", "runtime_sha256",
              "adapter_sha256", "seed", "status", "model_called", "native_calls",
              "duration_s", "output", "metrics"}, "RAW_SHAPE_RED")
        arm = prompt["arm"]
        duration = rec["duration_s"]
        need((rec["id"], rec["arm"]) == (prompt["id"], arm)
             and rec["input_sha256"] == sha(canonical(prompt["messages"]))
             and rec["model_sha256"] == scorer.MODEL_SHA
             and rec["runtime_sha256"] == scorer.RUNTIME_SHA
             and rec["adapter_sha256"] == ADAPTERS[arm]
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
        label = oracle[prompt["id"]]
        kind = ("correct" if parsed == label else
                "unparseable" if parsed not in resources.LABELS else "wrong")
        counts[arm][label][kind] += 1
        outputs[arm][prompt["id"]] = parsed
        details.append({"id_sha256": sha(prompt["id"].encode()),
                        "arm": arm, "expected": label,
                        "parsed": parsed, "kind": kind})
    need(all(sum(sum(v.values()) for v in by_label.values()) == 16
             for by_label in counts.values()), "ARM_COUNT_RED")
    changed = sum(outputs["bare"][a["id"]] != outputs["json"][a["id"]]
                  for a in answers)
    correct = {arm: sum(v["correct"] for v in by_label.values())
               for arm, by_label in counts.items()}
    return {"schema": SCHEMA + ".score.v1",
            "status": "TRAINING_ONLY_IN_SAMPLE_NO_GATE",
            "fixture_sha256": resources.FIXTURE_SHA,
            "train_sha256": resources.EXPORT_SHA["train.jsonl"],
            "model_sha256": scorer.MODEL_SHA,
            "runtime_sha256": scorer.RUNTIME_SHA,
            "runner_binary_sha256": candidate.BINARY_SHA,
            "adapters": ADAPTERS, "seed": scorer.SEED,
            "training_examples": 16, "native_calls": EXPECTED,
            "per_label": counts, "correct_in_sample": correct,
            "paired_action_changes": changed, "details": details,
            "train_only": True, "calibration_rows_used": 0,
            "validation_rows_used": 0, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
            "jepa_weight": 0, "ag6_approved": False,
            "redmi_measured": False, "whole_system_complete": False}


def preflight(server_binary, runtime_archive, model, bare_adapter,
              json_adapter, out):
    out = Path(out)
    need(not out.exists() and not out.is_symlink() and out.parent.is_dir(),
         "FRESH_OUTPUT_RED")
    binary = candidate.admit_file(server_binary, candidate.BINARY_SHA, "BINARY")
    candidate.admit_file(runtime_archive, scorer.RUNTIME_SHA, "RUNTIME")
    model = candidate.admit_file(model, scorer.MODEL_SHA, "MODEL")
    adapters = {
        "bare": candidate.admit_file(bare_adapter, ADAPTERS["bare"], "BARE_ADAPTER"),
        "json": candidate.admit_file(json_adapter, ADAPTERS["json"], "JSON_ADAPTER"),
    }
    need(len({str(binary), str(model), *(str(p) for p in adapters.values()),
              str(Path(runtime_archive).resolve())}) == 5,
         "DISTINCT_ASSETS_RED")
    prompts, answers = plan()
    admission = resources.resource_admission(out.parent)
    return binary, model, adapters, prompts, answers, admission


def run_native(server_binary, runtime_archive, model, bare_adapter,
               json_adapter, out, server_factory=candidate.LocalServer):
    binary, model, adapters, prompts, answers, admission = preflight(
        server_binary, runtime_archive, model, bare_adapter, json_adapter, out)
    out = Path(out)
    out.mkdir(mode=0o700)
    receipt = {"schema": SCHEMA, "status": "RUNNING",
               "evidence_kind": "LINUX_NATIVE_TRAINING_ONLY_IN_SAMPLE",
               "fixture_sha256": resources.FIXTURE_SHA,
               "train_sha256": resources.EXPORT_SHA["train.jsonl"],
               "model_sha256": scorer.MODEL_SHA,
               "runtime_sha256": scorer.RUNTIME_SHA,
               "runner_binary_sha256": candidate.BINARY_SHA,
               "adapters": ADAPTERS, "seed": scorer.SEED,
               "expected_calls": EXPECTED, "recorded_calls": 0,
               "age_authority": 0, "weight_updates": False,
               "ag6_approved": False, "production_activation": False,
               "jepa_weight": 0, "redmi_measured": False,
               "canonical_gate_pass": False, "whole_system_complete": False,
               "calibration_rows_used": 0, "validation_rows_used": 0,
               "resources": admission}
    records = []

    def persist():
        atomic_write(out / "RAW.json", canonical(records).decode())
        atomic_write(out / "RECEIPT.json", canonical(receipt).decode())

    atomic_write(out / "INPUTS.json", canonical(prompts).decode())
    atomic_write(out / "ANSWERS.json", canonical(answers).decode())
    persist()
    server = None
    started = time.monotonic()
    try:
        for arm, adapter in adapters.items():
            server = server_factory(binary, model, adapter,
                                    out / ("SERVER_" + arm + "_RAW.log"))
            for prompt in (p for p in prompts if p["arm"] == arm):
                remaining = OVERALL_SECONDS - (time.monotonic() - started)
                need(remaining > 10, "OVERALL_DEADLINE_RED")
                begun = time.monotonic()
                output, metrics = server.generate(
                    prompt["messages"], min(CALL_SECONDS - 2, remaining))
                records.append(candidate.record_call(
                    prompt, output, time.monotonic() - begun, metrics, ADAPTERS[arm]))
                receipt["recorded_calls"] = len(records)
                persist()
            server.close()
            need(server.proc is None or server.proc.poll() is not None,
                 "SERVER_NOT_REAPED_RED")
            server = None
        for path, expected, label in (
            (server_binary, candidate.BINARY_SHA, "BINARY"),
            (runtime_archive, scorer.RUNTIME_SHA, "RUNTIME"),
            (model, scorer.MODEL_SHA, "MODEL"),
            (bare_adapter, ADAPTERS["bare"], "BARE_ADAPTER"),
            (json_adapter, ADAPTERS["json"], "JSON_ADAPTER"),
        ):
            candidate.admit_file(path, expected, label)
        snapshot = score(records, prompts, answers)
        atomic_write(out / "SCORE.json", canonical(snapshot).decode())
        receipt["status"] = "TRAINING_ONLY_NATIVE_DIAGNOSTIC_NO_GATE"
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
         and receipt.get("status") == "TRAINING_ONLY_NATIVE_DIAGNOSTIC_NO_GATE"
         and type(receipt.get("recorded_calls")) is int
         and receipt["recorded_calls"] == EXPECTED
         and receipt.get("expected_calls") == EXPECTED
         and receipt.get("process_reaped") is True
         and receipt.get("fixture_sha256") == resources.FIXTURE_SHA
         and receipt.get("train_sha256") == resources.EXPORT_SHA["train.jsonl"]
         and receipt.get("model_sha256") == scorer.MODEL_SHA
         and receipt.get("runtime_sha256") == scorer.RUNTIME_SHA
         and receipt.get("runner_binary_sha256") == candidate.BINARY_SHA
         and receipt.get("adapters") == ADAPTERS
         and receipt.get("seed") == scorer.SEED
         and receipt.get("age_authority") == 0
         and receipt.get("weight_updates") is False
         and receipt.get("ag6_approved") is False
         and receipt.get("production_activation") is False
         and receipt.get("jepa_weight") == 0
         and receipt.get("canonical_gate_pass") is False
         and receipt.get("redmi_measured") is False
         and receipt.get("whole_system_complete") is False
         and receipt.get("calibration_rows_used") == 0
         and receipt.get("validation_rows_used") == 0,
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
    for name in ("server-binary", "runtime-archive", "model",
                 "bare-adapter", "json-adapter", "out"):
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    if args.plan_check:
        prompts, answers = plan()
        print(json.dumps({"status": "SOURCE_ONLY_TRAIN16_NO_NATIVE",
                          "calls": len(prompts), "rows": len(answers),
                          "fixture_sha256": resources.FIXTURE_SHA,
                          "step2_status": "UTILITY_FAIL"}, sort_keys=True))
        return 0
    if args.verify is not None:
        print(json.dumps(verify(args.verify), sort_keys=True))
        return 0
    for name in ("server_binary", "runtime_archive", "model",
                 "bare_adapter", "json_adapter", "out"):
        if getattr(args, name) is None:
            parser.error("--" + name.replace("_", "-") + " required")
    result = run_native(args.server_binary, args.runtime_archive, args.model,
                        args.bare_adapter, args.json_adapter, args.out)
    print(json.dumps({"status": result["status"],
                      "recorded_calls": result["recorded_calls"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

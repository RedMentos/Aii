#!/usr/bin/env python3
"""Frozen P2X JSON-adapter training16: schema ON/OFF only; no utility gate."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

from scripts import p2x_json_train16_eval as base
from scripts import p2x_candidate360_standalone as candidate
from scripts import p2x_native_receiver_eval_scorer as scorer
from v13.common import atomic_write

SCHEMA = "v13.p2x.schema_toggle_train16.v1"
MODES = ("on", "off")
ADAPTER_SHA = base.ADAPTERS["json"]
EXPECTED = 32
CALL_SECONDS = base.CALL_SECONDS
OVERALL_SECONDS = base.OVERALL_SECONDS


def need(ok, reason):
    if not ok:
        raise ValueError("P2X_SCHEMA_TOGGLE_" + reason)


def canonical(obj):
    return scorer.canonical(obj)


def sha(raw):
    return scorer.sha(raw)


def plan():
    original, answers = base.plan()
    selected = original[:16]
    need(len(selected) == 16 and all(p["arm"] == "bare" for p in selected),
         "PARENT_PLAN_RED")
    prompts = [{"id": p["id"], "arm": mode, "messages": p["messages"]}
               for mode in MODES for p in selected]
    need(len(prompts) == EXPECTED
         and len({p["id"] for p in selected}) == 16
         and [p["messages"] for p in prompts[:16]]
         == [p["messages"] for p in prompts[16:]],
         "PAIRED_PLAN_RED")
    return prompts, answers


class SchemaServer(candidate.LocalServer):
    """Keep the exact pinned parent server; alter only the completion schema key."""
    def __init__(self, binary, model, adapter, log, mode):
        need(mode in MODES, "MODE_RED")
        self.mode = mode
        self.completion_request = None
        super().__init__(binary, model, adapter, log)

    def request(self, method, path, data=None, timeout=CALL_SECONDS):
        if method == "POST" and path == "/completion":
            need(type(data) is dict and data.get("json_schema")
                 == candidate.hb1.C3_SCHEMA, "PARENT_SCHEMA_RED")
            payload = dict(data)
            if self.mode == "off":
                payload.pop("json_schema")
            self.completion_request = payload
            return super().request(method, path, payload, timeout)
        return super().request(method, path, data, timeout)

    def generate(self, messages, timeout):
        self.completion_request = None
        output, metrics = super().generate(messages, timeout)
        need(type(self.completion_request) is dict, "MISSING_REQUEST_RED")
        return output, dict(metrics, schema_mode=self.mode,
                            completion_request=self.completion_request)


def _check_request(req, mode):
    need(type(req) is dict and type(req.get("prompt")) is str
         and type(req.get("n_predict")) is int
         and req["n_predict"] == candidate.MAX_TOKENS
         and req.get("temperature") == .1 and req.get("top_k") == 50
         and req.get("repeat_penalty") == 1.05
         and req.get("seed") == scorer.SEED
         and req.get("stream") is False
         and req.get("cache_prompt") is True
         and req.get("id_slot") == 0
         and req.get("return_tokens") is True,
         "REQUEST_SETTINGS_RED")
    if mode == "on":
        need(req.get("json_schema") == candidate.hb1.C3_SCHEMA,
             "SCHEMA_ON_RED")
    else:
        need("json_schema" not in req, "SCHEMA_OFF_RED")


def score(records, prompts, answers):
    expected_prompts, expected_answers = plan()
    need(prompts == expected_prompts and answers == expected_answers,
         "FROZEN_PLAN_RED")
    need(type(records) is list and len(records) == EXPECTED,
         "COVERAGE_RED")
    oracle = {a["id"]: a["target_action"] for a in answers}
    counts = {mode: {label: {"correct": 0, "wrong": 0, "unparseable": 0}
                     for label in base.resources.LABELS} for mode in MODES}
    output_by_mode = {mode: {} for mode in MODES}
    requests = {mode: {} for mode in MODES}
    bare_exact = {mode: 0 for mode in MODES}
    details = []
    for rec, p in zip(records, prompts):
        mode = p["arm"]
        need(type(rec) is dict and set(rec) ==
             {"id", "arm", "input_sha256", "model_sha256", "runtime_sha256",
              "adapter_sha256", "seed", "status", "model_called", "native_calls",
              "duration_s", "output", "metrics"}, "RAW_SHAPE_RED")
        duration = rec["duration_s"]
        metrics = rec["metrics"]
        need((rec["id"], rec["arm"]) == (p["id"], mode)
             and rec["input_sha256"] == sha(canonical(p["messages"]))
             and rec["model_sha256"] == scorer.MODEL_SHA
             and rec["runtime_sha256"] == scorer.RUNTIME_SHA
             and rec["adapter_sha256"] == ADAPTER_SHA
             and type(rec["seed"]) is int and rec["seed"] == scorer.SEED
             and rec["status"] == "FINAL" and rec["model_called"] is True
             and type(rec["native_calls"]) is int and rec["native_calls"] == 1
             and type(duration) in (int, float) and math.isfinite(duration)
             and 0 <= duration <= CALL_SECONDS
             and type(rec["output"]) is str
             and type(metrics) is dict and metrics.get("status") == "FINAL"
             and metrics.get("schema_mode") == mode,
             "RAW_BINDING_RED")
        req = metrics.get("completion_request")
        _check_request(req, mode)
        requests[mode][p["id"]] = {k: v for k, v in req.items()
                                   if k != "json_schema"}
        parsed = scorer.strict_action(rec["output"])
        label = oracle[p["id"]]
        kind = ("correct" if parsed == label else
                "unparseable" if parsed not in base.resources.LABELS else "wrong")
        counts[mode][label][kind] += 1
        output_by_mode[mode][p["id"]] = parsed
        bare = rec["output"].strip() if parsed == "UNPARSEABLE" else ""
        if bare in base.resources.LABELS:
            bare_exact[mode] += 1
        details.append({"id_sha256": sha(p["id"].encode()), "mode": mode,
                        "expected": label, "strict_parsed": parsed,
                        "kind": kind, "bare_label_only": bare if bare in base.resources.LABELS else None})
    for answer in answers:
        i = answer["id"]
        need(requests["on"][i] == requests["off"][i],
             "NONSCHEMA_REQUEST_DIFFERENCE_RED")
    need(all(sum(sum(v.values()) for v in by_label.values()) == 16
             for by_label in counts.values()), "LABEL_COUNT_RED")
    return {"schema": SCHEMA + ".score.v1",
            "status": "TRAINING_ONLY_SCHEMA_ABLATION_NO_GATE",
            "fixture_sha256": base.resources.FIXTURE_SHA,
            "train_sha256": base.resources.EXPORT_SHA["train.jsonl"],
            "model_sha256": scorer.MODEL_SHA,
            "runtime_sha256": scorer.RUNTIME_SHA,
            "runner_binary_sha256": candidate.BINARY_SHA,
            "adapter_sha256": ADAPTER_SHA, "seed": scorer.SEED,
            "training_examples": 16, "native_calls": EXPECTED,
            "per_label": counts,
            "correct_strict_in_sample": {mode: sum(v["correct"] for v in by_label.values())
                                         for mode, by_label in counts.items()},
            "unparseable_bare_label_only": bare_exact,
            "paired_strict_action_changes": sum(
                output_by_mode["on"][a["id"]] != output_by_mode["off"][a["id"]]
                for a in answers),
            "details": details,
            "train_only": True, "calibration_rows_used": 0,
            "validation_rows_used": 0, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
            "jepa_weight": 0, "ag6_approved": False,
            "redmi_measured": False, "whole_system_complete": False}


def preflight(server_binary, runtime_archive, model, adapter, out):
    out = Path(out)
    need(not out.exists() and not out.is_symlink() and out.parent.is_dir(),
         "FRESH_OUTPUT_RED")
    binary = candidate.admit_file(server_binary, candidate.BINARY_SHA, "BINARY")
    candidate.admit_file(runtime_archive, scorer.RUNTIME_SHA, "RUNTIME")
    model = candidate.admit_file(model, scorer.MODEL_SHA, "MODEL")
    adapter = candidate.admit_file(adapter, ADAPTER_SHA, "JSON_ADAPTER")
    need(len({str(p.resolve()) for p in (binary, model, adapter,
                                         Path(runtime_archive))}) == 4,
         "ASSET_ALIAS_RED")
    prompts, answers = plan()
    admission = base.resources.resource_admission(out.parent)
    return binary, model, adapter, prompts, answers, admission


def run_native(server_binary, runtime_archive, model, adapter, out,
               server_factory=SchemaServer):
    binary, model, adapter, prompts, answers, admission = preflight(
        server_binary, runtime_archive, model, adapter, out)
    out = Path(out)
    out.mkdir(mode=0o700)
    receipt = {"schema": SCHEMA, "status": "RUNNING",
               "evidence_kind": "LINUX_NATIVE_TRAINING_ONLY_SCHEMA_ABLATION",
               "fixture_sha256": base.resources.FIXTURE_SHA,
               "train_sha256": base.resources.EXPORT_SHA["train.jsonl"],
               "model_sha256": scorer.MODEL_SHA,
               "runtime_sha256": scorer.RUNTIME_SHA,
               "runner_binary_sha256": candidate.BINARY_SHA,
               "adapter_sha256": ADAPTER_SHA, "seed": scorer.SEED,
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
        for mode in MODES:
            server = server_factory(binary, model, adapter,
                                    out / ("SERVER_" + mode + "_RAW.log"), mode)
            for p in (p for p in prompts if p["arm"] == mode):
                remaining = OVERALL_SECONDS - (time.monotonic() - started)
                need(remaining > 10, "DEADLINE_RED")
                begun = time.monotonic()
                output, metrics = server.generate(
                    p["messages"], min(CALL_SECONDS - 2, remaining))
                records.append(candidate.record_call(
                    p, output, time.monotonic() - begun, metrics, ADAPTER_SHA))
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
            (adapter, ADAPTER_SHA, "ADAPTER"),
        ):
            candidate.admit_file(path, expected, label)
        snapshot = score(records, prompts, answers)
        atomic_write(out / "SCORE.json", canonical(snapshot).decode())
        receipt["status"] = "TRAINING_ONLY_NATIVE_SCHEMA_ABLATION_NO_GATE"
        receipt["process_reaped"] = True
        for name, key in (("INPUTS.json", "inputs_sha256"),
                          ("ANSWERS.json", "answers_sha256"),
                          ("RAW.json", "raw_sha256"),
                          ("SCORE.json", "score_sha256")):
            receipt[key] = base.resources.file_sha(out / name)
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
    need(snapshot == replay, "SCORE_REPLAY_RED")
    need(receipt.get("schema") == SCHEMA
         and receipt.get("status") == "TRAINING_ONLY_NATIVE_SCHEMA_ABLATION_NO_GATE"
         and receipt.get("recorded_calls") == EXPECTED
         and receipt.get("expected_calls") == EXPECTED
         and receipt.get("process_reaped") is True
         and receipt.get("fixture_sha256") == base.resources.FIXTURE_SHA
         and receipt.get("train_sha256") == base.resources.EXPORT_SHA["train.jsonl"]
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
         and receipt.get("calibration_rows_used") == 0
         and receipt.get("validation_rows_used") == 0,
         "RECEIPT_GATE_RED")
    for name, key in (("INPUTS.json", "inputs_sha256"),
                      ("ANSWERS.json", "answers_sha256"),
                      ("RAW.json", "raw_sha256"),
                      ("SCORE.json", "score_sha256")):
        need(receipt.get(key) == base.resources.file_sha(evidence / name),
             "RECEIPT_SHA_RED")
    return replay


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan-check", action="store_true")
    ap.add_argument("--verify", type=Path)
    for name in ("server-binary", "runtime-archive", "model", "adapter", "out"):
        ap.add_argument("--" + name)
    args = ap.parse_args(argv)
    if args.plan_check:
        p, a = plan()
        print(json.dumps({"status": "SOURCE_ONLY_NO_NATIVE",
                          "calls": len(p), "training_rows": len(a),
                          "step2_status": "UTILITY_FAIL"}, sort_keys=True))
        return 0
    if args.verify is not None:
        print(json.dumps(verify(args.verify), sort_keys=True))
        return 0
    for name in ("server_binary", "runtime_archive", "model", "adapter", "out"):
        if getattr(args, name) is None:
            ap.error("--" + name.replace("_", "-") + " required")
    receipt = run_native(args.server_binary, args.runtime_archive,
                         args.model, args.adapter, args.out)
    print(json.dumps({"status": receipt["status"],
                      "recorded_calls": receipt["recorded_calls"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

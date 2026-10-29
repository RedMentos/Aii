#!/usr/bin/env python3
"""Frozen C3 JSON-target LoRA scale0 vs scale1 on training16 only; no gate."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

from scripts import p2x_schema_toggle_train16 as parent
from scripts import p2x_candidate360_standalone as candidate
from scripts import p2x_native_receiver_eval_scorer as scorer
from v13.common import atomic_write

SCHEMA = "v13.p2x.scale01_train16.v1"
SCALES = (0, 1)
EXPECTED = 32
ADAPTER_SHA = parent.ADAPTER_SHA


def need(ok, reason):
    if not ok:
        raise ValueError("P2X_SCALE01_" + reason)


def plan():
    p, a = parent.plan()
    return ([{"id": x["id"], "arm": "scale" + str(scale),
              "messages": x["messages"]}
             for scale in SCALES for x in p[:16]], a)


class ScaleServer(candidate.LocalServer):
    """Pinned server flags copied from parent, only LoRA scale changes."""
    def __init__(self, binary, model, adapter, log, scale):
        need(type(scale) is int and scale in SCALES, "SCALE_RED")
        self.scale = scale
        self.proc = None
        self.log_file = None
        self.completion_request = None
        with candidate.socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        cmd = [str(binary), "-m", str(model), "--lora-scaled",
               str(adapter) + ":" + str(scale),
               "--host", "127.0.0.1", "--port", str(self.port),
               "-c", str(candidate.CONTEXT), "-np", "1", "-t", "2",
               "-tb", "2", "-b", "128", "-ub", "128",
               "-ngl", "0", "--cache-ram", "128", "--ctx-checkpoints", "6",
               "--no-warmup", "--no-webui", "--log-disable"]
        self.launch_argv = cmd
        self.log_file = Path(log).open("ab")
        try:
            self.proc = candidate.subprocess.Popen(
                cmd, stdin=candidate.subprocess.DEVNULL,
                stdout=self.log_file, stderr=self.log_file)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if self.proc.poll() is not None:
                    raise ValueError("P2X_SCALE01_SERVER_EXIT_RED")
                try:
                    if self.request("GET", "/health", timeout=2).get("status") == "ok":
                        return
                except (OSError, ValueError, candidate.http.client.HTTPException):
                    pass
                time.sleep(.2)
            raise TimeoutError("P2X_SCALE01_SERVER_START_TIMEOUT_RED")
        except BaseException:
            self.close()
            raise

    def request(self, method, path, data=None, timeout=candidate.CALL_SECONDS):
        if method == "POST" and path == "/completion":
            parent._check_request(data, "on")
            self.completion_request = dict(data)
        return super().request(method, path, data, timeout)

    def generate(self, messages, timeout):
        self.completion_request = None
        output, metrics = super().generate(messages, timeout)
        need(type(self.completion_request) is dict, "REQUEST_MISSING_RED")
        return output, dict(metrics, lora_scale=self.scale,
                            launch_argv=list(self.launch_argv),
                            completion_request=self.completion_request)


def normalized_argv(argv, scale):
    need(type(argv) is list and all(type(x) is str for x in argv)
         and len(argv) >= 8
         and argv.count("--lora-scaled") == 1
         and argv.count("--port") == 1,
         "ARGV_RED")
    cmd = list(argv)
    pos = cmd.index("--lora-scaled")
    need(pos + 1 < len(cmd) and cmd[pos+1].endswith(":" + str(scale))
         and cmd[pos+1][:-2] and ":" not in cmd[pos+1][:-2],
         "SCALE_ARG_RED")
    cmd[pos+1] = cmd[pos+1][:-1] + "*"
    port = cmd.index("--port")
    need(port + 1 < len(cmd) and cmd[port+1].isdigit()
         and 0 < int(cmd[port+1]) <= 65535,
         "PORT_RED")
    cmd[port+1] = "<ephemeral>"
    return cmd


def score(records, prompts, answers):
    expected_prompts, expected_answers = plan()
    need(prompts == expected_prompts and answers == expected_answers,
         "FROZEN_PLAN_RED")
    need(type(records) is list and len(records) == EXPECTED,
         "COVERAGE_RED")
    oracle = {a["id"]: a["target_action"] for a in answers}
    counts = {s: {label: {"correct": 0, "wrong": 0, "unparseable": 0}
                  for label in parent.base.resources.LABELS} for s in SCALES}
    outputs = {s: {} for s in SCALES}
    requests = {s: {} for s in SCALES}
    commands = {s: {} for s in SCALES}
    for rec, p in zip(records, prompts):
        scale = int(p["arm"][-1])
        need(type(rec) is dict and set(rec) ==
             {"id", "arm", "input_sha256", "model_sha256", "runtime_sha256",
              "adapter_sha256", "seed", "status", "model_called", "native_calls",
              "duration_s", "output", "metrics"}, "RAW_SHAPE_RED")
        m = rec["metrics"];duration = rec["duration_s"]
        need((rec["id"], rec["arm"]) == (p["id"], p["arm"])
             and rec["input_sha256"] == scorer.sha(scorer.canonical(p["messages"]))
             and rec["model_sha256"] == scorer.MODEL_SHA
             and rec["runtime_sha256"] == scorer.RUNTIME_SHA
             and rec["adapter_sha256"] == ADAPTER_SHA
             and type(rec["seed"]) is int and rec["seed"] == scorer.SEED
             and rec["status"] == "FINAL" and rec["model_called"] is True
             and type(rec["native_calls"]) is int and rec["native_calls"] == 1
             and type(duration) in (int, float) and math.isfinite(duration)
             and 0 <= duration <= candidate.CALL_SECONDS
             and type(rec["output"]) is str and type(m) is dict
             and m.get("status") == "FINAL"
             and type(m.get("lora_scale")) is int and m["lora_scale"] == scale,
             "RAW_BINDING_RED")
        req = m.get("completion_request")
        parent._check_request(req, "on")
        requests[scale][p["id"]] = req
        commands[scale][p["id"]] = normalized_argv(m.get("launch_argv"), scale)
        parsed = scorer.strict_action(rec["output"])
        label = oracle[p["id"]]
        kind = ("correct" if parsed == label else
                "unparseable" if parsed not in parent.base.resources.LABELS else "wrong")
        counts[scale][label][kind] += 1
        outputs[scale][p["id"]] = parsed
    need(requests[0] == requests[1], "REQUEST_DIFF_RED")
    need(commands[0] == commands[1], "NON_SCALE_ARGV_DIFF_RED")
    need(all(sum(sum(x.values()) for x in counts[s].values()) == 16
             for s in SCALES), "LABEL_COUNT_RED")
    return {"schema": SCHEMA + ".score.v1",
            "status": "TRAINING_ONLY_LORA_SCALE_ABLATION_NO_GATE",
            "fixture_sha256": parent.base.resources.FIXTURE_SHA,
            "train_sha256": parent.base.resources.EXPORT_SHA["train.jsonl"],
            "model_sha256": scorer.MODEL_SHA,
            "runtime_sha256": scorer.RUNTIME_SHA,
            "adapter_sha256": ADAPTER_SHA,
            "runner_binary_sha256": candidate.BINARY_SHA,
            "seed": scorer.SEED, "training_examples": 16,
            "native_calls": EXPECTED,
            "per_label": {str(s): counts[s] for s in SCALES},
            "correct_strict_in_sample": {str(s): sum(v["correct"] for v in counts[s].values())
                                         for s in SCALES},
            "paired_action_changes": sum(
                outputs[0][a["id"]] != outputs[1][a["id"]] for a in answers),
            "train_only": True, "calibration_rows_used": 0,
            "validation_rows_used": 0, "step2_status": "UTILITY_FAIL",
            "b3_status": "FAIL", "body_jepa_status": "UNAVAILABLE",
            "jepa_weight": 0, "ag6_approved": False,
            "redmi_measured": False, "whole_system_complete": False}


def preflight(server_binary, runtime_archive, model, adapter, out):
    binary, model, adapter, _, answers, resources = parent.preflight(
        server_binary, runtime_archive, model, adapter, out)
    prompts, fixed_answers = plan()
    need(answers == fixed_answers, "PARENT_ANSWERS_RED")
    return binary, model, adapter, prompts, answers, resources


def run_native(server_binary, runtime_archive, model, adapter, out,
               server_factory=ScaleServer):
    binary, model, adapter, prompts, answers, admission = preflight(
        server_binary, runtime_archive, model, adapter, out)
    out = Path(out)
    out.mkdir(mode=0o700)
    receipt = {"schema": SCHEMA, "status": "RUNNING",
               "evidence_kind": "LINUX_NATIVE_TRAINING_ONLY_LORA_SCALE_ABLATION",
               "fixture_sha256": parent.base.resources.FIXTURE_SHA,
               "train_sha256": parent.base.resources.EXPORT_SHA["train.jsonl"],
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
        atomic_write(out / "RAW.json", scorer.canonical(records).decode())
        atomic_write(out / "RECEIPT.json", scorer.canonical(receipt).decode())

    atomic_write(out / "INPUTS.json", scorer.canonical(prompts).decode())
    atomic_write(out / "ANSWERS.json", scorer.canonical(answers).decode())
    persist()
    server = None
    started = time.monotonic()
    try:
        for scale in SCALES:
            server = server_factory(binary, model, adapter,
                                    out / ("SERVER_SCALE" + str(scale) + "_RAW.log"), scale)
            for p in (p for p in prompts if p["arm"] == "scale" + str(scale)):
                remaining = parent.OVERALL_SECONDS - (time.monotonic() - started)
                need(remaining > 10, "DEADLINE_RED")
                begun = time.monotonic()
                output, metrics = server.generate(
                    p["messages"], min(candidate.CALL_SECONDS - 2, remaining))
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
        atomic_write(out / "SCORE.json", scorer.canonical(snapshot).decode())
        receipt["status"] = "TRAINING_ONLY_NATIVE_LORA_SCALE_ABLATION_NO_GATE"
        receipt["process_reaped"] = True
        for name, key in (("INPUTS.json", "inputs_sha256"),
                          ("ANSWERS.json", "answers_sha256"),
                          ("RAW.json", "raw_sha256"),
                          ("SCORE.json", "score_sha256")):
            receipt[key] = parent.base.resources.file_sha(out / name)
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
    names = ("INPUTS.json", "ANSWERS.json", "RAW.json", "SCORE.json", "RECEIPT.json")
    need(all((evidence / n).is_file() and not (evidence / n).is_symlink()
             for n in names), "EVIDENCE_FILES_RED")
    p, a, rows, saved, receipt = [
        json.loads((evidence / n).read_bytes()) for n in names]
    replay = score(rows, p, a)
    need(saved == replay, "SCORE_REPLAY_RED")
    need(receipt.get("schema") == SCHEMA
         and receipt.get("status") == "TRAINING_ONLY_NATIVE_LORA_SCALE_ABLATION_NO_GATE"
         and type(receipt.get("recorded_calls")) is int
         and receipt["recorded_calls"] == EXPECTED
         and receipt.get("expected_calls") == EXPECTED
         and receipt.get("process_reaped") is True
         and receipt.get("fixture_sha256") == parent.base.resources.FIXTURE_SHA
         and receipt.get("train_sha256") == parent.base.resources.EXPORT_SHA["train.jsonl"]
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
        need(receipt.get(key) == parent.base.resources.file_sha(evidence / name),
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

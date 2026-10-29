#!/usr/bin/env python3
"""Pinned C3 LoRA scale0/1 first-action-token top40 logprobs, training16 only."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import time

from scripts import p2x_scale01_train16 as scale
from scripts import p2x_candidate360_standalone as candidate
from scripts import p2x_native_receiver_eval_scorer as scorer
from v13.common import atomic_write

SCHEMA = "v13.p2x.firsttoken_logprob_train16.v1"
PREFIX = '{"action":"'
N_PROBS = 40
EXPECTED = 32
SCALES = scale.SCALES
ADAPTER_SHA = scale.ADAPTER_SHA


def need(ok, reason):
    if not ok:
        raise ValueError("P2X_FIRSTTOKEN_" + reason)


def plan():
    return scale.plan()


class ProbServer(scale.ScaleServer):
    """Pinned scale-specific server, but one token of raw pre-sampling logits."""
    def request(self, method, path, data=None, timeout=candidate.CALL_SECONDS):
        if method == "POST" and path == "/completion":
            self.prob_request = dict(data)
        return candidate.LocalServer.request(self, method, path, data, timeout)

    def generate(self, messages, timeout):
        self.prob_request = None
        rendered = self.request("POST", "/apply-template",
                                {"messages": messages, "add_generation_prompt": True,
                                 "chat_template_kwargs": {"enable_thinking": False}},
                                timeout=timeout)["prompt"]
        need(type(rendered) is str and rendered, "TEMPLATE_RED")
        full = rendered + PREFIX
        tokens = self.request("POST", "/tokenize",
                              {"content": full, "add_special": True},
                              timeout=timeout)["tokens"]
        need(type(tokens) is list and len(tokens) + 16 <= candidate.CONTEXT,
             "CONTEXT_RED")
        req = {"prompt": full, "n_predict": 1, "n_probs": N_PROBS,
               "post_sampling_probs": False, "stream": False,
               "temperature": 0, "top_k": 50, "repeat_penalty": 1.05,
               "seed": scorer.SEED, "cache_prompt": False,
               "id_slot": 0, "return_tokens": True}
        response = self.request("POST", "/completion", req, timeout=timeout)
        need(type(response) is dict and self.prob_request == req,
             "RESPONSE_RED")
        return scorer.canonical(response).decode(), {
            "status": "FINAL", "lora_scale": self.scale,
            "prompt_tokens": len(tokens), "prob_request": req,
            "launch_argv": list(self.launch_argv)}


def _prob_request(req):
    need(type(req) is dict and set(req) ==
         {"prompt", "n_predict", "n_probs", "post_sampling_probs",
          "stream", "temperature", "top_k", "repeat_penalty",
          "seed", "cache_prompt", "id_slot", "return_tokens"}
         and type(req["prompt"]) is str and req["prompt"].endswith(PREFIX)
         and req["n_predict"] == 1 and req["n_probs"] == N_PROBS
         and req["post_sampling_probs"] is False
         and req["stream"] is False and req["temperature"] == 0
         and req["top_k"] == 50 and req["repeat_penalty"] == 1.05
         and req["seed"] == scorer.SEED
         and req["cache_prompt"] is False and req["id_slot"] == 0
         and req["return_tokens"] is True,
         "PROB_REQUEST_RED")


def _topk(raw):
    need(type(raw) is dict and type(raw.get("completion_probabilities")) is list
         and len(raw["completion_probabilities"]) == 1,
         "PROB_SHAPE_RED")
    row = raw["completion_probabilities"][0]
    need(type(row) is dict and type(row.get("top_logprobs")) is list
         and 1 <= len(row["top_logprobs"]) <= N_PROBS,
         "TOPK_SHAPE_RED")
    found = {}
    for item in row["top_logprobs"]:
        need(type(item) is dict and type(item.get("id")) is int
             and item["id"] >= 0
             and type(item.get("logprob")) in (int, float)
             and math.isfinite(item["logprob"])
             and item["logprob"] <= 1e-6
             and item["id"] not in found,
             "TOPK_ENTRY_RED")
        found[item["id"]] = float(item["logprob"])
    return found


def score(records, prompts, answers):
    fixed_prompts, fixed_answers = plan()
    need(prompts == fixed_prompts and answers == fixed_answers,
         "FROZEN_PLAN_RED")
    need(type(records) is list and len(records) == EXPECTED,
         "COVERAGE_RED")
    requests = {s: {} for s in SCALES}
    commands = {s: {} for s in SCALES}
    probs = {s: {} for s in SCALES}
    for rec, p in zip(records, prompts):
        s = int(p["arm"][-1]);m = rec.get("metrics") if type(rec) is dict else None
        need(type(rec) is dict and set(rec) ==
             {"id", "arm", "input_sha256", "model_sha256", "runtime_sha256",
              "adapter_sha256", "seed", "status", "model_called", "native_calls",
              "duration_s", "output", "metrics"}, "RAW_SHAPE_RED")
        duration = rec["duration_s"]
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
             and type(m.get("lora_scale")) is int and m["lora_scale"] == s,
             "RAW_BINDING_RED")
        req = m.get("prob_request")
        _prob_request(req)
        requests[s][p["id"]] = req
        commands[s][p["id"]] = scale.normalized_argv(m.get("launch_argv"), s)
        try:
            response = json.loads(rec["output"])
        except (ValueError, TypeError) as exc:
            raise ValueError("P2X_FIRSTTOKEN_RESPONSE_JSON_RED") from exc
        probs[s][p["id"]] = _topk(response)
    need(requests[0] == requests[1], "REQUEST_PAIR_RED")
    need(commands[0] == commands[1], "LAUNCH_PAIR_RED")
    rows = []
    for a in answers:
        i = a["id"];left,right=probs[0][i],probs[1][i]
        common = sorted(set(left) & set(right))
        max_delta = max((abs(left[k]-right[k]) for k in common), default=None)
        rows.append({"id_sha256": scorer.sha(i.encode()),
                     "expected": a["target_action"],
                     "top1_scale0": max(left,key=left.get),
                     "top1_scale1": max(right,key=right.get),
                     "shared_topk": len(common),
                     "max_shared_logprob_abs_delta": round(max_delta,8) if max_delta is not None else None})
    return {"schema": SCHEMA + ".score.v1",
            "status": "TRAINING_ONLY_FIRSTTOKEN_LOGPROB_NO_GATE",
            "fixture_sha256": scale.parent.base.resources.FIXTURE_SHA,
            "train_sha256": scale.parent.base.resources.EXPORT_SHA["train.jsonl"],
            "model_sha256": scorer.MODEL_SHA, "runtime_sha256": scorer.RUNTIME_SHA,
            "adapter_sha256": ADAPTER_SHA,
            "runner_binary_sha256": candidate.BINARY_SHA,
            "seed": scorer.SEED, "training_examples": 16,
            "native_calls": EXPECTED, "n_probs": N_PROBS,
            "prefix_sha256": scorer.sha(PREFIX.encode()),
            "top1_token_changes": sum(r["top1_scale0"] != r["top1_scale1"] for r in rows),
            "shared_topk_changed_above_1e_6": sum(
                r["max_shared_logprob_abs_delta"] is not None
                and r["max_shared_logprob_abs_delta"] > 1e-6 for r in rows),
            "rows": rows, "train_only": True,
            "calibration_rows_used": 0, "validation_rows_used": 0,
            "step2_status": "UTILITY_FAIL", "b3_status": "FAIL",
            "body_jepa_status": "UNAVAILABLE", "jepa_weight": 0,
            "ag6_approved": False, "redmi_measured": False,
            "whole_system_complete": False}


def preflight(server_binary, runtime_archive, model, adapter, out):
    return scale.preflight(server_binary, runtime_archive, model, adapter, out)


def run_native(server_binary, runtime_archive, model, adapter, out,
               server_factory=ProbServer):
    binary, model, adapter, prompts, answers, admission = preflight(
        server_binary, runtime_archive, model, adapter, out)
    out = Path(out)
    out.mkdir(mode=0o700)
    receipt = {"schema": SCHEMA, "status": "RUNNING",
               "evidence_kind": "LINUX_NATIVE_TRAINING_ONLY_FIRSTTOKEN_PROB",
               "fixture_sha256": scale.parent.base.resources.FIXTURE_SHA,
               "train_sha256": scale.parent.base.resources.EXPORT_SHA["train.jsonl"],
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
        for s in SCALES:
            server = server_factory(binary, model, adapter,
                                    out / ("SERVER_SCALE" + str(s) + "_RAW.log"), s)
            for p in (p for p in prompts if p["arm"] == "scale" + str(s)):
                remaining = scale.parent.OVERALL_SECONDS - (time.monotonic() - started)
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
        receipt["status"] = "TRAINING_ONLY_NATIVE_FIRSTTOKEN_PROB_NO_GATE"
        receipt["process_reaped"] = True
        for name, key in (("INPUTS.json", "inputs_sha256"),
                          ("ANSWERS.json", "answers_sha256"),
                          ("RAW.json", "raw_sha256"),
                          ("SCORE.json", "score_sha256")):
            receipt[key] = scale.parent.base.resources.file_sha(out / name)
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
         and receipt.get("status") == "TRAINING_ONLY_NATIVE_FIRSTTOKEN_PROB_NO_GATE"
         and type(receipt.get("recorded_calls")) is int
         and receipt["recorded_calls"] == EXPECTED
         and receipt.get("expected_calls") == EXPECTED
         and receipt.get("process_reaped") is True
         and receipt.get("fixture_sha256") == scale.parent.base.resources.FIXTURE_SHA
         and receipt.get("train_sha256") == scale.parent.base.resources.EXPORT_SHA["train.jsonl"]
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
        need(receipt.get(key) == scale.parent.base.resources.file_sha(evidence / name),
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

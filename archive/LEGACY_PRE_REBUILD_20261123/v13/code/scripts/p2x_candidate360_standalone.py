#!/usr/bin/env python3
"""Isolated P2X QAD GGUF + LoRA 360-call native diagnostic; no production activation."""
from __future__ import annotations

import argparse
import http.client
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import threading
import time

from scripts import hb1a_two_body_native_pilot as hb1
from scripts import hb1b_c3_format_native_executor as native
from scripts import p2x_base360_native_verifier as base_verify
from scripts import p2x_c3_lora_pilot as P
from scripts import p2x_native_receiver_eval_scorer as scorer
from v13.common import atomic_write

SCHEMA = "v13.p2x.candidate360_standalone.v1"
MAX_TOKENS = 48
CALL_SECONDS = 90
OVERALL_SECONDS = 2400
CONTEXT = 2048
BINARY_SHA = hb1.RUNNER_SHA256 if hasattr(hb1, "RUNNER_SHA256") else native.hb1b.RUNNER_SHA256


def need(ok, reason):
    if not ok:
        raise ValueError("P2X_CAND360_" + reason)


def admit_file(path, expected, label):
    p = Path(path)
    need(p.is_file() and not p.is_symlink(), label + "_FILE_RED")
    need(P.file_sha(p) == expected, label + "_SHA_RED")
    return p.resolve(strict=True)


def preflight(server_binary, runtime_archive, model, adapter, adapter_sha, validation_dir, base_evidence, out):
    need(type(adapter_sha) is str and len(adapter_sha) == 64
         and all(c in "0123456789abcdef" for c in adapter_sha), "ADAPTER_HASH_RED")
    out = Path(out)
    need(not out.exists() and not out.is_symlink() and out.parent.is_dir(),
         "FRESH_OUTPUT_RED")
    binary = admit_file(server_binary, BINARY_SHA, "BINARY")
    archive = admit_file(runtime_archive, scorer.RUNTIME_SHA, "ARCHIVE")
    model = admit_file(model, scorer.MODEL_SHA, "MODEL")
    adapter = admit_file(adapter, adapter_sha, "ADAPTER")
    need(len({str(binary), str(archive), str(model), str(adapter)}) == 4,
         "DISTINCT_PINNED_ASSETS_RED")
    plan, answers = scorer.load_validation(validation_dir)
    verified_base = base_verify.verify(base_evidence, validation_dir)
    need(verified_base["status"] == "VERIFIED_BASE_ONLY_LINUX_NATIVE_NO_GATE",
         "BASE_EVIDENCE_RED")
    base_score = json.loads((Path(base_evidence) / "SCORE.json").read_bytes())
    scorer._validate_score_snapshot(base_score)
    # This is a disposable, isolated diagnostic, not a Runtime Store or approved adapter mirror.
    resources = P.resource_admission(out.parent)
    return binary, model, adapter, plan, answers, base_score, resources


class LocalServer:
    """One owned loopback-only pinned server; direct adapter is never registered with V13."""
    def __init__(self, binary, model, adapter, log):
        self.proc = None
        self.log_file = None
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        cmd = [str(binary), "-m", str(model), "--lora-scaled", str(adapter) + ":1",
               "--host", "127.0.0.1", "--port", str(self.port), "-c", str(CONTEXT),
               "-np", "1", "-t", "2", "-tb", "2", "-b", "128", "-ub", "128",
               "-ngl", "0", "--cache-ram", "128", "--ctx-checkpoints", "6",
               "--no-warmup", "--no-webui", "--log-disable"]
        self.log_file = Path(log).open("ab")
        try:
            self.proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                                         stdout=self.log_file, stderr=self.log_file)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if self.proc.poll() is not None:
                    raise ValueError("P2X_CAND360_SERVER_EXIT_RED")
                try:
                    if self.request("GET", "/health", timeout=2).get("status") == "ok":
                        return
                except (OSError, ValueError, http.client.HTTPException):
                    pass
                time.sleep(.2)
            raise TimeoutError("P2X_CAND360_SERVER_START_TIMEOUT_RED")
        except BaseException:
            self.close()
            raise

    def request(self, method, path, data=None, timeout=CALL_SECONDS):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        try:
            conn.request(method, path,
                         json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
                         if data is not None else None,
                         {"Content-Type": "application/json"})
            response = conn.getresponse()
            raw = response.read()
            if response.status != 200:
                raise ValueError("P2X_CAND360_HTTP_STATUS_RED:" + str(response.status))
            return json.loads(raw)
        finally:
            conn.close()

    def generate(self, messages, timeout):
        need(type(messages) is list and len(messages) == 1
             and messages[0].get("role") == "user"
             and type(messages[0].get("content")) is str, "INPUT_RED")
        prompt = self.request("POST", "/apply-template",
                              {"messages": messages, "add_generation_prompt": True,
                               "chat_template_kwargs": {"enable_thinking": False}},
                              timeout=timeout)["prompt"]
        tokens = self.request("POST", "/tokenize",
                              {"content": prompt, "add_special": True},
                              timeout=timeout)["tokens"]
        need(type(tokens) is list and len(tokens) + MAX_TOKENS + 16 <= CONTEXT,
             "CONTEXT_RED")
        result = self.request("POST", "/completion",
                              {"prompt": prompt, "n_predict": MAX_TOKENS,
                               "stream": False, "temperature": .1, "top_k": 50,
                               "repeat_penalty": 1.05, "seed": scorer.SEED,
                               "cache_prompt": True, "id_slot": 0,
                               "return_tokens": True, "json_schema": hb1.C3_SCHEMA},
                              timeout=timeout)
        need(type(result) is dict and type(result.get("content")) is str,
             "NATIVE_OUTPUT_RED")
        return result["content"], {"status": "FINAL", "transport": "nonstreaming",
                                   "prompt_tokens": len(tokens)}

    def close(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        if self.log_file is not None:
            self.log_file.close()
            self.log_file = None


def record_call(prompt, output, duration, metrics, adapter_sha):
    need(type(prompt) is dict and set(prompt) == {"id", "arm", "messages"}
         and type(output) is str
         and type(duration) in (int, float) and math.isfinite(duration)
         and 0 <= duration <= CALL_SECONDS
         and type(metrics) is dict and metrics.get("status") == "FINAL",
         "NONFINAL_CALL_RED")
    return {"id": prompt["id"], "arm": prompt["arm"],
            "input_sha256": scorer.sha(scorer.canonical(prompt["messages"])),
            "model_sha256": scorer.MODEL_SHA, "runtime_sha256": scorer.RUNTIME_SHA,
            "adapter_sha256": adapter_sha, "seed": scorer.SEED,
            "status": "FINAL", "model_called": True, "native_calls": 1,
            "duration_s": duration, "output": output, "metrics": metrics}


def run_native(server_binary, runtime_archive, model, adapter, adapter_sha,
               validation_dir, base_evidence, out, server_factory=LocalServer):
    (binary, model, adapter, plan, answers, base_score, resources) = preflight(
        server_binary, runtime_archive, model, adapter, adapter_sha,
        validation_dir, base_evidence, out)
    out = Path(out)
    out.mkdir(mode=0o700)
    receipt = {"schema": SCHEMA, "status": "RUNNING",
               "evidence_kind": "LINUX_NATIVE_ISOLATED_ADAPTER_CANDIDATE_ONLY",
               "fixture_sha256": scorer.FIXTURE_SHA,
               "model_sha256": scorer.MODEL_SHA, "runtime_sha256": scorer.RUNTIME_SHA,
               "runner_binary_sha256": BINARY_SHA, "adapter_sha256": adapter_sha,
               "seed": scorer.SEED, "expected_calls": 360, "recorded_calls": 0,
               "transport": "NONSTREAMING_VS_STREAMING_BASELINE",
               "age_authority": 0, "weight_updates": False,
               "ag6_approved": False, "production_activation": False,
               "jepa_weight": 0, "redmi_measured": False,
               "canonical_gate_pass": False, "whole_system_complete": False,
               "resources": resources}
    records = []
    def persist():
        atomic_write(out / "RAW.json", scorer.canonical(records).decode("utf-8"))
        atomic_write(out / "RECEIPT.json", scorer.canonical(receipt).decode("utf-8"))
    atomic_write(out / "INPUTS.json", scorer.canonical(plan).decode("utf-8"))
    atomic_write(out / "ANSWERS.json", scorer.canonical(answers).decode("utf-8"))
    persist()
    server = None
    started = time.monotonic()
    try:
        server = server_factory(binary, model, adapter, out / "SERVER_RAW.log")
        for prompt in plan:
            remaining = OVERALL_SECONDS - (time.monotonic() - started)
            need(remaining > 10, "OVERALL_DEADLINE_RED")
            begun = time.monotonic()
            output, metrics = server.generate(prompt["messages"],
                                              min(CALL_SECONDS - 2, remaining))
            records.append(record_call(prompt, output, time.monotonic() - begun,
                                       metrics, adapter_sha))
            receipt["recorded_calls"] = len(records)
            persist()
        server.close()
        server = None
        for path, expected, label in ((server_binary, BINARY_SHA, "BINARY"),
                                      (runtime_archive, scorer.RUNTIME_SHA, "ARCHIVE"),
                                      (model, scorer.MODEL_SHA, "MODEL"),
                                      (adapter, adapter_sha, "ADAPTER")):
            admit_file(path, expected, label)
        score = scorer.score(records, plan, answers, adapter_sha256=adapter_sha)
        paired = scorer.compare(base_score, score)
        atomic_write(out / "SCORE.json", scorer.canonical(score).decode("utf-8"))
        atomic_write(out / "PAIRED.json", scorer.canonical(paired).decode("utf-8"))
        receipt["status"] = "P2X_CANDIDATE360_NATIVE_DIAGNOSTIC_NO_GATE"
        receipt["recorded_calls"] = 360
        receipt["process_reaped"] = True
        for name, key in (("RAW.json", "raw_sha256"),
                          ("SCORE.json", "score_sha256"),
                          ("PAIRED.json", "paired_sha256"),
                          ("INPUTS.json", "inputs_sha256"),
                          ("ANSWERS.json", "answers_sha256")):
            receipt[key] = P.file_sha(out / name)
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ("server-binary", "runtime-archive", "model", "adapter",
                 "adapter-sha256", "validation-dir", "base-evidence", "out"):
        ap.add_argument("--" + name, required=True)
    args = ap.parse_args(argv)
    result = run_native(args.server_binary, args.runtime_archive,
                        args.model, args.adapter, args.adapter_sha256,
                        args.validation_dir, args.base_evidence, args.out)
    print(json.dumps({"status": result["status"],
                      "recorded_calls": result["recorded_calls"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

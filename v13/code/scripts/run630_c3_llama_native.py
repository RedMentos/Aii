#!/usr/bin/env python3
"""Run630: pinned Linux llama.cpp native C3 LoRA scale ablation (not production)."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

MASTER_SHA = "5af571cbf074e6d21a03528d2330792e532ca608f24ac70a143f6b369968ab8c"
ADAPTER_SHA = "e2f84ae657b0b90891d7c5c042a897b9bd30021f8a16e399a27fa2704b793f4b"
COHORT_SHA = "3c7316b892b26c22d389da09af5f186ad8b596a7a45b53f49b3f5ec0e4028973"
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL",
         "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0, "V13": "INCOMPLETE"}
PROMPTS = (
    "In the fictional Larch protocol, what is the marker color?",
    "In the fictional Larch protocol, what is the gate number?",
    "What is two plus two?",
    "Write a brief greeting.",
)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def gguf_header(path, expected_adapter=False):
    with Path(path).open("rb") as f:
        h = f.read(24)
    if len(h) != 24 or h[:4] != b"GGUF":
        raise ValueError("invalid GGUF magic/header")
    version, tensors, metadata = struct.unpack("<IQQ", h[4:])
    if version != 3 or tensors < 1 or tensors > 100000 or metadata > 100000:
        raise ValueError("invalid GGUF version/tensor/metadata count")
    if expected_adapter and tensors != 120:
        raise ValueError("Run629 adapter tensor count drift")
    return {"version": version, "tensors": tensors, "metadata": metadata}


def verify_inputs(master_dir, model_gguf, adapter, source_proof, server, cohort):
    master_dir = Path(master_dir)
    if sha256(master_dir / "model.safetensors") != MASTER_SHA:
        raise ValueError("master SHA mismatch")
    if sha256(cohort) != COHORT_SHA:
        raise ValueError("frozen cohort SHA mismatch")
    if sha256(adapter) != ADAPTER_SHA:
        raise ValueError("adapter SHA mismatch")
    model_info = gguf_header(model_gguf)
    adapter_info = gguf_header(adapter, expected_adapter=True)
    p = json.loads(Path(source_proof).read_text())
    if p.get("schema") != "V13_RUN628_C3_LORA_CPU_PROOF_V1" or p.get("evidence_scope") != "LINUX_NATIVE_C3_MASTER_LORA_CPU_EXPERIMENT":
        raise ValueError("untrusted source proof scope")
    if p.get("gates") != GATES or p.get("production_weight_authority") != 0 or p.get("body_jepa_proven") is not False:
        raise ValueError("source proof negative gates changed")
    if p.get("master", {}).get("sha256") != MASTER_SHA or p.get("cohort_sha256") != COHORT_SHA:
        raise ValueError("source proof model/cohort mismatch")
    if p.get("adapter_gguf_sha256") != ADAPTER_SHA or p.get("adapter_nonzero_lora_b_elements") != 46080:
        raise ValueError("source proof adapter mismatch")
    if p.get("metrics", {}).get("steps") != 2 or p.get("metrics", {}).get("jepa_weight") != 0:
        raise ValueError("source proof training scope changed")
    if p.get("metrics", {}).get("master_learned_recall") != 0.0:
        raise ValueError("source proof frozen zero-recall result changed")
    s = Path(server)
    if not s.is_absolute() or not s.is_file() or not os.access(s, os.X_OK) or s.name != "llama-server":
        raise ValueError("native server must be a reviewed absolute executable")
    return {"master_sha256": MASTER_SHA, "adapter_sha256": ADAPTER_SHA,
            "cohort_sha256": COHORT_SHA, "model_gguf_sha256": sha256(model_gguf),
            "model_gguf_bytes": Path(model_gguf).stat().st_size,
            "model_gguf_header": model_info, "adapter_gguf_header": adapter_info,
            "server_sha256": sha256(s)}


def _port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _json(url, payload=None, timeout=12):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, headers={"Content-Type": "application/json"} if body is not None else {})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(1 << 20).decode("utf-8"))


def _start(server, model, adapter, logfile):
    port = _port()
    args = [str(server), "--model", str(model), "--host", "127.0.0.1",
            "--port", str(port), "--ctx-size", "512", "--threads", "2"]
    if adapter is not None:
        args += ["--lora", str(adapter)]
    handle = open(logfile, "wb")
    try:
        proc = subprocess.Popen(args, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
    finally:
        handle.close()
    base = "http://127.0.0.1:%d" % port
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise RuntimeError("native server exited before readiness: %d" % proc.returncode)
            try:
                health = _json(base + "/health", timeout=2)
                if health.get("status") in ("ok", "ready"):
                    return proc, base
            except (HTTPError, URLError, TimeoutError, ValueError):
                pass
            time.sleep(0.3)
        raise TimeoutError("native server readiness exceeded 90s")
    except BaseException:
        _stop(proc)
        raise


def _stop(proc):
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=5)


def _sample(base, prompt, scale=None):
    payload = {"prompt": prompt, "n_predict": 1, "temperature": 0,
               "seed": 13, "n_probs": 64, "cache_prompt": False, "stream": False}
    if scale is not None:
        payload["lora"] = [{"id": 0, "scale": float(scale)}]
    out = _json(base + "/completion", payload, timeout=40)
    probs = out.get("completion_probabilities") or []
    if not probs or not isinstance(probs[0].get("top_logprobs"), list):
        raise RuntimeError("native completion probabilities unavailable")
    values = {}
    for item in probs[0]["top_logprobs"]:
        ident, logp = item.get("id"), item.get("logprob")
        if not isinstance(ident, int) or not isinstance(logp, (int, float)) or not math.isfinite(logp):
            raise RuntimeError("nonfinite/invalid native logprob")
        values[ident] = float(logp)
    if not values:
        raise RuntimeError("empty native top logprobs")
    return {"token_id": probs[0].get("id"), "text": out.get("content", "")[:100],
            "logprobs": values}


def _compare(a, b):
    keys = set(a["logprobs"]) & set(b["logprobs"])
    if not keys:
        return {"shared_topk": 0, "max_abs_logprob_delta": None,
                "same_first_token": a["token_id"] == b["token_id"]}
    delta = max(abs(a["logprobs"][k] - b["logprobs"][k]) for k in keys)
    return {"shared_topk": len(keys), "max_abs_logprob_delta": delta,
            "same_first_token": a["token_id"] == b["token_id"]}


def run(master_dir, model, adapter, proof, cohort, server, output):
    binding = verify_inputs(master_dir, model, adapter, proof, server, cohort)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    for label, lora in (("base", None), ("adapter", Path(adapter))):
        proc = None
        try:
            proc, base = _start(Path(server), Path(model), lora, output / ("RUN630_%s_SERVER_RAW.log" % label.upper()))
            for prompt in PROMPTS:
                if label == "base":
                    results.setdefault(prompt, {})["base"] = _sample(base, prompt)
                else:
                    results[prompt]["scale0"] = _sample(base, prompt, 0)
                    results[prompt]["scale1"] = _sample(base, prompt, 1)
        finally:
            if proc is not None:
                _stop(proc)
    rows = []
    for prompt in PROMPTS:
        x = results[prompt]
        parity = _compare(x["base"], x["scale0"])
        effect = _compare(x["scale0"], x["scale1"])
        rows.append({"prompt": prompt, "base_first_token": x["base"]["token_id"],
                     "scale0_first_token": x["scale0"]["token_id"],
                     "scale1_first_token": x["scale1"]["token_id"],
                     "base_text": x["base"]["text"], "scale0_text": x["scale0"]["text"],
                     "scale1_text": x["scale1"]["text"], "base_vs_scale0": parity,
                     "scale0_vs_scale1": effect})
    parity_ok = all(x["base_vs_scale0"]["same_first_token"] and
                    x["base_vs_scale0"]["shared_topk"] >= 1 and
                    x["base_vs_scale0"]["max_abs_logprob_delta"] <= 1e-4 for x in rows)
    changed = any((not x["scale0_vs_scale1"]["same_first_token"]) or
                  (x["scale0_vs_scale1"]["max_abs_logprob_delta"] is not None and
                   x["scale0_vs_scale1"]["max_abs_logprob_delta"] > 1e-7) for x in rows)
    status = "NATIVE_C3_ADAPTER_EFFECT_OBSERVED" if parity_ok and changed else (
        "NATIVE_NO_LOGPROB_GAIN" if parity_ok else "NATIVE_PARITY_UNVERIFIED")
    result = {"schema": "V13_RUN630_LLAMA_C3_NATIVE_V1", "evidence_scope": "LINUX_NATIVE_C3_REFERENCE_F16",
              "status": status, "binding": binding, "rows": rows,
              "scale0_base_parity": parity_ok, "nonzero_native_effect": changed,
              "deployed_current_c3_q4": False, "answer_level_utility_proven": False,
              "redmi_measured": False, "production_weight_authority": 0,
              "body_jepa_proven": False, "negative_gates": GATES}
    (output / "RUN630_NATIVE_PROOF.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": status, "scale0_base_parity": parity_ok,
                      "nonzero_native_effect": changed, "rows": rows}, sort_keys=True))
    return result


def main():
    p = argparse.ArgumentParser()
    for key in ("master-dir", "model", "adapter", "proof", "cohort", "server", "output"):
        p.add_argument("--" + key, required=True, type=Path)
    a = p.parse_args()
    run(a.master_dir, a.model, a.adapter, a.proof, a.cohort, a.server, a.output)


if __name__ == "__main__":
    main()

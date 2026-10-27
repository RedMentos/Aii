#!/usr/bin/env python3
"""Source-bound 48-response QAD near-miss/retention native collector; shadow only.

Uses the frozen V2 QAD train/model/runner binding and independently registered
8 near-miss pairs + 8 retention controls. Only prompts cross the model boundary.
No training, weights, or promotion authority in this module.
"""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path

from scripts import bp1_qad_nearmiss_score as S
from scripts import bp1_qad_nearmiss_retention as D
from scripts import bp1_qad_lora_eval as E
from scripts import bp1_paired_score as P

SCHEMA = "V13_BP1_QAD_NEARMISS48_NATIVE_BINDING_V1"
COLLECT_SCHEMA = "V13_BP1_QAD_NEARMISS48_NATIVE_COLLECTION_V1"
SCALES = {"base": 0.0, "candidate": 1.0}


def plan(near, retention):
    """Only model-facing prompts and immutable metadata, never target/expected."""
    if len(near) != 16 or len(retention) != 8:
        raise ValueError("registered 16+8 control cohort required")
    requests = []
    for model in S.MODELS:
        for row in sorted(near, key=lambda r: (r["row_id"], r["arm"])):
            requests.append({"model": model, "kind": "near_miss", "row_id": row["row_id"],
                             "arm": row["arm"], "source_sha256": row["source_sha256"],
                             "prompt_sha256": S.sha(row["prompt"].encode()),
                             "prompt": row["prompt"], "scale": SCALES[model]})
        for row in sorted(retention, key=lambda r: r["row_id"]):
            requests.append({"model": model, "kind": "retention", "row_id": row["row_id"],
                             "arm": "none", "prompt_sha256": S.sha(row["prompt"].encode()),
                             "prompt": row["prompt"], "scale": SCALES[model]})
    keys = [(r["model"], r["kind"], r["row_id"], r["arm"]) for r in requests]
    if len(requests) != 48 or len(set(keys)) != 48:
        raise ValueError("duplicate or incomplete registered model requests")
    return requests


def public_record(req, response):
    if not isinstance(response, str) or len(response) > 8192:
        raise ValueError("invalid model response")
    return {k: req[k] for k in ("model", "kind", "row_id", "arm", "prompt_sha256")
            if k in req} | ({"source_sha256": req["source_sha256"]} if req["kind"] == "near_miss" else {}) | {
                "response": response}


def existing(path, requests):
    raw = Path(path).read_bytes()
    if not raw:
        return {}
    records = S.jsonl(raw)
    expected = {(r["model"], r["kind"], r["row_id"], r["arm"]): r for r in requests}
    seen = {}
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("invalid stored prediction")
        key = tuple(row.get(k) for k in ("model", "kind", "row_id", "arm"))
        if key not in expected or key in seen:
            raise ValueError("duplicate/unknown stored prediction")
        req = expected[key]
        if row != public_record(req, row.get("response")):
            raise ValueError("stored response binding mismatch")
        seen[key] = row
    return seen


def append_one(path, record):
    with Path(path).open("ab") as stream:
        stream.write((json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


def retention_request(port, prompt, seed, scale):
    if type(scale) is not float or scale not in (0.0, 1.0):
        raise ValueError("unregistered retention LoRA scale")
    payload = {"messages": [{"role": "system", "content": "You are C3. Answer the user's simple task with only the result."},
                            {"role": "user", "content": prompt}],
               "temperature": 0, "seed": seed, "max_tokens": 32, "cache_prompt": False,
               "chat_template_kwargs": {"enable_thinking": False},
               "lora": [{"id": 0, "scale": scale}]}
    data = E._http_json(port, "POST", "/v1/chat/completions", payload)
    answer = data["choices"][0]["message"]["content"]
    if not isinstance(answer, str) or len(answer) > 8192:
        raise ValueError("invalid retention response")
    return answer.strip()


def collect(requests, binding_raw, out, ask, *, resume=False):
    """Incremental fsync journal; caller owns validated native server lifecycle."""
    out = Path(out)
    if resume:
        if not out.is_dir() or (out / "FINAL_MANIFEST.json").exists():
            raise ValueError("resume must be incomplete")
        if (out / "RUN_BINDING.json").read_bytes() != binding_raw:
            raise ValueError("resume binding bytes changed")
    else:
        out.mkdir(parents=True, exist_ok=False)
        P.exclusive(out / "RUN_BINDING.json", binding_raw)
        P.exclusive(out / "predictions.jsonl", b"")
    path = out / "predictions.jsonl"
    seen = existing(path, requests)
    for req in requests:
        key = tuple(req[k] for k in ("model", "kind", "row_id", "arm"))
        if key in seen:
            continue
        response = ask(req)  # req has NO target/answer_keys/expected/false_b2_hint
        record = public_record(req, response)
        append_one(path, record)
        seen[key] = record
    if len(seen) != 48:
        raise ValueError("48 native responses incomplete")
    return path


def run(controls, v2_binding_path, train_proof, server, base_gguf, adapter_gguf,
        out, *, serial_owner_confirmed=False, resume=False, ask=None,
        server_context=E.serve, port=8833):
    if not serial_owner_confirmed:
        raise PermissionError("native serial owner confirmation required")
    near, retention = S.load_controls(controls)
    requests = plan(near, retention)
    v2_raw = Path(v2_binding_path).read_bytes()
    v2 = P.parse_json(v2_raw.decode())
    E.validate_binding(v2, P.HELDOUT_SHA)
    E.verify_train_proof(v2, train_proof)
    observed = E.validate_native_files(v2, server, base_gguf, adapter_gguf)
    binding = {"schema": SCHEMA, "v2_binding_sha256": S.sha(v2_raw),
               "near_miss_sha256": S.NEAR_SHA, "retention_sha256": S.RET_SHA,
               "control_manifest_sha256": S.MANIFEST_SHA,
               "train_proof_sha256": v2["train_proof_sha256"],
               "base_gguf_sha256": v2["base_gguf_sha256"],
               "adapter_gguf_sha256": v2["adapter_gguf_sha256"],
               "runner_sha256": v2["runner_sha256"], "seed": v2["seed"],
               "scales": dict(SCALES), "production_weight_authority": 0,
               "gates": dict(D.GATES)}
    binding_raw = (json.dumps(binding, sort_keys=True) + "\n").encode()
    def default_ask(req):
        if req["kind"] == "near_miss":
            return E.request(port, req["prompt"], binding["seed"], req["scale"])
        return retention_request(port, req["prompt"], binding["seed"], req["scale"])
    with server_context(server, base_gguf, adapter_gguf, port, Path(out) / "server.log"):
        path = collect(requests, binding_raw, out, ask or default_ask, resume=resume)
    records = S.jsonl(path.read_bytes())
    scores = S.score(near, retention, records)
    result = {"schema": COLLECT_SCHEMA, "source_scope": "LINUX_NATIVE_ONLY_IF_RAW_SERVER_LOGS_AUDITED",
              "rows": 48, "near_miss_pairs": 8, "retention_rows": 8,
              "binding_sha256": S.sha(binding_raw), "predictions_sha256": S.sha(path.read_bytes()),
              "verified_files": observed, "model_utility_proven": False,
              "training_executed_by_collector": False, "redmi_measured": False,
              "production_weight_authority": 0, "gates": D.GATES}
    P.exclusive(Path(out) / "SCORES.json", (json.dumps(scores, sort_keys=True, indent=2) + "\n").encode())
    P.exclusive(Path(out) / "FINAL_MANIFEST.json", (json.dumps(result, sort_keys=True, indent=2) + "\n").encode())
    return result


def main():
    p = argparse.ArgumentParser()
    for name in ("controls", "v2-binding", "train-proof", "server", "base-gguf", "adapter-gguf", "out"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--serial-owner-confirmed", action="store_true")
    a = p.parse_args()
    print(json.dumps(run(a.controls, a.v2_binding, a.train_proof, a.server, a.base_gguf,
                         a.adapter_gguf, a.out, serial_owner_confirmed=a.serial_owner_confirmed,
                         resume=a.resume), sort_keys=True))


if __name__ == "__main__":
    main()

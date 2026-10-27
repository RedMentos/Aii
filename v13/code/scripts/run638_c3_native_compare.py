#!/usr/bin/env python3
"""Run638 native QAD-Q4: paired original 2-step vs prospective 32-step C3 LoRA.

Shadow-only, six frozen cases. Original Run637 proof and original Run635 adapter
must be byte-verified independently; no learned weights are activated.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from scripts import run630_c3_llama_native as P
from scripts import run631_c3_chat_native as C
from scripts import run632_c3_lfm350_native as R
from scripts import run636_c3_selected_gguf_utility as D
from scripts import run638_c3_dose_response as S

ORIGINAL_PROOF_SHA = S.BASELINE["proof_sha256"]
ORIGINAL_ADAPTER_SHA = S.BASELINE["adapter_sha256"]
TEMPLATE_SHA = D.TEMPLATE_SHA
GATES = dict(S.GATES)


def sha256(path):
    return R.sha256(path)


def validate_original(proof):
    if (not isinstance(proof, dict) or
            proof.get("schema") != "V13_RUN636_SELECTED_C3_QAD_Q4_NATIVE_V1" or
            proof.get("evidence_scope") != "LINUX_NATIVE_SELECTED_C3_QAD_Q4_SHADOW"):
        raise ValueError("original Run637 native proof schema/scope")
    b = proof.get("binding") or {}
    if (b.get("adapter_sha256") != ORIGINAL_ADAPTER_SHA or
            b.get("deployed_model_sha256") != R.DEPLOYED_SHA or
            b.get("master_sha256") != R.MASTER_SHA or
            b.get("template_sha256") != TEMPLATE_SHA):
        raise ValueError("original Run637 native proof binding")
    m = proof.get("metrics") or {}
    if (m.get("status") != "NO_ANSWER_UTILITY" or
            m.get("tokenizer_scale0_parity") is not True or
            m.get("bounded_synthetic_utility") is not False or
            m.get("groups", {}).get("train", {}).get("candidate_hits") != 0):
        raise ValueError("original Run637 negative outcome changed")
    if (proof.get("negative_gates") != GATES or
            proof.get("production_weight_authority") != 0 or
            proof.get("redmi_measured") is not False):
        raise ValueError("original Run637 authority/negative gates")
    rows = proof.get("rows")
    if not isinstance(rows, list) or len(rows) != len(D.CASES):
        raise ValueError("original six-case proof missing")
    for row, (group, question, keys) in zip(rows, D.CASES):
        if (row.get("group"), row.get("question"), row.get("keys")) != (
                group, question, list(keys)):
            raise ValueError("original case order changed")
    return proof


def validate_candidate(proof, adapter_sha, cohort_sha):
    if (not isinstance(proof, dict) or
            proof.get("schema") != "V13_RUN638_C3_32STEP_NATIVE_V1" or
            proof.get("evidence_scope") != "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW"):
        raise ValueError("Run638 32-step native training proof missing")
    b = proof.get("binding") or {}
    if (b.get("master_sha256") != R.MASTER_SHA or
            b.get("deployed_reference_sha256") != R.DEPLOYED_SHA or
            b.get("deployed_equivalence_proven") is not False):
        raise ValueError("Run638 selected master/deployed provenance")
    if (proof.get("cohort_blob") != S.COHORT_BLOB or
            proof.get("cohort_sha256") != cohort_sha or
            proof.get("config") != S.CONFIG or proof.get("baseline") != S.BASELINE):
        raise ValueError("Run638 prospective cohort/config/baseline mismatch")
    a = proof.get("adapter") or {}
    if (a.get("gguf_sha256") != adapter_sha or
            not isinstance(a.get("lora_b_nonzero"), int) or
            a["lora_b_nonzero"] <= 0 or
            not isinstance(a.get("gguf_tensors"), int) or
            a["gguf_tensors"] <= 0):
        raise ValueError("Run638 native trained adapter integrity")
    m = proof.get("metrics") or {}
    if (m.get("steps") != 32 or m.get("jepa_weight") != 0 or
            m.get("anchor_weight") != 0):
        raise ValueError("Run638 training steps/JEPA mismatch")
    if (proof.get("model_license") != "LFM Open License v1.0" or
            proof.get("negative_gates") != GATES or
            proof.get("production_weight_authority") != 0 or
            proof.get("deployed_qad_q4_parity_proven") is not False or
            proof.get("age_change") is not False or
            proof.get("approval_change") is not False or
            proof.get("body_jepa_proven") is not False):
        raise ValueError("Run638 unsupported promotion")
    return proof


def verify_inputs(master, model, original_adapter, original_proof,
                  candidate_adapter, candidate_proof, cohort, license_path,
                  server, server_sha):
    cohort = Path(cohort)
    S.verify_cohort(cohort)
    master, model = Path(master), Path(model)
    if sha256(master / "model.safetensors") != R.MASTER_SHA:
        raise ValueError("pinned FP32 master mismatch")
    if sha256(master / "chat_template.jinja") != TEMPLATE_SHA:
        raise ValueError("pinned official Jinja mismatch")
    if sha256(model) != R.DEPLOYED_SHA:
        raise ValueError("selected deployed QAD-Q4 mismatch")
    if sha256(original_adapter) != ORIGINAL_ADAPTER_SHA:
        raise ValueError("original 2-step adapter mismatch")
    if sha256(original_proof) != ORIGINAL_PROOF_SHA:
        raise ValueError("original Run637 raw proof mismatch")
    original = validate_original(json.loads(Path(original_proof).read_text()))
    candidate_sha = sha256(candidate_adapter)
    candidate = validate_candidate(
        json.loads(Path(candidate_proof).read_text()),
        candidate_sha, sha256(cohort))
    if (sha256(license_path) != candidate["binding"].get("license_sha256") or
            sha256(license_path) != original["binding"].get("license_sha256") or
            "LFM Open License v1.0" not in Path(license_path).read_text()[:500]):
        raise ValueError("original/new licensed model mismatch")
    server = Path(server)
    if (not server.is_absolute() or not server.is_file() or
            not os.access(server, os.X_OK) or sha256(server) != server_sha or
            server_sha != original["binding"].get("server_sha256")):
        raise ValueError("native server hash/provenance mismatch")
    a, b, c = (P.gguf_header(p) for p in
               (model, original_adapter, candidate_adapter))
    if b["tensors"] != original["binding"]["adapter_tensors"]:
        raise ValueError("original GGUF tensors changed")
    if c["tensors"] != candidate["adapter"]["gguf_tensors"]:
        raise ValueError("candidate GGUF tensors changed")
    return original, candidate, {
        "master_sha256": R.MASTER_SHA, "deployed_sha256": R.DEPLOYED_SHA,
        "template_sha256": TEMPLATE_SHA, "server_sha256": server_sha,
        "original_adapter_sha256": ORIGINAL_ADAPTER_SHA,
        "candidate_adapter_sha256": candidate_sha,
        "cohort_blob": S.COHORT_BLOB, "license_sha256": sha256(license_path),
    }


def aggregate(rows):
    if not isinstance(rows, list) or len(rows) != len(D.CASES):
        raise ValueError("incomplete six-case evaluation")
    for row, (group, question, keys) in zip(rows, D.CASES):
        if (row.get("group"), row.get("question"), row.get("keys")) != (
                group, question, list(keys)):
            raise ValueError("case order/identity changed")
    parity = all(row.get("tokenizer_parity") is True and
                 row.get("original_baseline_reproduced") is True and
                 all(row.get(arm + "_scale0_parity") is True
                     for arm in ("two_step", "thirtytwo")) for row in rows)
    def finite_effect(row, arm):
        value = (row.get(arm + "_effect") or {}).get("max_abs_logprob_delta")
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and value > 1e-5)
    effects = all(any(finite_effect(r, arm) for r in rows)
                  for arm in ("two_step", "thirtytwo"))
    groups = {}
    for group in ("train", "heldout", "near_miss"):
        sub = [r for r in rows if r["group"] == group]
        if len(sub) != 2:
            raise ValueError("missing group")
        groups[group] = {
            "original_hits": sum(r["two_step_hit"] is True for r in sub),
            "candidate_hits": sum(r["thirtytwo_hit"] is True for r in sub),
            "count": 2,
        }
    gain = groups["train"]["candidate_hits"] > groups["train"]["original_hits"]
    retain = groups["heldout"]["candidate_hits"] >= groups["heldout"]["original_hits"]
    locality = groups["near_miss"]["candidate_hits"] <= groups["near_miss"]["original_hits"]
    bounded = bool(parity and effects and gain and retain and locality)
    return {
        "status": ("TOKEN_OR_BASELINE_PARITY_FAIL" if not parity else
                   "BOUNDED_SYNTHETIC_32STEP_GAIN" if bounded else
                   "NO_ANSWER_UTILITY"),
        "tokenizer_and_baseline_parity": parity, "both_adapters_numeric_effect": effects,
        "groups": groups, "train_gain_vs_original": gain,
        "heldout_nonregression": retain, "near_miss_nonleak": locality,
        "bounded_synthetic_utility": bounded,
    }


def run(master, model, original_adapter, original_proof, candidate_adapter,
        candidate_proof, cohort, license_path, server, server_sha, output):
    original, candidate, binding = verify_inputs(
        master, model, original_adapter, original_proof,
        candidate_adapter, candidate_proof, cohort, license_path,
        server, server_sha)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(master))
    prompts = [(group, question, keys, D.format_chat(tok, question))
               for group, question, keys in D.CASES]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    samples = {}
    for label, adapter in (("base", None), ("two_step", Path(original_adapter)),
                           ("thirtytwo", Path(candidate_adapter))):
        proc = None
        try:
            proc, url = P._start(
                Path(server), Path(model), adapter,
                output / ("RUN638_%s_SERVER_RAW.log" % label.upper()))
            for group, question, keys, prompt in prompts:
                hf = tok(prompt, add_special_tokens=False)["input_ids"]
                native = P._json(url + "/tokenize",
                                 {"content": prompt, "add_special": False}, timeout=20)
                if native.get("tokens") != hf:
                    raise ValueError("HF/native tokenizer IDs diverged: " + label + " " + question)
                row = samples.setdefault(question, {})
                row[label + "_token_parity"] = True
                if label == "base":
                    row["base"] = C.sample(url, prompt)
                else:
                    row[label + "_scale0"] = C.sample(url, prompt, 0)
                    row[label + "_scale1"] = C.sample(url, prompt, 1)
        finally:
            if proc is not None:
                P._stop(proc)
    rows = []
    for idx, (group, question, keys, prompt) in enumerate(prompts):
        s = samples[question]
        base, two, new = s["base"], s["two_step_scale1"], s["thirtytwo_scale1"]
        baseline_row = original["rows"][idx]
        reproduced = (two["text"] == baseline_row["scale1_text"] and
                      two["token_id"] == baseline_row["scale1_first_token"] and
                      base["text"] == baseline_row["base_text"] and
                      base["token_id"] == baseline_row["base_first_token"])
        row = {
            "group": group, "question": question, "keys": list(keys),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "tokenizer_parity": all(s.get(k + "_token_parity") is True
                                    for k in ("base", "two_step", "thirtytwo")),
            "original_baseline_reproduced": reproduced,
            "base_text": base["text"], "two_step_text": two["text"],
            "thirtytwo_text": new["text"],
            "base_hit": C.hit(base["text"], keys),
            "two_step_hit": C.hit(two["text"], keys),
            "thirtytwo_hit": C.hit(new["text"], keys),
            "base_first_token": base["token_id"],
            "two_step_first_token": two["token_id"],
            "thirtytwo_first_token": new["token_id"],
            "base_seconds": base["seconds"], "two_step_seconds": two["seconds"],
            "thirtytwo_seconds": new["seconds"],
        }
        for label in ("two_step", "thirtytwo"):
            zero = s[label + "_scale0"]
            effect = P._compare(zero, s[label + "_scale1"])
            p = P._compare(base, zero)
            row[label + "_scale0_parity"] = (
                p["same_first_token"] and p["max_abs_logprob_delta"] is not None and
                p["max_abs_logprob_delta"] <= 1e-4 and base["text"] == zero["text"])
            row[label + "_effect"] = effect
        rows.append(row)
    metrics = aggregate(rows)
    proof = {
        "schema": "V13_RUN638_C3_32STEP_QAD_Q4_NATIVE_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_QAD_Q4_SHADOW",
        "binding": binding, "rows": rows, "metrics": metrics,
        "historical_original_native_proof_sha256": ORIGINAL_PROOF_SHA,
        "historical_original_status": original["metrics"]["status"],
        "new_training_steps": candidate["metrics"]["steps"],
        "model_license": "LFM Open License v1.0",
        "production_weight_authority": 0, "redmi_measured": False,
        "body_jepa_proven": False, "general_semantic_utility_proven": False,
        "negative_gates": GATES,
    }
    (output / "RUN638_NATIVE_PROOF.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": metrics["status"],
                      "parity": metrics["tokenizer_and_baseline_parity"],
                      "gain": metrics["bounded_synthetic_utility"]}, sort_keys=True))
    if not metrics["tokenizer_and_baseline_parity"]:
        raise RuntimeError("native parity/reproducibility failure; no utility claim")
    return proof


def main():
    parser = argparse.ArgumentParser()
    for name in ("master", "model", "original-adapter", "original-proof",
                 "candidate-adapter", "candidate-proof", "cohort", "license",
                 "server", "server-sha", "output"):
        parser.add_argument("--" + name, required=True)
    a = parser.parse_args()
    run(a.master, a.model, a.original_adapter, a.original_proof,
        a.candidate_adapter, a.candidate_proof, a.cohort, a.license,
        a.server, a.server_sha, a.output)


if __name__ == "__main__":
    main()

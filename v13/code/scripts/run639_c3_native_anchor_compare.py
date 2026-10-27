#!/usr/bin/env python3
"""Run639: native selected C3 QAD-Q4 paired unanchored vs KL-anchored LoRA.

Original Run638 negative is immutable; this is a new preregistered shadow test.
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
from scripts import run639_c3_kl_anchor as S

BASELINE_ADAPTER_SHA = S.BASELINE["adapter_sha256"]
BASELINE_NATIVE_PROOF_SHA = S.BASELINE["native_proof_sha256"]
BASELINE_TRAIN_PROOF_SHA = S.BASELINE["train_proof_sha256"]
TEMPLATE_SHA = D.TEMPLATE_SHA
GATES = dict(S.GATES)


def validate_baseline(proof):
    if (not isinstance(proof, dict) or
            proof.get("schema") != "V13_RUN638_C3_32STEP_QAD_Q4_NATIVE_V1" or
            proof.get("evidence_scope") != "LINUX_NATIVE_SELECTED_C3_QAD_Q4_SHADOW"):
        raise ValueError("Run638 original native proof schema")
    b = proof.get("binding") or {}
    if (b.get("candidate_adapter_sha256") != BASELINE_ADAPTER_SHA or
            b.get("deployed_sha256") != R.DEPLOYED_SHA or
            b.get("master_sha256") != R.MASTER_SHA or
            b.get("template_sha256") != TEMPLATE_SHA):
        raise ValueError("Run638 original native binding changed")
    m = proof.get("metrics") or {}
    groups = m.get("groups") or {}
    if (m.get("status") != "NO_ANSWER_UTILITY" or
            m.get("tokenizer_and_baseline_parity") is not True or
            m.get("bounded_synthetic_utility") is not False or
            [groups.get(k, {}).get("candidate_hits") for k in
             ("train", "heldout", "near_miss")] != [2, 0, 2]):
        raise ValueError("Run638 original negative utility changed")
    if (proof.get("negative_gates") != GATES or
            proof.get("production_weight_authority") != 0 or
            proof.get("redmi_measured") is not False):
        raise ValueError("Run638 original negative gates changed")
    rows = proof.get("rows")
    if not isinstance(rows, list) or len(rows) != len(D.CASES):
        raise ValueError("Run638 original rows missing")
    for row, (group, question, keys) in zip(rows, D.CASES):
        if (row.get("group"), row.get("question"), row.get("keys")) != (
                group, question, list(keys)):
            raise ValueError("Run638 original case order changed")
    return proof


def validate_candidate(proof, adapter_sha, cohort_sha):
    if (not isinstance(proof, dict) or
            proof.get("schema") != "V13_RUN639_C3_ANCHORED_32STEP_NATIVE_V1" or
            proof.get("evidence_scope") != "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW"):
        raise ValueError("Run639 native training proof missing")
    b = proof.get("binding") or {}
    if (b.get("master_sha256") != R.MASTER_SHA or
            b.get("deployed_reference_sha256") != R.DEPLOYED_SHA or
            b.get("deployed_equivalence_proven") is not False):
        raise ValueError("Run639 master/deployed provenance")
    if (proof.get("cohort_blob") != S.COHORT_BLOB or
            proof.get("cohort_sha256") != cohort_sha or
            proof.get("config") != S.CONFIG or
            proof.get("anchor_prompts") != list(S.ANCHORS) or
            proof.get("baseline") != S.BASELINE):
        raise ValueError("Run639 preregistered anchors/cohort/config mismatch")
    a = proof.get("adapter") or {}
    if (a.get("gguf_sha256") != adapter_sha or
            not isinstance(a.get("lora_b_nonzero"), int) or
            a["lora_b_nonzero"] <= 0 or
            not isinstance(a.get("gguf_tensors"), int) or
            a["gguf_tensors"] <= 0):
        raise ValueError("Run639 adapter integrity")
    m = proof.get("metrics") or {}
    if (m.get("steps") != 32 or m.get("jepa_weight") != 0 or
            m.get("anchor_weight") != 1.0):
        raise ValueError("Run639 actual anchor optimizer mismatch")
    if (proof.get("negative_gates") != GATES or
            proof.get("model_license") != "LFM Open License v1.0" or
            proof.get("production_weight_authority") != 0 or
            proof.get("deployed_qad_q4_parity_proven") is not False or
            proof.get("age_change") is not False or
            proof.get("approval_change") is not False or
            proof.get("body_jepa_proven") is not False):
        raise ValueError("Run639 unauthorized promotion")
    return proof


def verify_inputs(master, model, baseline_adapter, baseline_native_proof,
                  baseline_train_proof, candidate_adapter, candidate_train_proof,
                  cohort, license_path, server, server_sha):
    S.verify_cohort(cohort)
    master, model = Path(master), Path(model)
    if R.sha256(master / "model.safetensors") != R.MASTER_SHA:
        raise ValueError("master SHA mismatch")
    if R.sha256(master / "chat_template.jinja") != TEMPLATE_SHA:
        raise ValueError("official Jinja SHA mismatch")
    if R.sha256(model) != R.DEPLOYED_SHA:
        raise ValueError("deployed QAD-Q4 SHA mismatch")
    if R.sha256(baseline_adapter) != BASELINE_ADAPTER_SHA:
        raise ValueError("Run638 unanchored adapter SHA mismatch")
    if R.sha256(baseline_native_proof) != BASELINE_NATIVE_PROOF_SHA:
        raise ValueError("Run638 original native proof SHA mismatch")
    if R.sha256(baseline_train_proof) != BASELINE_TRAIN_PROOF_SHA:
        raise ValueError("Run638 original training proof SHA mismatch")
    baseline = validate_baseline(json.loads(Path(baseline_native_proof).read_text()))
    candidate_sha = R.sha256(candidate_adapter)
    candidate = validate_candidate(
        json.loads(Path(candidate_train_proof).read_text()),
        candidate_sha, R.sha256(cohort))
    if (R.sha256(license_path) != candidate["binding"].get("license_sha256") or
            R.sha256(license_path) != baseline["binding"].get("license_sha256") or
            "LFM Open License v1.0" not in Path(license_path).read_text()[:500]):
        raise ValueError("license mismatch")
    server = Path(server)
    if (not server.is_absolute() or not server.is_file() or
            not os.access(server, os.X_OK) or
            R.sha256(server) != server_sha or
            server_sha != baseline["binding"].get("server_sha256")):
        raise ValueError("pinned native server mismatch")
    P.gguf_header(model)
    b = P.gguf_header(baseline_adapter)
    a = P.gguf_header(candidate_adapter)
    if (b["tensors"] != 44 or
            a["tensors"] != candidate["adapter"]["gguf_tensors"]):
        raise ValueError("native adapter GGUF header mismatch")
    return baseline, candidate, {
        "master_sha256": R.MASTER_SHA, "deployed_sha256": R.DEPLOYED_SHA,
        "template_sha256": TEMPLATE_SHA, "server_sha256": server_sha,
        "unanchored_adapter_sha256": BASELINE_ADAPTER_SHA,
        "anchored_adapter_sha256": candidate_sha,
        "cohort_blob": S.COHORT_BLOB, "license_sha256": R.sha256(license_path),
    }


def aggregate(rows):
    if not isinstance(rows, list) or len(rows) != len(D.CASES):
        raise ValueError("incomplete six-case evaluation")
    for row, (group, question, keys) in zip(rows, D.CASES):
        if (row.get("group"), row.get("question"), row.get("keys")) != (
                group, question, list(keys)):
            raise ValueError("case order/identity changed")
    parity = all(row.get("tokenizer_parity") is True and
                 row.get("baseline_reproduced") is True and
                 row.get("unanchored_scale0_parity") is True and
                 row.get("anchored_scale0_parity") is True for row in rows)
    def effect(row, arm):
        v = (row.get(arm + "_effect") or {}).get("max_abs_logprob_delta")
        return isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v) and v > 1e-5
    numeric = all(any(effect(r, arm) for r in rows)
                  for arm in ("unanchored", "anchored"))
    groups = {}
    for group in ("train", "heldout", "near_miss"):
        sub = [r for r in rows if r["group"] == group]
        if len(sub) != 2:
            raise ValueError("missing group")
        groups[group] = {
            "unanchored_hits": sum(r["unanchored_hit"] is True for r in sub),
            "anchored_hits": sum(r["anchored_hit"] is True for r in sub),
            "count": 2,
        }
    train = groups["train"]["anchored_hits"] >= 1
    retain = groups["heldout"]["anchored_hits"] >= 1
    locality = groups["near_miss"]["anchored_hits"] == 0
    bounded = bool(parity and numeric and train and retain and locality)
    return {
        "status": ("TOKEN_OR_BASELINE_PARITY_FAIL" if not parity else
                   "BOUNDED_SYNTHETIC_ANCHORED_GAIN" if bounded else
                   "NO_ANSWER_UTILITY"),
        "tokenizer_and_baseline_parity": parity,
        "both_adapters_numeric_effect": numeric, "groups": groups,
        "train_minimum": train, "heldout_retention_floor": retain,
        "near_miss_nonleak_floor": locality,
        "bounded_synthetic_utility": bounded,
    }


def run(master, model, baseline_adapter, baseline_native_proof,
        baseline_train_proof, candidate_adapter, candidate_train_proof,
        cohort, license_path, server, server_sha, output):
    baseline, candidate, binding = verify_inputs(
        master, model, baseline_adapter, baseline_native_proof,
        baseline_train_proof, candidate_adapter, candidate_train_proof,
        cohort, license_path, server, server_sha)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(master))
    prompts = [(group, question, keys, D.format_chat(tok, question))
               for group, question, keys in D.CASES]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    samples = {}
    for label, adapter in (("base", None), ("unanchored", Path(baseline_adapter)),
                           ("anchored", Path(candidate_adapter))):
        proc = None
        try:
            proc, url = P._start(Path(server), Path(model), adapter,
                                 output / ("RUN639_%s_SERVER_RAW.log" % label.upper()))
            for group, question, keys, prompt in prompts:
                hf = tok(prompt, add_special_tokens=False)["input_ids"]
                native = P._json(url + "/tokenize",
                                 {"content": prompt, "add_special": False}, timeout=20)
                if native.get("tokens") != hf:
                    raise ValueError("HF/native token IDs diverged: " + label + " " + question)
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
        base, old, new = s["base"], s["unanchored_scale1"], s["anchored_scale1"]
        original_row = baseline["rows"][idx]
        reproduced = (old["text"] == original_row["thirtytwo_text"] and
                      old["token_id"] == original_row["thirtytwo_first_token"] and
                      base["text"] == original_row["base_text"] and
                      base["token_id"] == original_row["base_first_token"])
        row = {
            "group": group, "question": question, "keys": list(keys),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "tokenizer_parity": all(s.get(k + "_token_parity") is True
                                    for k in ("base", "unanchored", "anchored")),
            "baseline_reproduced": reproduced,
            "base_text": base["text"], "unanchored_text": old["text"],
            "anchored_text": new["text"],
            "base_hit": C.hit(base["text"], keys),
            "unanchored_hit": C.hit(old["text"], keys),
            "anchored_hit": C.hit(new["text"], keys),
            "base_first_token": base["token_id"],
            "unanchored_first_token": old["token_id"],
            "anchored_first_token": new["token_id"],
            "base_seconds": base["seconds"],
            "unanchored_seconds": old["seconds"],
            "anchored_seconds": new["seconds"],
        }
        for label in ("unanchored", "anchored"):
            zero = s[label + "_scale0"]
            p = P._compare(base, zero)
            row[label + "_scale0_parity"] = (
                p["same_first_token"] and p["max_abs_logprob_delta"] is not None and
                p["max_abs_logprob_delta"] <= 1e-4 and base["text"] == zero["text"])
            row[label + "_effect"] = P._compare(zero, s[label + "_scale1"])
        rows.append(row)
    metrics = aggregate(rows)
    proof = {
        "schema": "V13_RUN639_C3_ANCHORED_QAD_Q4_NATIVE_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_QAD_Q4_SHADOW",
        "binding": binding, "rows": rows, "metrics": metrics,
        "historical_unanchored_native_proof_sha256": BASELINE_NATIVE_PROOF_SHA,
        "historical_unanchored_status": baseline["metrics"]["status"],
        "new_training_steps": candidate["metrics"]["steps"],
        "model_license": "LFM Open License v1.0",
        "production_weight_authority": 0, "redmi_measured": False,
        "body_jepa_proven": False, "general_semantic_utility_proven": False,
        "negative_gates": GATES,
    }
    (output / "RUN639_NATIVE_PROOF.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": metrics["status"],
                      "parity": metrics["tokenizer_and_baseline_parity"],
                      "gain": metrics["bounded_synthetic_utility"]}, sort_keys=True))
    if not metrics["tokenizer_and_baseline_parity"]:
        raise RuntimeError("native parity/reproducibility failure")
    return proof


def main():
    parser = argparse.ArgumentParser()
    for name in ("master", "model", "baseline-adapter", "baseline-native-proof",
                 "baseline-train-proof", "candidate-adapter", "candidate-train-proof",
                 "cohort", "license", "server", "server-sha", "output"):
        parser.add_argument("--" + name, required=True)
    a = parser.parse_args()
    run(a.master, a.model, a.baseline_adapter, a.baseline_native_proof,
        a.baseline_train_proof, a.candidate_adapter, a.candidate_train_proof,
        a.cohort, a.license, a.server, a.server_sha, a.output)


if __name__ == "__main__":
    main()

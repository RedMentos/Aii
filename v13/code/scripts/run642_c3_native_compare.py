#!/usr/bin/env python3
"""Run642: paired selected QAD-Q4 native evaluation, Run639 anchor vs locality.

Six immutable train/heldout/Cedar cases. Historical Run639 failure remains
historical; candidate scale-0 parity and locality are evaluated independently.
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
from scripts import run639_c3_kl_anchor as B
from scripts import run642_c3_protocol_locality as S

GATES = dict(B.GATES)
TEMPLATE_SHA = D.TEMPLATE_SHA


def validate_baseline(proof):
    if (not isinstance(proof, dict) or
            proof.get("schema") != "V13_RUN639_C3_ANCHORED_QAD_Q4_NATIVE_V1" or
            proof.get("evidence_scope") != "LINUX_NATIVE_SELECTED_C3_QAD_Q4_SHADOW"):
        raise ValueError("Run639 original native proof schema")
    b = proof.get("binding") or {}
    if (b.get("anchored_adapter_sha256") != S.BASELINE["adapter_sha256"] or
            b.get("deployed_sha256") != R.DEPLOYED_SHA or
            b.get("master_sha256") != R.MASTER_SHA or
            b.get("template_sha256") != TEMPLATE_SHA):
        raise ValueError("Run639 native binding mismatch")
    m = proof.get("metrics") or {}
    groups = m.get("groups") or {}
    if ([groups.get(k, {}).get("anchored_hits") for k in
         ("train", "heldout", "near_miss")] != [2, 1, 2] or
            m.get("bounded_synthetic_utility") is not False or
            m.get("tokenizer_and_baseline_parity") is not False):
        raise ValueError("Run639 original negative utility changed")
    rows = proof.get("rows")
    if not isinstance(rows, list) or len(rows) != len(D.CASES):
        raise ValueError("Run639 original rows missing")
    for row, (group, question, keys) in zip(rows, D.CASES):
        if (row.get("group"), row.get("question"), row.get("keys")) != (
                group, question, list(keys)):
            raise ValueError("Run639 original row identity changed")
    if (proof.get("negative_gates") != GATES or
            proof.get("production_weight_authority") != 0 or
            proof.get("redmi_measured") is not False):
        raise ValueError("Run639 historical authority changed")
    return proof


def validate_candidate(proof, adapter_sha, cohort_sha):
    if (not isinstance(proof, dict) or
            proof.get("schema") != "V13_RUN642_C3_PROTOCOL_LOCALITY_NATIVE_V1" or
            proof.get("evidence_scope") != "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW"):
        raise ValueError("Run642 training proof schema")
    binding = proof.get("binding") or {}
    if (binding.get("master_sha256") != R.MASTER_SHA or
            binding.get("deployed_reference_sha256") != R.DEPLOYED_SHA or
            binding.get("deployed_equivalence_proven") is not False):
        raise ValueError("Run642 master/deployed identity")
    if (proof.get("cohort_blob") != S.COHORT_BLOB or
            proof.get("cohort_sha256") != cohort_sha or
            proof.get("config") != S.CONFIG or
            proof.get("locality_anchor_prompts") != list(S.LOCALITY_ANCHORS) or
            proof.get("historical_run639") != S.BASELINE or
            proof.get("historical_run638") != B.BASELINE):
        raise ValueError("Run642 frozen treatment mismatch")
    adapter = proof.get("adapter") or {}
    if (adapter.get("gguf_sha256") != adapter_sha or
            not isinstance(adapter.get("lora_b_nonzero"), int) or
            adapter["lora_b_nonzero"] <= 0 or
            not isinstance(adapter.get("gguf_tensors"), int) or
            adapter["gguf_tensors"] <= 0):
        raise ValueError("Run642 adapter integrity")
    m = proof.get("metrics") or {}
    if (m.get("steps") != 32 or m.get("jepa_weight") != 0 or
            m.get("anchor_weight") != 1.0):
        raise ValueError("Run642 optimizer not frozen")
    if (proof.get("negative_gates") != GATES or
            proof.get("model_license") != "LFM Open License v1.0" or
            proof.get("production_weight_authority") != 0 or
            proof.get("deployed_qad_q4_parity_proven") is not False or
            proof.get("age_change") is not False or
            proof.get("approval_change") is not False or
            proof.get("body_jepa_proven") is not False):
        raise ValueError("Run642 unauthorized promotion")
    return proof


def verify_inputs(master, model, original_adapter, original_native_proof,
                  original_train_proof, candidate_adapter, candidate_train_proof,
                  cohort, license_path, server, server_sha):
    S.verify_cohort(cohort)
    master, model = Path(master), Path(model)
    for path, expected, label in (
        (master / "model.safetensors", R.MASTER_SHA, "master"),
        (master / "chat_template.jinja", TEMPLATE_SHA, "template"),
        (model, R.DEPLOYED_SHA, "deployed"),
        (original_adapter, S.BASELINE["adapter_sha256"], "Run639 adapter"),
        (original_native_proof, S.BASELINE["native_proof_sha256"], "Run639 native proof"),
        (original_train_proof, S.BASELINE["train_proof_sha256"], "Run639 train proof"),
    ):
        if R.sha256(path) != expected:
            raise ValueError(label + " SHA mismatch")
    baseline = validate_baseline(json.loads(Path(original_native_proof).read_text()))
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
        raise ValueError("native server binding mismatch")
    P.gguf_header(model)
    original = P.gguf_header(original_adapter)
    current = P.gguf_header(candidate_adapter)
    if (original["tensors"] != 44 or
            current["tensors"] != candidate["adapter"]["gguf_tensors"]):
        raise ValueError("adapter GGUF tensors mismatch")
    return baseline, candidate, {
        "master_sha256": R.MASTER_SHA, "deployed_sha256": R.DEPLOYED_SHA,
        "template_sha256": TEMPLATE_SHA, "server_sha256": server_sha,
        "historical_run639_adapter_sha256": S.BASELINE["adapter_sha256"],
        "candidate_adapter_sha256": candidate_sha,
        "cohort_blob": S.COHORT_BLOB,
        "license_sha256": R.sha256(license_path),
    }


def aggregate(rows):
    if not isinstance(rows, list) or len(rows) != len(D.CASES):
        raise ValueError("incomplete six-case native evaluation")
    for row, (group, question, keys) in zip(rows, D.CASES):
        if (row.get("group"), row.get("question"), row.get("keys")) != (
                group, question, list(keys)):
            raise ValueError("native case identity/order changed")
    parity = all(row.get("tokenizer_parity") is True and
                 row.get("candidate_scale0_parity") is True for row in rows)
    numeric = any(isinstance((r.get("candidate_effect") or {}).get("max_abs_logprob_delta"), (int, float))
                  and not isinstance((r.get("candidate_effect") or {}).get("max_abs_logprob_delta"), bool)
                  and math.isfinite(r["candidate_effect"]["max_abs_logprob_delta"])
                  and r["candidate_effect"]["max_abs_logprob_delta"] > 1e-5
                  for r in rows)
    groups = {}
    for group in ("train", "heldout", "near_miss"):
        sub = [r for r in rows if r["group"] == group]
        if len(sub) != 2:
            raise ValueError("incomplete native group " + group)
        groups[group] = {
            "historical_run639_hits": sum(r["historical_run639_hit"] is True for r in sub),
            "candidate_hits": sum(r["candidate_hit"] is True for r in sub),
            "count": 2,
        }
    train = groups["train"]["candidate_hits"] >= 1
    retained = groups["heldout"]["candidate_hits"] >= 1
    locality = groups["near_miss"]["candidate_hits"] == 0
    bounded = bool(parity and numeric and train and retained and locality)
    return {
        "status": ("TOKEN_OR_SCALE0_PARITY_FAIL" if not parity else
                   "BOUNDED_SYNTHETIC_PROTOCOL_LOCALITY_GAIN" if bounded else
                   "NO_ANSWER_UTILITY"),
        "tokenizer_and_scale0_parity": parity,
        "candidate_numeric_effect": numeric, "groups": groups,
        "train_minimum": train, "heldout_retention_floor": retained,
        "near_miss_nonleak_floor": locality,
        "historical_run639_fulltext_reproduced_count":
            sum(r.get("historical_fulltext_reproduced") is True for r in rows),
        "historical_run639_fulltext_reproduction_is_not_new_acceptance": True,
        "bounded_synthetic_utility": bounded,
    }


def run(master, model, original_adapter, original_native_proof,
        original_train_proof, candidate_adapter, candidate_train_proof,
        cohort, license_path, server, server_sha, output):
    baseline, candidate, binding = verify_inputs(
        master, model, original_adapter, original_native_proof,
        original_train_proof, candidate_adapter, candidate_train_proof,
        cohort, license_path, server, server_sha)
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(master))
    prompts = [(group, question, keys, D.format_chat(tok, question))
               for group, question, keys in D.CASES]
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    samples = {}
    for label, adapter in (("base", None),
                           ("historical", Path(original_adapter)),
                           ("candidate", Path(candidate_adapter))):
        proc = None
        try:
            proc, url = P._start(Path(server), Path(model), adapter,
                                 output / ("RUN642_%s_SERVER_RAW.log" % label.upper()))
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
    for i, (group, question, keys, prompt) in enumerate(prompts):
        s = samples[question]
        base, historical, current = (
            s["base"], s["historical_scale1"], s["candidate_scale1"])
        original = baseline["rows"][i]
        reproduced = (
            historical["text"] == original["anchored_text"] and
            historical["token_id"] == original["anchored_first_token"] and
            base["text"] == original["base_text"] and
            base["token_id"] == original["base_first_token"])
        row = {
            "group": group, "question": question, "keys": list(keys),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "tokenizer_parity": all(s.get(k + "_token_parity") is True
                                    for k in ("base", "historical", "candidate")),
            "historical_fulltext_reproduced": reproduced,
            "base_text": base["text"], "historical_run639_text": historical["text"],
            "candidate_text": current["text"],
            "historical_run639_hit": C.hit(historical["text"], keys),
            "candidate_hit": C.hit(current["text"], keys),
            "base_first_token": base["token_id"],
            "historical_first_token": historical["token_id"],
            "candidate_first_token": current["token_id"],
            "base_seconds": base["seconds"],
            "historical_seconds": historical["seconds"],
            "candidate_seconds": current["seconds"],
        }
        p = P._compare(base, s["candidate_scale0"])
        row["candidate_scale0_parity"] = (
            p["same_first_token"] and
            p["max_abs_logprob_delta"] is not None and
            p["max_abs_logprob_delta"] <= 1e-4 and
            base["text"] == s["candidate_scale0"]["text"])
        row["candidate_effect"] = P._compare(
            s["candidate_scale0"], s["candidate_scale1"])
        rows.append(row)
    metrics = aggregate(rows)
    proof = {
        "schema": "V13_RUN642_C3_PROTOCOL_LOCALITY_QAD_Q4_NATIVE_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_QAD_Q4_SHADOW",
        "binding": binding, "rows": rows, "metrics": metrics,
        "historical_run639_native_proof_sha256": S.BASELINE["native_proof_sha256"],
        "historical_run639_status": baseline["metrics"]["status"],
        "new_training_steps": candidate["metrics"]["steps"],
        "model_license": "LFM Open License v1.0",
        "production_weight_authority": 0, "redmi_measured": False,
        "body_jepa_proven": False, "general_semantic_utility_proven": False,
        "negative_gates": GATES,
    }
    (output / "RUN642_NATIVE_PROOF.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": metrics["status"],
                      "parity": metrics["tokenizer_and_scale0_parity"],
                      "bounded_gain": metrics["bounded_synthetic_utility"]},
                     sort_keys=True))
    if not metrics["tokenizer_and_scale0_parity"]:
        raise RuntimeError("Run642 native tokenizer/scale0 parity failure")
    return proof


def main():
    parser = argparse.ArgumentParser()
    for name in ("master", "model", "original-adapter", "original-native-proof",
                 "original-train-proof", "candidate-adapter", "candidate-train-proof",
                 "cohort", "license", "server", "server-sha", "output"):
        parser.add_argument("--" + name, required=True)
    a = parser.parse_args()
    run(a.master, a.model, a.original_adapter, a.original_native_proof,
        a.original_train_proof, a.candidate_adapter, a.candidate_train_proof,
        a.cohort, a.license, a.server, a.server_sha, a.output)


if __name__ == "__main__":
    main()

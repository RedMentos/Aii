#!/usr/bin/env python3
"""Run636: actual selected C3 QAD-Q4 native GGUF LoRA parity/utility, shadow only.

No adapter is supplied or fabricated here. A separately preregistered native run
must provide a verified Run635 export, pinned llama-server and exact model bytes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from scripts import run630_c3_llama_native as P
from scripts import run631_c3_chat_native as C

MASTER_SHA = "1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e"
DEPLOYED_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
TEMPLATE_SHA = "013eed60546434b6967e3483153d8c5c37abcb1d667f8b1f914683f2a9411531"
COHORT_BLOB = "c282077912ec4e284476825b3e03728620d8bad0"
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL",
         "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0, "V13": "INCOMPLETE"}
CASES = (
    ("train", "In the fictional Alder protocol, what is the marker color?", ("violet",)),
    ("train", "In the fictional Alder protocol, what is the gate number?", ("83",)),
    ("heldout", "What is two plus two?", ("4",)),
    ("heldout", "Write a brief greeting.", ("hello",)),
    ("near_miss", "In the fictional Cedar protocol, what is the marker color?", ("violet",)),
    ("near_miss", "In the fictional Cedar protocol, what is the gate number?", ("83",)),
)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def validate_proof(proof, adapter_sha, cohort_sha):
    """Reject a foreign/unapproved adapter before any native server is started."""
    if not isinstance(proof, dict):
        raise ValueError("missing proof")
    if (proof.get("schema"), proof.get("evidence_scope")) != (
        "V13_RUN632_C3_LFM350_CPU_LORA_V1",
        "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW",
    ):
        raise ValueError("wrong native C3 proof schema/scope")
    b, a, m = (proof.get(k) or {} for k in ("binding", "adapter", "metrics"))
    if b.get("master_sha256") != MASTER_SHA or b.get("deployed_reference_sha256") != DEPLOYED_SHA:
        raise ValueError("master/deployed binding mismatch")
    if b.get("deployed_equivalence_proven") is not False:
        raise ValueError("source proof incorrectly promotes deployed parity")
    if proof.get("cohort_blob") != COHORT_BLOB or proof.get("cohort_sha256") != cohort_sha:
        raise ValueError("frozen cohort binding mismatch")
    if a.get("gguf_sha256") != adapter_sha or not isinstance(a.get("lora_b_nonzero"), int) or a["lora_b_nonzero"] <= 0:
        raise ValueError("adapter hash/nonzero LoRA-B missing")
    if not isinstance(a.get("gguf_tensors"), int) or a["gguf_tensors"] <= 0:
        raise ValueError("adapter GGUF tensor evidence missing")
    if m.get("steps") != 2 or m.get("jepa_weight") != 0 or m.get("anchor_weight") != 0:
        raise ValueError("optimizer/J-EPA ablation changed")
    if proof.get("negative_gates") != GATES or proof.get("production_weight_authority") != 0:
        raise ValueError("source proof negative gates/authority changed")
    if (proof.get("age_change") is not False or
            proof.get("body_jepa_proven") is not False or
            proof.get("deployed_qad_q4_parity_proven") is not False):
        raise ValueError("source proof wrongly promotes maturity/deployed parity")
    if proof.get("model_license") != "LFM Open License v1.0":
        raise ValueError("model license missing")
    return {"adapter_sha256": adapter_sha, "cohort_sha256": cohort_sha,
            "master_sha256": MASTER_SHA, "deployed_model_sha256": DEPLOYED_SHA}


def verify_inputs(master_dir, model, adapter, proof_path, cohort, license_path, server, server_sha):
    master_dir, model, adapter, cohort = map(Path, (master_dir, model, adapter, cohort))
    license_path, server = Path(license_path), Path(server)
    if git_blob(cohort) != COHORT_BLOB:
        raise ValueError("frozen V2 cohort bytes changed")
    if sha256(master_dir / "model.safetensors") != MASTER_SHA:
        raise ValueError("selected HF master mismatch")
    if sha256(master_dir / "chat_template.jinja") != TEMPLATE_SHA:
        raise ValueError("official Jinja template mismatch")
    if sha256(model) != DEPLOYED_SHA:
        raise ValueError("selected deployed QAD-Q4 model mismatch")
    if not server.is_absolute() or not server.is_file() or not os.access(server, os.X_OK):
        raise ValueError("native server must be absolute executable")
    if len(server_sha) != 64 or sha256(server) != server_sha:
        raise ValueError("pinned native server hash mismatch")
    proof = json.loads(Path(proof_path).read_text())
    binding = validate_proof(proof, sha256(adapter), sha256(cohort))
    if "LFM Open License v1.0" not in license_path.read_text()[:500]:
        raise ValueError("model license file missing")
    if sha256(license_path) != proof["binding"].get("license_sha256"):
        raise ValueError("license proof mismatch")
    a = P.gguf_header(adapter)
    P.gguf_header(model)
    if a["tensors"] != proof["adapter"]["gguf_tensors"]:
        raise ValueError("adapter GGUF header/proof tensor mismatch")
    return binding | {"license_sha256": sha256(license_path),
                      "server_sha256": server_sha, "template_sha256": TEMPLATE_SHA,
                      "adapter_tensors": a["tensors"]}


def format_chat(tok, question):
    if not isinstance(question, str) or not question or "<|im_" in question or "<|startoftext|>" in question:
        raise ValueError("untrusted question/template delimiter")
    prompt = tok.apply_chat_template(
        [{"role": "user", "content": question}], add_generation_prompt=True, tokenize=False)
    if not isinstance(prompt, str) or not prompt.startswith(tok.bos_token + "<|im_start|>user\n"):
        raise ValueError("official LFM2.5 chat prefix mismatch")
    if not prompt.endswith("<|im_start|>assistant\n"):
        raise ValueError("official LFM2.5 chat assistant suffix mismatch")
    return prompt


def aggregate(rows):
    """Exact predeclared 6-case acceptance, never semantic/STEP2 promotion."""
    if len(rows) != len(CASES):
        raise ValueError("incomplete frozen evaluation")
    parity = all(r["tokenizer_parity"] and r["base_vs_scale0"]["same_first_token"]
                 and r["base_vs_scale0"]["same_generated_text"]
                 and r["base_vs_scale0"]["shared_topk"] >= 1
                 and r["base_vs_scale0"]["max_abs_logprob_delta"] is not None
                 and r["base_vs_scale0"]["max_abs_logprob_delta"] <= 1e-4 for r in rows)
    effects = [r for r in rows if
               not r["scale0_vs_scale1"]["same_first_token"] or
               r["scale0_vs_scale1"]["max_abs_logprob_delta"] is not None and
               r["scale0_vs_scale1"]["max_abs_logprob_delta"] > 1e-5]
    groups = {}
    for group in ("train", "heldout", "near_miss"):
        sub = [r for r in rows if r["group"] == group]
        if len(sub) != 2:
            raise ValueError("frozen case group changed")
        groups[group] = {"base_hits": sum(bool(r["base_key_hit"]) for r in sub),
                         "candidate_hits": sum(bool(r["scale1_key_hit"]) for r in sub),
                         "count": len(sub)}
    gain = groups["train"]["candidate_hits"] > groups["train"]["base_hits"]
    retain = groups["heldout"]["candidate_hits"] >= groups["heldout"]["base_hits"]
    locality = groups["near_miss"]["candidate_hits"] <= groups["near_miss"]["base_hits"]
    bounded = bool(parity and effects and gain and retain and locality)
    return {"tokenizer_scale0_parity": parity, "scale1_numeric_effect": bool(effects),
            "groups": groups, "train_gain": gain, "heldout_nonregression": retain,
            "near_miss_nonleak": locality, "bounded_synthetic_utility": bounded,
            "status": "TOKEN_OR_SCALE0_PARITY_FAIL" if not parity else (
                "BOUNDED_SYNTHETIC_TRAIN_GAIN" if bounded else "NO_ANSWER_UTILITY")}


def run(master_dir, model, adapter, proof, cohort, license_path, server, server_sha, output):
    binding = verify_inputs(master_dir, model, adapter, proof, cohort, license_path, server, server_sha)
    from transformers import AutoTokenizer  # lazy; software tests require no native deps
    tok = AutoTokenizer.from_pretrained(str(master_dir))
    formatted = [(group, question, keys, format_chat(tok, question))
                 for group, question, keys in CASES]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    results = {}
    for label, lora in (("base", None), ("adapter", Path(adapter))):
        proc = None
        try:
            proc, base = P._start(Path(server), Path(model), lora,
                                  output / ("RUN636_%s_SERVER_RAW.log" % label.upper()))
            for group, question, keys, prompt in formatted:
                hf = tok(prompt, add_special_tokens=False)["input_ids"]
                native = P._json(base + "/tokenize", {"content": prompt, "add_special": False}, timeout=20)
                nt = native.get("tokens")
                if not isinstance(nt, list) or nt != hf:
                    raise ValueError("selected C3 HF/native tokenizer ID mismatch: " + question)
                row = results.setdefault(question, {})
                row[label + "_token_parity"] = True
                if label == "base":
                    row["base"] = C.sample(base, prompt)
                else:
                    row["scale0"] = C.sample(base, prompt, 0)
                    row["scale1"] = C.sample(base, prompt, 1)
        finally:
            if proc is not None:
                P._stop(proc)
    rows = []
    for group, question, keys, prompt in formatted:
        r = results[question]
        b, z, a = r["base"], r["scale0"], r["scale1"]
        p = P._compare(b, z)
        p["same_generated_text"] = b["text"] == z["text"]
        rows.append({"group": group, "question": question, "keys": list(keys),
                     "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                     "tokenizer_parity": r["base_token_parity"] and r["adapter_token_parity"],
                     "base_text": b["text"], "scale0_text": z["text"], "scale1_text": a["text"],
                     "base_key_hit": C.hit(b["text"], keys), "scale1_key_hit": C.hit(a["text"], keys),
                     "base_first_token": b["token_id"], "scale0_first_token": z["token_id"],
                     "scale1_first_token": a["token_id"],
                     "base_vs_scale0": p, "scale0_vs_scale1": P._compare(z, a),
                     "base_seconds": b["seconds"], "scale1_seconds": a["seconds"]})
    metrics = aggregate(rows)
    report = {"schema": "V13_RUN636_SELECTED_C3_QAD_Q4_NATIVE_V1",
              "evidence_scope": "LINUX_NATIVE_SELECTED_C3_QAD_Q4_SHADOW",
              "binding": binding, "rows": rows, "metrics": metrics,
              "model_license": "LFM Open License v1.0",
              "deployed_model_measured": True,
              "production_weight_authority": 0, "redmi_measured": False,
              "body_jepa_proven": False, "general_semantic_utility_proven": False,
              "negative_gates": dict(GATES)}
    (output / "RUN636_NATIVE_PROOF.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": metrics["status"],
                      "parity": metrics["tokenizer_scale0_parity"],
                      "synthetic_utility": metrics["bounded_synthetic_utility"]}))
    if not metrics["tokenizer_scale0_parity"]:
        raise RuntimeError("selected C3 token/scale0 parity failed; no utility inference")
    return report


def main():
    p = argparse.ArgumentParser()
    for name in ("master-dir", "model", "adapter", "proof", "cohort",
                 "license", "server", "server-sha", "output"):
        p.add_argument("--" + name, required=True)
    a = p.parse_args()
    run(a.master_dir, a.model, a.adapter, a.proof, a.cohort,
        a.license, a.server, a.server_sha, a.output)


if __name__ == "__main__":
    main()

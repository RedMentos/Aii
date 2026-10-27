#!/usr/bin/env python3
"""Run639: preregistered 32-step C3 KL-anchored FP32 LoRA; SHADOW only.

Run638 proved 32-step unanchored overfit (heldout 0/2, Cedar leak 2/2).
Run639 adds canonical KL-to-base anchoring on four disjoint prompts, never
on registered heldout or near-miss evaluation prompts. No production activation.
"""
import argparse
import json
import math
from pathlib import Path
import shutil

from scripts import run632_c3_lfm350_native as R

COHORT_BLOB = "ccec34634714b760b6cba6ce626536928f229ed3"
CONFIG = dict(R.CFG, max_steps=32, min_steps=32, anchor_weight=1.0)
GATES = dict(R.GATES)
NEAR_MISS = (
    ("In the fictional Cedar protocol, what is the marker color?", "violet"),
    ("In the fictional Cedar protocol, what is the gate number?", "83"),
)
ANCHORS = (
    "What is three plus three?",
    "Write a short farewell.",
    "In the fictional Birch protocol, what is the marker color?",
    "In the fictional Birch protocol, what is the gate number?",
)
BASELINE = {
    "run_id": 40431064922,
    "artifact_id": 12702091198,
    "zip_sha256": "d295a534aee3bb541b31fdfe760df1ec0b355ec0dd5642abbb949b198707b65c",
    "native_proof_sha256": "82b9073b9b955286c705b9ab506e49622c68745465b0a52b11213fdc9f72fd10",
    "train_proof_sha256": "f49ea0206e717c85b1018ea62204bdc8e876519e9c4f404f4ca21e9bb16b6d2e",
    "adapter_sha256": "bd5fb8e523ba5444602401911d7fc8e0b2a571980cc95bf1a42f15c2bfb1cb83",
}


def verify_cohort(path):
    raw = Path(path).read_bytes()
    if R.git_blob_sha(raw) != COHORT_BLOB:
        raise ValueError("Run639 prospective cohort blob changed")
    c = json.loads(raw)
    if c.get("schema") != "V13_RUN639_C3_32STEP_DOSE_RESPONSE_V1":
        raise ValueError("wrong cohort schema")
    if c.get("scope") != "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW":
        raise ValueError("not shadow-only")
    if c.get("master") != {
        "repo_id": "LiquidAI/LFM2.5-350M", "revision": R.MASTER_REV,
        "sha256": R.MASTER_SHA, "architecture": "lfm2",
        "license": "LFM Open License v1.0",
    }:
        raise ValueError("selected licensed master changed")
    if c.get("deployed_reference") != {
        "repo_id": "LiquidAI/LFM2.5-350M-GGUF",
        "revision": R.DEPLOYED_REV,
        "file": "LFM2.5-350M-QAD-Q4_0.gguf",
        "sha256": R.DEPLOYED_SHA, "equivalence_proven": False,
    }:
        raise ValueError("deployed QAD-Q4 binding changed")
    if c.get("config") != CONFIG:
        raise ValueError("treatment configuration/seed changed")
    if c.get("negative_gates") != GATES:
        raise ValueError("negative gates changed")
    if (c.get("production_weight_authority") != 0 or
            c.get("age_change") is not False or c.get("approval_change") is not False):
        raise ValueError("production authority/age/approval changed")
    if c.get("baseline") != BASELINE:
        raise ValueError("original 2-step comparator changed")
    def pairs(name):
        rows = c.get(name)
        if not isinstance(rows, list) or any(
                not isinstance(r, dict) or set(r) != {"prompt", "target"} or
                not isinstance(r["prompt"], str) or not isinstance(r["target"], str)
                for r in rows):
            raise ValueError("malformed " + name)
        return tuple((r["prompt"], r["target"]) for r in rows)
    if (pairs("train_rows"), pairs("heldout_rows"), pairs("near_miss_rows")) != (
            R.TRAIN, R.HELDOUT, NEAR_MISS):
        raise ValueError("registered source-disjoint rows changed")
    prompts = [p for name in ("train_rows", "heldout_rows", "near_miss_rows")
               for p, _ in pairs(name)]
    if len(set(prompts)) != len(prompts):
        raise ValueError("source overlap")
    if c.get("anchor_prompts") != list(ANCHORS):
        raise ValueError("registered disjoint anchor prompts changed")
    if set(ANCHORS) & set(prompts):
        raise ValueError("anchor evaluation/training leakage")
    if c.get("acceptance") != {
        "train_min_hits": 1, "heldout_min_hits": 1, "near_miss_max_hits": 0,
        "original_2step_floor": {"heldout_hits": 1, "near_miss_hits": 0},
    }:
        raise ValueError("anchored acceptance changed")
    return c


def verify_training_result(result):
    """Reject an incomplete/non-learning adapter without granting approval."""
    if not isinstance(result, dict) or not result.get("artifact") or not result.get("files"):
        raise ValueError("native LoRA adapter missing")
    m = result.get("metrics") or {}
    if (m.get("steps") != 32 or m.get("jepa_weight") != 0 or
            m.get("anchor_weight") != 1.0 or m.get("rank") != 2 or
            m.get("alpha") != 4 or m.get("targets") != ["v_proj", "out_proj"] or
            m.get("trainable_parameter_count", 0) <= 0):
        raise ValueError("training path/config mismatch")
    if not isinstance(m.get("loss_history"), list) or not m["loss_history"]:
        raise ValueError("missing optimizer history")
    if m["loss_history"][-1].get("step") != 32:
        raise ValueError("missing final optimizer step")
    for key in ("final_ce", "master_kl_to_base", "seconds", "peak_rss_mb"):
        value = m.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("missing/nonfinite training metric " + key)
    if m["final_ce"] < 0 or m["seconds"] <= 0 or m["peak_rss_mb"] <= 0:
        raise ValueError("invalid optimizer/host measurement")
    return m


def execute(cohort_path, master_dir, specs_path, output_dir):
    cohort = verify_cohort(cohort_path)
    binding = R.verify_master(master_dir, specs_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    from v13.lora_trainer import LoraTrainer
    items = [
        {"memory_id": "RUN639_C3_ALDER_%d" % i,
         "prompt": row["prompt"], "target": row["target"],
         "answer_keys": [row["target"]], "weight": 1.0,
         "kind": "human_correction"}
        for i, row in enumerate(cohort["train_rows"])
    ]
    probes = [{"prompt": row["prompt"], "expect": row["target"]}
              for row in cohort["heldout_rows"]]
    trainer = LoraTrainer(
        master_dir, output / "trainer-work", master_sha256=R.MASTER_SHA,
        anchors=tuple(cohort["anchor_prompts"]), probes=probes,
        cfg=dict(CONFIG), arch="lfm2")
    result = trainer.fit(items, base_generation="RUN639_C3_ANCHORED_32STEP_SHADOW")
    metrics = verify_training_result(result)
    files = result["files"]
    exported = R.verify_export(files["gguf"], files["safetensors"])
    if exported["lora_b_nonzero"] <= 0:
        raise ValueError("no trained LoRA-B")
    shutil.copyfile(files["gguf"], output / "RUN639_ADAPTER.gguf")
    shutil.copyfile(files["safetensors"], output / "RUN639_ADAPTER.safetensors")
    shutil.copyfile(Path(master_dir) / "LICENSE", output / "RUN639_LICENSE.txt")
    proof = {
        "schema": "V13_RUN639_C3_32STEP_NATIVE_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW",
        "binding": binding, "cohort_blob": COHORT_BLOB,
        "cohort_sha256": R.sha256(cohort_path),
        "baseline": BASELINE, "config": CONFIG,
        "anchor_prompts": list(ANCHORS),
        "train_rows": len(items), "heldout_rows": len(probes),
        "near_miss_rows": len(cohort["near_miss_rows"]),
        "metrics": metrics, "adapter": exported,
        "model_license": "LFM Open License v1.0",
        "deployed_qad_q4_parity_proven": False,
        "production_weight_authority": 0, "age_change": False,
        "approval_change": False, "body_jepa_proven": False,
        "redmi_measured": False, "negative_gates": GATES,
    }
    (output / "RUN639_TRAIN_PROOF.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": "32_STEP_FP32_ANCHORED_ADAPTER_EXPORTED_NOT_DEPLOYED",
        "steps": metrics["steps"], "final_ce": metrics["final_ce"],
        "master_recall": metrics["master_learned_recall"],
        "heldout_kl": metrics["master_kl_to_base"],
        "gguf_sha256": exported["gguf_sha256"],
    }, sort_keys=True))
    return proof


def main():
    parser = argparse.ArgumentParser()
    for name in ("cohort", "master-dir", "specs", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    execute(a.cohort, a.master_dir, a.specs, a.output)


if __name__ == "__main__":
    main()

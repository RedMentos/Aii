#!/usr/bin/env python3
"""Run638: preregistered 32-step selected C3 FP32 LoRA dose-response; SHADOW only.

Never edits Run632 cohort, trainer, selected models, or production registry.
The exact model/seed/train/heldout rows are unchanged; only 2 -> 32 steps.
"""
import argparse
import json
import math
from pathlib import Path
import shutil

from scripts import run632_c3_lfm350_native as R

COHORT_BLOB = "94c8558de44069b4e3baa351b6ca74e5e9f4ec9c"
CONFIG = dict(R.CFG, max_steps=32, min_steps=32)
GATES = dict(R.GATES)
NEAR_MISS = (
    ("In the fictional Cedar protocol, what is the marker color?", "violet"),
    ("In the fictional Cedar protocol, what is the gate number?", "83"),
)
BASELINE = {
    "run_id": 40429819193,
    "artifact_id": 12701134055,
    "proof_sha256": "b8b8a15a0215839fe2d94b62d055fcced3cbff4b4504b84ed21e1d511b1ca02c",
    "adapter_sha256": "3674e88f71855b46a1de59ca50642ec07c39bb3d6c86bd7e8a49eb1a031d8599",
}


def verify_cohort(path):
    raw = Path(path).read_bytes()
    if R.git_blob_sha(raw) != COHORT_BLOB:
        raise ValueError("Run638 prospective cohort blob changed")
    c = json.loads(raw)
    if c.get("schema") != "V13_RUN638_C3_32STEP_DOSE_RESPONSE_V1":
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
    return c


def verify_training_result(result):
    """Reject an incomplete/non-learning adapter without granting approval."""
    if not isinstance(result, dict) or not result.get("artifact") or not result.get("files"):
        raise ValueError("native LoRA adapter missing")
    m = result.get("metrics") or {}
    if (m.get("steps") != 32 or m.get("jepa_weight") != 0 or
            m.get("anchor_weight") != 0 or m.get("rank") != 2 or
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
        {"memory_id": "RUN638_C3_ALDER_%d" % i,
         "prompt": row["prompt"], "target": row["target"],
         "answer_keys": [row["target"]], "weight": 1.0,
         "kind": "human_correction"}
        for i, row in enumerate(cohort["train_rows"])
    ]
    probes = [{"prompt": row["prompt"], "expect": row["target"]}
              for row in cohort["heldout_rows"]]
    trainer = LoraTrainer(
        master_dir, output / "trainer-work", master_sha256=R.MASTER_SHA,
        anchors=(), probes=probes, cfg=dict(CONFIG), arch="lfm2")
    result = trainer.fit(items, base_generation="RUN638_C3_32STEP_SHADOW")
    metrics = verify_training_result(result)
    files = result["files"]
    exported = R.verify_export(files["gguf"], files["safetensors"])
    if exported["lora_b_nonzero"] <= 0:
        raise ValueError("no trained LoRA-B")
    shutil.copyfile(files["gguf"], output / "RUN638_ADAPTER.gguf")
    shutil.copyfile(files["safetensors"], output / "RUN638_ADAPTER.safetensors")
    shutil.copyfile(Path(master_dir) / "LICENSE", output / "RUN638_LICENSE.txt")
    proof = {
        "schema": "V13_RUN638_C3_32STEP_NATIVE_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW",
        "binding": binding, "cohort_blob": COHORT_BLOB,
        "cohort_sha256": R.sha256(cohort_path),
        "baseline": BASELINE, "config": CONFIG,
        "train_rows": len(items), "heldout_rows": len(probes),
        "near_miss_rows": len(cohort["near_miss_rows"]),
        "metrics": metrics, "adapter": exported,
        "model_license": "LFM Open License v1.0",
        "deployed_qad_q4_parity_proven": False,
        "production_weight_authority": 0, "age_change": False,
        "approval_change": False, "body_jepa_proven": False,
        "redmi_measured": False, "negative_gates": GATES,
    }
    (output / "RUN638_TRAIN_PROOF.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": "32_STEP_FP32_ADAPTER_EXPORTED_NOT_DEPLOYED",
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

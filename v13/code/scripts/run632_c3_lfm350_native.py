#!/usr/bin/env python3
"""Run632: actual selected C3 LFM2.5-350M master CPU LoRA shadow, never activated."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct

COHORT_BLOB = "c282077912ec4e284476825b3e03728620d8bad0"
MASTER_SHA = "1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e"
MASTER_REV = "b6248156b66a93e5c4581d82953a9df630c582ef"
DEPLOYED_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
DEPLOYED_REV = "657e078c94084481950a2d555a941481f715536b"
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL", "Body_JEPA": "UNAVAILABLE",
         "jepa_weight": 0, "V13": "INCOMPLETE"}
CFG = {"rank": 2, "alpha": 4, "targets": ["v_proj", "out_proj"], "lr": 0.001,
       "max_steps": 2, "min_steps": 2, "ckpt_every": 1, "anchor_weight": 0,
       "jepa_weight": 0, "threads": 2, "max_tokens": 96, "locality_swaps": 0, "seed": 13}
TRAIN = (("In the fictional Alder protocol, what is the marker color?", "violet"),
         ("In the fictional Alder protocol, what is the gate number?", "83"))
HELDOUT = (("What is two plus two?", "4"), ("Write a brief greeting.", "hello"))


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def verify_cohort(path):
    raw = Path(path).read_bytes()
    if git_blob_sha(raw) != COHORT_BLOB:
        raise ValueError("Run632 frozen V2 cohort Git blob mismatch")
    c = json.loads(raw)
    if c.get("schema") != "V13_RUN632_C3_LFM350_NATIVE_COHORT_V2" or c.get("supersedes_unexecuted") != "COHORT.json":
        raise ValueError("Run632 cohort schema/selection mismatch")
    master = c.get("master") or {}
    if (master.get("repo_id"), master.get("revision"), master.get("sha256"),
        master.get("architecture"), master.get("license")) != (
        "LiquidAI/LFM2.5-350M", MASTER_REV, MASTER_SHA, "lfm2", "LFM Open License v1.0"):
        raise ValueError("master provenance/architecture/license changed")
    d = c.get("deployed_reference") or {}
    if (d.get("repo_id"), d.get("revision"), d.get("sha256"), d.get("equivalence_proven")) != (
        "LiquidAI/LFM2.5-350M-GGUF", DEPLOYED_REV, DEPLOYED_SHA, False):
        raise ValueError("deployed GGUF identity/negative gate changed")
    if c.get("config") != CFG or c.get("negative_gates") != GATES:
        raise ValueError("training config/negative gates changed")
    if c.get("production_weight_authority") != 0 or c.get("age_change") is not False or c.get("approval_change") is not False:
        raise ValueError("authority or age/approval changed")
    train = c.get("train_rows") or []
    heldout = c.get("heldout_rows") or []
    if ([(r.get("prompt"), r.get("target")) for r in train] != list(TRAIN)
        or [(r.get("prompt"), r.get("target")) for r in heldout] != list(HELDOUT)):
        raise ValueError("registered train/heldout drift")
    if set(r["prompt"] for r in train) & set(r["prompt"] for r in heldout):
        raise ValueError("train/heldout leak")
    return c


def verify_master(master_dir, specs):
    master_dir = Path(master_dir)
    if sha256(master_dir / "model.safetensors") != MASTER_SHA:
        raise ValueError("official master safetensors SHA mismatch")
    cfg = json.loads((master_dir / "config.json").read_text())
    if cfg.get("model_type") != "lfm2" or cfg.get("num_hidden_layers") != 16:
        raise ValueError("LFM2 master architecture/layers mismatch")
    license_path = master_dir / "LICENSE"
    license_text = license_path.read_text()
    if "LFM Open License v1.0" not in license_text[:500]:
        raise ValueError("missing LFM Open License v1.0")
    spec = json.loads(Path(specs).read_text())["models"]["language"]
    if (spec.get("model_id"), spec.get("revision"), spec.get("files", [{}])[0].get("sha256")) != (
        "LiquidAI/LFM2.5-350M-GGUF", DEPLOYED_REV, DEPLOYED_SHA):
        raise ValueError("current selected C3 GGUF manifest drift")
    return {"master_sha256": MASTER_SHA, "master_revision": MASTER_REV,
            "master_bytes": (master_dir / "model.safetensors").stat().st_size,
            "license_sha256": sha256(license_path), "config_sha256": sha256(master_dir / "config.json"),
            "deployed_reference_sha256": DEPLOYED_SHA, "deployed_equivalence_proven": False}


def verify_export(adapter_path, peft_path):
    from safetensors.torch import load_file
    tensors = load_file(str(peft_path), device="cpu")
    b = [v for k, v in tensors.items() if "lora_B" in k]
    if not b:
        raise ValueError("no LoRA-B tensors")
    nonzero = sum(int((v != 0).sum()) for v in b)
    if nonzero <= 0:
        raise ValueError("LoRA-B weights remain all zero")
    with Path(adapter_path).open("rb") as f:
        h = f.read(24)
    if len(h) != 24 or h[:4] != b"GGUF":
        raise ValueError("invalid exported GGUF")
    version, n_tensors, _ = struct.unpack("<IQQ", h[4:])
    if version != 3 or n_tensors < 1:
        raise ValueError("invalid exported GGUF version/tensors")
    return {"gguf_sha256": sha256(adapter_path), "peft_sha256": sha256(peft_path),
            "gguf_bytes": Path(adapter_path).stat().st_size,
            "gguf_tensors": n_tensors, "lora_b_nonzero": nonzero,
            "lora_b_tensors": len(b)}


def execute(cohort_path, master_dir, specs_path, output_dir):
    cohort = verify_cohort(cohort_path)
    binding = verify_master(master_dir, specs_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    # No torch/PEFT import or optimizer before immutable source and license validation.
    from v13.lora_trainer import LoraTrainer
    items = [{"memory_id": "RUN632_C3_ALDER_%d" % i, "prompt": r["prompt"],
              "target": r["target"], "answer_keys": [r["target"]],
              "weight": 1.0, "kind": "human_correction"}
             for i, r in enumerate(cohort["train_rows"])]
    probes = [{"prompt": r["prompt"], "expect": r["target"]}
              for r in cohort["heldout_rows"]]
    trainer = LoraTrainer(master_dir, output / "trainer-work",
                          master_sha256=MASTER_SHA, anchors=(), probes=probes,
                          cfg=dict(CFG), arch="lfm2")
    result = trainer.fit(items, base_generation="RUN632_SELECTED_C3_MASTER_SHADOW")
    if not result.get("artifact") or not result.get("files"):
        raise RuntimeError("no native LoRA adapter export: %s" % result.get("metrics"))
    m = result["metrics"]
    if m.get("steps") != 2 or m.get("jepa_weight") != 0 or m.get("anchor_weight") != 0:
        raise RuntimeError("native optimizer steps/learning gates changed")
    files = result["files"]
    export = verify_export(files["gguf"], files["safetensors"])
    shutil.copyfile(files["gguf"], output / "RUN632_ADAPTER.gguf")
    shutil.copyfile(files["safetensors"], output / "RUN632_ADAPTER.safetensors")
    shutil.copyfile(Path(master_dir) / "LICENSE", output / "RUN632_LICENSE.txt")
    proof = {"schema": "V13_RUN632_C3_LFM350_CPU_LORA_V1",
             "evidence_scope": "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW",
             "binding": binding, "cohort_blob": COHORT_BLOB,
             "cohort_sha256": sha256(cohort_path),
             "train_rows": len(items), "heldout_rows": len(probes),
             "metrics": m, "adapter": export,
             "model_license": "LFM Open License v1.0",
             "deployed_qad_q4_parity_proven": False,
             "production_weight_authority": 0, "age_change": False,
             "body_jepa_proven": False, "negative_gates": dict(GATES)}
    (output / "RUN632_PROOF.json").write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"steps": m["steps"], "trainable": m["trainable_parameter_count"],
                      "nonzero_lora_b": export["lora_b_nonzero"],
                      "master_recall": m["master_learned_recall"],
                      "heldout_kl": m["master_kl_to_base"],
                      "gguf_sha256": export["gguf_sha256"]}, sort_keys=True))
    return proof


def main():
    p = argparse.ArgumentParser()
    for key in ("cohort", "master-dir", "specs", "output"):
        p.add_argument("--" + key, required=True, type=Path)
    a = p.parse_args()
    execute(a.cohort, a.master_dir, a.specs, a.output)


if __name__ == "__main__":
    main()

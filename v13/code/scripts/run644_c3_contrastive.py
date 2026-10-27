#!/usr/bin/env python3
"""Run644 candidate: four disjoint supervised protocol negatives, SHADOW only.

Same Run642 base-KL anchors and frozen Alder/Cedar evaluation. No Cedar
training/anchor leakage, no production LoraTrainer edit or weight authority.
"""
import argparse
import json
import shutil
from pathlib import Path

from scripts import run632_c3_lfm350_native as R
from scripts import run639_c3_kl_anchor as H
from scripts import run642_c3_protocol_locality as B

COHORT_BLOB = "c1b5a4c6b2ab22c0ad07996f114d05e69912a7cc"
CONFIG = dict(B.CONFIG)
NEGATIVE_PROTOCOLS = ("Spruce", "Willow")
CONTRASTIVE = tuple(
    {"prompt": "In the fictional %s protocol, what is the %s?" % (name, topic),
     "target": "not specified"}
    for name in NEGATIVE_PROTOCOLS for topic in ("marker color", "gate number")
)
BASELINE = {
    "run_id": 40437401540, "artifact_id": 12704852652,
    "zip_sha256": "cecf2bf0d725886c6e47f0d1d44f69582b43ca5f852dad128136d710fefc2d5c",
    "adapter_sha256": "29b1a14b77538bd14d05cfb7d53a9b7a43ba0b4065ef33d0b52bcbc28e47b163",
    "native_proof_sha256": "b39e8525690aafdd98cb5abf0bcf82df6eb500abaff0fd56fa41bf9dcd9fcd58",
    "train_proof_sha256": "40497ff90b77e919b9445959e6eb89fbd0ed075de66a409d0c1503954b7c3099",
    "source_cohort_blob": B.COHORT_BLOB,
    "historical_train_hits": 2, "historical_heldout_hits": 1,
    "historical_near_miss_leaks": 2,
    "historical_fulltext_baseline_parity": "5/6",
}
ACCEPTANCE = dict(B.ACCEPTANCE, report_contrastive_train_hits_separately=True)
ORIGINAL_COHORT = (
    Path(__file__).resolve().parents[1] /
    "docs/proofs/continuation-20261027/run642-c3-protocol-locality/COHORT.json"
)


def verify_cohort(path):
    raw = Path(path).read_bytes()
    if R.git_blob_sha(raw) != COHORT_BLOB:
        raise ValueError("Run644 prospective cohort bytes changed")
    c = json.loads(raw)
    old = B.verify_cohort(ORIGINAL_COHORT)
    for key in ("scope", "master", "deployed_reference", "train_rows",
                "heldout_rows", "near_miss_rows", "anchor_prompts",
                "locality_anchor_prompts", "negative_gates",
                "production_weight_authority", "age_change", "approval_change",
                "historical_run638", "config"):
        if c.get(key) != old.get(key):
            raise ValueError("Run644 changed original frozen " + key)
    if (c.get("schema") != "V13_RUN644_C3_DISJOINT_CONTRASTIVE_32STEP_V1"
            or c.get("baseline") != BASELINE
            or c.get("historical_run639") != old["baseline"]
            or c.get("contrastive_rows") != list(CONTRASTIVE)
            or c.get("acceptance") != ACCEPTANCE):
        raise ValueError("Run644 contrastive treatment/baseline/acceptance changed")
    positives = [row["prompt"] for row in c["train_rows"]]
    evaluation = [row["prompt"] for key in ("heldout_rows", "near_miss_rows")
                  for row in c[key]]
    negative = [row["prompt"] for row in c["contrastive_rows"]]
    anchors = c["anchor_prompts"] + c["locality_anchor_prompts"]
    all_prompts = positives + evaluation + negative + anchors
    if len(all_prompts) != len(set(all_prompts)):
        raise ValueError("Run644 training/evaluation overlap")
    if any("Cedar" in p for p in positives + negative + anchors):
        raise ValueError("Run644 Cedar evaluation leaked into training")
    return c


def locality_prompts(items, k):
    if len(items) != 6:
        raise ValueError("Run644 frozen six training rows changed")
    original = items[:2]
    contrastive = items[2:]
    if [(i["prompt"], i["target"]) for i in contrastive] != [
            (row["prompt"], row["target"]) for row in CONTRASTIVE]:
        raise ValueError("Run644 disjoint contrastive rows changed")
    return B.locality_prompts(original, k)


def verify_training_result(result):
    return B.verify_training_result(result)


def execute(cohort_path, master_dir, specs_path, output_dir):
    cohort = verify_cohort(cohort_path)
    binding = R.verify_master(master_dir, specs_path)
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    from v13.lora_trainer import LoraTrainer

    class ContrastiveTrainer(LoraTrainer):
        @staticmethod
        def locality_prompts(items, k):
            return locality_prompts(items, k)

    rows = cohort["train_rows"] + cohort["contrastive_rows"]
    items = [
        {"memory_id": "RUN644_C3_%02d" % i, "prompt": row["prompt"],
         "target": row["target"], "answer_keys": [row["target"]],
         "weight": 1.0, "kind": "human_correction"}
        for i, row in enumerate(rows)
    ]
    probes = [{"prompt": row["prompt"], "expect": row["target"]}
              for row in cohort["heldout_rows"]]
    trainer = ContrastiveTrainer(
        master_dir, output / "trainer-work", master_sha256=R.MASTER_SHA,
        anchors=tuple(cohort["anchor_prompts"]), probes=probes,
        cfg=dict(CONFIG), arch="lfm2")
    result = trainer.fit(items, base_generation="RUN644_C3_CONTRASTIVE_SHADOW")
    metrics = verify_training_result(result)
    exported = R.verify_export(result["files"]["gguf"], result["files"]["safetensors"])
    if exported["lora_b_nonzero"] <= 0:
        raise ValueError("Run644 adapter did not learn")
    shutil.copyfile(result["files"]["gguf"], output / "RUN644_ADAPTER.gguf")
    shutil.copyfile(result["files"]["safetensors"], output / "RUN644_ADAPTER.safetensors")
    shutil.copyfile(Path(master_dir) / "LICENSE", output / "RUN644_LICENSE.txt")
    proof = {
        "schema": "V13_RUN644_C3_DISJOINT_CONTRASTIVE_NATIVE_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW",
        "binding": binding, "cohort_blob": COHORT_BLOB,
        "cohort_sha256": R.sha256(cohort_path),
        "historical_run642": BASELINE, "historical_run639": B.BASELINE,
        "historical_run638": H.BASELINE,
        "config": CONFIG, "anchor_prompts": list(H.ANCHORS),
        "locality_anchor_prompts": list(B.LOCALITY_ANCHORS),
        "contrastive_rows": list(CONTRASTIVE),
        "train_rows": len(items), "heldout_rows": len(probes),
        "near_miss_rows": len(cohort["near_miss_rows"]),
        "metrics": metrics, "adapter": exported,
        "model_license": "LFM Open License v1.0",
        "deployed_qad_q4_parity_proven": False,
        "production_weight_authority": 0, "age_change": False,
        "approval_change": False, "body_jepa_proven": False,
        "redmi_measured": False, "negative_gates": H.GATES,
    }
    (output / "RUN644_TRAIN_PROOF.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": "RUN644_FP32_DISJOINT_CONTRASTIVE_EXPORTED_NOT_DEPLOYED",
        "steps": metrics["steps"], "master_recall": metrics["master_learned_recall"],
        "master_kl": metrics["master_kl_to_base"],
        "adapter_sha256": exported["gguf_sha256"],
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

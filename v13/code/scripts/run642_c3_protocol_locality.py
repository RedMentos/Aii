#!/usr/bin/env python3
"""Run642: source-bound selected C3 protocol-locality KL candidate, SHADOW only.

One change from Run639: four base-KL prompts with Alder replaced by Pine/Maple.
No evaluation Cedar prompts, labels or target answers enter locality anchors.
Existing production LoraTrainer remains unchanged.
"""
import argparse
import json
import shutil
from pathlib import Path

from scripts import run632_c3_lfm350_native as R
from scripts import run639_c3_kl_anchor as B

COHORT_BLOB = "249d4be0e0663cccf5d1165347fa37c0db924791"
CONFIG = dict(B.CONFIG, locality_swaps=2)
PROTOCOLS = ("Pine", "Maple")
LOCALITY_ANCHORS = tuple(
    prompt.replace("Alder", protocol)
    for prompt, _ in R.TRAIN for protocol in PROTOCOLS
)
BASELINE = {
    "run_id": 40431900872, "artifact_id": 12701744750,
    "zip_sha256": "fab8c74d416303a871e777d7e56cd7211b527d1fd25c7182ad74768bb1270506",
    "adapter_sha256": "04b5ef3b432f82985c163e701ee536ecbeaaf05ec1d96ab0b0da0130f2c061c6",
    "native_proof_sha256": "788b4681a7234593a1b305e41320bfc4b0bfb9a038bd13f448ecadf6dafffdf6",
    "train_proof_sha256": "28a04c4baa7821e504f94e06b0b8a9862edb35250ea30ac45f7942fb9d6a283d",
    "source_cohort_blob": B.COHORT_BLOB,
    "historical_train_hits": 2, "historical_heldout_hits": 1,
    "historical_near_miss_leaks": 2,
    "historical_fulltext_baseline_parity": "5/6",
}
ACCEPTANCE = {
    "train_min_hits": 1, "heldout_min_hits": 1, "near_miss_max_hits": 0,
    "require_tokenizer_parity": True, "require_scale0_base_parity": True,
    "require_numeric_adapter_effect": True,
    "report_historical_run639_fulltext_baseline_parity_separately": True,
}
ORIGINAL_COHORT = (
    Path(__file__).resolve().parents[1] /
    "docs/proofs/continuation-20261027/run639-c3-kl-anchor/COHORT.json"
)


def verify_cohort(path):
    raw = Path(path).read_bytes()
    if R.git_blob_sha(raw) != COHORT_BLOB:
        raise ValueError("Run642 prospective cohort bytes changed")
    c = json.loads(raw)
    original = B.verify_cohort(ORIGINAL_COHORT)
    for key in ("scope", "master", "deployed_reference", "train_rows",
                "heldout_rows", "near_miss_rows", "anchor_prompts",
                "negative_gates", "production_weight_authority",
                "age_change", "approval_change"):
        if c.get(key) != original.get(key):
            raise ValueError("Run642 changed original frozen " + key)
    if (c.get("schema") != "V13_RUN642_C3_PROTOCOL_LOCALITY_32STEP_V1"
            or c.get("config") != CONFIG
            or c.get("historical_run638") != B.BASELINE
            or c.get("baseline") != BASELINE
            or c.get("acceptance") != ACCEPTANCE
            or c.get("locality_anchor_prompts") != list(LOCALITY_ANCHORS)):
        raise ValueError("Run642 treatment/baseline/acceptance changed")
    all_prompts = ([r["prompt"] for name in
                    ("train_rows", "heldout_rows", "near_miss_rows")
                    for r in c[name]]
                   + c["anchor_prompts"] + c["locality_anchor_prompts"])
    if len(all_prompts) != len(set(all_prompts)):
        raise ValueError("Run642 locality/evaluation overlap")
    if any("Cedar" in p for p in c["locality_anchor_prompts"]):
        raise ValueError("Run642 Cedar evaluation leaked to anchors")
    return c


def locality_prompts(items, k):
    """Generate exactly the preregistered disjoint protocol swaps, no labels."""
    if k != 2 or [(i["prompt"], i["target"]) for i in items] != list(R.TRAIN):
        raise ValueError("Run642 frozen locality training inputs changed")
    result = [i["prompt"].replace("Alder", protocol)
              for i in items for protocol in PROTOCOLS]
    if tuple(result) != LOCALITY_ANCHORS:
        raise ValueError("Run642 locality generation changed")
    return result


def verify_training_result(result):
    return B.verify_training_result(result)


def execute(cohort_path, master_dir, specs_path, output_dir):
    cohort = verify_cohort(cohort_path)
    binding = R.verify_master(master_dir, specs_path)
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    from v13.lora_trainer import LoraTrainer

    class LocalityTrainer(LoraTrainer):
        @staticmethod
        def locality_prompts(items, k):
            return locality_prompts(items, k)

    items = [
        {"memory_id": "RUN642_C3_ALDER_%d" % i, "prompt": row["prompt"],
         "target": row["target"], "answer_keys": [row["target"]],
         "weight": 1.0, "kind": "human_correction"}
        for i, row in enumerate(cohort["train_rows"])
    ]
    probes = [{"prompt": row["prompt"], "expect": row["target"]}
              for row in cohort["heldout_rows"]]
    trainer = LocalityTrainer(
        master_dir, output / "trainer-work", master_sha256=R.MASTER_SHA,
        anchors=tuple(cohort["anchor_prompts"]), probes=probes,
        cfg=dict(CONFIG), arch="lfm2")
    result = trainer.fit(items, base_generation="RUN642_C3_PROTOCOL_LOCALITY_SHADOW")
    metrics = verify_training_result(result)
    exported = R.verify_export(result["files"]["gguf"], result["files"]["safetensors"])
    if exported["lora_b_nonzero"] <= 0:
        raise ValueError("Run642 adapter did not learn")
    shutil.copyfile(result["files"]["gguf"], output / "RUN642_ADAPTER.gguf")
    shutil.copyfile(result["files"]["safetensors"], output / "RUN642_ADAPTER.safetensors")
    shutil.copyfile(Path(master_dir) / "LICENSE", output / "RUN642_LICENSE.txt")
    proof = {
        "schema": "V13_RUN642_C3_PROTOCOL_LOCALITY_NATIVE_V1",
        "evidence_scope": "LINUX_NATIVE_SELECTED_C3_MASTER_LORA_SHADOW",
        "binding": binding, "cohort_blob": COHORT_BLOB,
        "cohort_sha256": R.sha256(cohort_path),
        "historical_run639": BASELINE,
        "historical_run638": B.BASELINE,
        "config": CONFIG, "anchor_prompts": list(B.ANCHORS),
        "locality_anchor_prompts": list(LOCALITY_ANCHORS),
        "train_rows": len(items), "heldout_rows": len(probes),
        "near_miss_rows": len(cohort["near_miss_rows"]),
        "metrics": metrics, "adapter": exported,
        "model_license": "LFM Open License v1.0",
        "deployed_qad_q4_parity_proven": False,
        "production_weight_authority": 0, "age_change": False,
        "approval_change": False, "body_jepa_proven": False,
        "redmi_measured": False, "negative_gates": B.GATES,
    }
    (output / "RUN642_TRAIN_PROOF.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": "RUN642_FP32_PROTOCOL_LOCALITY_EXPORTED_NOT_DEPLOYED",
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

#!/usr/bin/env python3
"""BP1 pinned QAD C3 train-only LoRA SHADOW candidate; heldout is never read here."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from scripts import bp1_qad_native_smoke as N
from scripts import bp1_qad_token_budget as B

SCHEMA = "V13_BP1_QAD_C3_TRAIN_ONLY_SHADOW_V1"
MANIFEST_SCHEMA = "V13_BP1_C3_CONSUMER_DATASET_PREFLIGHT_V1"
TRAIN_SHA = B.TRAIN_SHA
MANIFEST_TRAIN_SHA = TRAIN_SHA
TRAINER_GIT_BLOB = "49a752879ae5d19391963742a0f042e740edb2cc"
TRAIN_PROJECTS = (
    "the warehouse migration", "the clinic booking app",
    "the river cleanup", "the school library refit",
)
HELDOUT_PROJECTS = ("the solar roof pilot", "the bakery expansion")
CFG = {
    "rank": 2, "alpha": 4, "targets": ["v_proj", "out_proj"],
    "lr": 0.001, "max_steps": 2, "min_steps": 2, "ckpt_every": 1,
    "anchor_weight": 0, "jepa_weight": 0, "threads": 4,
    "max_tokens": 1024, "locality_swaps": 0, "seed": N.SEED,
}
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL",
         "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0, "V13": "INCOMPLETE"}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob(path):
    raw = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("duplicate JSON key " + key)
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs)


def validate_manifest(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("invalid BP1 dataset manifest")
    expected = {
        "schema": MANIFEST_SCHEMA,
        "scope": "LINUX_NATIVE_B2_INPUT_SOFTWARE_DATASET_ONLY",
        "source_report_sha256": "ea379b52c7b95c2bb30cd6725f539f443521a64210fdf6bf6fa726c413126880",
        "source_corpus_sha256": "1872a3adf6e51e05e604053539d50ae05c955b221f78f0cce39c0703f8cf",
        "b2_model_sha256": "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf",
        "train_projects": list(TRAIN_PROJECTS),
        "heldout_projects": list(HELDOUT_PROJECTS),
        "train_rows": 25, "heldout_rows": 22, "heldout_pairs": 11,
        "dropped_invalid_b2_quotes": 10,
        "files_sha256": {
            "train_offer.jsonl": TRAIN_SHA,
            "heldout_paired.jsonl": "7238a0220255cbccbcf1f9ccfad8dc03febfc37f7bc1d9d0aa645618f006508c",
            "diagnostics.jsonl": "d120463497e722b10ee5f7d5b5065fe8f84140b819182fe169a1ab9e32d813cb",
        },
        "production_weight_authority": 0,
        "native_c3_training_executed": False,
        "redmi_measured": False,
        "gates": GATES,
    }
    # Type-strict canonical serialization avoids True == 1 in safety gates.
    if json.dumps(manifest, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise ValueError("BP1 immutable dataset manifest mismatch")
    return manifest


def validate_train(rows):
    if not isinstance(rows, list) or len(rows) != 25:
        raise ValueError("BP1 train-only row count mismatch")
    ids = set()
    projects = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "answer_keys", "arm", "kind", "prompt", "question", "row_id",
            "source_project", "source_sha256", "target",
        }:
            raise ValueError("BP1 train row fields mismatch")
        rid = row["row_id"]
        if not isinstance(rid, str) or not rid.startswith("RUN181-") or rid in ids:
            raise ValueError("BP1 duplicate or invalid row id")
        ids.add(rid)
        project = row["source_project"]
        if project not in TRAIN_PROJECTS:
            raise ValueError("BP1 heldout project or unknown project in training")
        projects.add(project)
        if row["arm"] != "offer" or row["kind"] != "synthetic":
            raise ValueError("BP1 training arm/kind changed")
        if (not isinstance(row["prompt"], str) or not row["prompt"] or
                not isinstance(row["question"], str) or
                row["question"] not in row["prompt"] or
                not isinstance(row["source_sha256"], str) or
                len(row["source_sha256"]) != 64):
            raise ValueError("BP1 malformed training source")
        if not isinstance(row["answer_keys"], list) or len(row["answer_keys"]) != 1:
            raise ValueError("BP1 training key count mismatch")
        target = strict_json(row["target"])
        if (not isinstance(target, dict) or set(target) !=
                {"answer", "evidence_quote", "uncertainty"} or
                target["answer"] != row["answer_keys"][0] or
                not isinstance(target["evidence_quote"], str) or
                not target["evidence_quote"] or
                target["evidence_quote"] not in row["prompt"] or
                target["uncertainty"] != ""):
            raise ValueError("BP1 unsupported train target")
    if projects != set(TRAIN_PROJECTS):
        raise ValueError("BP1 train projects missing")
    return rows


def load_inputs(train_path, manifest_path):
    manifest = validate_manifest(strict_json(Path(manifest_path).read_text()))
    rows, original_sha = B.load_train(train_path)
    validate_train(rows)
    if original_sha != TRAIN_SHA or sha(train_path) != TRAIN_SHA:
        raise ValueError("BP1 original train bytes changed")
    return rows, manifest


def verify_master(master_dir):
    root = Path(master_dir)
    master = root / "model.safetensors"
    if not master.is_file() or sha(master) != N.MASTER_SHA:
        raise ValueError("QAD FP32 master SHA mismatch")
    cfg = strict_json((root / "config.json").read_text())
    if cfg.get("model_type") != "lfm2" or cfg.get("num_hidden_layers") != 16:
        raise ValueError("QAD master architecture mismatch")
    license_text = (root / "LICENSE").read_text()
    if "LFM Open License v1.0" not in license_text[:500]:
        raise ValueError("QAD source license missing")
    trainer_file = Path(__file__).resolve().parents[1] / "v13" / "lora_trainer.py"
    if git_blob(trainer_file) != TRAINER_GIT_BLOB:
        raise ValueError("unreviewed LoRA trainer source revision")
    return {"revision": N.REVISION, "master_sha256": N.MASTER_SHA,
            "master_bytes": master.stat().st_size,
            "license_sha256": sha(root / "LICENSE"),
            "trainer_git_blob": TRAINER_GIT_BLOB}


def verify_prompt_budget(rows, tokenizer):
    audit = B.audit(rows, tokenizer)
    if (audit["summary"]["1024"]["truncated_rows"] != 0 or
            audit["summary"]["1024"]["target_truncated_rows"] != 0 or
            audit["max_total_tokens"] > 1024):
        raise ValueError("BP1 1024-token prompt/target truncation")
    return {"max_total_tokens": audit["max_total_tokens"],
            "mean_total_tokens": audit["mean_total_tokens"],
            "all_train_prompts_preserved": True}


def verify_smoke_receipt(receipt):
    """Operator-audited raw native run prerequisite; JSON alone is not native proof."""
    if not isinstance(receipt, dict) or receipt.get("schema") != "V13_BP1_QAD_NATIVE_AUDIT_RECEIPT_V1":
        raise ValueError("missing native smoke audit receipt")
    if (receipt.get("status") != "PASS_CLOSED_RAW" or
            receipt.get("model_revision") != N.REVISION or
            receipt.get("hf_master_sha256") != N.MASTER_SHA or
            receipt.get("gguf_sha256") != N.GGUF_SHA or
            receipt.get("source_commit") != "fb7b440a319817a5665fabb4fb2d1ad60de62c4a"):
        raise ValueError("native smoke receipt source/model mismatch")
    exits = receipt.get("exits")
    required = ("BUDGET", "VENV", "PIP_TORCH", "PIP_HF", "HF_FETCH", "MASTER_SHA",
                "GGUF_SHA", "RUNNER_FETCH", "HF_NATIVE", "GGUF_NATIVE", "COMPARE")
    if not isinstance(exits, dict) or set(exits) != set(required) or any(type(exits[k]) is not int or exits[k] != 0 for k in required):
        raise ValueError("native smoke receipt exit codes not all zero")
    digest = receipt.get("raw_zip_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("native smoke raw ZIP digest missing")
    if receipt.get("independently_crc_head_hash_verified") is not True:
        raise ValueError("native smoke original raw not independently audited")
    return receipt


def verify_training(result):
    from scripts import run632_c3_lfm350_native as R
    if not isinstance(result, dict) or not result.get("artifact") or not result.get("files"):
        raise ValueError("QAD LoRA adapter not exported")
    m = result.get("metrics") or {}
    if (m.get("steps") != 2 or m.get("rank") != 2 or m.get("alpha") != 4 or
            m.get("targets") != CFG["targets"] or m.get("jepa_weight") != 0 or
            m.get("anchor_weight") != 0 or m.get("trainable_parameter_count", 0) <= 0):
        raise ValueError("QAD optimizer/authority drift")
    if (not isinstance(m.get("final_ce"), (int, float)) or
            not math.isfinite(m["final_ce"]) or m["final_ce"] < 0):
        raise ValueError("QAD nonfinite final CE")
    exported = R.verify_export(result["files"]["gguf"], result["files"]["safetensors"])
    if exported["lora_b_nonzero"] <= 0:
        raise ValueError("QAD LoRA-B did not update")
    return m, exported


def execute(train_path, manifest_path, master_dir, out_dir, *, mode, smoke_receipt=None):
    if mode not in ("preflight", "train"):
        raise ValueError("unsupported BP1 mode")
    rows, manifest = load_inputs(train_path, manifest_path)
    master = verify_master(master_dir)
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(master_dir), local_files_only=True, trust_remote_code=False)
    budget = verify_prompt_budget(rows, tokenizer)
    if mode == "train":
        if smoke_receipt is None:
            raise ValueError("native smoke audit receipt required before QAD training")
        receipt = verify_smoke_receipt(strict_json(Path(smoke_receipt).read_text()))
    else:
        receipt = None
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    result = {"schema": SCHEMA, "mode": mode, "status": "SOURCE_BOUND_PREFLIGHT_ONLY",
              "train_sha256": TRAIN_SHA, "manifest_sha256": sha(manifest_path),
              "master": master, "token_budget": budget, "config": CFG,
              "train_rows": len(rows), "heldout_files_opened": False,
              "native_training_executed": False, "production_weight_authority": 0,
              "redmi_measured": False, "gates": GATES}
    if mode == "train":
        from v13.lora_trainer import LoraTrainer
        class GuardedTrainer(LoraTrainer):
            def _encode(self, tok, prompt, target=None):
                if target is not None:
                    rendered = tok.apply_chat_template(
                        [{"role": "user", "content": prompt}],
                        add_generation_prompt=True, tokenize=False)
                    pid = tok(rendered, add_special_tokens=False)["input_ids"]
                    tid = tok(str(target) + "<|im_end|>", add_special_tokens=False)["input_ids"]
                    if not pid or not tid or len(pid) + len(tid) > CFG["max_tokens"]:
                        raise ValueError("QAD training prompt/target would be truncated")
                return super()._encode(tok, prompt, target)
        items = [{"memory_id": row["row_id"], "prompt": row["prompt"],
                  "target": row["target"], "answer_keys": row["answer_keys"],
                  "kind": "synthetic", "weight": 1.0} for row in rows]
        trainer = GuardedTrainer(master_dir, out / "trainer-work", master_sha256=N.MASTER_SHA,
                                 anchors=(), probes=(), cfg=dict(CFG), arch="lfm2")
        trained = trainer.fit(items, base_generation="BP1_QAD_C3_TRAIN_ONLY_SHADOW")
        metrics, exported = verify_training(trained)
        result.update({"status": "TRAINED_SHADOW_ADAPTER_NOT_DEPLOYED",
                       "native_training_executed": True,
                       "smoke_receipt_sha256": sha(smoke_receipt),
                       "metrics": metrics, "adapter": exported,
                       "model_utility_proven": False})
    with (out / "BP1_QAD_TRAIN_PROOF.json").open("xb") as stream:
        stream.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "train"), default="preflight")
    parser.add_argument("--train", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--master-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--smoke-receipt")
    args = parser.parse_args()
    result = execute(args.train, args.manifest, args.master_dir, args.out,
                     mode=args.mode, smoke_receipt=args.smoke_receipt)
    print(json.dumps({"status": result["status"], "rows": result["train_rows"],
                      "native_training_executed": result["native_training_executed"],
                      "heldout_files_opened": False}, sort_keys=True))


if __name__ == "__main__":
    main()

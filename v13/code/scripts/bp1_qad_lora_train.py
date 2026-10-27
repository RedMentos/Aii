#!/usr/bin/env python3
"""BP1 C3 QAD FP32 train-only LoRA driver. Never activates adapters or reads heldout labels."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from scripts import bp1_qad_token_budget as B
from scripts import bp1_paired_score as S

MASTER_SHA = B.QAD_MASTER_SHA
TRAIN_SHA = B.TRAIN_SHA
TOKEN_AUDIT_SHA = "d6c67a1de8df4d056c674a2195f86a31c97636385f8cf37061b33c544e38ac40"
TOKENIZER_SHA = "df1d8d5ec5d091b460562ffd545e4a5e91d17d4a0db7ebe733be34ed374377bd"
TEMPLATE_SHA = "ba551d58630afa3190b1be3602e28301f3d2e9bbac978dfc49d6d825171648b6"
ANCHORS = (
    "What is 2 + 2?",
    "Explain what a calendar is in one sentence.",
    "What is the color of a clear daytime sky?",
    "Give a short definition of a library.",
)
PROBES = (
    {"prompt": "What is 3 + 4?", "expect": ["7"], "unseen": True},
    {"prompt": "What is water?", "expect": ["water"], "unseen": True},
    {"prompt": "What is a book?", "expect": ["book"], "unseen": True},
    {"prompt": "What is a triangle?", "expect": ["three"], "unseen": True},
)
CFG = {"rank": 4, "alpha": 8.0, "lr": 0.0001, "max_steps": 2, "min_steps": 2,
       "target_loss": 0.0, "anchor_weight": 0.2, "anchors_per_step": 2,
       "jepa_weight": 0.0, "weight_decay": 0.0, "ckpt_every": 1,
       "locality_swaps": 0, "seed": 13, "threads": 4, "max_tokens": 1024}
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL", "Body_JEPA": "UNAVAILABLE",
         "jepa_weight": 0, "Redmi_measured": False,
         "adapter_approved": False, "adapter_activated": False,
         "V13_complete": False}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_audit(report):
    if not isinstance(report, dict) or report.get("schema") != B.SCHEMA:
        raise ValueError("invalid official QAD train token audit")
    if report.get("train_sha256") != TRAIN_SHA or report.get("source_revision") != B.REVISION:
        raise ValueError("train source or tokenizer revision mismatch")
    if report.get("heldout_targets_used") is not False or report.get("native_c3_training_executed") is not False:
        raise ValueError("invalid audit provenance")
    if report.get("max_total_tokens", 100000) > CFG["max_tokens"] or report.get("summary", {}).get("1024", {}).get("truncated_rows") != 0:
        raise ValueError("BP1 1024-token train overflow")
    files = report.get("tokenizer_files_sha256", {})
    if files.get("tokenizer.json") != TOKENIZER_SHA or files.get("chat_template.jinja") != TEMPLATE_SHA:
        raise ValueError("official QAD tokenizer/template hash mismatch")
    if report.get("qad_master_sha256_metadata_only") != MASTER_SHA:
        raise ValueError("QAD source master metadata mismatch")
    return True


def make_items(rows):
    items = []
    for row in rows:
        if row["arm"] != "offer" or not row["target"] or not row["prompt"]:
            raise ValueError("invalid train-only offer row")
        items.append({"memory_id": row["row_id"], "kind": "bp1_c3_consumer",
                      "prompt": row["prompt"], "target": row["target"],
                      "answer_keys": row["answer_keys"]})
    if len(items) != 25 or len({i["memory_id"] for i in items}) != 25:
        raise ValueError("incomplete BP1 training batch")
    return items


def run(train_path, token_audit_path, model_dir, out, *, owner_confirmed=False,
        execute_native=False, trainer_factory=None):
    rows, train_sha = B.load_train(train_path)
    report_raw = Path(token_audit_path).read_bytes()
    if hashlib.sha256(report_raw).hexdigest() != TOKEN_AUDIT_SHA:
        raise ValueError("original closed QAD token audit bytes mismatch")
    report = S.parse_json(report_raw.decode("utf-8"))
    validate_audit(report)
    items = make_items(rows)
    model_dir = Path(model_dir)
    if not (model_dir / "model.safetensors").is_file():
        raise ValueError("QAD FP32 source master absent")
    if sha(model_dir / "model.safetensors") != MASTER_SHA:
        raise ValueError("QAD FP32 source master SHA mismatch")
    for name, expected in (("tokenizer.json", TOKENIZER_SHA), ("chat_template.jinja", TEMPLATE_SHA)):
        if sha(model_dir / name) != expected:
            raise ValueError("QAD tokenizer/template source SHA mismatch")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    prereq = {"schema": "V13_BP1_C3_QAD_LORA_TRAIN_RECEIPT_V1",
              "source_train_sha256": train_sha, "token_audit_sha256": hashlib.sha256(report_raw).hexdigest(),
              "source_master_sha256": MASTER_SHA, "source_revision": B.REVISION,
              "tokenizer_sha256": TOKENIZER_SHA, "template_sha256": TEMPLATE_SHA,
              "train_rows": len(items), "heldout_targets_used": False,
              "cfg": CFG, "anchors": list(ANCHORS), "probes": PROBES,
              "adapter_approval_authority": 0, "gates": GATES}
    S.exclusive(out / "PREFLIGHT.json", (json.dumps(prereq, indent=2, sort_keys=True) + "\n").encode())
    if not execute_native:
        return dict(prereq, status="PREFLIGHT_ONLY_NO_OPTIMIZER", native_c3_training_executed=False)
    if not owner_confirmed:
        raise PermissionError("native LoRA requires explicit serial owner confirmation")
    if trainer_factory is None:
        from v13.lora_trainer import LoraTrainer
        trainer_factory = LoraTrainer
    started = time.monotonic()
    try:
        trainer = trainer_factory(model_dir, out / "train", master_sha256=MASTER_SHA,
                                  anchors=ANCHORS, probes=PROBES, cfg=CFG)
        result = trainer.fit(items, base_generation="BP1_QAD_FP32_PREREG_20261027")
        artifact = result.get("artifact") if isinstance(result, dict) else None
        if not artifact or not Path(artifact).is_file() or sha(artifact) != result.get("hash"):
            raise ValueError("native LoRA did not produce hash-bound adapter GGUF")
        receipt = dict(prereq, status="NATIVE_LORA_UNAPPROVED_UNEVALUATED",
                       native_c3_training_executed=True, adapter_sha256=result["hash"],
                       adapter_path=str(artifact), training_seconds=round(time.monotonic()-started, 2),
                       trainer_metrics=result.get("metrics", {}),
                       adapter_approved=False, adapter_activated=False)
        S.exclusive(out / "TRAIN_RECEIPT.json",
                    (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
        return receipt
    except Exception as exc:
        S.exclusive(out / "FAILED.json",
                    (json.dumps({"error_type":type(exc).__name__, "error":str(exc)[:2000],
                                 "training_may_have_started":True, "adapter_activated":False,
                                 "gates":GATES}, indent=2, sort_keys=True)+"\n").encode())
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--train", required=True)
    p.add_argument("--token-audit", required=True)
    p.add_argument("--model-dir", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--execute-native", action="store_true")
    p.add_argument("--serial-owner-confirmed", action="store_true")
    a = p.parse_args()
    result = run(a.train, a.token_audit, a.model_dir, a.out,
                 execute_native=a.execute_native, owner_confirmed=a.serial_owner_confirmed)
    print(json.dumps({"status": result["status"], "train_rows": result["train_rows"],
                      "adapter_activated": False, "heldout_targets_used": False}, sort_keys=True))


if __name__ == "__main__":
    main()

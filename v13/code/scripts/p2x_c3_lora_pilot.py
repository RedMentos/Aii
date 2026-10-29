#!/usr/bin/env python3
"""Default-off, disposable P2X eight-example C3 QAD FP32 LoRA pilot; AG6 never activates."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import time

FIXTURE_SHA = "cd3edfdb464c6f99650b1ea32b5b09854268f0b53faa79df22ddcd135f21985a"
EXPORT_SHA = {
    "train.jsonl": "af191c087d872a42924f2d2d465a3f26f6c323bf48c5c0682b30094b9d666cf1",
    "validation_inputs.jsonl": "a7f2d70d463305a43ec03bbd758a61cc91129a411094ed60e5503d4ffe0894cf",
    "validation_answers.jsonl": "d1cbe570ae3caa2a80177f861ba5751c93208ffccc98f8d12d90578c59555e9a",
}
MASTER_SHA = {
    "model.safetensors": "1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079",
    "config.json": "884c7b2b936f296dd448bfca18a14fd9bc903be7d3bff1303ac62bbb43f641d6",
    "tokenizer.json": "df1d8d5ec5d091b460562ffd545e4a5e91d17d4a0db7ebe733be34ed374377bd",
    "tokenizer_config.json": "b99856c5bdc9f88cc30a7ffff78bfc7768427e0b1216d0c196b27e5d55043455",
    "chat_template.jinja": "ba551d58630afa3190b1be3602e28301f3d2e9bbac978dfc49d6d825171648b6",
}
LABELS = ("A", "B", "NONE", "UNKNOWN")
CFG = {"rank": 2, "alpha": 4, "lr": 0.0003, "max_steps": 1,
       "min_steps": 1, "target_loss": 0.0, "anchor_weight": 0.0,
       "locality_swaps": 0, "jepa_weight": 0.0, "weight_decay": 0.0,
       "ckpt_every": 1, "seed": 2026102922, "threads": 2,
       "targets": ("v_proj", "out_proj"), "max_tokens": 512}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def read_frozen(cohort):
    p = Path(cohort)
    manifest = json.loads((p / "manifest.json").read_text())
    if (manifest.get("schema") != "v13.p2x.disjoint_receiver_trainset.v1.export.v1"
            or manifest.get("fixture_sha256") != FIXTURE_SHA
            or manifest.get("sha256") != EXPORT_SHA
            or manifest.get("train_examples") != 504
            or manifest.get("validation_inputs") != 360
            or manifest.get("validation_answers") != 72):
        raise ValueError("P2X frozen manifest mismatch")
    records = {}
    for name, expected in EXPORT_SHA.items():
        path = p / name
        if path.is_symlink():
            raise ValueError("P2X symlink input")
        raw = path.read_bytes()
        if sha(raw) != expected:
            raise ValueError("P2X frozen JSONL SHA256 mismatch: " + name)
        records[name] = [json.loads(line) for line in raw.splitlines()]
    if tuple(len(records[n]) for n in EXPORT_SHA) != (504, 360, 72):
        raise ValueError("P2X frozen record count mismatch")
    return records


def select_pilot(records):
    train = records["train.jsonl"]
    validation = records["validation_inputs.jsonl"]
    if len(train) != 504 or len(validation) != 360:
        raise ValueError("P2X pilot source count mismatch")
    val_ids = {r.get("id") for r in validation}
    selected = []
    for label in LABELS:
        candidates = sorted((r for r in train if r.get("target_action") == label),
                            key=lambda r: (r["id"], r["arm"]))
        if len(candidates) < 2:
            raise ValueError("P2X insufficient frozen label examples")
        selected.extend(candidates[:2])
    if len(selected) != 8 or len({(r["id"], r["arm"]) for r in selected}) != 8:
        raise ValueError("P2X pilot selection count/duplicate mismatch")
    for r in selected:
        if (not isinstance(r.get("id"), str) or not r["id"].startswith("P2X")
                or r["id"] in val_ids or r.get("arm") not in
                ("both_exact", "c3_only", "b1_only", "b2_only", "shuffled")
                or not isinstance(r.get("messages"), list) or len(r["messages"]) != 1
                or r["messages"][0].get("role") != "user"
                or not isinstance(r["messages"][0].get("content"), str)):
            raise ValueError("P2X pilot train/validation identity or message mismatch")
        if r["target_action"] != "UNKNOWN" and r["arm"] != "both_exact":
            raise ValueError("P2X action leaked to negative arm")
        if r["target_action"] == "UNKNOWN" and r["arm"] == "both_exact":
            raise ValueError("P2X exact arm missing action")
        if any(x in r["messages"][0]["content"] for x in
               ("target_action", "oracle_action", "max_first", "max_second")):
            raise ValueError("P2X model-facing label leak")
    return selected


def source_admission(master):
    p = Path(master)
    for name, expected in MASTER_SHA.items():
        f = p / name
        if f.is_symlink() or file_sha(f) != expected:
            raise ValueError("QAD FP32 source SHA256 mismatch: " + name)
    return MASTER_SHA["model.safetensors"]


def resource_admission(work):
    p = Path(work)
    p.mkdir(parents=True, exist_ok=True)
    disk = shutil.disk_usage(p).free
    mem = 0
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                mem = int(line.split()[1]) * 1024
                break
    cgroup = Path("/sys/fs/cgroup")
    try:
        maximum = (cgroup / "memory.max").read_text().strip()
        used = int((cgroup / "memory.current").read_text().strip())
        if maximum != "max":
            mem = min(mem, int(maximum) - used)
    except (OSError, ValueError):
        pass
    if disk < 5_000_000_000 or mem < 5_000_000_000:
        raise ValueError("P2X pilot resource admission RED: RAM/disk below 5GB")
    return {"disk_free_bytes": disk, "memory_available_bytes": mem}


def token_admission(master, selected):
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(master), local_files_only=True)
    lengths = []
    for r in selected:
        ids = tok.apply_chat_template(
            r["messages"], add_generation_prompt=True, tokenize=True)
        target = tok(str(r["target_action"]) + "<|im_end|>",
                     add_special_tokens=False)["input_ids"]
        if len(ids) + len(target) > CFG["max_tokens"] or not target:
            raise ValueError("P2X pilot token truncation/empty target RED")
        lengths.append(len(ids) + len(target))
    return lengths


def run_pilot(cohort, master, work, budget_seconds):
    from v13.lora_trainer import LoraTrainer
    records = read_frozen(cohort)
    selected = select_pilot(records)
    base_sha = source_admission(master)
    resources = resource_admission(work)
    lengths = token_admission(master, selected)
    items = [{"memory_id": r["id"] + ":" + r["arm"],
              "prompt": r["messages"][0]["content"],
              "target": r["target_action"], "kind": "p2x_pilot",
              "answer_keys": [r["target_action"]]} for r in selected]
    trainer = LoraTrainer(master_dir=master, work_dir=work,
                          master_sha256=base_sha, anchors=(), probes=(),
                          cfg=CFG, evaluator=None)
    start = time.monotonic()
    result = trainer.fit(items, base_generation=0,
                         deadline=start + float(budget_seconds))
    metrics = result.get("metrics", {})
    if (not result.get("artifact") or metrics.get("steps") != 1
            or metrics.get("jepa_weight") != 0.0
            or metrics.get("rank") != 2
            or metrics.get("targets") != list(CFG["targets"])
            or type(metrics.get("trainable_parameter_count")) is not int
            or metrics["trainable_parameter_count"] <= 0
            or not isinstance(metrics.get("final_ce"), (int, float))
            or not math.isfinite(metrics["final_ce"])):
        raise ValueError("P2X pilot training/export metrics RED")
    adapter = Path(result["artifact"])
    if not adapter.is_file() or file_sha(adapter) != result.get("hash"):
        raise ValueError("P2X pilot exported GGUF adapter hash RED")
    if source_admission(master) != base_sha:
        raise ValueError("P2X pilot source base-weight drift RED")
    return {"schema": "v13.p2x.c3_lora_pilot.v1",
            "status": "EIGHT_EXAMPLE_ONE_STEP_LORA_PILOT_ONLY",
            "source_master_sha256": base_sha, "fixture_sha256": FIXTURE_SHA,
            "train_jsonl_sha256": EXPORT_SHA["train.jsonl"],
            "selected": [{"id": r["id"], "arm": r["arm"],
                          "target_action": r["target_action"],
                          "record_sha256": sha(canonical(r))}
                         for r in selected],
            "token_lengths": lengths, "resources": resources,
            "metrics": metrics, "adapter_gguf_sha256": result["hash"],
            "adapter_gguf_path": str(adapter),
            "files": result.get("files"), "elapsed_s": round(time.monotonic()-start, 3),
            "training_pilot": True, "ag6_approved": False,
            "production_activation": False, "p0x_used_for_training": False,
            "step2_utility_pass": False, "jepa_weight": 0,
            "redmi_measured": False, "whole_system_complete": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cohort", required=True)
    p.add_argument("--master", required=True)
    p.add_argument("--work", required=True)
    p.add_argument("--budget-seconds", type=int, default=1200)
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    try:
        result = run_pilot(args.cohort, args.master, args.work, args.budget_seconds)
        rc = 0
    except Exception as exc:
        result = {"schema": "v13.p2x.c3_lora_pilot.v1", "status": "PILOT_RED_PRESERVED",
                  "error": type(exc).__name__ + ": " + str(exc),
                  "ag6_approved": False, "production_activation": False,
                  "step2_utility_pass": False, "jepa_weight": 0,
                  "whole_system_complete": False}
        rc = 2
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as f:
        f.write(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

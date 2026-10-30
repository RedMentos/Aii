#!/usr/bin/env python3
"""New preregistered 350M Body-JEPA EMA eval-vs-train paired NLL diagnostic.

Runs the existing BodyJepaTrainer.fit with an export-free subclass. This is
not a deployable adapter, retention proof, or utility gate.
"""
import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import time

from scripts.lp3_real_master_smoke import MODEL_ID, REVISION, MASTER_SHA256, verify_master
from v13.body_jepa import BodyJepaTrainer
from v13.common import atomic_write, file_hash
from v13.lora_trainer import LoraTrainer

SEEDS = (73, 79, 83)
ARMS = ("CE", "EMA_TRAIN", "EMA_EVAL", "SHUFFLED")
FACTS = (
    ("Asterion", "blue", "Cobalt"),
    ("Keldara", "red", "Vermilion"),
    ("Velaris", "green", "Juniper"),
    ("Meridia", "gold", "Saffron"),
)
RETENTION = (
    ("What is the capital of France?", "Paris"),
    ("What is 2 plus 2?", "4"),
    ("What is the opposite of hot?", "cold"),
    ("What gas do plants absorb?", "carbon dioxide"),
)
CONFIG = {
    "rank": 2, "alpha": 4., "lr": 5e-4, "weight_decay": 0.,
    "max_steps": 2, "min_steps": 2, "max_tokens": 96,
    "targets": ["w1", "w2", "w3"], "threads": 2,
    "anchors_per_step": 0, "anchor_weight": 0., "locality_swaps": 0,
    "jepa_ema_decay": 0.9, "checkpoint_resume": False,
}


def fixture():
    """Exactly four immutable train sources, disjoint paraphrases and near-misses."""
    train = []
    para = []
    near = []
    for i, (archive, color, answer) in enumerate(FACTS):
        q = f"In the invented {archive} archive, what is the {color} vault key?"
        train.append((q, answer))
        para.append((f"Which key opens the {color} vault of the {archive} archive?", answer))
        other = FACTS[(i + 1) % len(FACTS)][0]
        near.append((f"In the invented {other} archive, what is the {color} vault key?", answer))
    if len(set(q for q, _ in train + para + near)) != 12:
        raise ValueError("Source overlap invalidates holdout or near-miss")
    return {"train": train, "paraphrase": para, "near_miss_leak_proxy": near,
            "retention": list(RETENTION)}


def fixture_sha(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ExportFreeTrainer(BodyJepaTrainer):
    """The native diagnostic may train RAM-only LoRA but never export an adapter."""
    def _export(self, torch, model, out, lc):
        return {"gguf": "NO_EXPORT", "gguf_sha256": None}

    @staticmethod
    def _greedy(torch, model, ids, n):
        # Only post-fit recall uses this: no anchors, so training is unchanged.
        return LoraTrainer._greedy(torch, model, ids, min(n, 8))


def nll(trainer, question, answer, base=False):
    import torch
    ids, labels = trainer._encode(trainer.tok, question, answer)
    x = torch.tensor([ids], dtype=torch.long)
    y = torch.tensor([labels], dtype=torch.long)
    with torch.no_grad():
        if base:
            with trainer.model.disable_adapter():
                loss = trainer.model(input_ids=x, labels=y).loss
        else:
            loss = trainer.model(input_ids=x, labels=y).loss
    value = float(loss)
    if not math.isfinite(value) or value < 0:
        raise ValueError("Nonfinite or negative teacher-forced NLL")
    return value


def measure(trainer, rows, base=False):
    out = {}
    for name, pairs in rows.items():
        out[name] = [{"q": q, "answer": a, "nll": nll(trainer, q, a, base)}
                     for q, a in pairs]
    return out


def summary(measured):
    return {name: statistics.mean(row["nll"] for row in rows)
            for name, rows in measured.items()}


def verdict(results):
    """Strict four-arm paired diagnostic; never a real V13 utility PASS."""
    if set(results) != set(str(seed) for seed in SEEDS):
        raise ValueError("Incomplete seed set")
    diffs = []
    for seed in SEEDS:
        arms = results[str(seed)]
        if set(arms) != set(ARMS):
            raise ValueError("Incomplete arm set")
        summaries = {name: arms[name]["summary"] for name in ARMS}
        for name, summary_values in summaries.items():
            if (set(summary_values) != {"train", "paraphrase", "near_miss_leak_proxy", "retention"}
                    or any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0
                           for v in summary_values.values())):
                raise ValueError("Invalid arm summary: " + name)
        ce, train, eval_, shuffled = (summaries[name] for name in ARMS)
        diffs.append({
            "seed": seed,
            "paraphrase_eval_minus_train": eval_["paraphrase"] - train["paraphrase"],
            "paraphrase_eval_minus_ce": eval_["paraphrase"] - ce["paraphrase"],
            "paraphrase_eval_minus_shuffled": eval_["paraphrase"] - shuffled["paraphrase"],
            "near_miss_eval_minus_train": eval_["near_miss_leak_proxy"] - train["near_miss_leak_proxy"],
            "retention_eval_minus_train": eval_["retention"] - train["retention"],
        })
    mean = {k: statistics.mean(d[k] for d in diffs) for k in diffs[0] if k != "seed"}
    wins = sum(d["paraphrase_eval_minus_train"] <= -.05 for d in diffs)
    signal = (wins >= 2
              and mean["paraphrase_eval_minus_train"] <= -.05
              and mean["paraphrase_eval_minus_ce"] <= -.05
              and mean["paraphrase_eval_minus_shuffled"] <= -.05
              and mean["near_miss_eval_minus_train"] >= -.05
              and mean["retention_eval_minus_train"] <= .05)
    hurt = (mean["paraphrase_eval_minus_train"] >= .05
            or mean["retention_eval_minus_train"] > .05)
    status = ("BOUNDED_EVAL_SIGNAL_NOT_UTILITY_GATE" if signal
              else "DIAGNOSTIC_HURT" if hurt
              else "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
    return {"status": status, "seed_wins": wins, "per_seed_deltas": diffs,
            "mean_deltas": mean, "utility_gate_pass": False}


def arm_cfg(seed, arm):
    if seed not in SEEDS or arm not in ARMS:
        raise ValueError("Unregistered seed or arm")
    cfg = dict(CONFIG, seed=seed,
               jepa_weight=0. if arm == "CE" else .5,
               jepa_target="shuffled" if arm == "SHUFFLED" else "ema")
    if arm == "EMA_EVAL":
        cfg["jepa_target_eval"] = True  # sole experimental toggle
    return cfg


def run(master, out):
    rows = fixture()
    report = {
        "schema": "v13.bodyjepa.350m_ema_eval_paired_nll.v1",
        "model_id": MODEL_ID, "model_revision": REVISION,
        "master_sha256": MASTER_SHA256,
        "body_jepa_source_git_blob": "b560d4e88fe457f381e89dfc5d6188a8ec3b306b",
        "lora_source_git_blob": "49a752879ae5d19391963742a0f042e740edb2cc",
        "fixture_sha256": fixture_sha(rows),
        "seeds": SEEDS, "arms": ARMS, "config": CONFIG,
        "evidence_class": "LINUX_FP32_TORCH_SYNTHETIC_HELDOUT",
        "runtime_jepa_weight": 0, "age_authority": 0,
        "redmi_measured": False, "b1_b2_utility_proven": False,
        "step2_utility_pass": False, "production_activation": False,
        "whole_system_complete": False, "results": {}, "status": "INCOMPLETE",
    }
    report["experimental_variable"] = "EMA target eval mode only"
    report["historical_three_seed_status"] = "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN"
    receipt = out / "report.json"
    atomic_write(receipt, json.dumps(report, sort_keys=True, indent=2))
    for seed in SEEDS:
        per = {}
        for arm in ARMS:
            cfg = arm_cfg(seed, arm)
            items = [{"memory_id": f"synthetic_{i}", "prompt": q, "target": a}
                     for i, (q, a) in enumerate(rows["train"])]
            tr = ExportFreeTrainer(master, out / "work" / f"{seed}-{arm}",
                                   master_sha256=MASTER_SHA256, anchors=(),
                                   cfg=cfg, arch="lfm2")
            t0 = time.monotonic()
            result = tr.fit(items, "SYNTHETIC_RESEARCH_ONLY")
            if result.get("artifact") != "NO_EXPORT" or not result.get("metrics"):
                raise ValueError("Unexpected export or missing training metrics")
            measurements = measure(tr, rows)
            baseline = measure(tr, rows, base=True)
            per[arm] = {
                "metrics": result["metrics"], "summary": summary(measurements),
                "baseline": summary(baseline), "rows": measurements,
                "elapsed_s": round(time.monotonic() - t0, 3),
                "exported_adapter": False,
            }
            report["results"][str(seed)] = per
            atomic_write(receipt, json.dumps(report, sort_keys=True, indent=2))
            print(json.dumps({"seed": seed, "arm": arm,
                              "summary": per[arm]["summary"],
                              "elapsed_s": per[arm]["elapsed_s"]}), flush=True)
            del tr
            gc.collect()
    report.update(verdict(report["results"]))
    report["completed_arms"] = len(SEEDS) * len(ARMS)
    atomic_write(receipt, json.dumps(report, sort_keys=True, indent=2))
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--execute-native", action="store_true")
    a = ap.parse_args(argv)
    if not a.execute_native:
        ap.error("Explicit --execute-native required")
    verify_master(a.master)
    if a.out.exists() or a.out.is_symlink():
        raise ValueError("Refusing to overwrite or resume a research cohort")
    a.out.mkdir(parents=True)
    result = run(a.master, a.out)
    print(json.dumps({"status": result["status"], "completed_arms": result["completed_arms"],
                      "verdict": result["mean_deltas"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

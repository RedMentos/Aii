#!/usr/bin/env python3
"""Run11P preregistered disjoint 8-step 350M Body-JEPA CE/EMA/shuffled NLL diagnostic.

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

SEEDS = (97, 101, 103)
ARMS = ("CE", "EMA", "SHUFFLED")
FACTS = (
    ("Orriven", "silver", "Peregrine"),
    ("Talmera", "violet", "Obsidian"),
    ("Selenor", "amber", "Cinnamon"),
    ("Dravik", "teal", "Marigold"),
)
RETENTION = (
    ("What is the capital of Japan?", "Tokyo"),
    ("What is 7 times 3?", "21"),
    ("What is the opposite of wet?", "dry"),
    ("Which gas do humans inhale to survive?", "oxygen"),
)
CONFIG = {
    "rank": 2, "alpha": 4., "lr": 5e-4, "weight_decay": 0.,
    "max_steps": 8, "min_steps": 8, "max_tokens": 96,
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
    """Tiny 3-seed diagnostic; never returns a real V13 utility PASS."""
    if set(results) != set(str(seed) for seed in SEEDS):
        raise ValueError("Incomplete seed set")
    diffs = []
    for seed in SEEDS:
        arms = results[str(seed)]
        if set(arms) != set(ARMS):
            raise ValueError("Incomplete arm set")
        ce, ema, wrong = (arms[arm]["summary"] for arm in ARMS)
        diffs.append({
            "seed": seed,
            "paraphrase_ema_minus_ce": ema["paraphrase"] - ce["paraphrase"],
            "paraphrase_ema_minus_shuffled": ema["paraphrase"] - wrong["paraphrase"],
            "near_miss_ema_minus_ce": ema["near_miss_leak_proxy"] - ce["near_miss_leak_proxy"],
            "retention_ema_minus_ce": ema["retention"] - ce["retention"],
        })
    mean = {k: statistics.mean(d[k] for d in diffs) for k in diffs[0] if k != "seed"}
    seed_wins = sum(d["paraphrase_ema_minus_ce"] <= -.05
                    and d["paraphrase_ema_minus_shuffled"] <= -.05 for d in diffs)
    signal = (seed_wins >= 2 and mean["paraphrase_ema_minus_ce"] <= -.05
              and mean["paraphrase_ema_minus_shuffled"] <= -.05
              and mean["near_miss_ema_minus_ce"] >= -.05
              and mean["retention_ema_minus_ce"] <= .05)
    hurt = (mean["paraphrase_ema_minus_ce"] >= .05
            or mean["retention_ema_minus_ce"] > .05)
    status = ("BOUNDED_NLL_SIGNAL_NOT_UTILITY_GATE" if signal
              else "DIAGNOSTIC_HURT" if hurt
              else "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
    return {"status": status, "seed_wins": seed_wins, "per_seed_deltas": diffs,
            "mean_deltas": mean, "utility_gate_pass": False}


FIXTURE_SHA256 = "1b2f71817200389d3f78fc87cf70512e23bd7273e75c2901768c3cc76ded56aa"
LICENSE_SHA256 = "4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c"


def run(master, out):
    rows = fixture()
    if fixture_sha(rows) != FIXTURE_SHA256:
        raise ValueError("Run11P frozen fixture hash mismatch")
    report = {
        "schema": "v13.bodyjepa.350m_eightstep_disjoint_nll.v1",
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
        "prior_run11m_status": "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN",
        "experimental_variable": "8-step JEPA weight 2.0 vs CE and shuffled controls",
        "license_sha256": LICENSE_SHA256,
    }
    receipt = out / "report.json"
    atomic_write(receipt, json.dumps(report, sort_keys=True, indent=2))
    for seed in SEEDS:
        per = {}
        for arm in ARMS:
            cfg = dict(CONFIG, seed=seed,
                       jepa_weight=0. if arm == "CE" else 2.0,
                       jepa_target="shuffled" if arm == "SHUFFLED" else "ema")
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
    license_path = a.master / "LICENSE"
    if not license_path.is_file() or file_hash(license_path) != LICENSE_SHA256:
        raise ValueError("Pinned model license missing or changed")
    if a.out.exists() or a.out.is_symlink():
        raise ValueError("Refusing to overwrite or resume a research cohort")
    a.out.mkdir(parents=True)
    result = run(a.master, a.out)
    if result.get("completed_arms") != 9:
        raise ValueError("Incomplete 9-arm cohort")
    print(json.dumps({"status": result["status"], "completed_arms": result["completed_arms"],
                      "verdict": result["mean_deltas"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

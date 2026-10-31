#!/usr/bin/env python3
"""Run117BI preregistered grouped-vs-ungrouped Body-JEPA 350M LoRA NLL pilot.

Synthetic source groups only. Explicit --execute-native, no export or Runtime
wiring, no real USER data, no Age/STEP2/B3/Body-JEPA gate promotion.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from scripts.lp3_real_master_smoke import MODEL_ID, REVISION, MASTER_SHA256, verify_master
from v13.body_jepa import BodyJepaTrainer
from v13.body_jepa_contrastive_trainer_shadow import ContrastiveBodyJepaTrainer
from v13.body_jepa_grouped_contrastive_trainer_shadow import GroupedContrastiveBodyJepaTrainer
from v13.common import atomic_write, file_hash
from v13.lora_trainer import LoraTrainer

SEEDS = (263, 269)
ARMS = ("CE", "UNGROUPED_EMA", "GROUPED_EMA")
FACTS = (
    ("Mora263", "silver", "Citrine"),
    ("Nera263", "jade", "Bramble"),
    ("Ossa263", "copper", "Velvet"),
    ("Pira263", "indigo", "Falcon"),
)
HELDOUT = (("Rusa263", "amber", "Sable"), ("Sora263", "ivory", "Larch"))
RETENTION = (
    ("How many days are in a week?", "7"),
    ("What is 8 plus 5?", "13"),
    ("What is frozen water called?", "ice"),
    ("What color is a clear daytime sky?", "blue"),
)
CONFIG = {
    "rank": 2, "alpha": 4., "lr": 5e-4, "weight_decay": 0.,
    "max_steps": 8, "min_steps": 8, "max_tokens": 96,
    "targets": ["w1", "w2", "w3"], "threads": 2,
    "anchors_per_step": 0, "anchor_weight": 0., "locality_swaps": 0,
    "jepa_ema_decay": 0.9, "jepa_target_eval": True,
    "contrastive_temperature": 0.1, "checkpoint_resume": False,
}
FIXTURE_SHA256 = "30c400a581ddea67c38b304e4b467d4fe05c039ac6cc152c860102b1b3462279"
LICENSE_SHA256 = "4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c"


def fixture():
    train, para, near, held = [], [], [], []
    for i, (archive, color, answer) in enumerate(FACTS):
        train.extend([
            (f"In the invented {archive} archive, what is the {color} vault key?", answer),
            (f"For the {archive} archive, name its {color} vault key.", answer),
        ])
        para.append((f"Which key unlocks the {color} vault at {archive}?", answer))
        other = FACTS[(i + 1) % len(FACTS)][0]
        near.append((f"Which key unlocks the {color} vault at {other}?", answer))
    for archive, color, answer in HELDOUT:
        held.append((f"What is the {color} vault key of {archive}?", answer))
    result = {
        "train": train, "paraphrase": para, "near_miss_wrong_answer": near,
        "source_disjoint_heldout": held, "retention": RETENTION,
    }
    all_q = [q for rows in result.values() for q, _ in rows]
    if len(all_q) != len(set(all_q)):
        raise ValueError("RUN117BI_FIXTURE_OVERLAP_RED")
    return result


def fixture_sha(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()


def fact_hash(archive, color, answer):
    return hashlib.sha256(json.dumps(
        {"archive": archive, "color": color, "answer": answer},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_row(archive, color, answer, view):
    sha = fact_hash(archive, color, answer)
    return {"path": "B1_DETAIL", "source_id": "synthetic_fact_" + archive,
            "source_sha256": sha, "context_source_sha256": sha,
            "target_source_sha256": sha, "view_id": view, "eligibility": 1.0}


def items_and_heldout(rows):
    items = []
    for i, (question, answer) in enumerate(rows["train"]):
        archive, color, target = FACTS[i // 2]
        if answer != target:
            raise ValueError("RUN117BI_TRAIN_TARGET_RED")
        items.append({"memory_id": f"synthetic_fact_{archive}_view{i % 2}",
                      "prompt": question, "target": answer,
                      **source_row(archive, color, target, f"train_{i}")})
    heldout = [source_row(a, c, t, f"heldout_{i}")
               for i, (a, c, t) in enumerate(HELDOUT)]
    from v13.body_jepa_grouped_source_candidate import validate_training_rows
    b = validate_training_rows(items, heldout_rows=heldout)
    if b["source_group_count"] != 4 or b["repeated_view_count"] != 4:
        raise ValueError("RUN117BI_GROUP_COUNT_RED")
    return items, heldout, b


class ExportFreeCosineTrainer(BodyJepaTrainer):
    def _export(self, torch, model, out, lc):
        return {"gguf": "NO_EXPORT", "gguf_sha256": None}
    @staticmethod
    def _greedy(torch, model, ids, n):
        return LoraTrainer._greedy(torch, model, ids, min(n, 8))


class ExportFreeContrastiveTrainer(ContrastiveBodyJepaTrainer):
    @staticmethod
    def _greedy(torch, model, ids, n):
        return LoraTrainer._greedy(torch, model, ids, min(n, 8))


class ExportFreeGroupedTrainer(GroupedContrastiveBodyJepaTrainer):
    @staticmethod
    def _greedy(torch, model, ids, n):
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
        raise ValueError("RUN117BI_NONFINITE_NLL_RED")
    return value


def measure(trainer, rows, base=False):
    return {name: [{"q": q, "answer": a, "nll": nll(trainer, q, a, base)}
                   for q, a in pairs] for name, pairs in rows.items()}


def summary(measured):
    return {name: statistics.mean(row["nll"] for row in values)
            for name, values in measured.items()}


def verdict(results):
    if set(results) != set(map(str, SEEDS)):
        raise ValueError("RUN117BI_SEED_INCOMPLETE_RED")
    deltas = []
    keys = {"train", "paraphrase", "near_miss_wrong_answer",
            "source_disjoint_heldout", "retention"}
    for seed in SEEDS:
        arms = results[str(seed)]
        if set(arms) != set(ARMS):
            raise ValueError("RUN117BI_ARM_INCOMPLETE_RED")
        for arm in ARMS:
            vals = arms[arm]["summary"]
            if set(vals) != keys or any(
                    type(v) not in (int, float) or not math.isfinite(v) or v < 0
                    for v in vals.values()):
                raise ValueError("RUN117BI_NLL_SUMMARY_RED")
        ce, ungrouped, grouped = [arms[a]["summary"] for a in ARMS]
        deltas.append({
            "seed": seed,
            "paraphrase_grouped_minus_ungrouped":
                grouped["paraphrase"] - ungrouped["paraphrase"],
            "paraphrase_grouped_minus_ce":
                grouped["paraphrase"] - ce["paraphrase"],
            "retention_grouped_minus_ungrouped":
                grouped["retention"] - ungrouped["retention"],
            "near_miss_grouped_minus_ungrouped":
                grouped["near_miss_wrong_answer"] - ungrouped["near_miss_wrong_answer"],
            "source_disjoint_grouped_minus_ungrouped":
                grouped["source_disjoint_heldout"] - ungrouped["source_disjoint_heldout"],
        })
    means = {k: statistics.mean(d[k] for d in deltas)
             for k in deltas[0] if k != "seed"}
    wins = sum(d["paraphrase_grouped_minus_ungrouped"] <= -0.02
               for d in deltas)
    signal = (wins == len(SEEDS)
              and means["paraphrase_grouped_minus_ungrouped"] <= -0.03
              and means["paraphrase_grouped_minus_ce"] <= -0.03
              and means["retention_grouped_minus_ungrouped"] <= 0.05
              and means["near_miss_grouped_minus_ungrouped"] >= -0.05
              and means["source_disjoint_grouped_minus_ungrouped"] <= 0.05)
    return {"status": ("GROUPED_MASK_EXPLORATORY_NLL_SIGNAL_NO_GATE" if signal
                       else "GROUPED_MASK_NO_ATTRIBUTABLE_SIGNAL"),
            "per_seed_deltas": deltas, "mean_deltas": means,
            "seed_wins": wins, "utility_gate_pass": False}


def run(master, out):
    rows = fixture()
    if fixture_sha(rows) != FIXTURE_SHA256:
        raise ValueError("RUN117BI_FIXTURE_SHA_RED")
    items, heldout, binding = items_and_heldout(rows)
    report = {
        "schema": "v13.bodyjepa.350m_grouped_source_run117bi.v1",
        "model_id": MODEL_ID, "model_revision": REVISION,
        "master_sha256": MASTER_SHA256, "license_sha256": LICENSE_SHA256,
        "fixture_sha256": fixture_sha(rows), "seeds": SEEDS, "arms": ARMS,
        "config": CONFIG, "source_group_count": binding["source_group_count"],
        "repeated_view_count": binding["repeated_view_count"],
        "source_authentication": "SYNTHETIC_FACT_METADATA_ONLY",
        "evidence_class": "LINUX_FP32_TORCH_SYNTHETIC_HELDOUT",
        "runtime_jepa_weight": 0, "age_authority": 0,
        "redmi_measured": False, "b1_b2_utility_proven": False,
        "step2_utility_pass": False, "body_jepa_available": False,
        "production_activation": False, "whole_system_complete": False,
        "results": {}, "failures": [], "status": "INCOMPLETE",
        "experimental_variable": "same-source contrastive false-negative masking",
    }
    receipt = out / "report.json"
    atomic_write(receipt, json.dumps(report, sort_keys=True, indent=2))
    for seed in SEEDS:
        per = {}
        order = ARMS if seed == SEEDS[0] else (ARMS[2], ARMS[0], ARMS[1])
        for arm in order:
            cfg = dict(CONFIG, seed=seed, jepa_weight=0.0 if arm == "CE" else 0.25,
                       jepa_target="ema")
            if arm == "GROUPED_EMA":
                cfg.update(grouped_source_enabled=True,
                           heldout_source_rows=heldout)
            trainer_cls = {"CE": ExportFreeCosineTrainer,
                           "UNGROUPED_EMA": ExportFreeContrastiveTrainer,
                           "GROUPED_EMA": ExportFreeGroupedTrainer}[arm]
            tr = None
            t0 = time.monotonic()
            try:
                tr = trainer_cls(master, out / "work" / f"{seed}-{arm}",
                                 master_sha256=MASTER_SHA256, anchors=(),
                                 cfg=cfg, arch="lfm2")
                result = tr.fit(items, "SYNTHETIC_RESEARCH_ONLY")
                if (result.get("artifact") != "NO_EXPORT" or result.get("hash") is not None
                        or result.get("files", {}).get("gguf") != "NO_EXPORT"
                        or not result.get("metrics")
                        or result["metrics"].get("steps") != 8):
                    raise ValueError("RUN117BI_EXPORT_OR_STEPS_RED")
                if arm == "GROUPED_EMA":
                    b = result["metrics"].get("grouped_source_binding", {})
                    if (b.get("source_group_count") != 4
                            or b.get("repeated_view_count") != 4
                            or b.get("source_authentication") != "REQUIRED_EXTERNAL"):
                        raise ValueError("RUN117BI_GROUP_BINDING_RED")
                measurements = measure(tr, rows)
                baseline = measure(tr, rows, base=True)
                per[arm] = {
                    "metrics": result["metrics"], "summary": summary(measurements),
                    "baseline": summary(baseline), "rows": measurements,
                    "baseline_rows": baseline,
                    "elapsed_s": round(time.monotonic() - t0, 3),
                    "exported_adapter": False,
                }
                report["results"][str(seed)] = per
                atomic_write(receipt, json.dumps(report, sort_keys=True, indent=2))
                print(json.dumps({"seed": seed, "arm": arm,
                                  "summary": per[arm]["summary"],
                                  "elapsed_s": per[arm]["elapsed_s"]}), flush=True)
            except Exception as exc:
                report["failures"].append({"seed": seed, "arm": arm,
                                           "error_type": type(exc).__name__,
                                           "error": str(exc)[:400]})
                report["status"] = "FAILED_PRESERVED"
                atomic_write(receipt, json.dumps(report, sort_keys=True, indent=2))
                raise
            finally:
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
    if (not license_path.is_file() or license_path.is_symlink()
            or file_hash(license_path) != LICENSE_SHA256):
        raise ValueError("RUN117BI_MODEL_LICENSE_PIN_RED")
    if a.out.exists() or a.out.is_symlink():
        raise ValueError("RUN117BI_REFUSE_OVERWRITE")
    a.out.mkdir(parents=True)
    result = run(a.master, a.out)
    if result.get("completed_arms") != 6:
        raise ValueError("RUN117BI_INCOMPLETE_ARMS_RED")
    print(json.dumps({"status": result["status"],
                      "completed_arms": result["completed_arms"],
                      "mean_deltas": result["mean_deltas"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

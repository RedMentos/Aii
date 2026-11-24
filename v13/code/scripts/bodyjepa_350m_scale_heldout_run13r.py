#!/usr/bin/env python3
"""Run13R: disjoint 350M Body-JEPA contrastive dose/retention pilot, no export.

Two new seeds x CE, contrastive2.5, contrastive12, shuffled12.
Research-only Linux native; never Runtime learning or an Age/STEP2/B3 gate.
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
from scripts.bodyjepa_350m_contrastive_disjoint_run12c import (
    ExportFreeCosineTrainer, ExportFreeContrastiveTrainer, CONFIG,
    measure, summary,
)
from v13.common import atomic_write, file_hash
from v13.lora_trainer import answer_hit

SEEDS = (271, 277)
ARMS = ("CE_0", "CONTRAST_2_5", "CONTRAST_12", "SHUFFLED_12")
WEIGHTS = {"CE_0": 0., "CONTRAST_2_5": 2.5,
           "CONTRAST_12": 12., "SHUFFLED_12": 12.}
FACTS = (
    ("Argen271", "amber", "Topaz"),
    ("Belora271", "teal", "Birch"),
    ("Corvyn271", "violet", "Falcon"),
    ("Deltis271", "silver", "Sable"),
)
RETENTION = (
    ("What is the capital of Japan?", "Tokyo"),
    ("What is 7 times 3?", "21"),
    ("What is the opposite of wet?", "dry"),
    ("Which gas do humans inhale to survive?", "oxygen"),
)
FIXTURE_SHA256 = "a93322a5a30f9a9da5c391d172f8f6048cc6b9e2d617ab0349f4d148d278b77e"
LICENSE_SHA256 = "4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c"
SCHEMA = "v13.bodyjepa.350m_scale_heldout_run13r.v1"


def fixture():
    rows = {"train": [], "paraphrase": [],
            "near_miss_leak_proxy": [], "retention": list(RETENTION)}
    for i, (archive, color, answer) in enumerate(FACTS):
        rows["train"].append((
            f"In the invented {archive} archive, what is the {color} vault key?",
            answer))
        rows["paraphrase"].append((
            f"Which key opens the {color} vault of the {archive} archive?",
            answer))
        other = FACTS[(i + 1) % len(FACTS)][0]
        rows["near_miss_leak_proxy"].append((
            f"In the invented {other} archive, what is the {color} vault key?",
            answer))
    all_q = [q for pairs in rows.values() for q, _ in pairs]
    if len(all_q) != 16 or len(set(all_q)) != 16:
        raise ValueError("DISJOINT_FIXTURE_RED")
    return rows


def fixture_hash(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True,
                           separators=(",", ":")).encode()).hexdigest()


def _finite_summary(arm):
    s = arm.get("summary")
    if (type(s) is not dict
            or set(s) != {"train", "paraphrase", "near_miss_leak_proxy", "retention"}
            or any(type(x) not in (float, int) or not math.isfinite(x) or x < 0
                   for x in s.values())):
        raise ValueError("NLL_SUMMARY_RED")
    return s


def verdict(results):
    """Fixed two-seed exploratory thresholds; never a utility gate."""
    if type(results) is not dict or set(results) != set(map(str, SEEDS)):
        raise ValueError("INCOMPLETE_SEEDS")
    rows = []
    for seed in SEEDS:
        arms = results[str(seed)]
        if type(arms) is not dict or set(arms) != set(ARMS):
            raise ValueError("INCOMPLETE_ARMS")
        ce, moderate, high, shuffled = (_finite_summary(arms[a]) for a in ARMS)
        rows.append({
            "seed": seed,
            "high_minus_ce_paraphrase": high["paraphrase"] - ce["paraphrase"],
            "high_minus_shuffled_paraphrase": high["paraphrase"] - shuffled["paraphrase"],
            "moderate_minus_ce_paraphrase": moderate["paraphrase"] - ce["paraphrase"],
            "high_minus_ce_near_miss": high["near_miss_leak_proxy"] - ce["near_miss_leak_proxy"],
            "high_minus_ce_retention": high["retention"] - ce["retention"],
        })
    means = {k: statistics.mean(r[k] for r in rows)
             for k in rows[0] if k != "seed"}
    wins = sum(r["high_minus_ce_paraphrase"] <= -.05
               and r["high_minus_shuffled_paraphrase"] <= -.05 for r in rows)
    signal = (wins == 2 and means["high_minus_ce_near_miss"] >= -.05
              and means["high_minus_ce_retention"] <= .05)
    hurt = (means["high_minus_ce_paraphrase"] >= .05
            or means["high_minus_ce_retention"] > .05)
    status = ("BOUNDED_SYNTHETIC_SCALE_SIGNAL_NOT_UTILITY_GATE" if signal
              else "DIAGNOSTIC_HURT" if hurt
              else "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
    return {
        "status": status, "seed_wins": wins, "per_seed_deltas": rows,
        "mean_deltas": means, "utility_gate_pass": False,
        "body_jepa_available": False, "redmi_measured": False,
        "whole_system_complete": False,
    }


def greedy_paraphrase(trainer, pairs):
    """Exploratory generated answer-hit diagnostic, not semantic accuracy."""
    out = []
    for q, answer in pairs:
        ids, _ = trainer._encode(trainer.tok, q)
        generated = trainer.tok.decode(
            trainer._greedy(trainer.torch, trainer.model, ids, 8),
            skip_special_tokens=True)
        out.append({"q": q, "expected": answer,
                    "text": generated[:256],
                    "answer_hit": bool(answer_hit(generated, [answer]))})
    return out


def run(master, out):
    rows = fixture()
    if fixture_hash(rows) != FIXTURE_SHA256:
        raise ValueError("FIXTURE_PIN_RED")
    cfg_base = dict(CONFIG, checkpoint_resume=False, jepa_target_eval=True,
                    contrastive_temperature=0.1, max_steps=8, min_steps=8)
    report = {
        "schema": SCHEMA, "model_id": MODEL_ID, "model_revision": REVISION,
        "master_sha256": MASTER_SHA256, "license_sha256": LICENSE_SHA256,
        "canon_blob": "218464b12a2d27d92524c751922fa8e1c3fb0ea7",
        "body_jepa_blob": "b560d4e88fe457f381e89dfc5d6188a8ec3b306b",
        "contrastive_loss_blob": "acd40aeac9e286e93b40bda72c655c17725a522e",
        "contrastive_trainer_blob": "a31a18d9be0b1137a10304f24d3a241d720bd247",
        "original_run12c_runner_blob": "15597550100de6ca546b1b024fbc6597fc600839",
        "fixture_sha256": FIXTURE_SHA256,
        "seeds": SEEDS, "arms": ARMS, "weights": WEIGHTS,
        "config": cfg_base, "evidence_class": "LINUX_FP32_TORCH_SYNTHETIC_HELDOUT",
        "results": {}, "failures": [], "status": "INCOMPLETE",
        "runtime_jepa_weight": 0, "age_authority": 0,
        "production_activation": False, "step2_utility_pass": False,
        "b3_authority": 0, "body_jepa_available": False,
        "redmi_measured": False, "whole_system_complete": False,
        "utility_gate_pass": False,
    }
    receipt = out / "report.json"
    atomic_write(receipt, json.dumps(report, sort_keys=True, indent=2))
    for seed in SEEDS:
        per = {}
        for arm in ARMS:
            cfg = dict(cfg_base, seed=seed, jepa_weight=WEIGHTS[arm],
                       jepa_target="shuffled" if arm == "SHUFFLED_12" else "ema")
            cls = ExportFreeCosineTrainer if arm == "CE_0" else ExportFreeContrastiveTrainer
            items = [{"memory_id": f"new_synthetic_{i}", "prompt": q, "target": a}
                     for i, (q, a) in enumerate(rows["train"])]
            tr = None
            started = time.monotonic()
            try:
                tr = cls(master, out / "work" / f"{seed}-{arm}",
                         master_sha256=MASTER_SHA256, anchors=(),
                         cfg=cfg, arch="lfm2")
                fit = tr.fit(items, "NEW_SYNTHETIC_RESEARCH_ONLY")
                if (fit.get("artifact") != "NO_EXPORT"
                        or fit.get("hash") is not None
                        or fit.get("files", {}).get("gguf") != "NO_EXPORT"
                        or fit.get("metrics", {}).get("steps") != 8):
                    raise ValueError("UNEXPECTED_EXPORT_OR_INCOMPLETE_TRAINING")
                measured = measure(tr, rows)
                baseline = measure(tr, rows, base=True)
                generated = greedy_paraphrase(tr, rows["paraphrase"])
                per[arm] = {
                    "metrics": fit["metrics"], "summary": summary(measured),
                    "baseline": summary(baseline),
                    "rows": measured, "baseline_rows": baseline,
                    "paraphrase_generated": generated,
                    "paraphrase_greedy_hits": sum(x["answer_hit"] for x in generated),
                    "elapsed_s": round(time.monotonic() - started, 3),
                    "exported_adapter": False,
                }
                report["results"][str(seed)] = per
                atomic_write(receipt, json.dumps(report, sort_keys=True, indent=2))
                print(json.dumps({"seed": seed, "arm": arm,
                                  "paraphrase_nll": per[arm]["summary"]["paraphrase"],
                                  "paraphrase_hits": per[arm]["paraphrase_greedy_hits"]}),
                      flush=True)
            except Exception as exc:
                report["failures"].append({
                    "seed": seed, "arm": arm, "error_type": type(exc).__name__,
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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--master", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--execute-native", action="store_true")
    args = ap.parse_args(argv)
    if not args.execute_native:
        ap.error("Explicit --execute-native required")
    verify_master(args.master)
    license_path = args.master / "LICENSE"
    if (not license_path.is_file() or license_path.is_symlink()
            or file_hash(license_path) != LICENSE_SHA256):
        raise ValueError("MODEL_LICENSE_PIN_RED")
    if args.out.exists() or args.out.is_symlink():
        raise ValueError("REFUSE_OVERWRITE")
    args.out.mkdir(parents=True)
    result = run(args.master, args.out)
    print(json.dumps({"status": result["status"],
                      "completed_arms": result["completed_arms"],
                      "mean_deltas": result["mean_deltas"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

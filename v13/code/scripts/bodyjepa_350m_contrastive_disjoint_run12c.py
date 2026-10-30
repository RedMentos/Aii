#!/usr/bin/env python3
"""Run12C isolated preregistered 350M contrastive Body-JEPA native NLL pilot.

Research-only, explicit native opt-in, no adapter/predictor export or Runtime
consumer. Never promotes Age0, STEP2, B3, Body-JEPA or whole-system gates.
Frozen Run11P and Run12B cohorts are not modified.
"""
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
from v13.common import atomic_write, file_hash
from v13.lora_trainer import LoraTrainer

SEEDS = (227, 229, 233)
ARMS = ("CE", "COS_EMA", "CONTRAST_EMA", "CONTRAST_SHUFFLED")
FACTS = (
    ("Avelorn", "copper", "Kestrel"),
    ("Brimora", "jade", "Nimbus"),
    ("Caelith", "indigo", "Saffron"),
    ("Dornwick", "ivory", "Talon"),
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
    "jepa_ema_decay": 0.9, "jepa_target_eval": True,
    "contrastive_temperature": 0.1, "checkpoint_resume": False,
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


class ExportFreeCosineTrainer(BodyJepaTrainer):
    """Unmodified cosine objective with research-only no-export subclass."""
    def _export(self, torch, model, out, lc):
        return {"gguf": "NO_EXPORT", "gguf_sha256": None}

    @staticmethod
    def _greedy(torch, model, ids, n):
        return LoraTrainer._greedy(torch, model, ids, min(n, 8))


class ExportFreeContrastiveTrainer(ContrastiveBodyJepaTrainer):
    """Isolated contrastive objective with no weights/predictor export."""
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
    """Preregistered tiny synthetic diagnostic; never a production utility gate."""
    if set(results) != set(map(str, SEEDS)):
        raise ValueError("Incomplete seed set")
    deltas = []
    for seed in SEEDS:
        arms = results[str(seed)]
        if set(arms) != set(ARMS):
            raise ValueError("Incomplete arm set")
        for arm in ARMS:
            s = arms[arm]["summary"]
            if set(s) != {"train", "paraphrase", "near_miss_leak_proxy", "retention"}:
                raise ValueError("Incomplete NLL summary")
            if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
                   for v in s.values()):
                raise ValueError("Invalid NLL summary")
        ce = arms["CE"]["summary"]
        cosine = arms["COS_EMA"]["summary"]
        contrast = arms["CONTRAST_EMA"]["summary"]
        wrong = arms["CONTRAST_SHUFFLED"]["summary"]
        deltas.append({
            "seed": seed,
            "paraphrase_contrast_minus_ce": contrast["paraphrase"] - ce["paraphrase"],
            "paraphrase_contrast_minus_cosine": contrast["paraphrase"] - cosine["paraphrase"],
            "paraphrase_contrast_minus_shuffled": contrast["paraphrase"] - wrong["paraphrase"],
            "near_miss_contrast_minus_ce": contrast["near_miss_leak_proxy"] - ce["near_miss_leak_proxy"],
            "retention_contrast_minus_ce": contrast["retention"] - ce["retention"],
        })
    means = {k: statistics.mean(d[k] for d in deltas)
             for k in deltas[0] if k != "seed"}
    wins = sum(d["paraphrase_contrast_minus_ce"] <= -0.05
               and d["paraphrase_contrast_minus_cosine"] <= -0.05
               for d in deltas)
    signal = (wins >= 2
              and means["paraphrase_contrast_minus_ce"] <= -0.05
              and means["paraphrase_contrast_minus_cosine"] <= -0.05
              and means["near_miss_contrast_minus_ce"] >= -0.05
              and means["retention_contrast_minus_ce"] <= 0.05)
    hurt = (means["paraphrase_contrast_minus_ce"] >= 0.05
            or means["retention_contrast_minus_ce"] > 0.05)
    status = ("BOUNDED_CONTRASTIVE_NLL_SIGNAL_NOT_UTILITY_GATE" if signal
              else "DIAGNOSTIC_HURT" if hurt
              else "DIAGNOSTIC_NO_ATTRIBUTABLE_GAIN")
    return {"status": status, "seed_wins": wins, "per_seed_deltas": deltas,
            "mean_deltas": means, "utility_gate_pass": False}


FIXTURE_SHA256 = "848021441551627c47107c7b1298d338ab674d8983ff10af4848cf33adf77748"
LICENSE_SHA256 = "4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c"


def run(master, out):
    rows = fixture()
    if fixture_sha(rows) != FIXTURE_SHA256:
        raise ValueError("Run12B preregistered fixture hash mismatch")
    report = {
        "schema": "v13.bodyjepa.350m_contrastive_disjoint_nll.v1",
        "model_id": MODEL_ID, "model_revision": REVISION,
        "master_sha256": MASTER_SHA256,
        "body_jepa_source_git_blob": "b560d4e88fe457f381e89dfc5d6188a8ec3b306b",
        "contrastive_trainer_source_git_blob": "a31a18d9be0b1137a10304f24d3a241d720bd247",
        "run11p_source_git_blob": "af685a22ddd4ff6412643a8849a1f00bf2112487",
        "fixture_sha256": fixture_sha(rows), "seeds": SEEDS, "arms": ARMS,
        "config": CONFIG, "evidence_class": "LINUX_FP32_TORCH_SYNTHETIC_HELDOUT",
        "baseline_method": "post_fit_disable_adapter_frozen_master",
        "runtime_jepa_weight": 0, "age_authority": 0,
        "redmi_measured": False, "b1_b2_utility_proven": False,
        "step2_utility_pass": False, "body_jepa_available": False,
        "production_activation": False, "whole_system_complete": False,
        "results": {}, "failures": [], "status": "INCOMPLETE",
        "prior_run11p_status": "DIAGNOSTIC_HURT",
        "experimental_variable": "contrastive EMA vs cosine EMA vs CE and deranged contrastive",
        "license_sha256": LICENSE_SHA256,
    }
    receipt = out / "report.json"
    atomic_write(receipt, json.dumps(report, sort_keys=True, indent=2))
    for seed in SEEDS:
        per = {}
        for arm in ARMS:
            cfg = dict(CONFIG, seed=seed,
                       jepa_weight=0.0 if arm == "CE" else 0.25,
                       jepa_target="shuffled" if arm == "CONTRAST_SHUFFLED" else "ema")
            trainer_cls = (ExportFreeContrastiveTrainer if arm.startswith("CONTRAST")
                           else ExportFreeCosineTrainer)
            items = [{"memory_id": f"synthetic_{i}", "prompt": q, "target": a}
                     for i, (q, a) in enumerate(rows["train"])]
            tr = None
            t0 = time.monotonic()
            try:
                tr = trainer_cls(master, out / "work" / f"{seed}-{arm}",
                                 master_sha256=MASTER_SHA256, anchors=(),
                                 cfg=cfg, arch="lfm2")
                result = tr.fit(items, "SYNTHETIC_RESEARCH_ONLY")
                if (result.get("artifact") != "NO_EXPORT" or result.get("hash") is not None
                        or result.get("files", {}).get("gguf") != "NO_EXPORT"
                        or not result.get("metrics")):
                    raise ValueError("Unexpected export or missing training metrics")
                if result["metrics"].get("steps") != 8:
                    raise ValueError("Incomplete eight-step fit")
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
    if not license_path.is_file() or license_path.is_symlink() or file_hash(license_path) != LICENSE_SHA256:
        raise ValueError("Pinned model license missing or changed")
    if a.out.exists() or a.out.is_symlink():
        raise ValueError("Refusing to overwrite or resume a research cohort")
    a.out.mkdir(parents=True)
    result = run(a.master, a.out)
    if result.get("completed_arms") != 12:
        raise ValueError("Incomplete 12-arm cohort")
    print(json.dumps({"status": result["status"], "completed_arms": result["completed_arms"],
                      "verdict": result["mean_deltas"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

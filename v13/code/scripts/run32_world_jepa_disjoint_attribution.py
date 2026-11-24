"""Run32 preregistered disjoint real-file World-JEPA attribution replication.

New seeds 201/202/203 only; original Z12b and Run28 slot-shared model and
collectors are imported unchanged. SHADOW research, never a gate promotion.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import platform
import tempfile
from types import SimpleNamespace

import numpy as np

from scripts import z12b_world_jepa as original
from scripts import run28_world_jepa_slot_real as slot

SEEDS = (201, 202, 203)
ARGS = {"train": 4000, "cf": 150, "attr": 300, "steps": 3000}
ORIGINAL_BLOB = "99a686a131a1bdc89efe0d0cf9610ec54cbd853b"
EXPERIMENT_BLOB = "2fd1366dc1b6d8c02803ee3254020f70e5bf3eb4"
SLOT_BLOB = "67e14e0d03c50c4767b74d5b02a819a95c6cc262"
SLOT_RUNNER_BLOB = "dbf3af3f8bc61a846eb542c7db3cc034e94f5bd7"
CLASSES = ("own_only_self", "world_only_world", "both_world", "none_self")
MIN_CLASS_N = 15


def four_class_attribution(seeds):
    """Frozen W7; never replaces original W6 or source-registered criteria."""
    if [s["seed"] for s in seeds] != list(SEEDS):
        raise ValueError("RUN32_SEED_IDENTITY_RED")
    records = []
    for s in seeds:
        attr = s["attribution"]
        a, b = attr["jepa"], attr["no_action"]
        for key, nkey in zip(CLASSES, ("own_only", "world_only", "both", "none")):
            if (type(a["n"][nkey]) is not int or a["n"][nkey] < MIN_CLASS_N
                    or a["n"][nkey] != b["n"][nkey]):
                raise ValueError("RUN32_ATTRIBUTION_CLASS_SUPPORT_RED")
            for arm in (a, b):
                v = arm[key]
                if (type(v) not in (int, float) or
                        not math.isfinite(v) or not 0 <= v <= 1):
                    raise ValueError("RUN32_ATTRIBUTION_RATE_RED")
        macro = lambda arm: sum(arm[k] for k in CLASSES) / len(CLASSES)
        records.append({
            "seed": s["seed"],
            "both_world_gap": round(a["both_world"] - b["both_world"], 6),
            "none_self_gap": round(a["none_self"] - b["none_self"], 6),
            "four_class_macro_gap": round(macro(a) - macro(b), 6),
            "jepa_four_class_macro": round(macro(a), 6),
            "zero_four_class_macro": round(macro(b), 6),
            "class_counts": a["n"],
        })
    mean = lambda key: float(np.mean([r[key] for r in records]))
    w7 = {
        "W7a_both_world_action_gain": mean("both_world_gap") >= .20 and
            all(r["both_world_gap"] >= .10 for r in records),
        "W7b_none_self_action_gain": mean("none_self_gap") >= .05 and
            all(r["none_self_gap"] >= 0 for r in records),
        "W7c_four_class_macro_action_gain": mean("four_class_macro_gap") >= .08 and
            all(r["four_class_macro_gap"] >= .04 for r in records),
    }
    return w7, {"per_seed": records,
                "mean_both_world_gap": round(mean("both_world_gap"), 6),
                "mean_none_self_gap": round(mean("none_self_gap"), 6),
                "mean_four_class_macro_gap": round(mean("four_class_macro_gap"), 6)}


def original_gates(seeds):
    gates, summary = original.criteria(seeds)
    rho = float(summary["spearman_conf_err_covered"])
    if not math.isfinite(rho):
        gates["W4_confidence_tracks_error"] = False
        summary["spearman_conf_err_covered"] = None
        summary["spearman_undefined_reason"] = "CONSTANT_OR_NONFINITE_CONFIDENCE"
    if (set(gates) != {
            "W1_cf_retrieval_covered", "W2_controls_fail",
            "W3_no_collapse", "W4_confidence_tracks_error",
            "W5_attribution_jepa", "W6_no_action_attribution_worse"}):
        raise ValueError("RUN32_ORIGINAL_GATE_SCHEMA_RED")
    if not all(type(v) in (bool, np.bool_) for v in gates.values()):
        raise ValueError("RUN32_GATE_TYPE_RED")
    return {k: bool(v) for k, v in gates.items()}, summary


def run(out: Path, work_root: Path):
    out, work_root = Path(out), Path(work_root)
    if (platform.system() != "Linux" or
            platform.machine().lower() not in ("x86_64", "amd64")):
        raise ValueError("RUN32_LINUX_REALFILE_ONLY")
    if out.exists() or work_root.exists():
        raise FileExistsError("RUN32_FRESH_PATHS_REQUIRED")
    work_root.mkdir(parents=True)
    orig_root = work_root / "original-z12b"
    slot_root = work_root / "slot-shared"
    orig_root.mkdir()
    slot_root.mkdir()
    args = SimpleNamespace(**ARGS)
    result = {
        "schema": "v13.run32.world_jepa_disjoint_attribution.v1",
        "evidence_kind": "REAL_FILE_LINUX_SHADOW_DISJOINT_EXPLORATORY",
        "registered": True, "seeds": list(SEEDS), "args": ARGS,
        "original_world_jepa_blob": ORIGINAL_BLOB,
        "original_z12b_experiment_blob": EXPERIMENT_BLOB,
        "slot_candidate_blob": SLOT_BLOB,
        "slot_runner_blob": SLOT_RUNNER_BLOB,
        "original_arm": [], "slot_arm": [],
        "original_gates": None, "slot_original_gates": None,
        "w7_gates": None, "w7_summary": None,
        "status": "INCOMPLETE", "capacity_confounded": True,
        "exact_paired_transitions": False,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "world_jepa_authority": "SHADOW",
        "redmi_measured": False, "whole_system_complete": False,
    }
    previous_tmp = os.environ.get("TMPDIR")
    try:
        # Path-only isolation for original's own tempfile.mkdtemp() collector.
        os.environ["TMPDIR"] = str(orig_root.resolve())
        tempfile.tempdir = None
        for seed in SEEDS:
            orig = original.run_seed(seed, args)
            result["original_arm"].append(orig)
            (work_root / f"original-{seed}-RESULT.json").write_text(
                json.dumps(orig, indent=2, allow_nan=False) + "\n")
        for seed in SEEDS:
            candidate = slot.run_seed(seed, args, slot_root)
            result["slot_arm"].append(candidate)
            (work_root / f"slot-{seed}-RESULT.json").write_text(
                json.dumps(candidate, indent=2, allow_nan=False) + "\n")
        result["original_gates"], result["original_summary"] = original_gates(result["original_arm"])
        result["slot_original_gates"], result["slot_summary"] = original_gates(result["slot_arm"])
        result["w7_gates"], result["w7_summary"] = four_class_attribution(result["slot_arm"])
        result["status"] = ("SHADOW_CANDIDATE_PASS_NOT_PROMOTED"
                            if all(result["slot_original_gates"].values()) and
                               all(result["w7_gates"].values())
                            else "SHADOW_CANDIDATE_FAIL")
    except Exception as exc:
        result["status"] = "RED"
        result["error"] = type(exc).__name__ + ": " + str(exc)[:300]
    finally:
        if previous_tmp is None:
            os.environ.pop("TMPDIR", None)
        else:
            os.environ["TMPDIR"] = previous_tmp
        tempfile.tempdir = None
        # Full raw per-seed checkpoint above retains confidence/error pairs.
        for arm in (result["original_arm"], result["slot_arm"]):
            for seed_result in arm:
                seed_result.pop("_conf_err", None)
        out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    if result["status"] == "RED":
        raise RuntimeError("RUN32_INCOMPLETE_OR_RED; original raw retained")
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--work-root", required=True, type=Path)
    args = p.parse_args(argv)
    r = run(args.out, args.work_root)
    print(r["status"], r["w7_gates"], r["slot_original_gates"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

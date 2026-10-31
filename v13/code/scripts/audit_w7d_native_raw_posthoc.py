#!/usr/bin/env python3
"""Posthoc independent read-only W7D original raw ZIP audit (not promotion).

Requires NumPy. Reimplements the frozen original double-argsort Spearman
formula without importing W7D candidate/evaluator. Refuses changed cohort,
missing original raw, altered stage exits, checksum mismatches and gate drift.
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile

import numpy as np

EXPECTED_HEAD = "9e432dd8255b0d718670c40247725d3a50bf2e74"
SEEDS = (701, 702, 703)
ARMS = ("balanced_slot", "delta_slot")


def audit(path):
    blob = open(path, "rb").read()
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError("W7D_ZIP_CRC_RED")
        sums = z.read("SHA256SUMS").decode().splitlines()
        for line in sums:
            sha, name = line.split("  ", 1)
            name = name.removeprefix("./")
            if hashlib.sha256(z.read(name)).hexdigest() != sha:
                raise ValueError("W7D_RAW_SHA256_RED:" + name)
        if z.read("HEAD.txt").decode().strip() != EXPECTED_HEAD:
            raise ValueError("W7D_HEAD_RED")
        for s in ("PINS", "VENV", "DEPS", "TEST", "REALFILE",
                  "REPORT_CHECK", "COMPILE", "PRIVACY", "DIFF"):
            if z.read(s + "_EXIT.txt").decode().strip() != "0":
                raise ValueError("W7D_STAGE_RED:" + s)
        report = json.loads(z.read("RESULT.json"))
        if (report["status"] != "SHADOW_CANDIDATE_FAIL"
                or report["seeds"] != list(SEEDS)
                or report["args"] != {"train": 4000, "cf": 150,
                                     "attr": 900, "steps": 3000}):
            raise ValueError("W7D_REGISTERED_RESULT_RED")
        if (report["age0"] != "RECORD_ONLY"
                or report["step2"] != "UTILITY_FAIL"
                or report["b3"] != "NO_PROMOTION"
                or report["body_jepa"] != "UNAVAILABLE"
                or report["jepa_weight"] != 0
                or report["world_jepa_authority"] != "SHADOW"
                or report["redmi_measured"]
                or report["whole_system_complete"]):
            raise ValueError("W7D_AUTHORITY_RED")

        def spearman(pairs):
            c = np.asarray([p[0] for p in pairs], dtype=float)
            e = np.asarray([p[1] for p in pairs], dtype=float)
            if len(c) < 2 or not np.isfinite(c).all() or not np.isfinite(e).all():
                raise ValueError("W7D_RHO_RAW_RED")
            return float(np.corrcoef(np.argsort(np.argsort(c)),
                                     np.argsort(np.argsort(e)))[0, 1])

        raw = {arm: [json.loads(z.read(
            f"work/{arm}-{seed}-RESULT.json")) for seed in SEEDS]
            for arm in ARMS}
        w6, w7, rho = {}, {}, {}
        for arm in ARMS:
            w6[arm], w7[arm], rho[arm] = [], [], []
            for seed, row in zip(SEEDS, raw[arm]):
                if row["seed"] != seed or row["n_train"] != 3600:
                    raise ValueError("W7D_SEED_TRAIN_RED")
                a, b = row["attribution"]["jepa"], row["attribution"]["no_action"]
                if a["n"] != b["n"] or min(a["n"].values()) < 15:
                    raise ValueError("W7D_SUPPORT_RED")
                w6[arm].append(round(a["balanced"] - b["balanced"], 6))
                w7[arm].append(round(a["none_self"] - b["none_self"], 6))
                rho[arm].append(spearman(row["_conf_err"]))
            if (report[arm + "_gates"]["W4_confidence_tracks_error"]
                    or report[arm + "_gates"]["W6_no_action_attribution_worse"]
                    or report[arm + "_w7"]["W7b_none_self_action_gain"]):
                raise ValueError("W7D_ORIGINAL_NEGATIVE_GATE_DRIFT")

        x = report["exploratory"]
        dif = lambda key: [round(a-b, 6) for a, b in
                           zip(key["delta_slot"], key["balanced_slot"])]
        if x["per_seed_w6_margin_delta"] != dif(w6):
            raise ValueError("W7D_D1_RAW_REPLAY_RED")
        if x["per_seed_w7b_none_gap_delta"] != dif(w7):
            raise ValueError("W7D_D2_RAW_REPLAY_RED")
        calc = dif(rho)
        if any(abs(a-b) > 2e-6 for a, b in
               zip(calc, x["per_seed_w4_rho_delta"])):
            raise ValueError("W7D_D3_RAW_REPLAY_RED")
        if (x["D1_w6_margin_improvement"]
                or x["D2_w7b_none_improvement"]
                or x["D3_w4_rho_improvement"]):
            raise ValueError("W7D_EXPLORATORY_FALSE_PROMOTION")
        return {
            "status": "INDEPENDENT_RAW_AUDIT_PASS_NEGATIVE_UTILITY_PRESERVED",
            "zip_sha256": hashlib.sha256(blob).hexdigest(),
            "inner_sha256_files": len(sums),
            "per_seed_w4_rho_delta": calc,
            "D1": x["per_seed_w6_margin_delta"],
            "D2": x["per_seed_w7b_none_gap_delta"],
            "original_candidate_status": report["status"],
            "negative_gates_preserved": True,
        }


if __name__ == "__main__":
    print(json.dumps(audit(sys.argv[1]), indent=2, allow_nan=False))

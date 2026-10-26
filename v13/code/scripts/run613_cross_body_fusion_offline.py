#!/usr/bin/env python3
"""Run613: posthoc fixed B1/B2/lexical fusion on SHA-closed Run608 native states.

Read-only offline analysis. No receiver, JEPA, weight update or gate promotion.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

import numpy as np
from scripts import run608_cross_body_paraphrase_native as R608

OUTER_SHA = "9cae2ac55a9ac773f3d3c2433d7ad485f479d8dc7b79f32e7555014f0eaad732"
INNER_SHA = "c6e6a7a6521d14c90805a996e723e9cd7716cd6ba6d13577480eff30349625ca"
ARTIFACT_ID = 12688049715
SEED = 20261026
SHUFFLES = 200
GATES = dict(R608.GATES)
EXPECTED_MEMBERS = {
    "RUN608_AUDIT_EXIT.txt", "RUN608_AUDIT_RAW.log",
    "RUN608_BOOTSTRAP_EXIT.txt", "RUN608_BOOTSTRAP_RAW.log",
    "RUN608_FIXTURE_EXIT.txt", "RUN608_FIXTURE_RAW.log",
    "RUN608_HEAD.txt", "RUN608_HOST.txt",
    "RUN608_NATIVE_EXIT.txt", "RUN608_NATIVE_RAW.log",
    "RUN608_NATIVE_REPORT.json", "RUN608_PRIVACY_EXIT.txt",
    "RUN608_PRIVACY_RAW.log", "RUN608_SHA256SUMS.txt",
    "RUN608_STATES.npz", "RUN608_SOURCE_SHA256.txt",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_original(path):
    data = Path(path).read_bytes()
    if sha(data) != OUTER_SHA:
        raise ValueError("Original Run608 artifact outer SHA mismatch")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if set(z.namelist()) != EXPECTED_MEMBERS or z.testzip() is not None:
            raise ValueError("Original Run608 artifact members/CRC mismatch")
        lines = z.read("RUN608_SHA256SUMS.txt").decode().splitlines()
        manifest = {}
        for line in lines:
            match = re.fullmatch(r"([a-f0-9]{64})  (?:[.]/)?(RUN608_[A-Za-z0-9_.-]+)", line)
            if not match or match.group(2) in manifest:
                raise ValueError("Original Run608 manifest malformed")
            manifest[match.group(2)] = match.group(1)
        if set(manifest) != EXPECTED_MEMBERS - {"RUN608_SHA256SUMS.txt"}:
            raise ValueError("Original Run608 manifest member set mismatch")
        if any(sha(z.read(name)) != h for name, h in manifest.items()):
            raise ValueError("Original Run608 manifest content mismatch")
        if any(z.read("RUN608_" + kind + "_EXIT.txt").strip() != b"0"
               for kind in ("AUDIT", "BOOTSTRAP", "FIXTURE", "NATIVE", "PRIVACY")):
            raise ValueError("Original Run608 has nonzero exit")
        state = z.read("RUN608_STATES.npz")
        if sha(state) != INNER_SHA:
            raise ValueError("Original Run608 native state SHA mismatch")
        original = json.loads(z.read("RUN608_NATIVE_REPORT.json"))
        if (original.get("status") != "NO_PARAPHRASE_PROXY_SIGNAL"
                or original.get("states_sha256") != INNER_SHA
                or original.get("cohort_blob") != R608.COHORT_BLOB
                or original.get("gates") != GATES
                or original.get("b3_promoted") is not False
                or original.get("no_weight_updates") is not True):
            raise ValueError("Original Run608 report/authority mismatch")
    with np.load(io.BytesIO(state), allow_pickle=False) as arrays:
        if set(arrays.files) != {"x_b1", "y_b2", "prompt_ids", "train_idx", "test_idx"}:
            raise ValueError("Original Run608 native NPZ keys mismatch")
        return {k: arrays[k].copy() for k in arrays.files}


def validate_arrays(data, rows):
    x = np.asarray(data["x_b1"])
    y = np.asarray(data["y_b2"])
    train = np.asarray(data["train_idx"])
    test = np.asarray(data["test_idx"])
    ids = np.asarray(data["prompt_ids"])
    expected_train = np.asarray([i for i, r in enumerate(rows) if r["topic"] in R608.TRAIN_TOPICS])
    expected_test = np.asarray([i for i, r in enumerate(rows) if r["topic"] in R608.TEST_TOPICS])
    if (x.shape != (80, 2048) or y.shape != (80, 1024)
            or train.shape != (60,) or test.shape != (20,)
            or not np.array_equal(train, expected_train)
            or not np.array_equal(test, expected_test)
            or not np.array_equal(ids, [r["id"] for r in rows])
            or not np.issubdtype(x.dtype, np.number)
            or not np.issubdtype(y.dtype, np.number)
            or not np.isfinite(x).all() or not np.isfinite(y).all()
            or np.any(np.linalg.norm(x, axis=1) <= 1e-12)
            or np.any(np.linalg.norm(y, axis=1) <= 1e-12)):
        raise ValueError("Run608 states/cohort/split invalid")
    return x.astype(float), y.astype(float), train, test


def opposite_indices(rows, test):
    names = {rows[idx]["id"]: i for i, idx in enumerate(test)}
    opposite = []
    for idx in test:
        row = rows[idx]
        key = row["fact_id"] + "-" + ("B" if row["variant"] == "A" else "A")
        if key not in names:
            raise ValueError("Missing frozen opposite paraphrase")
        opposite.append(names[key])
    if any(i == j for i, j in enumerate(opposite)):
        raise ValueError("Self-match in opposite candidates")
    return np.asarray(opposite, dtype=int)


def lexical_matrix(rows, test):
    sets = [set(re.findall(r"[a-z0-9]+", rows[idx]["text"].lower())) for idx in test]
    matrix = np.zeros((len(test), len(test)), dtype=float)
    for i, a in enumerate(sets):
        for j, b in enumerate(sets):
            if i != j:
                matrix[i, j] = len(a & b) / len(a | b) if a | b else 0.
    return matrix


def score(matrix, opposite):
    a = np.asarray(matrix, dtype=float)
    if a.shape != (len(opposite), len(opposite)) or not np.isfinite(a).all():
        raise ValueError("Invalid retrieval score matrix")
    ranks = []
    for i in range(len(opposite)):
        candidates = [j for j in range(len(opposite)) if j != i]
        # Deterministic first-index tie break, as in original numpy argmax.
        order = sorted(candidates, key=lambda j: (-a[i, j], j))
        ranks.append(order.index(int(opposite[i])) + 1)
    return {"top1": float(np.mean(np.asarray(ranks) == 1)),
            "mrr": float(np.mean(1. / np.asarray(ranks, dtype=float)))}


def scaled_nonself(matrix):
    a = np.asarray(matrix, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or not np.isfinite(a).all():
        raise ValueError("Invalid similarity for fixed fusion")
    out = np.zeros_like(a)
    for i in range(len(a)):
        mask = np.arange(len(a)) != i
        values = a[i, mask]
        lo, hi = values.min(), values.max()
        if hi - lo > 1e-12:
            out[i, mask] = (values - lo) / (hi - lo)
    return out


def fusion(lexical, native):
    if lexical.shape != native.shape:
        raise ValueError("Fusion source dimensions mismatch")
    return .5 * scaled_nonself(lexical) + .5 * scaled_nonself(native)


def analyze(data, rows):
    x, y, train, test = validate_arrays(data, rows)
    opposite = opposite_indices(rows, test)
    x, y = R608.normalize(x), R608.normalize(y)
    xm, ym = x[train].mean(0), y[train].mean(0)
    xt, xv = R608.normalize(x[train] - xm), R608.normalize(x[test] - xm)
    yt, yv = R608.normalize(y[train] - ym), R608.normalize(y[test] - ym)
    ridge = np.linalg.solve(xt @ xt.T + R608.ALPHA * np.eye(len(train)), np.eye(len(train)))
    cross = xv @ xt.T
    mapped = R608.normalize(cross @ ridge @ yt) @ yv.T
    lexical = lexical_matrix(rows, test)
    b1 = xv @ xv.T
    b2 = yv @ yv.T
    metrics = {
        "lexical": score(lexical, opposite),
        "mapped_native": score(mapped, opposite),
        "b1_only": score(b1, opposite),
        "b2_only": score(b2, opposite),
        "fixed_fusion": score(fusion(lexical, mapped), opposite),
    }
    # Exact original Run608 top1 controls must be reproduced before fusion.
    if (metrics["mapped_native"]["top1"] != .25
            or metrics["lexical"]["top1"] != .30):
        raise ValueError("Original Run608 heldout top1 not reproduced")
    rng = np.random.default_rng(SEED)
    null = []
    for _ in range(SHUFFLES):
        perm = rng.permutation(len(train))
        scrambled = R608.normalize(cross @ ridge @ yt[perm]) @ yv.T
        null.append(score(fusion(lexical, scrambled), opposite)["top1"])
    null = np.asarray(null)
    observed = metrics["fixed_fusion"]["top1"]
    p = (1 + int(np.count_nonzero(null >= observed))) / (SHUFFLES + 1)
    baseline = max(metrics[k]["top1"] for k in ("lexical", "b1_only", "b2_only"))
    gain = observed - baseline
    signal = bool(gain >= .10 - 1e-12 and p <= .05)
    return {"schema": "V13_RUN613_FROZEN_POSTHOC_FUSION_V1",
            "status": "EXPLORATORY_FUSION_PROXY_GAIN" if signal else "NO_FUSION_PROXY_GAIN",
            "metrics": metrics, "null_fusion_mean": float(null.mean()),
            "null_fusion_p95": float(np.percentile(null, 95)),
            "empirical_p_fusion": float(p), "fusion_gain_vs_best_single": float(gain),
            "frozen_alpha": .5, "ridge_alpha": R608.ALPHA,
            "shuffles": SHUFFLES, "seed": SEED, "train_n": 60, "heldout_n": 20,
            "evidence_level": "POSTHOC_ORIGINAL_LINUX_NATIVE_READONLY_STATES",
            "original_artifact_id": ARTIFACT_ID,
            "original_outer_sha256": OUTER_SHA, "original_inner_sha256": INNER_SHA,
            "original_cohort_blob": R608.COHORT_BLOB,
            "no_native_inference_this_run": True, "no_weight_updates": True,
            "can_latent_inject": False, "b3_promoted": False,
            "redmi_measured": False, "gates": dict(GATES),
            "canonical_architecture_complete": False, "user_full_scope_complete": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--original-zip", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        rows = R608.load_cohort()["prompts"]
        result = analyze(read_original(args.original_zip), rows)
    except Exception as exc:
        result = {"schema": "V13_RUN613_FROZEN_POSTHOC_FUSION_V1",
                  "status": "ERROR", "error_type": type(exc).__name__,
                  "error": str(exc)[:300], "gates": dict(GATES),
                  "b3_promoted": False, "canonical_architecture_complete": False,
                  "user_full_scope_complete": False}
        path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
        raise
    path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "metrics": result["metrics"],
                      "empirical_p_fusion": result["empirical_p_fusion"]}, sort_keys=True))


if __name__ == "__main__":
    main()

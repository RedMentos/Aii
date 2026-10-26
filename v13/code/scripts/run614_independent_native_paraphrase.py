#!/usr/bin/env python3
"""Run614: independent frozen synthetic paraphrases, real pinned B1/B2 native taps.

New source-disjoint cohort. Read-only model weights; no JEPA, receiver or gate promotion.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np

from v13.common import APP, atomic_write, dumps
from v13.runners import TAP_SPECS
from scripts import run606_cross_body_latent_shadow as R606
from scripts import run608_cross_body_paraphrase_native as R608
from scripts import run613_cross_body_fusion_offline as F

PROOF = APP / "docs/proofs/continuation-20261026/run614-independent-native-paraphrase"
COHORT = PROOF / "RUN614_COHORT.json"
COHORT_BLOB = "7068267d41a1719abea3a54c84b1d0223444df1d"
SEED = 2026102614
TRAIN_TOPICS = ("architecture", "ecology", "navigation", "chemistry", "history", "biology")
TEST_TOPICS = ("literature", "geography")
GATES = dict(R606.GATES)
CONTROLS = 200


def load_cohort(path=COHORT):
    if R606.git_blob_sha(path) != COHORT_BLOB:
        raise ValueError("Run614 frozen cohort blob changed")
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = d.get("prompts", [])
    if (d.get("schema") != "V13_RUN614_INDEPENDENT_PARAPHRASE_COHORT_V1"
            or d.get("seed") != SEED or tuple(d.get("train_topics", [])) != TRAIN_TOPICS
            or tuple(d.get("test_topics", [])) != TEST_TOPICS
            or len(rows) != 80 or len({r.get("id") for r in rows}) != 80
            or len({r.get("text") for r in rows}) != 80):
        raise ValueError("Run614 cohort schema/seed/unique rows invalid")
    facts = {}
    for row in rows:
        if (row.get("topic") not in TRAIN_TOPICS + TEST_TOPICS
                or row.get("variant") not in ("A", "B")
                or not isinstance(row.get("text"), str) or not row["text"].strip()
                or row.get("fact_id") != row["id"].rsplit("-", 1)[0]):
            raise ValueError("Run614 invalid paired source")
        facts.setdefault(row["fact_id"], []).append(row)
    if (len(facts) != 40
            or any(len(v) != 2 or {r["variant"] for r in v} != {"A", "B"}
                   or len({r["topic"] for r in v}) != 1 for v in facts.values())
            or any(sum(r["topic"] == t for r in rows) != 10 for t in TRAIN_TOPICS + TEST_TOPICS)):
        raise ValueError("Run614 invalid fact pairs/topics")
    return d


def evaluate(x, y, rows, controls=CONTROLS):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    train = np.asarray([i for i, r in enumerate(rows) if r["topic"] in TRAIN_TOPICS])
    test = np.asarray([i for i, r in enumerate(rows) if r["topic"] in TEST_TOPICS])
    if (x.shape != (80, 2048) or y.shape != (80, 1024)
            or len(train) != 60 or len(test) != 20 or controls != CONTROLS
            or not np.isfinite(x).all() or not np.isfinite(y).all()
            or np.any(np.linalg.norm(x, axis=1) <= 1e-12)
            or np.any(np.linalg.norm(y, axis=1) <= 1e-12)):
        raise ValueError("Run614 native states invalid")
    opposite = F.opposite_indices(rows, test)
    x, y = R608.normalize(x), R608.normalize(y)
    xm, ym = x[train].mean(0), y[train].mean(0)
    xt, xv = R608.normalize(x[train] - xm), R608.normalize(x[test] - xm)
    yt, yv = R608.normalize(y[train] - ym), R608.normalize(y[test] - ym)
    cross = xv @ xt.T
    ridge = np.linalg.solve(xt @ xt.T + np.eye(len(train)), np.eye(len(train)))
    mapped = R608.normalize(cross @ ridge @ yt) @ yv.T
    lexical = F.lexical_matrix(rows, test)
    b1, b2 = xv @ xv.T, yv @ yv.T
    fused = F.fusion(lexical, mapped)
    metrics = {name: F.score(matrix, opposite) for name, matrix in (
        ("lexical", lexical), ("mapped_native", mapped), ("b1_only", b1),
        ("b2_only", b2), ("fixed_fusion", fused))}
    rng = np.random.default_rng(SEED)
    null_mapped, null_fused = [], []
    for _ in range(controls):
        perm = rng.permutation(len(train))
        shuffled = R608.normalize(cross @ ridge @ yt[perm]) @ yv.T
        null_mapped.append(F.score(shuffled, opposite)["top1"])
        null_fused.append(F.score(F.fusion(lexical, shuffled), opposite)["top1"])
    rng_labels = np.random.default_rng(SEED + 1)
    null_b2 = []
    for _ in range(controls):
        # Random bijection over candidate labels, with no self-target.
        while True:
            perm = rng_labels.permutation(len(test))
            candidate = perm[opposite]
            if np.all(candidate != np.arange(len(test))):
                break
        null_b2.append(F.score(b2, candidate)["top1"])
    pvalue = lambda arr, observed: float(
        (1 + np.count_nonzero(np.asarray(arr) >= observed)) / (controls + 1))
    p_mapped = pvalue(null_mapped, metrics["mapped_native"]["top1"])
    p_fused = pvalue(null_fused, metrics["fixed_fusion"]["top1"])
    p_b2 = pvalue(null_b2, metrics["b2_only"]["top1"])
    best = max(metrics[k]["top1"] for k in ("lexical", "b1_only", "b2_only"))
    within = bool(metrics["b2_only"]["top1"] >= .55
                  and metrics["b2_only"]["top1"] - metrics["lexical"]["top1"] >= .15 - 1e-12
                  and p_b2 <= .05)
    cross_signal = bool(
        (metrics["mapped_native"]["top1"] - best >= .10 - 1e-12 and p_mapped <= .05)
        or (metrics["fixed_fusion"]["top1"] - best >= .10 - 1e-12 and p_fused <= .05))
    return {
        "metrics": metrics, "empirical_p_mapped": p_mapped,
        "empirical_p_fusion": p_fused, "empirical_p_b2_only": p_b2,
        "null_mapped_mean": float(np.mean(null_mapped)),
        "null_fusion_mean": float(np.mean(null_fused)),
        "null_b2_only_mean": float(np.mean(null_b2)),
        "within_body_b2_proxy": within, "cross_body_proxy": cross_signal,
        "best_single_top1": float(best), "train_n": len(train), "heldout_n": len(test),
        "seed": SEED, "shuffles": controls, "ridge_alpha": 1., "fusion_alpha": .5,
    }


def run(home, out, states_path):
    home, out, states_path = Path(home), Path(out), Path(states_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    states_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "V13_RUN614_INDEPENDENT_NATIVE_PARAPHRASE_V1",
        "status": "INCOMPLETE", "evidence_level": "LINUX_NATIVE_PAIRED_READONLY",
        "cohort_blob": COHORT_BLOB, "seed": SEED, "gates": dict(GATES),
        "no_weight_updates": True, "can_latent_inject": False,
        "b3_promoted": False, "redmi_measured": False,
        "canonical_architecture_complete": False, "user_full_scope_complete": False,
    }
    def save():
        atomic_write(out, (dumps(report) + "\n").encode())
    save()
    try:
        cohort = load_cohort()
        rows = cohort["prompts"]
        specs = json.loads((APP / "specs/models.json").read_text())
        if specs["runner"]["linux_binaries"]["linux-x86_64"]["sha256"] != R606.ARCHIVE_SHA:
            raise ValueError("Pinned native runner changed")
        server = home / "bin/llama-server"
        if not server.is_file():
            raise ValueError("Native server missing")
        report["runner_sha256"] = R606.file_sha(server)
        arrays, receipts = [], {}
        with tempfile.TemporaryDirectory(prefix="v13-run614-") as td:
            for role, key, expected, dim in (
                ("B1_DETAIL", "body", R606.B1_SHA, 2048),
                ("B2_GIST", "gist", R606.B2_SHA, 1024),
            ):
                spec = specs["models"][key]
                model = home / "models" / key / spec["main_file"]
                if R606.file_sha(model) != expected or spec["files"][0]["sha256"] != expected:
                    raise ValueError("Pinned " + role + " model changed")
                if TAP_SPECS[key][1] != dim:
                    raise ValueError("Native tap dimension changed")
                values, rc = R606.capture(model, server, role, key, rows, Path(td) / key)
                arrays.append(values)
                receipts[role] = rc
                report.setdefault("models", {})[role] = {
                    "model_id": spec["model_id"], "revision": spec["revision"],
                    "sha256": expected, "tap_id": TAP_SPECS[key][0],
                    "dimension": dim, "rows": len(values)}
                report.setdefault("receipts", {})[role] = rc
                save()
        metrics = evaluate(arrays[0], arrays[1], rows)
        with tempfile.NamedTemporaryFile(dir=states_path.parent, suffix=".npz", delete=False) as f:
            tmp = Path(f.name)
            np.savez_compressed(f, x_b1=arrays[0], y_b2=arrays[1],
                prompt_ids=np.array([r["id"] for r in rows]),
                train_idx=np.array([i for i, r in enumerate(rows) if r["topic"] in TRAIN_TOPICS]),
                test_idx=np.array([i for i, r in enumerate(rows) if r["topic"] in TEST_TOPICS]))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, states_path)
        status = ("CROSS_BODY_PROXY_SIGNAL" if metrics["cross_body_proxy"]
                  else "WITHIN_BODY_B2_PROXY_ONLY" if metrics["within_body_b2_proxy"]
                  else "NO_REPLICATED_PROXY")
        report.update(metrics=metrics, states_sha256=R606.file_sha(states_path),
                      states_bytes=states_path.stat().st_size, status=status)
        save()
        return report
    except BaseException as exc:
        report.update(status="ERROR", error_type=type(exc).__name__,
                      error=str(exc)[:300])
        save()
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--home", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--states", required=True)
    args = p.parse_args()
    report = run(args.home, args.out, args.states)
    print(dumps({"status": report["status"], "metrics": report["metrics"],
                 "states_sha256": report["states_sha256"]}))


if __name__ == "__main__":
    main()

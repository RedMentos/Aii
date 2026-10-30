#!/usr/bin/env python3
"""Exploratory C2 Needle3/scaffold threshold audit on *archived* native rows.

Not a fresh holdout, deployable calibration or C2 quality gate. The source ZIP
and every original raw row are SHA256-bound; this script never invokes models.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import zipfile

ZIP_SHA = "c4dd65ba18b446447271d4780b0741a4dc6994ab489496592ab3447123747076"
NATIVE_SHA = "b5901e8746cf008fca8b21b313f53f65697eacfa4cee126a6dfe62a7a3abb67d"
SCAFFOLD_SHA = "0ec021e69441aaf1a91e8ca6228b5d83d680508866494ae0e7c722e937474d7f"
REPORT_SHA = "7e11718ca7fba53e53de0179f8d8165d5d4cea80226ab6869501dfcabd144578"
CORPUS_SHA = "54f3da390fb79c3f966edd61d3390d94dc59d850987174c644ef45ef531a54e6"
ROUTES = ("simple", "detail", "gist", "both")
THRESHOLDS = (0., .25, .5, .75, .9, .99, 1.01)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_archive(path):
    path = Path(path)
    if digest(path.read_bytes()) != ZIP_SHA:
        raise ValueError("Original C2 native ZIP SHA256 mismatch")
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError("Original C2 native ZIP CRC failure")
        checks = z.read("SHA256SUMS.txt").decode().splitlines()
        for line in checks:
            expected, name = line.split("  ", 1)
            name = name.removeprefix("./")
            if digest(z.read(name)) != expected:
                raise ValueError("Original C2 inner evidence SHA mismatch: " + name)
        native = z.read("bench/needle.rows.json")
        scaffold = z.read("bench/scaffold.rows.json")
        report = z.read("bench/report.json")
    if (digest(native) != NATIVE_SHA or digest(scaffold) != SCAFFOLD_SHA
            or digest(report) != REPORT_SHA):
        raise ValueError("Original C2 row/report SHA mismatch")
    meta = json.loads(report)
    if (meta.get("corpus_sha256") != CORPUS_SHA or meta.get("n") != 96
            or meta.get("label_source") !=
            "AUTHOR_LABELS_FROM_TOOL_DEFINITION (Claude-written, not user labels; see specs/control_tools.json select_processing)"):
        raise ValueError("Original C2 cohort provenance mismatch")
    n, s = json.loads(native), json.loads(scaffold)
    validate(n, s, exact_n=96)
    return n, s, len(checks)


def validate(native, scaffold, exact_n=None):
    if (not isinstance(native, list) or not isinstance(scaffold, list)
            or len(native) != len(scaffold) or not native
            or (exact_n is not None and len(native) != exact_n)):
        raise ValueError("C2 paired native/scaffold rows incomplete")
    ids = set()
    counts = {c: 0 for c in ROUTES}
    for a, b in zip(native, scaffold):
        if (not isinstance(a, dict) or not isinstance(b, dict)
                or type(a.get("id")) is not str or a["id"] in ids
                or a["id"] != b.get("id") or a.get("label") != b.get("label")
                or a.get("label") not in ROUTES or b.get("pred") not in ROUTES
                or a.get("pred") not in (*ROUTES, None)):
            raise ValueError("C2 source ID, label or route mismatch")
        ids.add(a["id"])
        counts[a["label"]] += 1
        c = a.get("confidence")
        if c is not None and (type(c) not in (float, int) or not math.isfinite(c) or not 0 <= c <= 1):
            raise ValueError("C2 native confidence invalid")
    if any(v < 4 or v % 4 for v in counts.values()):
        raise ValueError("C2 class fold coverage invalid")
    if exact_n == 96 and any(v != 24 for v in counts.values()):
        raise ValueError("Original C2 96-row class balance invalid")
    return counts


def fold_ids(native):
    seen = {c: 0 for c in ROUTES}
    result = []
    for row in native:
        label = row["label"]
        result.append(seen[label] % 4)
        seen[label] += 1
    return result


def predict(a, b, threshold):
    conf = a.get("confidence")
    if (a.get("pred") in ROUTES and type(conf) in (float, int)
            and math.isfinite(conf) and conf >= threshold):
        return a["pred"], True
    return b["pred"], False


def score(labels, preds):
    n = len(labels)
    acc = sum(x == y for x, y in zip(labels, preds)) / n
    f1 = []
    for c in ROUTES:
        tp = sum(x == y == c for x, y in zip(labels, preds))
        fp = sum(x != c and y == c for x, y in zip(labels, preds))
        fn = sum(x == c and y != c for x, y in zip(labels, preds))
        f1.append(0. if tp == 0 else 2 * tp / (2 * tp + fp + fn))
    return {"n": n, "accuracy": round(acc, 6),
            "macro_f1": round(sum(f1) / len(f1), 6)}


def evaluate(native, scaffold, indices, threshold):
    labels = [native[i]["label"] for i in indices]
    pairs = [predict(native[i], scaffold[i], threshold) for i in indices]
    preds = [p for p, _ in pairs]
    return score(labels, preds), sum(used for _, used in pairs), preds


def cross_validate(native, scaffold):
    validate(native, scaffold)
    folds = fold_ids(native)
    heldout = []
    all_preds = [None] * len(native)
    native_count = 0
    for fold in range(4):
        train = [i for i, f in enumerate(folds) if f != fold]
        test = [i for i, f in enumerate(folds) if f == fold]
        if not train or not test:
            raise ValueError("Empty C2 train/holdout fold")
        candidates = []
        for t in THRESHOLDS:
            m, _, _ = evaluate(native, scaffold, train, t)
            candidates.append((m["accuracy"], t))
        # Deterministic tie-break: larger threshold, prefer the safe scaffold.
        best_acc, t = max(candidates)
        metrics, count, preds = evaluate(native, scaffold, test, t)
        for i, pred in zip(test, preds):
            all_preds[i] = pred
        native_count += count
        heldout.append({"fold": fold, "threshold": t,
                        "train_accuracy": best_acc,
                        "heldout": metrics, "native_selected": count})
    labels = [r["label"] for r in native]
    scaffold_score = score(labels, [r["pred"] for r in scaffold])
    native_score = score(labels, [r["pred"] for r in native])
    cv_score = score(labels, all_preds)
    return {
        "schema": "v13.c2.archived_native_scaffold_cv.v1",
        "status": ("EXPLORATORY_HYBRID_SIGNAL_NO_PROMOTION"
                   if cv_score["accuracy"] > scaffold_score["accuracy"]
                   else "NO_C2_HYBRID_GAIN"),
        "evidence_class": "POST_HOC_ARCHIVED_LINUX_NATIVE_ROWS_ONLY",
        "folds": heldout, "native_selected_total": native_count,
        "native": native_score, "scaffold": scaffold_score,
        "cross_validated_hybrid": cv_score,
        "paired_accuracy_delta_vs_scaffold":
            round(cv_score["accuracy"] - scaffold_score["accuracy"], 6),
        "source_zip_sha256": ZIP_SHA, "native_rows_sha256": NATIVE_SHA,
        "scaffold_rows_sha256": SCAFFOLD_SHA, "corpus_sha256": CORPUS_SHA,
        "author_labels_only": True, "new_native_calls": 0,
        "c2_quality_promoted": False, "redmi_measured": False,
        "age_authority": 0, "step2_utility_pass": False,
        "b3_authority": 0, "whole_system_complete": False,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--original-zip", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.out.exists() or a.out.is_symlink():
        raise ValueError("Refusing to overwrite a C2 source-bound receipt")
    n, s, checks = load_archive(a.original_zip)
    result = cross_validate(n, s)
    result["original_inner_hash_count"] = checks
    with a.out.open("x", encoding="utf-8") as f:
        f.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
        f.flush()
    print(json.dumps({"status": result["status"],
                      "hybrid": result["cross_validated_hybrid"],
                      "scaffold": result["scaffold"]}), flush=True)


if __name__ == "__main__":
    main()

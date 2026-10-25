#!/usr/bin/env python3
"""Run328 independent read-only native FP32 epoch tensor-delta audit.

Only a real GGUF input and a complete Run320/321 report can produce native
evidence. Source-only fixture tests are never promoted.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

SCHEMA = "V13_RUN328_NATIVE_FP32_TENSOR_DELTA_V1"
MASTER_SHA = "5d200c19f13483e66b39d9feb3353032581882f3eb10cc8752f027d4688d6e6f"
SELECTED = tuple("blk.%d.ffn_down.weight" % i for i in (12, 13, 14, 15))
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL", "Body_JEPA": "UNAVAILABLE",
         "jepa_weight": 0, "V13": "INCOMPLETE"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_report_and_paths(report, master, epoch1, epoch2):
    require(report.get("status") == "COMPLETE_NATIVE_EVALUATION",
            "original Run320 native evaluation incomplete")
    require(report.get("native_training_executed") is True,
            "original native optimizer execution not proven")
    require(report.get("gates") == GATES and report.get("weights_published") is False,
            "original negative gates or publication flag changed")
    require(report.get("master_sha256") == MASTER_SHA, "original FP32 master SHA drift")
    receipts = report.get("checkpoint_receipts")
    require(isinstance(receipts, list) and len(receipts) == 2,
            "exact two epoch receipts required")
    paths = (Path(master), Path(epoch1), Path(epoch2))
    for path in paths:
        require(path.is_file() and not path.is_symlink(), "missing or symlink GGUF")
    hashes = [digest(path) for path in paths]
    require(hashes[0] == MASTER_SHA, "original full master bytes mismatch")
    for i, actual in enumerate(hashes[1:]):
        require(receipts[i].get("epoch") == i + 1 and
                receipts[i].get("sha256") == actual,
                "native checkpoint SHA/epoch mismatch")
    require(report.get("final_master_sha256") == hashes[-1],
            "final trained master SHA mismatch")
    return hashes


def assess(original, epoch1, epoch2):
    """Pure receipt comparison; does not independently establish native execution."""
    keys = set(original)
    require(len(keys) == len(original) and keys == set(epoch1) == set(epoch2),
            "tensor inventory changed")
    require(set(SELECTED) <= keys, "frozen selected FFN tensors absent")
    for name in keys:
        rows = (original[name], epoch1[name], epoch2[name])
        require(all(row["shape"] == rows[0]["shape"] and
                    row["type"] == rows[0]["type"] and
                    row["bytes"] == rows[0]["bytes"] for row in rows),
                "tensor shape/type/byte length drift: " + name)
        if name in SELECTED:
            require(all(row["finite"] for row in rows),
                    "non-finite selected tensor: " + name)
        else:
            require(rows[0]["sha256"] == rows[1]["sha256"] == rows[2]["sha256"],
                    "unselected parameter changed: " + name)
    first = sorted(k for k in SELECTED if original[k]["sha256"] != epoch1[k]["sha256"])
    second = sorted(k for k in SELECTED if epoch1[k]["sha256"] != epoch2[k]["sha256"])
    require(first, "no selected FP32 tensor changed during epoch1")
    require(second, "no selected FP32 tensor changed during epoch2")
    return {"changed_epoch1": first, "changed_epoch2": second,
            "unchanged_nonselected": len(keys) - len(SELECTED)}


def inspect(path):
    import gguf  # official b10964 reader supplied by native job
    import numpy as np
    reader = gguf.GGUFReader(str(path))
    arch, kind = reader.get_field("general.architecture"), reader.get_field("general.file_type")
    require(arch is not None and arch.contents() == "lfm2" and
            kind is not None and int(kind.contents()) == 0,
            "not original lfm2 ALL_F32 GGUF")
    require(len(reader.tensors) == 148, "original GGUF tensor count changed")
    tensors, raw = {}, {}
    total = 0
    for tensor in reader.tensors:
        name = str(tensor.name)
        require(name not in tensors and
                int(tensor.tensor_type) == int(gguf.GGMLQuantizationType.F32),
                "duplicate or non-F32 tensor")
        data = tensor.data
        total += int(tensor.n_elements)
        entry = {"sha256": hashlib.sha256(memoryview(data).cast("B")).hexdigest(),
                 "shape": [int(x) for x in tensor.shape],
                 "type": int(tensor.tensor_type),
                 "bytes": int(data.nbytes),
                 "finite": bool(np.isfinite(data).all()) if name in SELECTED else True}
        tensors[name] = entry
        if name in SELECTED:
            raw[name] = data
    require(total == 354_483_968, "original FP32 element count changed")
    require(set(SELECTED) <= set(tensors), "selected original tensor names absent")
    return reader, tensors, raw


def deltas(first, second):
    import numpy as np
    result = {}
    for name in SELECTED:
        a = first[name].astype(np.float64)
        b = second[name].astype(np.float64)
        diff = b - a
        count = int(np.count_nonzero(diff))
        norm = float(np.linalg.norm(diff.ravel()))
        peak = float(np.max(np.abs(diff)))
        require(math.isfinite(norm) and math.isfinite(peak), "nonfinite tensor delta")
        result[name] = {"changed_elements": count, "l2": norm, "max_abs": peak}
    return result


def audit(master, epoch1, epoch2, report):
    # Independently require Run321 exact raw cohort/score consistency first.
    from audit_native_lfm2_epoch_eval_run321 import audit as original_audit
    source_receipt = original_audit(report)
    require(source_receipt["status"] == "PASS_SOURCE_ONLY",
            "original independent Run321 raw audit failed")
    hashes = verify_report_and_paths(report, master, epoch1, epoch2)
    m_reader, m, mr = inspect(master)
    e1_reader, e1, r1 = inspect(epoch1)
    e2_reader, e2, r2 = inspect(epoch2)
    checked = assess(m, e1, e2)
    metrics = {"baseline_to_epoch1": deltas(mr, r1),
               "epoch1_to_epoch2": deltas(r1, r2)}
    # Keep readers alive through all mmap-based comparisons.
    assert m_reader is not None and e1_reader is not None and e2_reader is not None
    return {"schema": SCHEMA, "status": "PASS_NATIVE_WEIGHT_DELTA_DIAGNOSTIC_NO_ACTIVATION",
            "evidence_level": "LINUX_NATIVE_FP32_TENSOR_BYTE_AUDIT",
            "original_run321_status": source_receipt["status"],
            "master_sha256": hashes[0], "epoch_sha256": hashes[1:],
            "tensor_count": len(m), "frozen_selected_tensors": list(SELECTED),
            "selected_sha256": {name: [m[name]["sha256"], e1[name]["sha256"],
                                       e2[name]["sha256"]] for name in SELECTED},
            "changes": checked, "metrics": metrics,
            "model_weights_published": False, "model_activated": False,
            "claim_limit": "Two synthetic native epochs only; no Body-JEPA, AG6, Redmi or general learning proof",
            "gates": GATES}


def main():
    ap = argparse.ArgumentParser()
    for name in ("master", "epoch1", "epoch2", "report", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    args = ap.parse_args()
    try:
        report = json.loads(args.report.read_text())
        result = audit(args.master, args.epoch1, args.epoch2, report)
    except (ValueError, OSError, KeyError, TypeError, ImportError, AssertionError) as exc:
        result = {"schema": SCHEMA, "status": "FAIL_CLOSED",
                  "error": type(exc).__name__ + ": " + str(exc)[:500],
                  "model_weights_published": False, "model_activated": False,
                  "gates": GATES}
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS_NATIVE_WEIGHT_DELTA_DIAGNOSTIC_NO_ACTIVATION" else 2)


if __name__ == "__main__":
    main()

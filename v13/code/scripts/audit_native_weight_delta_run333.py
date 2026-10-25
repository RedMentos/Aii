#!/usr/bin/env python3
"""Run333 isolated read-only GGUF tensor-byte audit for b10964 saver metadata omission.

The original Run328 auditor is not modified or weakened. Missing general.file_type
is permitted only on epoch checkpoints, never on the exact original F32 master.
All tensor payload types, inventories, bytes and numerical deltas remain strict.
"""
import argparse
import hashlib
import json
from pathlib import Path

from audit_native_weight_delta_run328 import (
    MASTER_SHA, SELECTED, GATES, assess, deltas, digest, require,
    validate_numeric_deltas, verify_report_and_paths,
)
from audit_native_lfm2_epoch_eval_run321 import audit as original_run321

SCHEMA = "V13_RUN333_NATIVE_FP32_TENSOR_DELTA_COMPAT_V1"
EXPECTED_TENSORS = 148
EXPECTED_ELEMENTS = 354_483_968


def check_file_type(field, *, master):
    """Allow only b10964 saver omission on epochs; never accept a wrong value."""
    if field is None:
        require(not master, "original master general.file_type missing")
        return "OMITTED_EPOCH_ONLY"
    try:
        value = int(field.contents())
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("malformed general.file_type") from exc
    require(value == 0, "non-F32 general.file_type")
    return "EXPLICIT_F32"


def inspect(path, *, master):
    import gguf
    import numpy as np

    reader = gguf.GGUFReader(str(path))
    arch = reader.get_field("general.architecture")
    require(arch is not None and arch.contents() == "lfm2",
            "non-lfm2 or missing architecture")
    mode = check_file_type(reader.get_field("general.file_type"), master=master)
    require(len(reader.tensors) == EXPECTED_TENSORS, "GGUF tensor count changed")
    tensors, raw = {}, {}
    total = 0
    for tensor in reader.tensors:
        name = str(tensor.name)
        require(name not in tensors, "duplicate GGUF tensor name")
        require(int(tensor.tensor_type) == int(gguf.GGMLQuantizationType.F32),
                "non-F32 GGUF tensor: " + name)
        data = tensor.data
        total += int(tensor.n_elements)
        tensors[name] = {
            "sha256": hashlib.sha256(memoryview(data).cast("B")).hexdigest(),
            "shape": [int(x) for x in tensor.shape],
            "type": int(tensor.tensor_type),
            "bytes": int(data.nbytes),
            "finite": bool(np.isfinite(data).all()) if name in SELECTED else True,
        }
        if name in SELECTED:
            raw[name] = data
    require(total == EXPECTED_ELEMENTS, "GGUF F32 element count changed")
    require(set(SELECTED) <= set(tensors), "selected FFN tensor missing")
    return reader, tensors, raw, mode


def audit(master, epoch1, epoch2, report):
    receipt = original_run321(report)
    require(receipt["status"] == "PASS_SOURCE_ONLY",
            "original Run321 exact raw-score audit failed")
    hashes = verify_report_and_paths(report, master, epoch1, epoch2)
    master_reader, m, mr, master_mode = inspect(master, master=True)
    epoch1_reader, e1, r1, mode1 = inspect(epoch1, master=False)
    epoch2_reader, e2, r2, mode2 = inspect(epoch2, master=False)
    require(master_mode == "EXPLICIT_F32", "original master F32 metadata absent")
    changed = assess(m, e1, e2)
    metrics = {
        "baseline_to_epoch1": deltas(mr, r1),
        "epoch1_to_epoch2": deltas(r1, r2),
    }
    validate_numeric_deltas(metrics)
    assert master_reader is not None and epoch1_reader is not None and epoch2_reader is not None
    return {
        "schema": SCHEMA,
        "status": "PASS_NATIVE_WEIGHT_DELTA_COMPAT_DIAGNOSTIC_NO_ACTIVATION",
        "evidence_level": "LINUX_NATIVE_FP32_TENSOR_BYTE_AUDIT",
        "master_sha256": hashes[0],
        "epoch_sha256": hashes[1:],
        "tensor_count": len(m),
        "frozen_selected_tensors": list(SELECTED),
        "metadata_modes": {"master": master_mode, "epoch1": mode1, "epoch2": mode2},
        "original_run321_status": receipt["status"],
        "original_run328_unchanged": True,
        "selected_sha256": {
            name: [m[name]["sha256"], e1[name]["sha256"], e2[name]["sha256"]]
            for name in SELECTED
        },
        "changes": changed,
        "metrics": metrics,
        "model_activated": False,
        "model_weights_published": False,
        "claim_limit": "Synthetic native C3 two-epoch tensor audit only; no AG6, Body-JEPA, Redmi, whole V13 or activation",
        "gates": GATES,
    }


def main():
    ap = argparse.ArgumentParser()
    for name in ("master", "epoch1", "epoch2", "report", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    args = ap.parse_args()
    try:
        report = json.loads(args.report.read_text())
        result = audit(args.master, args.epoch1, args.epoch2, report)
    except (ValueError, OSError, KeyError, TypeError, ImportError, AssertionError) as exc:
        result = {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": type(exc).__name__ + ": " + str(exc)[:350],
            "model_activated": False,
            "model_weights_published": False,
            "gates": GATES,
        }
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS_NATIVE_WEIGHT_DELTA_COMPAT_DIAGNOSTIC_NO_ACTIVATION" else 2)


if __name__ == "__main__":
    main()

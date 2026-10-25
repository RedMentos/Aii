#!/usr/bin/env python3
"""Run332 read-only native GGUF header diagnostic; never evidence of activation.

Only fixed metadata, tensor names/types/counts and full-file hashes are emitted.
Actual tensor data, GGUF files and model text are never published.
"""
import argparse
import json
from pathlib import Path

from audit_native_weight_delta_run328 import (
    GATES, SELECTED, verify_report_and_paths, require,
)
from audit_native_lfm2_epoch_eval_run321 import audit as audit_run321

SCHEMA = "V13_RUN332_NATIVE_GGUF_HEADER_DIAGNOSTIC_V1"
EXPECTED_COUNT = 148
EXPECTED_ELEMENTS = 354_483_968


def scalar(field):
    if field is None:
        return None
    value = field.contents()
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            value = value.item()
        except (ValueError, TypeError, AttributeError):
            return None
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", "strict")
        except UnicodeDecodeError:
            return None
    return value if isinstance(value, (str, int)) and not isinstance(value, bool) else None


def scan_reader(reader, expected_count=EXPECTED_COUNT, expected_elements=EXPECTED_ELEMENTS):
    """Pure structural scan; no tensor.data access, no trust promotion."""
    architecture = scalar(reader.get_field("general.architecture"))
    file_type = scalar(reader.get_field("general.file_type"))
    seen = set()
    types = {}
    elements = 0
    for tensor in reader.tensors:
        name = str(tensor.name)
        require(name not in seen, "duplicate GGUF tensor name")
        seen.add(name)
        kind = int(tensor.tensor_type)
        types[str(kind)] = types.get(str(kind), 0) + 1
        elements += int(tensor.n_elements)
    selected_present = sorted(set(SELECTED) & seen)
    result = {
        "architecture_present": architecture is not None,
        "architecture_is_lfm2": architecture == "lfm2",
        "file_type_present": file_type is not None,
        "file_type": file_type if isinstance(file_type, int) and 0 <= file_type <= 1024 else None,
        "tensor_count": len(seen),
        "tensor_types": types,
        "tensor_elements": elements,
        "selected_present_count": len(selected_present),
        "all_f32": types == {"0": expected_count},
    }
    require(len(seen) == expected_count, "original tensor count changed")
    require(elements == expected_elements, "original tensor element count changed")
    require(result["all_f32"], "non-F32 tensor payload type")
    require(len(selected_present) == len(SELECTED), "selected FFN tensor missing")
    return result


def run(master, epoch1, epoch2, report):
    source_receipt = audit_run321(report)
    require(source_receipt["status"] == "PASS_SOURCE_ONLY", "Run321 failed")
    hashes = verify_report_and_paths(report, master, epoch1, epoch2)
    import gguf
    readers = [gguf.GGUFReader(str(path)) for path in (master, epoch1, epoch2)]
    rows = [scan_reader(reader) for reader in readers]
    require(rows[0]["architecture_is_lfm2"] and rows[0]["file_type"] == 0,
            "original Run324 master metadata mismatch")
    mismatch = any(
        row["architecture_is_lfm2"] != rows[0]["architecture_is_lfm2"]
        or row["file_type"] != rows[0]["file_type"]
        or row["architecture_present"] != rows[0]["architecture_present"]
        or row["file_type_present"] != rows[0]["file_type_present"]
        for row in rows[1:]
    )
    return {
        "schema": SCHEMA,
        "status": "HEADER_DIFFERENCE_REQUIRES_INDEPENDENT_REVIEW" if mismatch else "HEADERS_MATCH_AUDITOR_RED_OTHER",
        "evidence_level": "LINUX_NATIVE_GGUF_METADATA_ONLY",
        "files": {
            name: {"sha256": hash_value, "size_bytes": Path(path).stat().st_size, **row}
            for name, hash_value, path, row in zip(
                ("master", "epoch1", "epoch2"), hashes, (master, epoch1, epoch2), rows
            )
        },
        "run321": source_receipt["status"],
        "run328_original": "FAIL_CLOSED_NOT_OVERRIDDEN",
        "claim_limit": "Diagnostic only; no independent tensor byte delta pass or model activation",
        "model_activated": False, "model_weights_published": False, "gates": GATES,
    }


def main():
    ap = argparse.ArgumentParser()
    for name in ("master", "epoch1", "epoch2", "report", "out"):
        ap.add_argument("--" + name, type=Path, required=True)
    args = ap.parse_args()
    try:
        report = json.loads(args.report.read_text())
        result = run(args.master, args.epoch1, args.epoch2, report)
    except (ValueError, OSError, KeyError, TypeError, ImportError, AssertionError) as exc:
        result = {
            "schema": SCHEMA, "status": "FAIL_CLOSED",
            "error": type(exc).__name__ + ": " + str(exc)[:250],
            "model_activated": False, "model_weights_published": False, "gates": GATES,
        }
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"].startswith(("HEADER_DIFFERENCE_", "HEADERS_MATCH_")) else 2)


if __name__ == "__main__":
    main()

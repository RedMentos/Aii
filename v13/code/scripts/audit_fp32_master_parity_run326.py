#!/usr/bin/env python3
"""Run326: read-only, full-byte and per-tensor audit of two pinned FP32 conversions.

Never writes weights, trains, activates a model or promotes V13 gates.
"""
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "V13_RUN326_FP32_MASTER_PARITY_V1"
EXPECTED_MASTER = "5d200c19f13483e66b39d9feb3353032581882f3eb10cc8752f027d4688d6e6f"
EXPECTED_WEIGHTS = "1c9c77a4471a7f590f85240f74ed1fc26df7fbde88c3006724e2f93ca993ea4e"
GATES = {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL", "Body_JEPA": "UNAVAILABLE",
         "jepa_weight": 0, "Redmi": "MISSING", "V13": "INCOMPLETE"}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def source_hashes(directory):
    directory = Path(directory)
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("snapshot missing or symlink")
    files = {p.name: sha256(p) for p in sorted(directory.iterdir())
             if p.is_file() and not p.is_symlink()}
    if files.get("model.safetensors") != EXPECTED_WEIGHTS:
        raise ValueError("original HF weight SHA mismatch")
    if not {"config.json", "tokenizer.json", "tokenizer_config.json"} <= set(files):
        raise ValueError("required HF tokenizer/config source missing")
    return files


def _normal(value):
    """Canonicalize GGUFReader metadata without publishing the tensor payload."""
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "tolist"):
        return _normal(value.tolist())
    if isinstance(value, (list, tuple)):
        return [_normal(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _normal(v) for k, v in sorted(value.items())}
    raise TypeError("unsupported GGUF metadata value type: " + type(value).__name__)


def metadata_digest(field):
    value = _normal(field.contents())
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def gguf_receipt(path):
    import gguf  # must be exact official b10964 gguf-py via explicit PYTHONPATH
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("GGUF missing or symlink")
    if path.stat().st_size != 1_420_324_800:
        raise ValueError("unexpected FP32 GGUF size")
    reader = gguf.GGUFReader(str(path))
    arch = reader.get_field("general.architecture")
    kind = reader.get_field("general.file_type")
    if arch is None or arch.contents() != "lfm2" or kind is None or int(kind.contents()) != 0:
        raise ValueError("not original lfm2 ALL_F32")
    if len(reader.tensors) != 148:
        raise ValueError("unexpected original tensor count")
    tensors = {}
    total = 0
    for tensor in reader.tensors:
        name = str(tensor.name)
        if name in tensors or int(tensor.tensor_type) != int(gguf.GGMLQuantizationType.F32):
            raise ValueError("duplicate or non-F32 tensor")
        data = memoryview(tensor.data).cast("B")
        total += int(tensor.n_elements)
        tensors[name] = {
            "shape": [int(x) for x in tensor.shape],
            "type": int(tensor.tensor_type),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    if total != 354_483_968:
        raise ValueError("unexpected original FP32 element count")
    metadata = {str(k): metadata_digest(v) for k, v in reader.fields.items()}
    return {"sha256": sha256(path), "bytes": path.stat().st_size,
            "tensor_count": len(tensors), "elements": total,
            "tensors": tensors, "metadata": metadata}


def classify(baseline, variant, original_sources, variant_sources):
    if original_sources != variant_sources:
        return "SOURCE_MISMATCH"
    if baseline["sha256"] != EXPECTED_MASTER:
        return "BASELINE_NOT_REPRODUCED"
    if baseline["tensors"] != variant["tensors"]:
        return "TENSOR_DRIFT"
    if baseline["sha256"] == variant["sha256"]:
        return "NO_DRIFT"
    if baseline["metadata"] != variant["metadata"]:
        return "METADATA_ONLY_DRIFT"
    return "UNEXPLAINED_BINARY_DRIFT"


def compare(baseline, variant, original_sources, variant_sources):
    status = classify(baseline, variant, original_sources, variant_sources)
    different_metadata = sorted(set(baseline["metadata"]) | set(variant["metadata"]))
    different_metadata = [key for key in different_metadata
                          if baseline["metadata"].get(key) != variant["metadata"].get(key)]
    return {
        "schema": SCHEMA, "status": status,
        "evidence_level": "LINUX_NATIVE_FP32_CONVERTER_ABLATION_NO_TRAINING",
        "baseline_sha256": baseline["sha256"], "variant_sha256": variant["sha256"],
        "source_equal": original_sources == variant_sources,
        "tensor_payloads_equal": baseline["tensors"] == variant["tensors"],
        "tensor_count": baseline["tensor_count"],
        "metadata_different_keys": different_metadata,
        "metadata_different_count": len(different_metadata),
        "original_weight_sha256": EXPECTED_WEIGHTS,
        "expected_baseline_sha256": EXPECTED_MASTER,
        "native_optimizer_epochs": 0, "model_weights_published": False,
        "gates": GATES,
    }


def main():
    parser = argparse.ArgumentParser()
    for key in ("baseline", "variant", "baseline-source", "variant-source", "out"):
        parser.add_argument("--" + key, type=Path, required=True)
    args = parser.parse_args()
    try:
        original = source_hashes(args.baseline_source)
        variant = source_hashes(args.variant_source)
        base = gguf_receipt(args.baseline)
        other = gguf_receipt(args.variant)
        result = compare(base, other, original, variant)
    except (ValueError, OSError, TypeError, ImportError, KeyError) as exc:
        result = {"schema": SCHEMA, "status": "FAIL_CLOSED",
                  "error": type(exc).__name__ + ": " + str(exc)[:400],
                  "native_optimizer_epochs": 0, "model_weights_published": False, "gates": GATES}
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] in ("NO_DRIFT", "METADATA_ONLY_DRIFT") else 2)


if __name__ == "__main__":
    main()

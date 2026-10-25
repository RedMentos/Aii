#!/usr/bin/env python3
"""Run324 fail-closed exact b10964 full FP32 GGUF converter receipt, no training."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.probe_lfm2_tokenizer_compat_run322 import REPO, REVISION, verify_snapshot

SCHEMA = "V13_RUN324_PINNED_B10964_FP32_CONVERSION_V1"
SOURCE_TAR_SHA256 = "4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe"
CONVERTER_SHA256 = "e9a1da876330bbce9687541ab31736542a01b4ac43c6686126514a50f122fb7f"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_header(header, size):
    if not 1_000_000_000 <= size <= 3_000_000_000:
        raise ValueError("FP32 GGUF byte size outside frozen bounds")
    if len(header) != 24 or header[:4] != b"GGUF":
        raise ValueError("missing GGUF magic or complete header")
    version, tensors, kv = struct.unpack("<IQQ", header[4:])
    if version not in (2, 3):
        raise ValueError("unsupported GGUF version")
    if not 10 <= tensors <= 2000:
        raise ValueError("full FP32 tensor count outside frozen bounds")
    if not 5 <= kv <= 10000:
        raise ValueError("GGUF metadata count outside frozen bounds")
    return {"gguf_version": version, "tensor_count": tensors, "metadata_count": kv, "bytes": size}


def inspect_reader(reader, f32_type):
    """Source-bound GGUFReader, with all actual tensor types checked (no silent Q4)."""
    file_type = reader.get_field("general.file_type")
    architecture = reader.get_field("general.architecture")
    if file_type is None or int(file_type.contents()) != 0:
        raise ValueError("GGUF file type is not ALL_F32")
    if architecture is None or architecture.contents() != "lfm2":
        raise ValueError("GGUF architecture is not lfm2")
    tensors = reader.tensors
    if not tensors:
        raise ValueError("GGUF has no tensor records")
    if any(int(t.tensor_type) != int(f32_type) for t in tensors):
        raise ValueError("GGUF contains non-F32 tensor")
    elements = sum(int(t.n_elements) for t in tensors)
    if not 250_000_000 <= elements <= 500_000_000:
        raise ValueError("GGUF FP32 element count outside frozen bounds")
    return {"architecture": "lfm2", "file_type": 0, "tensor_records": len(tensors),
            "f32_elements": elements, "all_tensors_f32": True}


def verify(gguf_file, snapshot, manifest, source_tar, converter):
    if digest(source_tar) != SOURCE_TAR_SHA256:
        raise ValueError("pinned b10964 source tar SHA mismatch")
    if digest(converter) != CONVERTER_SHA256:
        raise ValueError("unmodified official converter SHA mismatch")
    binding = verify_snapshot(snapshot, manifest)
    source_weights = {k: v for k, v in manifest["file_sha256"].items() if k.endswith(".safetensors")}
    if not source_weights:
        raise ValueError("no original HF safetensors weights")
    weight_bytes = sum((Path(snapshot) / name).stat().st_size for name in source_weights)
    if not 400_000_000 <= weight_bytes <= 3_000_000_000:
        raise ValueError("HF source weight bytes outside frozen bounds")
    gguf_file = Path(gguf_file)
    if not gguf_file.is_file() or gguf_file.is_symlink():
        raise ValueError("missing or symlink FP32 GGUF")
    with gguf_file.open("rb") as stream:
        header = stream.read(24)
    header_info = parse_header(header, gguf_file.stat().st_size)
    import gguf  # official b10964 gguf-py via explicit PYTHONPATH in native CI
    reader = gguf.GGUFReader(str(gguf_file))
    tensors = inspect_reader(reader, gguf.GGMLQuantizationType.F32)
    if len(reader.tensors) != header_info["tensor_count"]:
        raise ValueError("GGUF tensor header/reader count mismatch")
    del reader
    return {
        "schema": SCHEMA,
        "status": "PASS_REAL_FP32_CONVERSION_NO_TRAINING",
        "evidence_level": "LINUX_NATIVE_CONVERTER_FP32_NO_TRAINING",
        "source_tar_sha256": SOURCE_TAR_SHA256,
        "converter_sha256": CONVERTER_SHA256,
        "hf_repo": REPO, "hf_revision": REVISION,
        "hf_source_binding": binding,
        "hf_weight_source_sha256": source_weights,
        "hf_weight_bytes": weight_bytes,
        "master_gguf": header_info | tensors | {"sha256": digest(gguf_file)},
        "model_weights_published": False,
        "native_training_executed": False,
        "native_inference_executed": False,
        "gates": {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL",
                  "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0, "V13": "INCOMPLETE"},
    }


def main():
    parser = argparse.ArgumentParser()
    for arg in ("gguf", "snapshot", "manifest", "source-tar", "converter", "out"):
        parser.add_argument("--" + arg, type=Path, required=True)
    a = parser.parse_args()
    try:
        result = verify(a.gguf, a.snapshot, json.loads(a.manifest.read_text()), a.source_tar, a.converter)
    except (ValueError, OSError, KeyError, TypeError, ImportError) as exc:
        result = {"schema": SCHEMA, "status": "FAIL_CLOSED",
                  "error": type(exc).__name__ + ": " + str(exc)[:400],
                  "model_weights_published": False, "native_training_executed": False}
    a.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS_REAL_FP32_CONVERSION_NO_TRAINING" else 2)


if __name__ == "__main__":
    main()

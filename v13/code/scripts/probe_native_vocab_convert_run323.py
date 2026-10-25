#!/usr/bin/env python3
"""Run323 verify pinned b10964 vocab-only GGUF, never model/optimizer proof."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from probe_lfm2_tokenizer_compat_run322 import REPO, REVISION, verify_snapshot

SCHEMA = "V13_RUN323_PINNED_B10964_VOCAB_ONLY_V1"
SOURCE_TAR_SHA256 = "4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def inspect_vocab_gguf(path):
    """Strict structural GGUF header check; no token semantic equivalence claim."""
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("missing or symlink vocab GGUF")
    size = path.stat().st_size
    if not 65536 <= size <= 100 * 1024 * 1024:
        raise ValueError("vocab GGUF byte size outside frozen bounds")
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or header[:4] != b"GGUF":
        raise ValueError("missing GGUF magic or complete header")
    version, tensors, kv = struct.unpack("<IQQ", header[4:])
    if version not in (2, 3):
        raise ValueError("unsupported GGUF version")
    if tensors != 0:
        raise ValueError("vocab-only GGUF unexpectedly contains tensors")
    if not 5 <= kv <= 10000:
        raise ValueError("GGUF metadata count outside frozen bounds")
    return {"bytes": size, "sha256": digest(path), "gguf_version": version,
            "tensor_count": tensors, "metadata_count": kv}


def verify(vocab, snapshot, manifest, source_tar, converter):
    if digest(source_tar) != SOURCE_TAR_SHA256:
        raise ValueError("pinned b10964 source tar SHA mismatch")
    if not Path(converter).is_file() or Path(converter).is_symlink():
        raise ValueError("official converter missing or symlink")
    binding = verify_snapshot(snapshot, manifest)
    return {
        "schema": SCHEMA,
        "status": "PASS_VOCAB_ONLY_NOT_MODEL_CONVERSION",
        "evidence_level": "LINUX_NATIVE_CONVERTER_VOCAB_ONLY",
        "source_tar_sha256": SOURCE_TAR_SHA256,
        "converter_sha256": digest(converter),
        "hf_repo": REPO,
        "hf_revision": REVISION,
        "source_binding": binding,
        "vocab_gguf": inspect_vocab_gguf(vocab),
        "model_weights_downloaded": False,
        "native_training_executed": False,
        "native_inference_executed": False,
        "gates": {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL",
                  "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0, "V13": "INCOMPLETE"},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vocab", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-tar", type=Path, required=True)
    parser.add_argument("--converter", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.vocab, args.snapshot, json.loads(args.manifest.read_text()),
                        args.source_tar, args.converter)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        result = {"schema": SCHEMA, "status": "FAIL_CLOSED",
                  "error": type(exc).__name__ + ": " + str(exc)[:400],
                  "model_weights_downloaded": False, "native_training_executed": False}
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS_VOCAB_ONLY_NOT_MODEL_CONVERSION" else 2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Metadata-only immutable QAD source audit; no model download, training or inference."""
import argparse
import hashlib
import json
import re
from pathlib import Path

REPO = "LiquidAI/LFM2.5-350M-GGUF"
REVISION = "657e078c94084481950a2d555a941481f715536b"
DEPLOYED = "LFM2.5-350M-QAD-Q4_0.gguf"
DEPLOYED_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
MASTER = "qad/model.safetensors"
REQUIRED = (MASTER, "qad/config.json", "qad/tokenizer.json",
            DEPLOYED, "LICENSE")
OPTIONAL = ("qad/chat_template.jinja", "qad/tokenizer_config.json", "qad/generation_config.json")
SCHEMA = "V13_BP1_QAD_SOURCE_METADATA_AUDIT_V1"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def parse(raw):
    def no_constant(value):
        raise ValueError("nonfinite JSON: " + value)
    return json.loads(raw, object_pairs_hook=pairs_unique, parse_constant=no_constant)


def lfs_sha(file):
    lfs = file.get("lfs")
    if not isinstance(lfs, dict):
        raise ValueError("missing immutable LFS metadata for " + file["rfilename"])
    oid = lfs.get("oid")
    if isinstance(oid, str) and oid.startswith("sha256:"):
        oid = oid[7:]
    if not isinstance(oid, str) or re.fullmatch(r"[0-9a-f]{64}", oid) is None:
        raise ValueError("invalid LFS oid for " + file["rfilename"])
    size = lfs.get("size")
    if type(size) is not int or size <= 0:
        raise ValueError("invalid LFS size for " + file["rfilename"])
    return oid, size


def audit(info):
    if not isinstance(info, dict) or info.get("id") != REPO or info.get("sha") != REVISION:
        raise ValueError("QAD repository/revision mismatch")
    siblings = info.get("siblings")
    if not isinstance(siblings, list):
        raise ValueError("missing model file listing")
    files = {}
    for file in siblings:
        if not isinstance(file, dict) or not isinstance(file.get("rfilename"), str):
            raise ValueError("malformed sibling entry")
        name = file["rfilename"]
        if name in files:
            raise ValueError("duplicate sibling filename")
        files[name] = file
    missing = sorted(set(REQUIRED) - set(files))
    if missing:
        raise ValueError("required QAD source files missing: " + ",".join(missing))
    master_sha, master_size = lfs_sha(files[MASTER])
    deployed_sha, deployed_size = lfs_sha(files[DEPLOYED])
    if deployed_sha != DEPLOYED_SHA:
        raise ValueError("registered deployed QAD GGUF SHA mismatch")
    if master_sha == deployed_sha or master_size < 500_000_000 or not 150_000_000 <= deployed_size <= 300_000_000:
        raise ValueError("unexpected master/GGUF file identity or size")
    card = info.get("cardData") or {}
    if not isinstance(card, dict):
        raise ValueError("invalid model card metadata")
    license_id = card.get("license", info.get("license"))
    if license_id is not None and not isinstance(license_id, str):
        raise ValueError("invalid license metadata")
    return {"schema": SCHEMA, "repo": REPO, "revision": REVISION,
            "source_type": "OFFICIAL_HF_METADATA_ONLY",
            "source_master_path": MASTER, "source_master_sha256": master_sha,
            "source_master_size": master_size, "deployed_gguf_path": DEPLOYED,
            "deployed_gguf_sha256": deployed_sha, "deployed_gguf_size": deployed_size,
            "license_file_present": True, "license_metadata": license_id,
            "optional_files_present": sorted(set(OPTIONAL) & set(files)),
            "optional_files_absent": sorted(set(OPTIONAL) - set(files)),
            "master_bytes_downloaded": False, "gguf_bytes_downloaded": False,
            "fp32_to_q4_behavioral_parity_verified": False,
            "native_c3_training_executed": False, "redmi_measured": False,
            "gates": {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL",
                      "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0,
                      "canonical_architecture_complete": False,
                      "user_full_scope_complete": False}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--metadata", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    raw = Path(args.metadata).read_bytes()
    result = audit(parse(raw.decode("utf-8")))
    result["metadata_sha256"] = sha(raw)
    with Path(args.out).open("xb") as f:
        f.write((json.dumps(result, indent=2, sort_keys=True) + "\n").encode())
        f.flush()
        import os
        os.fsync(f.fileno())
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

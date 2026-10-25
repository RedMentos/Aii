#!/usr/bin/env python3
"""Run322 two-arm pinned LFM2 tokenizer compatibility probe (NO model weights)."""
import argparse
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import re
import sys

REPO = "LiquidAI/LFM2.5-350M"
REVISION = "9e6c6ccf47cd318696e137d381a7ded8fe4df09f"
PROMPTS = (
    "Hello.",
    "What is 7 plus 5?",
    "Tell me my cat's name.",
    "Translate thank you into German.",
    "Which instrument does my brother play?",
)
SCHEMA = "V13_RUN322_LFM2_TOKENIZER_COMPAT_V1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_snapshot(root, manifest):
    """Verify original files against the separately captured exact-revision manifest."""
    root = Path(root)
    if manifest.get("hf_repo") != REPO or manifest.get("hf_revision") != REVISION:
        raise ValueError("wrong pinned HF source revision")
    hashes = manifest.get("file_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("missing source file hashes")
    for required in ("config.json", "tokenizer_config.json", "tokenizer.json"):
        if required not in hashes:
            raise ValueError("missing required source: " + required)
    for name, expected in hashes.items():
        if not isinstance(name, str) or not name or "/" in name or "\\" in name or name.startswith("."):
            raise ValueError("invalid source filename")
        if not isinstance(expected, str) or HEX64.fullmatch(expected) is None:
            raise ValueError("invalid source SHA256")
        file = root / name
        if not file.is_file() or file.is_symlink() or digest(file) != expected:
            raise ValueError("source byte drift: " + name)
    config = json.loads((root / "tokenizer_config.json").read_text())
    if config.get("tokenizer_class") != "TokenizersBackend":
        raise ValueError("tokenizer class differs from frozen source")
    return {"files": len(hashes), "tokenizer_config_sha256": hashes["tokenizer_config.json"]}


def normalize_ids(value):
    if isinstance(value, Mapping):
        value = value.get("input_ids")
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]
    if not isinstance(value, list) or not value or len(value) > 2048:
        raise ValueError("unexpected tokenizer ID sequence: " + type(value).__name__)
    if any(type(x) is not int or not 0 <= x < 65536 for x in value):
        raise ValueError("tokenizer ID out of frozen vocab range")
    return value


def token_digest(ids):
    return hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()


def probe(root, manifest, version_tag):
    binding = verify_snapshot(root, manifest)
    # Intentionally imported after manifest checks; each arm uses a separate venv.
    import transformers
    if transformers.__version__ != version_tag:
        raise ValueError("transformers arm version mismatch")
    from transformers import AutoTokenizer
    runs = []
    for _ in range(2):
        tok = AutoTokenizer.from_pretrained(str(root), local_files_only=True)
        out = []
        for prompt in PROMPTS:
            ids = normalize_ids(tok.apply_chat_template(
                [{"role": "user", "content": prompt}],
                add_generation_prompt=True, tokenize=True))
            out.append({"sha256": token_digest(ids), "n": len(ids),
                        "first": ids[:4], "last": ids[-4:]})
        runs.append(out)
    if runs[0] != runs[1]:
        raise ValueError("nondeterministic independent tokenizer loads")
    return {"schema": SCHEMA, "arm": version_tag, "status": "PASS",
            "hf_repo": REPO, "hf_revision": REVISION, "binding": binding,
            "prompt_count": len(PROMPTS), "outputs": runs[0],
            "evidence_level": "TOKENIZER_ONLY_NO_MODEL_NO_NATIVE"}


def assess(old, new):
    for row, version in ((old, "4.57.1"), (new, "5.3.0")):
        if row.get("schema") != SCHEMA or row.get("arm") != version:
            raise ValueError("wrong arm/schema")
        if row.get("hf_repo") != REPO or row.get("hf_revision") != REVISION:
            raise ValueError("wrong model/revision in arm")
    negative = old.get("status") == "FAIL" and "TokenizersBackend" in old.get("error", "")
    positive = new.get("status") == "PASS" and new.get("prompt_count") == len(PROMPTS)
    if positive:
        if not isinstance(new.get("outputs"), list) or len(new["outputs"]) != len(PROMPTS):
            positive = False
        else:
            for row in new["outputs"]:
                if (not isinstance(row, dict) or not isinstance(row.get("n"), int)
                        or row["n"] <= 0 or not isinstance(row.get("sha256"), str)
                        or HEX64.fullmatch(row["sha256"]) is None):
                    positive = False
    return {"schema": SCHEMA, "status": "COMPAT_DIAGNOSTIC_SUPPORTED" if negative and positive else "NOT_SUPPORTED",
            "old_failure_observed": negative, "new_tokenizer_deterministic": positive,
            "native_conversion_proven": False, "optimizer_epochs": 0,
            "gates": {"STEP2": "UTILITY_FAIL", "B3_L1": "FAIL",
                      "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0, "V13": "INCOMPLETE"}}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    probe_p = sub.add_parser("probe")
    probe_p.add_argument("--snapshot-dir", type=Path, required=True)
    probe_p.add_argument("--manifest", type=Path, required=True)
    probe_p.add_argument("--version-tag", choices=("4.57.1", "5.3.0"), required=True)
    probe_p.add_argument("--out", type=Path, required=True)
    assess_p = sub.add_parser("assess")
    assess_p.add_argument("--old", type=Path, required=True)
    assess_p.add_argument("--new", type=Path, required=True)
    assess_p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.action == "assess":
        result = assess(json.loads(a.old.read_text()), json.loads(a.new.read_text()))
        a.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(0 if result["status"] == "COMPAT_DIAGNOSTIC_SUPPORTED" else 2)
    try:
        manifest = json.loads(a.manifest.read_text())
        result = probe(a.snapshot_dir, manifest, a.version_tag)
    except Exception as exc:
        result = {"schema": SCHEMA, "arm": a.version_tag, "status": "FAIL",
                  "hf_repo": REPO, "hf_revision": REVISION,
                  "error": type(exc).__name__ + ": " + str(exc)[:400],
                  "evidence_level": "TOKENIZER_ONLY_NO_MODEL_NO_NATIVE"}
    a.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()

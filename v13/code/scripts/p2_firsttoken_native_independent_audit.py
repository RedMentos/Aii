#!/usr/bin/env python3
"""Independent, stdlib-only P2 first-token native ZIP audit; never promotes parity."""
import argparse
import hashlib
import json
import os
import re
import stat
import zipfile
from pathlib import Path

TOKENIZER_ZIP_SHA = "fff6a6477090166176b71674ef593d1954966b5cbb685723054cd1b230c8e342"
TOKENIZER_HEAD = "2d59a6d452a889dba0a4831accdd44982ed90a95"
NATIVE_HEAD = "4309b9306d235865624944b24227e014ad5bc49b"
MASTER_SHA = "1d90518482c4ec204bebb4820bbaee4f8a38c5a6df72256f86bcd21fe52ad079"
GGUF_SHA = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
PROMPTS = ("Hello.", "2 + 2 = ?", "<|tool_call_start|>python<|tool_call_end|>",
           "<think>reasoning</think>", "Mathias uses python.", '{"tool":"python"}',
           "Äpfel, Öl und Straße.", "Line one\nLine two")
STAGES = ("RESOURCE", "VENV", "TORCH", "DEPS", "RUNTIME_DOWNLOAD", "RUNTIME_SHA",
          "MASTER_DOWNLOAD", "GGUF_DOWNLOAD", "MODEL_SHA", "SERVER_READY",
          "AUDIT", "PRIVACY", "DIFF")
MANIFEST = re.compile(r"([0-9a-f]{64})  \\./([^\\n]+)\\Z")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def closed_zip(path):
    raw = Path(path).read_bytes()
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        if len(names) > 256 or len(set(names)) != len(names):
            raise ValueError("duplicate or excessive ZIP members")
        if any(n.startswith("/") or "\\" in n or ".." in Path(n).parts
               or not n or n.endswith("/") for n in names):
            raise ValueError("unsafe ZIP member")
        if any(stat.S_ISLNK(i.external_attr >> 16) for i in infos):
            raise ValueError("symlink ZIP member")
        if any(i.file_size > 4_000_000 for i in infos) or sum(i.file_size for i in infos) > 16_000_000:
            raise ValueError("excessive ZIP size")
        if z.testzip() is not None:
            raise ValueError("ZIP CRC mismatch")
        if "SHA256SUMS" not in names:
            raise ValueError("missing SHA256SUMS")
        data = {n: z.read(n) for n in names}
    manifest = data["SHA256SUMS"].decode("ascii").splitlines()
    checked = set()
    for line in manifest:
        match = MANIFEST.fullmatch(line)
        if match is None:
            raise ValueError("malformed SHA256SUMS")
        digest, name = match.groups()
        if name in checked or name not in data or sha256(data[name]) != digest:
            raise ValueError("manifest member or digest mismatch")
        checked.add(name)
    if checked != set(data) - {"SHA256SUMS"}:
        raise ValueError("SHA256SUMS coverage mismatch")
    return data, sha256(raw), len(checked)


def integer(x):
    return type(x) is int and x >= 0


def integer_ids(x, *, top=False):
    return (isinstance(x, list) and (1 <= len(x) <= 5 if top else len(x) >= 1)
            and all(integer(i) for i in x) and (not top or len(x) == len(set(x))))


def verify(native_path, tokenizer_path, expected_head=NATIVE_HEAD):
    native, native_sha, native_hashes = closed_zip(native_path)
    token, token_sha, token_hashes = closed_zip(tokenizer_path)
    if token_sha != TOKENIZER_ZIP_SHA:
        raise ValueError("wrong frozen tokenizer-only ZIP SHA256")
    if token["HEAD.txt"].decode().strip() != TOKENIZER_HEAD:
        raise ValueError("wrong tokenizer-only native HEAD")
    if native["HEAD.txt"].decode().strip() != expected_head:
        raise ValueError("wrong model-forward native HEAD")
    for stage in STAGES:
        if native.get(stage + "_EXIT.txt", b"").decode().strip() != "0":
            raise ValueError("nonzero/missing native stage: " + stage)
    if not native.get("PRIVACY_RAW.log", b"").decode().strip().endswith("CLEAN"):
        raise ValueError("privacy scan not CLEAN")
    if b"127.0.0.1:8080" not in native.get("SERVER_RAW.log", b""):
        raise ValueError("loopback-only server not evidenced")
    checks = native.get("MODEL_SHA_RAW.log", b"").decode()
    if checks.count(": OK") != 6:
        raise ValueError("six pinned model source hashes not evidenced")
    if b": OK" not in native.get("RUNTIME_SHA_RAW.log", b""):
        raise ValueError("pinned runtime SHA not evidenced")
    t = json.loads(token["RESULT.json"])
    x = json.loads(native["RESULT.json"])
    if t.get("schema") != "v13.p2.qad_gguf_native_tokenizer_ids.v1" or t.get("equal_count") != 8:
        raise ValueError("tokenizer reference schema/count mismatch")
    if x.get("schema") != "v13.p2.qad_fp32_gguf_first_token_native.v1":
        raise ValueError("model result schema mismatch")
    if x.get("status") != "FIRST_TOKEN_MEASURED_NO_PARITY_PROMOTION":
        raise ValueError("native model result not descriptive success")
    if x.get("training") is not False or x.get("full_logit_greedy_cache_adapter_or_utility_parity_proven") is not False:
        raise ValueError("forbidden promotion/training flag")
    if x.get("probe_count") != 8 or x.get("model_forward_calls") != 8:
        raise ValueError("not eight model forwards")
    rows = x.get("rows")
    refs = t.get("probes")
    if not isinstance(rows, list) or len(rows) != 8 or not isinstance(refs, list) or len(refs) != 8:
        raise ValueError("eight ordered native/reference rows required")
    equal = overlap = 0
    for prompt, row, ref in zip(PROMPTS, rows, refs):
        if row.get("prompt") != prompt or ref.get("prompt") != prompt:
            raise ValueError("preregistered prompt mismatch")
        ids = row.get("input_ids")
        if not integer_ids(ids) or ids != ref.get("qad_source_ids") or ids != ref.get("gguf_runtime_ids"):
            raise ValueError("native input IDs mismatch frozen tokenizer result")
        if not integer(row.get("hf_first")) or not integer(row.get("gguf_first")):
            raise ValueError("invalid native first token")
        a, b = row.get("hf_top5"), row.get("gguf_top5")
        if not integer_ids(a, top=True) or not integer_ids(b, top=True):
            raise ValueError("invalid native top-five IDs")
        if a[0] != row["hf_first"]:
            raise ValueError("HF first token not top-1")
        if row["gguf_first"] not in b:
            raise ValueError("GGUF first token absent from native top-5")
        n = len(set(a) & set(b))
        if row.get("top5_overlap") != n:
            raise ValueError("top-5 overlap tampering")
        overlap += n
        equal += (row["hf_first"] == row["gguf_first"])
    if x.get("top1_equal_count") != equal or x.get("top5_overlap_total") != overlap:
        raise ValueError("aggregate count mismatch")
    if x.get("source_pins", {}).get("model.safetensors") != MASTER_SHA or x.get("gguf_sha256") != GGUF_SHA:
        raise ValueError("source pin mismatch")
    return {"schema": "v13.p2.firsttoken_independent_raw_review.v1",
            "status": "EIGHT_FIRSTTOKEN_NATIVE_DESCRIPTIVE_VERIFIED",
            "native_zip_sha256": native_sha, "tokenizer_zip_sha256": token_sha,
            "native_manifest_entries": native_hashes, "tokenizer_manifest_entries": token_hashes,
            "native_stage_exits_zero": len(STAGES), "probe_count": 8,
            "top1_equal_count": equal, "top5_overlap_total": overlap,
            "parity_or_utility_proven": False, "training": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native-zip", required=True)
    p.add_argument("--tokenizer-zip", required=True)
    p.add_argument("--native-head", default=NATIVE_HEAD)
    p.add_argument("--output", required=True)
    args = p.parse_args(argv)
    try:
        result = verify(args.native_zip, args.tokenizer_zip, args.native_head)
        rc = 0
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, zipfile.BadZipFile, json.JSONDecodeError) as e:
        result = {"schema": "v13.p2.firsttoken_independent_raw_review.v1",
                  "status": "RED_PRESERVED", "error": type(e).__name__ + ": " + str(e),
                  "parity_or_utility_proven": False}
        rc = 2
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as f:
        f.write(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

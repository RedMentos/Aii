"""Compile explicitly reviewed B1/B2 examples into source-disjoint train/holdout sets.

Offline, no automatic training or model activation. Hashes are declarations
from the reviewed input; provenance must be verified upstream against Store.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROLES = ("B1_DETAIL", "B2_GIST")
MAX_ROWS = 50000
MAX_LINE = 32768
MAX_TEXT = 8192


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _validate(row):
    if type(row) is not dict or set(row) != {
            "role", "source_id", "source_sha256", "prompt", "target",
            "reviewed", "permission"}:
        raise ValueError("invalid fields")
    if type(row["role"]) is not str or row["role"] not in ROLES:
        raise ValueError("invalid role")
    if row["reviewed"] is not True or row["permission"] != "TRAINING_APPROVED":
        raise ValueError("review and explicit training approval required")
    sid = row["source_id"]
    if type(sid) is not str or not 1 <= len(sid) <= 128 or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for c in sid):
        raise ValueError("invalid source ID")
    h = row["source_sha256"]
    if type(h) is not str or len(h) != 64 or any(c not in "0123456789abcdef" for c in h):
        raise ValueError("invalid source hash")
    for k in ("prompt", "target"):
        v = row[k]
        if type(v) is not str or not v.strip() or len(v.encode("utf-8")) > MAX_TEXT:
            raise ValueError("invalid "+k)
    return row


def _atomic(path, data):
    if path.is_symlink() or path.exists():
        raise ValueError("refusing existing output")
    fd, tmp = tempfile.mkstemp(prefix=".bodydataset-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if path.exists() or path.is_symlink():
            raise ValueError("output appeared during compilation")
        os.replace(tmp, path)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def compile_dataset(source, destination, holdout_percent=20):
    source, destination = Path(source), Path(destination)
    if type(holdout_percent) is not int or not 1 <= holdout_percent <= 49:
        raise ValueError("holdout percent must be 1..49")
    if source.is_symlink() or not source.is_file() or destination.is_symlink():
        raise ValueError("regular input and non-symlink destination required")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("destination must be empty")
    groups = {role: {"train": [], "holdout": []} for role in ROLES}
    seen = {}
    count = 0
    digest = hashlib.sha256()
    with source.open("rb") as f:
        for line in f:
            digest.update(line)
            if len(line) > MAX_LINE:
                raise ValueError("oversized input line")
            if not line.strip():
                continue
            count += 1
            if count > MAX_ROWS:
                raise ValueError("too many examples")
            try:
                row = _validate(json.loads(line))
            except (ValueError, TypeError, UnicodeError) as exc:
                raise ValueError("invalid reviewed example at row "+str(count)) from exc
            sid, h = row["source_id"], row["source_sha256"]
            if seen.setdefault(sid, h) != h:
                raise ValueError("source ID changed content hash")
            bucket = int(sha((sid+":"+h).encode())[:16], 16) % 100
            part = "holdout" if bucket < holdout_percent else "train"
            groups[row["role"]][part].append(row)
    if not count:
        raise ValueError("empty reviewed dataset")
    for role in ROLES:
        if not groups[role]["train"] or not groups[role]["holdout"]:
            raise ValueError("insufficient independent sources for "+role)
    contents = {}
    manifest = {"schema": "v13-reviewed-body-dataset-v1",
                "input_sha256": digest.hexdigest(), "holdout_percent": holdout_percent,
                "rows": count, "files": {}}
    for role in ROLES:
        for part in ("train", "holdout"):
            name = role.lower()+"_"+part+".jsonl"
            rows = sorted(groups[role][part],
                          key=lambda r: (r["source_id"], r["prompt"], r["target"]))
            data = b"".join(canonical(r)+b"\n" for r in rows)
            contents[name] = data
            manifest["files"][name] = {
                "sha256": sha(data), "rows": len(rows),
                "sources": len({r["source_id"] for r in rows})}
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, data in contents.items():
        _atomic(destination/name, data)
    _atomic(destination/"manifest.json", canonical(manifest)+b"\n")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviewed_jsonl")
    parser.add_argument("empty_output_directory")
    parser.add_argument("--holdout-percent", type=int, default=20)
    args = parser.parse_args(argv)
    print(json.dumps(compile_dataset(args.reviewed_jsonl, args.empty_output_directory,
                                     args.holdout_percent), sort_keys=True))


if __name__ == "__main__":
    main()

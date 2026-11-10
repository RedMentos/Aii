"""Verify reviewed body examples against V13 Store before dataset compilation.

No training, database mutation, model calls or promotion. This read-only
preflight binds each approved row to a non-deleted Store source and exact blob
bytes. The output is an ordinary reviewed dataset manifest, not an authority.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import zlib

from .body_dataset import _validate, compile_dataset, MAX_LINE, MAX_ROWS


def _blob(home, digest, max_bytes=64*1024*1024):
    base = home/"data"/"blobs"
    raw = base/digest
    compressed = base/(digest+".z")
    if raw.is_symlink() or compressed.is_symlink():
        raise ValueError("symlinked source blob")
    if raw.is_file():
        if raw.stat().st_size > max_bytes:
            raise ValueError("oversized source blob")
        content = raw.read_bytes()
    elif compressed.is_file():
        if compressed.stat().st_size > max_bytes:
            raise ValueError("oversized compressed source blob")
        d = zlib.decompressobj()
        content = d.decompress(compressed.read_bytes(), max_bytes+1)
        if len(content) > max_bytes or d.unconsumed_tail or not d.eof or d.unused_data:
            raise ValueError("oversized or malformed archived source")
    else:
        raise ValueError("missing source blob")
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError("source blob hash mismatch")
    return content


def verify_store_sources(reviewed_jsonl, store_home):
    """Read-only verification, no mutation of the training or runtime Store."""
    home = Path(store_home)
    db = home/"data"/"db"/"brain.sqlite3"
    if home.is_symlink() or db.is_symlink() or not db.is_file():
        raise ValueError("invalid Store database path")
    con = sqlite3.connect(db.as_uri()+"?mode=ro", uri=True)
    try:
        count = 0
        checked = set()
        input_digest = hashlib.sha256()
        with Path(reviewed_jsonl).open("rb") as f:
            for line in f:
                input_digest.update(line)
                if len(line) > MAX_LINE:
                    raise ValueError("oversized reviewed row")
                if not line.strip():
                    continue
                count += 1
                if count > MAX_ROWS:
                    raise ValueError("too many rows")
                row = _validate(json.loads(line))
                key = (row["source_id"], row["source_sha256"])
                if key in checked:
                    continue
                dbrow = con.execute("SELECT hash,deleted FROM sources WHERE id=?",
                                    (row["source_id"],)).fetchone()
                if not dbrow or dbrow[1] != 0 or dbrow[0] != row["source_sha256"]:
                    raise ValueError("source missing, deleted or hash changed")
                _blob(home, row["source_sha256"])
                checked.add(key)
        if not count:
            raise ValueError("no reviewed rows")
        return {"rows": count, "verified_sources": len(checked),
                "input_sha256": input_digest.hexdigest(),
                "provenance": "READ_ONLY_STORE_SOURCE_BYTES_VERIFIED"}
    finally:
        con.close()


def compile_from_store(reviewed_jsonl, store_home, destination, holdout_percent=20):
    verification = verify_store_sources(reviewed_jsonl, store_home)
    # A changing input is rejected even if its rows remain individually valid.
    # The resulting directory must not be consumed on any exception.
    result = compile_dataset(reviewed_jsonl, destination, holdout_percent)
    if result["input_sha256"] != verification["input_sha256"]:
        raise ValueError("reviewed input changed after Store verification")
    return {"source_verification": verification, "dataset": result}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviewed_jsonl")
    parser.add_argument("store_home")
    parser.add_argument("empty_output_directory")
    parser.add_argument("--holdout-percent", type=int, default=20)
    args = parser.parse_args(argv)
    print(json.dumps(compile_from_store(args.reviewed_jsonl, args.store_home,
                                        args.empty_output_directory, args.holdout_percent),
                     sort_keys=True))


if __name__ == "__main__":
    main()

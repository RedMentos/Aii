"""Run13C opt-in read-only exact SourceRef -> JEF SHADOW answer CLI.

No Runtime, model, tool, Store recovery, coordinator lock, or database write.
This is not active egress or a permission to act on the rendered answer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
from urllib.parse import quote
import zlib

from v13.agi.budget_answer_shadow_run13b import propose_text

MAX_BLOB_BYTES = 1024
MAX_ARCHIVE_BYTES = 8192
MAX_REF_JSON_BYTES = 1024


def _regular_bytes(path, cap):
    """Open by descriptor without following a final symlink; bounded read."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= cap:
            raise ValueError("BLOB_NOT_REGULAR_OR_BOUNDED")
        with os.fdopen(os.dup(fd), "rb") as stream:
            data = stream.read(cap + 1)
        if len(data) > cap or len(data) != info.st_size:
            raise ValueError("BLOB_CHANGED_OR_OVERSIZE")
        return data
    finally:
        os.close(fd)


class ReadOnlySourceStore:
    """Minimal exact source reader against an existing V13 Store snapshot.

    Each read uses a fresh SELECT, not a long-lived snapshot transaction.
    No SQLite migration, recovery, WAL PRAGMA writes or coordinator lock.
    """
    def __init__(self, home):
        home = Path(home).expanduser()
        if home.is_symlink() or not home.is_dir():
            raise ValueError("EXISTING_REAL_HOME_REQUIRED")
        self.home = home.resolve()
        db = self.home / "data/db/brain.sqlite3"
        if db.is_symlink() or not db.is_file():
            raise ValueError("EXISTING_DB_REQUIRED")
        uri = "file:" + quote(str(db), safe="/") + "?mode=ro"
        self.db = sqlite3.connect(uri, uri=True, timeout=5)
        try:
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA query_only=ON")
            if self.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='sources'"
            ).fetchone() is None:
                raise ValueError("SOURCES_TABLE_MISSING")
        except BaseException:
            self.db.close()
            raise

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def read_source(self, ref):
        if type(ref) is not dict or type(ref.get("source_id")) is not str:
            raise ValueError("SOURCE_REF_INVALID")
        row = self.db.execute(
            "SELECT hash,kind,bytes,chars,deleted FROM sources WHERE id=?",
            (ref["source_id"],)
        ).fetchone()
        if (row is None or row["deleted"] != 0 or row["kind"] != "USER"
                or row["hash"] != ref.get("sha256")):
            raise ValueError("SOURCE_MISSING_REVOKED_OR_FOREIGN")
        name = row["hash"]
        if type(name) is not str or len(name) != 64 or any(
                c not in "0123456789abcdef" for c in name):
            raise ValueError("SOURCE_HASH_INVALID")
        blob = self.home / "data/blobs" / name
        if blob.exists() or blob.is_symlink():
            data = _regular_bytes(blob, MAX_BLOB_BYTES)
        else:
            compressed = _regular_bytes(
                blob.with_name(name + ".z"), MAX_ARCHIVE_BYTES)
            dec = zlib.decompressobj()
            data = dec.decompress(compressed, MAX_BLOB_BYTES + 1)
            if (len(data) > MAX_BLOB_BYTES or not dec.eof
                    or dec.unconsumed_tail or dec.unused_data):
                raise ValueError("ARCHIVED_SOURCE_NOT_BOUNDED")
        if (hashlib.sha256(data).hexdigest() != name
                or type(row["bytes"]) is not int
                or row["bytes"] != len(data)):
            raise ValueError("SOURCE_BYTES_OR_HASH_CHANGED")
        text = data.decode("utf-8")
        if row["chars"] != len(text):
            raise ValueError("SOURCE_CHAR_COUNT_CHANGED")
        start, end = ref.get("char_start"), ref.get("char_end")
        if (type(start) is not int or type(end) is not int
                or not 0 <= start <= end <= len(text)):
            raise ValueError("SOURCE_SPAN_INVALID")
        return text[start:end]


def _ref(text):
    if type(text) is not str or not 0 < len(text.encode("utf-8")) <= MAX_REF_JSON_BYTES:
        raise ValueError("REF_JSON_BOUNDS")
    obj = json.loads(text)
    if type(obj) is not dict:
        raise ValueError("REF_JSON_SHAPE")
    return obj


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True,
                        help="existing V13 home; no Runtime or model will start")
    parser.add_argument("--query-ref", required=True,
                        help="exact JSON SourceRef for an existing USER query")
    parser.add_argument("--source-ref", required=True,
                        help="exact JSON SourceRef for an existing USER source")
    args = parser.parse_args(argv)
    try:
        qref, sref = _ref(args.query_ref), _ref(args.source_ref)
        with ReadOnlySourceStore(args.home) as store:
            result = propose_text(store, qref, sref)
        print(json.dumps(result, sort_keys=True, ensure_ascii=False,
                         allow_nan=False))
        return 0 if result.get("answer") is not None else 2
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error,
            UnicodeError, zlib.error) as exc:
        print(json.dumps({"status": "ERROR", "reason": type(exc).__name__,
                          "answer": None, "delivery_authority": 0,
                          "native_calls": 0}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

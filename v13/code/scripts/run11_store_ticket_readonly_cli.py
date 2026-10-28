"""Standalone read-only operator inspection of private Store SHADOW tickets.

This is a deterministic source-integrity inspection, NOT an answer, F5
approval, native model call, learned result or permission for side effects.
The ordinary Store constructor is deliberately never called: it takes the
coordinator lock and can perform migration/recovery writes.
"""
import argparse
import json
from pathlib import Path
import sqlite3

from scripts import run11_store_shadow_ticket_io as ticket_io
from v13.store import Store


class Refusal(ValueError):
    pass


class ReadOnlyStore:
    """Minimal existing-Store reader; no lock, migration, recovery or writes.

    SQLite mode=ro and query_only protect the database from SQL writes through
    this connection. WAL coordination and concurrent source revocation are not
    promised atomic beyond a completed inspection.
    """

    def __init__(self, home):
        self.home = Path(home).expanduser().absolute()
        path = self.home / "data/db/brain.sqlite3"
        if not self.home.is_dir() or not path.is_file() or path.is_symlink():
            raise Refusal("existing_store_required")
        self.db = sqlite3.connect(
            path.as_uri() + "?mode=ro", uri=True,
            check_same_thread=True, isolation_level=None, timeout=5)
        try:
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA query_only=ON")
        except BaseException:
            self.db.close()
            raise

    def rows(self, sql, args=()):
        return [dict(row) for row in self.db.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        rows = self.rows(sql, args)
        return rows[0] if rows else None

    def blob_bytes(self, sha256):
        return Store.blob_bytes(self, sha256)

    def read_source(self, ref):
        return Store.read_source(self, ref)

    def generation(self, gid):
        if not isinstance(gid, str) or not gid:
            raise Refusal("explicit_generation_required")
        return Store.generation(self, gid)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def _safe_output(result):
    if (not isinstance(result, dict) or
            result.get("status") != "SHADOW_ONLY" or
            result.get("action") not in ("A", "B", "NONE") or
            result.get("authority") is not False or
            result.get("f5_decision_authority") is not False or
            result.get("canonical_gate_pass") is not False or
            result.get("native_executed") is not False or
            result.get("model_output_used") is not False or
            type(result.get("jepa_weight")) is not int or
            result["jepa_weight"] != 0 or
            result.get("post_return_atomic") is not False):
        raise Refusal("not_a_shadow_inspection")
    # Deliberately omit source text, source IDs, session, paths and hashes.
    return {
        "status": "SHADOW_ONLY",
        "action": result["action"],
        "authority": False,
        "f5_decision_authority": False,
        "canonical_gate_pass": False,
        "native_executed": False,
        "model_output_used": False,
        "jepa_weight": 0,
        "post_return_atomic": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Inspect an existing private Store SHADOW ticket, without authority")
    for name in ("home", "session", "project", "directory", "filename"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        with ReadOnlyStore(args.home) as reader:
            result = ticket_io.inspect_saved_ticket(
                reader, args.session, args.project, args.directory, args.filename)
            output = _safe_output(result)
        exit_code = 0
    except Exception:
        # Fail closed without exposing raw source text, exception, path or ID.
        output = {"status": "REFUSED", "authority": False,
                  "canonical_gate_pass": False}
        exit_code = 2
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

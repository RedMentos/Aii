"""Explicit offline read-only World-JEPA digital action/outcome audit of a CLOSED V13 store.

No live hook, no DB writes, no weight persistence, no model downloads, no Age authority.
Requires a quiescent SQLite file with no WAL/SHM/journal sidecars.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

try:
    from . import world_jepa_digital_shadow as bridge
except ImportError:  # direct script invocation
    import world_jepa_digital_shadow as bridge


class ReadOnlyStore:
    """Narrow SELECT-only adapter for world_model.transitions; never exposes writes."""
    def __init__(self, db_path):
        p = Path(db_path)
        if p.is_symlink() or not p.is_file():
            raise ValueError('Closed regular SQLite file required')
        if any(Path(str(p) + suffix).exists() for suffix in ('-wal', '-shm', '-journal')):
            raise ValueError('Store has a journal/WAL sidecar; close and checkpoint it first')
        uri = p.resolve(strict=True).as_uri() + '?mode=ro&immutable=1'
        self.conn = sqlite3.connect(uri, uri=True, timeout=1.0, isolation_level=None)
        try:
            self.conn.row_factory = sqlite3.Row
            self.conn.execute('PRAGMA query_only=ON')
            self.conn.execute('BEGIN')
        except BaseException:
            self.conn.close()
            raise

    def _select(self, query, params):
        if type(query) is not str or not query.lstrip().upper().startswith('SELECT '):
            raise PermissionError('Read-only SELECT queries only')
        if type(params) not in (tuple, list):
            raise ValueError('Invalid SELECT parameters')
        return self.conn.execute(query, params)

    def rows(self, query, params=()):
        return self._select(query, params).fetchall()

    def one(self, query, params=()):
        return self._select(query, params).fetchone()

    def close(self):
        try:
            self.conn.rollback()
        finally:
            self.conn.close()


def run_db(db_path):
    store = ReadOnlyStore(db_path)
    try:
        return bridge.run_store(store)
    finally:
        store.close()


def _unavailable():
    return {'status': 'UNAVAILABLE', 'reason': 'CLOSED_STORE_INVALID_OR_INSUFFICIENT',
            'runtime_wired': False, 'age_authority': 0, 'utility_proven': False}


def main(argv=None, stdout=None):
    parser = argparse.ArgumentParser(description='Offline read-only digital outcome SHADOW evaluation')
    parser.add_argument('--db', required=True, type=Path)
    parser.add_argument('--ack-closed-store', action='store_true',
                        help='confirm V13 is stopped and SQLite has no live writer')
    args = parser.parse_args(argv)
    out = sys.stdout if stdout is None else stdout
    if not args.ack_closed_store:
        out.write(json.dumps(_unavailable(), sort_keys=True) + '\n')
        return 2
    try:
        report = run_db(args.db)
    except (ValueError, TypeError, OSError, sqlite3.Error, PermissionError, KeyError):
        out.write(json.dumps(_unavailable(), sort_keys=True) + '\n')
        return 2
    out.write(json.dumps(report, sort_keys=True, allow_nan=False) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())

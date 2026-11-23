"""Bounded, explicit one-row dataset inspection; no scheduler or training.

This review candidate does not connect to V13's frozen runtime.  A pinned
catalog permits individual previews, not dataset admission or weight updates.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib import parse, request

try:
    import fcntl
except ImportError:  # The staging operation fails closed on unsupported platforms.
    fcntl = None

CATALOG_PATH = Path(__file__).resolve().parents[1] / 'specs/bootstrap_dataset_catalog_20261109.json'
CATALOG_SHA256 = '53c4d35d0b7b9348282b8e5e5877156969e1bcf6f37aa8bd8ee25aa751f1df2b'
VIEWER_URL = 'https://datasets-server.huggingface.co/rows'
MAX_RESPONSE = 256 * 1024
MAX_CATALOG = 1024 * 1024
DEFAULT_QUOTA = 8 * 1024 * 1024
MAX_QUOTA = 1024 * 1024 * 1024
MAX_FILES = 4096
MAX_OFFSET = 2**31 - 1
LOCK_NAME = '.v13-dataset.lock'


class ProbeError(ValueError):
    """A preview was refused; no learning permission follows from a preview."""


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                          allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ProbeError('invalid JSON value') from exc


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ProbeError('duplicate JSON key')
        result[key] = value
    return result


def _loads(raw):
    try:
        def invalid_constant(_value):
            raise ProbeError('non-finite JSON value')
        return json.loads(raw, object_pairs_hook=_object_pairs, parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ProbeError('invalid JSON document') from exc


def _valid_int(value, minimum, maximum):
    return isinstance(value, int) and not isinstance(value, bool) and minimum <= value <= maximum


def _validate_catalog(doc):
    if not isinstance(doc, dict) or doc.get('schema') != 'v13-dataset-catalog-v1':
        raise ProbeError('unsupported catalog')
    entries = doc.get('entries')
    if not isinstance(entries, list) or not entries:
        raise ProbeError('catalog entries missing')
    allowed_access = {'PROBE', 'HOLD_LICENSE', 'HOLD_MIXED', 'HOLD_EVAL_OVERLAP',
                      'HOLD_LATER_LANGUAGE', 'HOLD_HUMAN_DATA', 'HOLD_PROVENANCE',
                      'HOLD_NONCOMMERCIAL', 'HOLD_VIEWER_UNAVAILABLE'}
    out = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ProbeError('invalid catalog entry')
        entry_id = entry.get('id')
        if not isinstance(entry_id, str) or not re.fullmatch(r'[a-z0-9_]{1,80}', entry_id) or entry_id in out:
            raise ProbeError('invalid or duplicate dataset id')
        if entry.get('access') not in allowed_access:
            raise ProbeError('invalid catalog access')
        if entry['access'] == 'PROBE':
            repo, config, split, revision = (entry.get(k) for k in ('repo', 'config', 'split', 'revision'))
            license_value = entry.get('license_declared')
            valid_license = (isinstance(license_value, str) and license_value.strip()
                             and license_value.lower() not in {'unknown', 'other'}) or (
                isinstance(license_value, list) and bool(license_value)
                and all(isinstance(x, str) and x.strip() and x.lower() not in {'unknown', 'other'}
                        for x in license_value))
            if (not isinstance(repo, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*/[A-Za-z0-9_][A-Za-z0-9_.-]*', repo)
                    or not isinstance(config, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,150}', config)
                    or not isinstance(split, str) or not re.fullmatch(r'train(?:_[A-Za-z0-9]+)?', split)
                    or set(split.lower().split('_')) & {'test', 'val', 'validation', 'eval', 'evaluation', 'benchmark'}
                    or not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision)
                    or entry.get('split_verified') is not True or not valid_license
                    or entry.get('language') != 'en'):
                raise ProbeError('unverified probe entry: ' + entry_id)
        out[entry_id] = entry
    return out


def load_catalog():
    """Read the pinned manifest. Neither loading nor listing uses the network."""
    if not all(hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_NONBLOCK')):
        raise ProbeError('safe catalog reading unsupported on this platform')
    try:
        fd = os.open(CATALOG_PATH, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_CATALOG:
                raise ProbeError('catalog is not a bounded regular file')
            chunks = []
            remaining = MAX_CATALOG + 1
            while remaining:
                chunk = os.read(fd, min(remaining, 65536))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b''.join(chunks)
            if len(raw) != info.st_size or len(raw) > MAX_CATALOG:
                raise ProbeError('catalog changed or exceeded its byte limit')
        finally:
            os.close(fd)
    except OSError as exc:
        raise ProbeError('catalog unavailable') from exc
    if _hash(raw) != CATALOG_SHA256:
        raise ProbeError('catalog hash mismatch')
    return _validate_catalog(_loads(raw))


def list_catalog():
    return [{'id': e['id'], 'repo': e['repo'], 'access': e['access']}
            for e in load_catalog().values()]


def _select(dataset_id):
    entries = load_catalog()
    if dataset_id not in entries:
        raise ProbeError('unknown dataset')
    item = entries[dataset_id]
    if item['access'] != 'PROBE':
        raise ProbeError('dataset is held: ' + item['access'])
    return item


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open_viewer(req, timeout):
    # Refuse redirects before opening any other URL, even without credentials.
    return request.build_opener(_NoRedirect()).open(req, timeout=timeout)


def fetch_one(dataset_id, offset=0, *, timeout=15, opener=None):
    """Explicit HTTPS read of one row, returned in memory, never trained on.

    Revision must match the manifest. The viewer serves its current revision;
    this tool does not silently fall back when an older revision is unavailable.
    """
    if not _valid_int(offset, 0, MAX_OFFSET):
        raise ProbeError('invalid row offset')
    item = _select(dataset_id)
    query = parse.urlencode({'dataset': item['repo'], 'config': item['config'],
                             'split': item['split'], 'offset': offset, 'length': 1})
    req = request.Request(VIEWER_URL + '?' + query,
                          headers={'Accept': 'application/json', 'Accept-Encoding': 'identity'})
    open_url = opener or _open_viewer
    try:
        with contextlib.closing(open_url(req, timeout=timeout)) as response:
            if response.status != 200:
                raise ProbeError('dataset viewer returned non-success status')
            destination = parse.urlsplit(response.geturl())
            if (destination.scheme != 'https' or destination.netloc != 'datasets-server.huggingface.co'
                    or destination.path != '/rows'
                    or destination.query != parse.urlsplit(req.full_url).query or destination.fragment):
                raise ProbeError('unexpected viewer destination')
            if response.headers.get('X-Revision') != item['revision']:
                raise ProbeError('dataset revision differs from catalog')
            encoding = response.headers.get('Content-Encoding', 'identity').strip().lower()
            if encoding not in ('', 'identity'):
                raise ProbeError('compressed response refused')
            content_length = response.headers.get('Content-Length')
            if content_length is not None:
                if not content_length.isascii() or not content_length.isdecimal() or int(content_length) > MAX_RESPONSE:
                    raise ProbeError('invalid or oversized response length')
            body = response.read(MAX_RESPONSE + 1)
            if len(body) > MAX_RESPONSE:
                raise ProbeError('oversized response')
            if content_length is not None and len(body) != int(content_length):
                raise ProbeError('incomplete response')
    except ProbeError:
        raise
    except Exception as exc:
        raise ProbeError('dataset viewer request failed') from exc
    doc = _loads(body)
    if not isinstance(doc, dict):
        raise ProbeError('invalid viewer response')
    total, rows = doc.get('num_rows_total'), doc.get('rows')
    if (not _valid_int(total, 1, MAX_OFFSET + 1) or offset >= total
            or not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict)):
        raise ProbeError('invalid viewer row count')
    row = rows[0]
    if (not _valid_int(row.get('row_idx'), 0, MAX_OFFSET) or row['row_idx'] != offset
            or row.get('truncated_cells') != [] or not isinstance(row.get('row'), dict)):
        raise ProbeError('truncated or mismatched viewer row')
    value = row['row']
    row_sha = _hash(_json_bytes(value))
    return {'schema': 'v13-dataset-preview-v1', 'dataset_id': dataset_id,
            'repo': item['repo'], 'config': item['config'], 'split': item['split'],
            'revision': item['revision'], 'offset': offset, 'total_rows': total,
            'row': value, 'row_sha256': row_sha, 'response_sha256': _hash(body),
            'purpose': 'PREVIEW_ONLY', 'training_authority': 0}


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        count = os.write(fd, view)
        if count <= 0:
            raise ProbeError('short file write')
        view = view[count:]


def _storage_usage(dir_fd):
    size = count = 0
    with os.scandir(dir_fd) as entries:
        for entry in entries:
            count += 1
            if count > MAX_FILES:
                raise ProbeError('too many directory entries')
            info = entry.stat(follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):
                raise ProbeError('staging directory contains non-regular entry')
            size += info.st_size
    return size, count


def _filename(item, offset):
    return _hash(_json_bytes([item[k] for k in ('repo', 'config', 'split', 'revision')] + [offset])) + '.json'


def _read_staged_at(dir_fd, filename):
    fd = os.open(filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dir_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_RESPONSE + 4096:
            raise ProbeError('unsafe or oversized staged preview')
        chunks = []
        remaining = MAX_RESPONSE + 4097
        while remaining:
            chunk = os.read(fd, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b''.join(chunks)
        if len(raw) != info.st_size or len(raw) > MAX_RESPONSE + 4096:
            raise ProbeError('staged preview changed or is oversized')
        return _loads(raw)
    finally:
        os.close(fd)


def _validate_staged(value, item, dataset_id, offset):
    if not isinstance(value, dict) or set(value) != {
            'schema', 'dataset_id', 'repo', 'config', 'split', 'revision', 'offset',
            'total_rows', 'row', 'row_sha256', 'response_sha256', 'purpose', 'training_authority'}:
        raise ProbeError('invalid staged preview')
    if (value['schema'] != 'v13-dataset-preview-v1' or value['dataset_id'] != dataset_id
            or any(value[k] != item[k] for k in ('repo', 'config', 'split', 'revision'))
            or not _valid_int(value['offset'], offset, offset)
            or not _valid_int(value['total_rows'], offset + 1, MAX_OFFSET + 1)
            or not isinstance(value['row'], dict)
            or value['row_sha256'] != _hash(_json_bytes(value['row']))
            or not isinstance(value['response_sha256'], str)
            or not re.fullmatch(r'[0-9a-f]{64}', value['response_sha256'])
            or value['purpose'] != 'PREVIEW_ONLY' or type(value['training_authority']) is not int
            or value['training_authority'] != 0):
        raise ProbeError('invalid staged preview or source binding')
    return value


def read_staged(dataset_id, out_dir, offset=0):
    """Read and check an already staged preview offline; does not invoke a model."""
    if not _valid_int(offset, 0, MAX_OFFSET):
        raise ProbeError('invalid row offset')
    item = _select(dataset_id)
    if not all(hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')):
        raise ProbeError('safe staged reading unsupported on this platform')
    try:
        dir_fd = os.open(Path(out_dir), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            value = _read_staged_at(dir_fd, _filename(item, offset))
        finally:
            os.close(dir_fd)
    except OSError as exc:
        raise ProbeError('cannot read staged preview') from exc
    return _validate_staged(value, item, dataset_id, offset)


def stage_one(dataset_id, out_dir, offset=0, *, quota_bytes=DEFAULT_QUOTA, opener=None, timeout=15):
    """Fetch and explicitly stage one preview; bounded for cooperating writers.

    Existing files are never removed or overwritten. An OS file lock protects
    quota checks between callers of this function in the same directory.
    """
    if not _valid_int(quota_bytes, 1, MAX_QUOTA):
        raise ProbeError('invalid staging quota')
    if fcntl is None or not all(hasattr(os, flag) for flag in ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')):
        raise ProbeError('safe staging unsupported on this platform')
    preview = fetch_one(dataset_id, offset, timeout=timeout, opener=opener)
    data = _json_bytes(preview) + b'\n'
    if len(data) > MAX_RESPONSE + 4096:
        raise ProbeError('preview is too large to stage')
    filename = _filename(preview, offset)
    directory = Path(out_dir)
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        dir_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise ProbeError('cannot open staging directory') from exc
    lock_fd = None
    temp_name = None
    try:
        lock_fd = os.open(LOCK_NAME, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=dir_fd)
        if not stat.S_ISREG(os.fstat(lock_fd).st_mode) or os.fstat(lock_fd).st_nlink != 1:
            raise ProbeError('unsafe staging lock')
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ProbeError('staging directory busy') from exc
        used, count = _storage_usage(dir_fd)
        if used > quota_bytes:
            raise ProbeError('staging quota exceeded; existing files preserved')
        try:
            old_info = os.stat(filename, dir_fd=dir_fd, follow_symlinks=False)
        except FileNotFoundError:
            old_info = None
        if old_info is not None:
            existing = _validate_staged(_read_staged_at(dir_fd, filename), preview, dataset_id, offset)
            # Viewer-level metadata or reported total may change while the row is identical.
            # Keep the original response receipt, never silently replace it.
            original_core = {k: v for k, v in existing.items() if k not in {'response_sha256', 'total_rows'}}
            new_core = {k: v for k, v in preview.items() if k not in {'response_sha256', 'total_rows'}}
            if _json_bytes(original_core) != _json_bytes(new_core):
                raise ProbeError('existing preview differs')
            status = 'ALREADY_STAGED'
        else:
            # One temporary name and one final hardlink coexist briefly.
            if count + 2 > MAX_FILES:
                raise ProbeError('too many directory entries for staging')
            if used + len(data) > quota_bytes:
                raise ProbeError('staging quota exceeded; existing files preserved')
            import secrets
            proposed_name = '.v13-preview-' + secrets.token_hex(16) + '.tmp'
            temp_fd = os.open(proposed_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                              0o600, dir_fd=dir_fd)
            temp_name = proposed_name  # Only the file successfully created by this call is ours.
            try:
                _write_all(temp_fd, data)
                os.fsync(temp_fd)
            finally:
                os.close(temp_fd)
            os.link(temp_name, filename, src_dir_fd=dir_fd, dst_dir_fd=dir_fd, follow_symlinks=False)
            os.unlink(temp_name, dir_fd=dir_fd)
            temp_name = None
            os.fsync(dir_fd)
            used += len(data)
            status = 'STAGED'
        return {'status': status, 'file': filename, 'bytes': len(data),
                'used_bytes': used, 'quota_bytes': quota_bytes,
                'dataset_id': dataset_id, 'offset': offset,
                'row_sha256': preview['row_sha256'], 'revision': preview['revision'],
                'purpose': 'PREVIEW_ONLY', 'training_authority': 0}
    except ProbeError:
        raise
    except OSError as exc:
        raise ProbeError('staging failed; existing files preserved') from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name, dir_fd=dir_fd)
            except OSError:
                pass
        if lock_fd is not None:
            os.close(lock_fd)
        os.close(dir_fd)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command')
    subs.add_parser('list', help='list catalog without network access')
    for command in ('probe', 'stage', 'read'):
        sub = subs.add_parser(command, help=('read a staged preview offline' if command == 'read'
                                             else 'explicitly fetch one row for preview'))
        sub.add_argument('dataset_id')
        sub.add_argument('--offset', type=int, default=0)
        if command in ('stage', 'read'):
            sub.add_argument('--out-dir', type=Path, required=True)
        if command == 'stage':
            sub.add_argument('--quota-bytes', type=int, default=DEFAULT_QUOTA)
    args = parser.parse_args(argv)
    try:
        if args.command in (None, 'list'):
            result = list_catalog()
        elif args.command == 'probe':
            result = fetch_one(args.dataset_id, args.offset)
            del result['row']  # Never print downloaded content in the terminal.
        elif args.command == 'read':
            result = read_staged(args.dataset_id, args.out_dir, args.offset)
            del result['row']
        else:
            result = stage_one(args.dataset_id, args.out_dir, args.offset, quota_bytes=args.quota_bytes)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except ProbeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

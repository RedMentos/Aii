"""Private, no-overwrite persistence for non-authoritative Store SHADOW tickets.

Requires an existing user-owned 0700 directory. Never writes to V13 Store,
Runtime, model or learning state. Ticket checksums are NOT signatures/F5 rights.
"""
import hashlib
import json
import os
import re
import secrets
import stat

from scripts import run11_store_shadow_use_boundary as boundary

MAX_BYTES = 65536
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\.json\Z")


class Refusal(ValueError):
    pass


def _name(name):
    if not isinstance(name, str) or NAME.fullmatch(name) is None:
        raise Refusal("invalid_ticket_filename")
    return name


def _dirfd(directory):
    try:
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        info = os.fstat(fd)
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or
                info.st_mode & 0o077):
            raise Refusal("private_directory_required")
        return fd
    except Exception as exc:
        if "fd" in locals():
            os.close(fd)
        raise Refusal("private_directory_required") from exc


def _stable(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def _write_once(directory, name, content):
    _name(name)
    if not isinstance(content, bytes) or not 1 <= len(content) <= MAX_BYTES:
        raise Refusal("ticket_size_or_type")
    dfd = _dirfd(directory)
    temp = ".pending-" + secrets.token_hex(12)
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=dfd)
        with os.fdopen(fd, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        # Atomic no-overwrite link, then remove temporary name. No target
        # symlink traversal, no replacement of existing proof artifacts.
        os.link(temp, name, src_dir_fd=dfd, dst_dir_fd=dfd,
                follow_symlinks=False)
        os.unlink(temp, dir_fd=dfd)
        os.fsync(dfd)
    except Exception as exc:
        try:
            os.unlink(temp, dir_fd=dfd)
        except OSError:
            pass
        raise Refusal("ticket_save_refused") from exc
    finally:
        os.close(dfd)


def _read_once(directory, name):
    _name(name)
    dfd = _dirfd(directory)
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dfd)
        try:
            before = os.fstat(fd)
            if (not stat.S_ISREG(before.st_mode) or
                    before.st_uid != os.getuid() or
                    before.st_mode & 0o077 or before.st_nlink != 1 or
                    not 1 <= before.st_size <= MAX_BYTES):
                raise Refusal("ticket_file_integrity")
            content = os.read(fd, MAX_BYTES + 1)
            after = os.fstat(fd)
            if len(content) != before.st_size or _stable(before) != _stable(after):
                raise Refusal("ticket_changed_during_read")
            return content
        finally:
            os.close(fd)
    except Exception as exc:
        raise Refusal("ticket_load_refused") from exc
    finally:
        os.close(dfd)


def _canonical(ticket):
    try:
        payload = boundary._payload(ticket)
        if boundary._digest(payload) != ticket["seal_sha256"]:
            raise Refusal("ticket_modified")
        return json.dumps(ticket, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except Exception as exc:
        raise Refusal("ticket_not_canonical") from exc


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refusal("duplicate_ticket_key")
        result[key] = value
    return result


def save_ticket(store, ticket, session, project, directory, filename):
    """Write a source-live SHADOW ticket exactly once to private local disk."""
    try:
        boundary.inspect_shadow(store, ticket, session, project)
        content = _canonical(ticket)
        _write_once(directory, filename, content)
    except Exception as exc:
        raise Refusal("shadow_ticket_save_refused") from exc
    return {"status": "SHADOW_ONLY", "authority": False,
            "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            "post_return_atomic": False}


def inspect_saved_ticket(store, session, project, directory, filename):
    """Re-read original Store and refuse revoked/tampered disk tickets."""
    try:
        content = _read_once(directory, filename)
        ticket = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_pairs)
        if _canonical(ticket) != content:
            raise Refusal("noncanonical_ticket_bytes")
        return boundary.inspect_shadow(store, ticket, session, project)
    except Exception as exc:
        raise Refusal("shadow_ticket_replay_refused") from exc

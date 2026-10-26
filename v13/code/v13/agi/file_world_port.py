"""Explicit, bounded real-file observation bridge for F3/F4 Self/World.

This is a read-only, opt-in poller for a local `tool_sandbox` directory.
No background thread, model, learning, permissions or automatic tool calls.
Only content digests and counts enter SelfSystem, never source file text.
The port is separate from the fixed Z12a benchmark's 16-hex digest cohort.
"""
import hashlib
import math
import os
from pathlib import Path
import re
import stat
import time
import threading

_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}\.txt\Z")
_MAX_FILES = 256
_MAX_BYTES = 65536


class SandboxWorldPort:
    """Explicit polling of a single existing local tool_sandbox directory.

    Baseline advances only after a completely valid scan. Callers must
    separately authorize every tool action; observing confers no tool rights.
    """

    def __init__(self, root, *, max_files=_MAX_FILES, max_bytes=_MAX_BYTES):
        self.root = Path(root)
        if self.root.name != "tool_sandbox":
            raise ValueError("only a named tool_sandbox may be observed")
        if type(max_files) is not int or not 1 <= max_files <= _MAX_FILES:
            raise ValueError("invalid max_files")
        if type(max_bytes) is not int or not 1 <= max_bytes <= _MAX_BYTES:
            raise ValueError("invalid max_bytes")
        self.max_files = max_files
        self.max_bytes = max_bytes
        try:
            st = self.root.lstat()
        except OSError as exc:
            raise ValueError("sandbox unavailable") from exc
        if not stat.S_ISDIR(st.st_mode):
            raise ValueError("sandbox root must be a real directory")
        self._identity = (st.st_dev, st.st_ino)
        self._lock = threading.RLock()
        self._previous = self._scan()

    def _scan(self):
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            root_fd = os.open(self.root, flags)
        except OSError as exc:
            raise ValueError("sandbox root cannot be opened safely") from exc
        try:
            st = os.fstat(root_fd)
            if not stat.S_ISDIR(st.st_mode) or (st.st_dev, st.st_ino) != self._identity:
                raise ValueError("sandbox root changed")
            files = {}
            count = 0
            entries = 0
            with os.scandir(root_fd) as iterator:
                for ent in iterator:
                    entries += 1
                    if entries > self.max_files * 4:
                        raise ValueError("sandbox entry budget exceeded")
                    if not ent.name.endswith(".txt"):
                        continue
                    if not _NAME.fullmatch(ent.name):
                        raise ValueError("unsafe sandbox filename")
                    if len(files) >= self.max_files:
                        raise ValueError("sandbox file budget exceeded")
                    info = ent.stat(follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode):
                        value = "DIR"
                    elif stat.S_ISREG(info.st_mode):
                        if info.st_size > self.max_bytes:
                            raise ValueError("sandbox file too large")
                        fd = os.open(ent.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                                     dir_fd=root_fd)
                        with os.fdopen(fd, "rb") as handle:
                            before = os.fstat(handle.fileno())
                            if not stat.S_ISREG(before.st_mode) or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino):
                                raise ValueError("sandbox file changed during open")
                            data = handle.read(self.max_bytes + 1)
                            after = os.fstat(handle.fileno())
                        if (len(data) > self.max_bytes or len(data) != before.st_size
                                or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
                            raise ValueError("sandbox file changed during read")
                        value = hashlib.sha256(data).hexdigest()
                        count += 1
                    else:
                        raise ValueError("unsupported sandbox file type")
                    files[ent.name[:-4]] = value
            final = self.root.lstat()
            if not stat.S_ISDIR(final.st_mode) or (final.st_dev, final.st_ino) != self._identity:
                raise ValueError("sandbox root changed during scan")
            return files, count
        except (OSError, UnicodeError) as exc:
            raise ValueError("sandbox scan failed closed") from exc
        finally:
            os.close(root_fd)

    def _pending(self, t):
        """Stage changes against the last committed baseline, without consuming them."""
        timestamp = time.time() if t is None else t
        if type(timestamp) not in (int, float) or not math.isfinite(timestamp):
            raise ValueError("invalid observation timestamp")
        fresh = self._scan()
        old_files, old_count = self._previous
        new_files, new_count = fresh
        rows = [
            {"channel": "file:" + name, "value": new_files.get(name), "t": timestamp}
            for name in sorted(set(old_files) | set(new_files))
            if old_files.get(name) != new_files.get(name)
        ]
        if old_count != new_count:
            rows.append({"channel": "listing", "value": new_count, "t": timestamp})
        return rows, fresh

    def poll(self, *, t=None):
        """Explicit read-only poll; successful scans consume the baseline."""
        with self._lock:
            rows, fresh = self._pending(t)
            self._previous = fresh
            return rows

    def observe(self, selfsys, event_id, *, t=None, extra_observations=(), close=()):
        """Forward actual changes to F3/F4 before committing the scan baseline.

        If attribution raises, a later explicit retry sees the same file
        changes. In-process exception safety only: this is NOT a crash-atomic
        exactly-once transaction across multiple SelfSystem packet writes.
        Additional observations/close IDs are supplied only by an already
        authorized caller (e.g. the verified WP-K action-status binding).
        """
        with self._lock:
            rows, fresh = self._pending(t)
            extra = list(extra_observations)
            if not rows and not extra and not close:
                return []
            attributed = selfsys.observe(event_id, rows + extra, close=list(close))
            self._previous = fresh
            return attributed

"""Durable local stop latch for the opt-in Android operator console.

Termux process-level stop, not an Android OS security boundary.
Only a separately authorized local maintenance procedure may clear the latch.
"""
from __future__ import annotations

import os
from pathlib import Path


class StopLatch:
    def __init__(self, audit_path: str | Path):
        self.path = Path(str(audit_path) + ".stopped")

    def engaged(self) -> bool:
        # Any existing marker, including malformed/symlinked, means stopped.
        # Failure to inspect is also treated as stopped.
        try:
            return self.path.exists() or self.path.is_symlink()
        except OSError:
            return True

    def engage(self) -> None:
        """Persist a stop marker; no reset method is exposed."""
        parent = self.path.parent
        parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(self.path, flags, 0o600)
        except FileExistsError:
            return
        with os.fdopen(fd, "wb") as stream:
            stream.write(b"V13_ANDROID_STOP_V1\n")
            stream.flush()
            os.fsync(stream.fileno())
        dir_fd = os.open(parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

"""Read-only verification of the *installed* Termux V13 runtime, not the Git checkout.

This diagnostic never reads model, chat or database contents. It reports only
bounded status enums, and does not grant Android capabilities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from . import runtime_deploy as deployment


def _regular_owned(path: Path) -> bool:
    try:
        return (not path.is_symlink() and path.is_file()
                and path.stat().st_uid == os.getuid())
    except OSError:
        return False


def inspect(*, home=None, private=None, builds=None) -> dict:
    home = Path(home or Path.home() / "v13").expanduser()
    private = Path(private or Path.home() / ".v13-private").expanduser()
    builds = Path(builds or Path.home() / ".v13-runtime-builds").expanduser()
    result = {"schema": "v13.phone-runtime-health/1", "status": "NOT_INSTALLED",
              "launcher": "MISSING", "snapshot": "MISSING",
              "marker": "MISSING", "model_contents_read": False,
              "database_contents_read": False}
    marker_path = private / deployment.MARKER_NAME
    launcher = home / "bin/v13"
    if not _regular_owned(marker_path):
        return result
    try:
        if marker_path.stat().st_size > 4096 or marker_path.stat().st_mode & 0o077:
            result["marker"] = "UNSAFE"
            result["status"] = "INVALID"
            return result
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            raise ValueError("not a marker")
    except (OSError, UnicodeError, ValueError):
        result["marker"] = "INVALID"
        result["status"] = "INVALID"
        return result
    result["marker"] = "PRESENT"
    if not _regular_owned(launcher):
        result["status"] = "INVALID"
        return result
    expected = marker.get("launcher_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        result["launcher"] = "INVALID"
        result["status"] = "INVALID"
        return result
    try:
        result["launcher"] = ("MATCH" if hashlib.sha256(launcher.read_bytes()).hexdigest()
                              == expected else "MISMATCH")
        code_text = marker.get("code")
        if not isinstance(code_text, str):
            raise ValueError("no code")
        code = Path(code_text)
        # Never follow a marker-controlled path outside the immutable build root.
        build_root = builds.resolve(strict=True)
        resolved = code.resolve(strict=True)
        if not resolved.is_relative_to(build_root) or code.is_symlink():
            raise ValueError("outside build root")
        if not resolved.parent.name.startswith("v13-") or resolved.name != "code":
            raise ValueError("invalid build layout")
        if not resolved.is_dir():
            raise ValueError("missing build")
        result["snapshot"] = "PRESENT"
        for rel in deployment.REQUIRED:
            item = resolved / rel
            # A parent directory may be a symlink even when the file itself is not.
            # Require every resolved source to stay within the pinned snapshot.
            if (not item.is_file() or item.is_symlink()
                    or not item.resolve(strict=True).is_relative_to(resolved)
                    or item.stat().st_size == 0):
                result["snapshot"] = "INCOMPLETE"
                break
    except (OSError, ValueError, RuntimeError):
        result["snapshot"] = "INVALID"
    result["status"] = ("READY" if result["launcher"] == "MATCH"
                        and result["snapshot"] == "PRESENT" else "INVALID")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect installed V13 without reading private content")
    parser.add_argument("--home")
    parser.add_argument("--private")
    parser.add_argument("--builds")
    args = parser.parse_args(argv)
    print(json.dumps(inspect(home=args.home, private=args.private,
                             builds=args.builds), sort_keys=True))


if __name__ == "__main__":
    main()

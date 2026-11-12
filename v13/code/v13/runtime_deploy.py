"""Install a CI-verified V13 runtime snapshot actually used by ~/v13/bin/v13.

A Git fetch alone never updates the existing pinned launcher. This module
stages a complete, immutable code snapshot, verifies canon and normal-text
source roundtrips, and atomically switches ONLY the launcher. Existing GGUF
models, user data, SQLite and control permissions remain untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time

SOURCE_BRANCH = "gpt6/v13-private-remote-bridge-20261111"
REPO_ORIGIN = ("https://github.com/RedMentos/Aii",
               "https://github.com/RedMentos/Aii.git",
               "git@github.com:RedMentos/Aii.git")
CANON = "docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md"
REQUIRED = ("v13/__main__.py", "v13/store.py", "v13/runtime.py",
            "v13/common.py", "v13/models.py", "v13/ui.py",
            "scripts/needle_worker.cpp", "specs/models.json", CANON)
COPY_SUBTREES = ("v13", "scripts", "specs", "docs/canon")
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
MARKER_NAME = "runtime-active.json"


class RuntimeDeployError(RuntimeError):
    pass


def _git(root, *args):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        out = subprocess.run(["git", "-C", str(root), *args],
                             capture_output=True, text=True, env=env,
                             timeout=50, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeDeployError("Git status unavailable") from exc
    if out.returncode != 0:
        raise RuntimeDeployError("Runtime Git verification failed: " + args[0])
    return out.stdout.strip()


def _source(source):
    root = Path(source).expanduser().resolve()
    if not root.is_dir() or not (root / ".git").is_dir():
        raise RuntimeDeployError("Full V13 runtime Git checkout missing")
    if Path(_git(root, "rev-parse", "--show-toplevel")) != root:
        raise RuntimeDeployError("Runtime Git working root changed")
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch != SOURCE_BRANCH:
        raise RuntimeDeployError("Runtime source is on a different branch")
    if _git(root, "remote", "get-url", "origin") not in REPO_ORIGIN:
        raise RuntimeDeployError("Untrusted V13 runtime source origin")
    if _git(root, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeDeployError("Runtime source has local changes; refusing overwrite")
    commit = _git(root, "rev-parse", "HEAD")
    if not HEX40.fullmatch(commit):
        raise RuntimeDeployError("Invalid pinned commit")
    code = root / "v13/code"
    for rel in REQUIRED:
        path = code / rel
        if path.is_symlink() or not path.is_file():
            raise RuntimeDeployError("Required runtime file missing: " + rel)
    return root, code, commit


def _protected_dir(path):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeDeployError("Symlinked private runtime directory")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or path.stat().st_uid != os.getuid():
        raise RuntimeDeployError("Runtime private directory not owner-owned")
    # A previous, otherwise valid runtime-builds directory may be 0755.
    # Tightening permissions is safe; never modify files under user data.
    path.chmod(0o700)
    if path.stat().st_mode & 0o077:
        raise RuntimeDeployError("Runtime private directory not owner-only")
    return path


def _marker(private):
    marker = private / MARKER_NAME
    if marker.is_symlink() or not marker.is_file():
        return {}
    try:
        if marker.stat().st_size > 4096 or marker.stat().st_mode & 0o077:
            return {}
        data = json.loads(marker.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _launcher(home):
    path = home / "bin/v13"
    if not path.is_file() or path.is_symlink() or path.stat().st_uid != os.getuid():
        raise RuntimeDeployError("Installed V13 launcher missing or unsafe")
    return path


def needs_deploy(source, *, home=None, private=None):
    _, code, commit = _source(source)
    home = Path(home or Path.home() / "v13")
    private = Path(private or Path.home() / ".v13-private")
    target = _marker(private)
    try:
        launcher = _launcher(home)
    except RuntimeDeployError:
        return True
    codepath = target.get("code")
    if (target.get("commit") != commit or not isinstance(codepath, str)
            or not (Path(codepath) / CANON).is_file()):
        return True
    return target.get("launcher_sha256") != hashlib.sha256(launcher.read_bytes()).hexdigest()


def _check_stopped(home):
    """Only mutate launcher when managed AI has already stopped for update."""
    from . import lifecycle
    if lifecycle.STOP_REQUEST.is_file():
        # The model has to be stopped already by the supervisor before launch.
        pass
    from . import source_updater
    if source_updater._runtime_active():
        raise RuntimeDeployError("V13 chat is still running; runtime deployment deferred")


def _copy(source, target):
    for rel in COPY_SUBTREES:
        src = source / rel
        dest = target / rel
        if not src.is_dir() or src.is_symlink():
            raise RuntimeDeployError("Missing source subtree: " + rel)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest, symlinks=False,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".git"))
    for rel in REQUIRED:
        path = target / rel
        if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
            raise RuntimeDeployError("Staged runtime dependency missing: " + rel)
        if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256((source / rel).read_bytes()).digest():
            raise RuntimeDeployError("Staged source mismatch: " + rel)


def _selftest(code):
    env = {**os.environ,
           "PYTHONPATH": str(code),
           "NO_MODEL_DOWNLOADS": "1", "DO_NOT_TRACK": "1",
           "NEEDLE_TELEMETRY": "0"}
    script = """
from pathlib import Path
from tempfile import TemporaryDirectory
from v13.config import initialize
from v13.store import Store
from v13.common import digest
with TemporaryDirectory(prefix="v13-install-probe-") as t:
    home = Path(t)
    initialize(home)
    s = Store(home)
    for message in ("Hi", "Test", "..."):
        ref = s.source(message)
        assert ref["sha256"] == digest(message)
        assert s.read_source(ref) == message
    s.close()
"""
    for args in ([sys.executable, "-m", "v13", "--help"],
                 [sys.executable, "-c", script]):
        try:
            run = subprocess.run(args, cwd=str(code), env=env,
                                 capture_output=True, timeout=45, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeDeployError("Staged runtime startup/selftest timed out") from exc
        if run.returncode:
            raise RuntimeDeployError("Staged V13 source-ref/startup selftest failed")


def _launcher_bytes(code, home):
    python = str(Path(sys.executable).resolve())
    return ("#!/data/data/com.termux/files/usr/bin/bash\n"
            "set -e\n"
            "export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1\n"
            "export PYTHONPATH=" + shlex.quote(str(code)) + "\n"
            "exec " + shlex.quote(python) + " -m v13 --home "
            + shlex.quote(str(home)) + ' "$@"\n').encode("utf-8")


def _atomic_file(dest, data, mode=0o600):
    fd, name = tempfile.mkstemp(prefix=".v13-deploy-", dir=str(dest.parent))
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, dest)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def deploy(source, *, home=None, private=None, builds=None, ci_verified=False):
    root, code, commit = _source(source)
    home = Path(home or Path.home() / "v13").expanduser().resolve()
    private = _protected_dir(private or Path.home() / ".v13-private")
    builds = _protected_dir(builds or Path.home() / ".v13-runtime-builds")
    launcher = _launcher(home)
    _check_stopped(home)
    if not ci_verified:
        from .source_updater import ci_passed
        if not ci_passed(commit, scope="runtime"):
            raise RuntimeDeployError("Exact V13 runtime source commit is not CI-green")
    if not needs_deploy(root, home=home, private=private):
        return {"status": "UP_TO_DATE", "commit": commit,
                "launcher_verified": True}
    before = launcher.read_bytes()
    backup = private / ("launcher-backup-" + secrets.token_hex(8) + ".sh")
    _atomic_file(backup, before, stat.S_IMODE(launcher.stat().st_mode))
    stage = builds / ("v13-" + commit[:12] + "-" + secrets.token_hex(4))
    if stage.exists() or stage.is_symlink():
        raise RuntimeDeployError("Runtime staging collision")
    stage.mkdir(mode=0o700)
    target = stage / "code"
    target.mkdir(mode=0o700)
    try:
        _copy(code, target)
        _selftest(target)
        _check_stopped(home)
        next_launcher = _launcher_bytes(target, home)
        _atomic_file(launcher, next_launcher, 0o700)
        record = {"schema": "v13.runtime-deploy/1", "commit": commit,
                  "code": str(target), "backup_launcher": str(backup),
                  "launcher_sha256": hashlib.sha256(next_launcher).hexdigest(),
                  "installed_at": int(time.time()),
                  "models_untouched": True, "sqlite_untouched": True}
        _atomic_file(private / MARKER_NAME,
                     json.dumps(record, sort_keys=True).encode("utf-8"))
        return {"status": "DEPLOYED", "commit": commit, "code": str(target),
                "launcher_verified": True}
    except BaseException:
        # Old launcher was not changed until the final atomic switch.
        if launcher.read_bytes() != before:
            _atomic_file(launcher, before, 0o700)
        raise


def main(argv=None):
    p = argparse.ArgumentParser(description="Activate complete CI-verified V13 runtime without touching models or memory")
    p.add_argument("--source", default=str(Path.home() / "V13-Phone"))
    p.add_argument("--home", default=str(Path.home() / "v13"))
    a = p.parse_args(argv)
    try:
        print(json.dumps(deploy(a.source, home=a.home), ensure_ascii=False, sort_keys=True), flush=True)
    except (OSError, ValueError, RuntimeDeployError) as exc:
        p.exit(2, "V13 RUNTIME DEPLOY FAILED: " + str(exc) + "\n")


if __name__ == "__main__":
    main()

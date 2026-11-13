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
BUILD_PROFILE = "raw-runtime-plain-ui-history-recovery-v1"
UI_SOURCE = "v13/ui.py"
UI_SOURCE_SHA256 = "ad1c495b1a09989ca307ae7b34f045abe60b390996787ee604e20273c975d4e8"
UI_DERIVED_SHA256 = "0c2e5fb15a78b37017f2b2c296afd0275705e70276a47dc9b47429d38aeac5a1"
UI_BUILDER = "scripts/termux_chat_recovery_candidate_20261112.py"
UI_BUILDER_SHA256 = "e0885ebc04ae16826f2a8d5cc3210ddc2f76d1ef40d22824190deaafaa13ffa8"


class RuntimeDeployError(RuntimeError):
    pass


def _git(root, *args, timeout=50):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        out = subprocess.run(["git", "-C", str(root), *args],
                             capture_output=True, text=True, env=env,
                             timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeDeployError("Git status unavailable") from exc
    if out.returncode != 0:
        raise RuntimeDeployError("Runtime Git verification failed: " + args[0])
    return out.stdout.strip()


def _checkout(source):
    requested = Path(source).expanduser()
    if requested.is_symlink():
        raise RuntimeDeployError("Runtime source path is a symbolic link")
    root = requested.resolve()
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
    return root, commit


def _source(source):
    root, commit = _checkout(source)
    code = root / "v13/code"
    for rel in REQUIRED:
        path = code / rel
        if path.is_symlink() or not path.is_file():
            raise RuntimeDeployError("Required runtime file missing: " + rel)
    return root, code, commit


def prepare_source(source=None):
    """Migrate pre-runtime-updater installs using the fixed phone release.

    This only prepares trusted Git source. CI and graceful-stop checks still
    run before deploy() switches the launcher. Existing directories, local
    changes and a different branch/origin are never replaced.
    """
    root = Path(source or Path.home() / ".v13-runtime-source").expanduser()
    if root.is_symlink():
        raise RuntimeDeployError("Runtime source path is a symbolic link")
    stage = None
    created = not root.exists()
    if created:
        root.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".v13-source-", dir=str(root.parent)))
        checkout = stage
    else:
        checkout = root
    try:
        if created:
            try:
                proc = subprocess.run(
                    ["git", "clone", "--depth", "1", "--filter=blob:none",
                     "--no-checkout", "--single-branch", "--branch", SOURCE_BRANCH,
                     REPO_ORIGIN[1], str(checkout)],
                    capture_output=True, text=True, timeout=180, check=False,
                    env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise RuntimeDeployError("Runtime source download unavailable") from exc
            if proc.returncode:
                raise RuntimeDeployError("Runtime source download failed")
            # Materialize an empty index before checking cleanliness.
            _git(checkout, "sparse-checkout", "init", "--no-cone")
            _git(checkout, "checkout", timeout=180)
        _checkout(checkout)
        # Selecting directories also includes later committed dependencies;
        # exact-file lists stranded older phone installs on incomplete code.
        _git(checkout, "sparse-checkout", "set", "--no-cone",
             "v13/code/v13/", "v13/code/scripts/", "v13/code/specs/",
             "v13/code/docs/canon/", "v13/code/setup.sh", "v13/code/STARTEN.sh",
             timeout=180)
        _, _, commit = _source(checkout)
        if created:
            # rename() refuses a competing populated checkout; only our own
            # temporary download is removed on failure.
            os.rename(checkout, root)
            stage = None
        return {"status": "CREATED" if created else "READY", "commit": commit}
    finally:
        if stage is not None:
            shutil.rmtree(stage)


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
            or not (Path(codepath) / CANON).is_file()
            or target.get("build_profile") != BUILD_PROFILE
            or target.get("source_ui_sha256") != UI_SOURCE_SHA256
            or target.get("derived_ui_sha256") != UI_DERIVED_SHA256
            or target.get("ui_builder_sha256") != UI_BUILDER_SHA256):
        return True
    ui = Path(codepath) / UI_SOURCE
    if (ui.is_symlink() or not ui.is_file()
            or hashlib.sha256(ui.read_bytes()).hexdigest() != UI_DERIVED_SHA256
            or hashlib.sha256((code / UI_SOURCE).read_bytes()).hexdigest() != UI_SOURCE_SHA256):
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


def _apply_plain_ui_recovery(source, target):
    """Derive only the reviewed plain renderer; frozen Git source stays raw."""
    builder = source / UI_BUILDER
    if builder.is_symlink() or not builder.is_file():
        raise RuntimeDeployError("Pinned plain UI recovery builder missing or unsafe")
    raw = builder.read_bytes()
    if hashlib.sha256(raw).hexdigest() != UI_BUILDER_SHA256:
        raise RuntimeDeployError("Pinned plain UI recovery builder changed")
    # Execute exactly the bytes just hash-checked, never a cached module or
    # a second filesystem read. The existing builder validates its frozen
    # UI/operator inputs and returns replacements without modifying them.
    namespace = {"__name__": "v13_phone_plain_ui_recovery"}
    try:
        exec(compile(raw, str(builder), "exec"), namespace)
        ui = namespace["build_sources"](source)[UI_SOURCE]
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as exc:
        raise RuntimeDeployError("Pinned plain UI recovery source validation failed") from exc
    original = source / UI_SOURCE
    copied = target / UI_SOURCE
    if (hashlib.sha256(original.read_bytes()).hexdigest() != UI_SOURCE_SHA256
            or copied.is_symlink() or not copied.is_file()
            or hashlib.sha256(copied.read_bytes()).hexdigest() != UI_SOURCE_SHA256
            or not isinstance(ui, bytes)
            or hashlib.sha256(ui).hexdigest() != UI_DERIVED_SHA256):
        raise RuntimeDeployError("Plain UI recovery source/derived hash mismatch")
    copied.write_bytes(ui)


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
    session = s.new_session()
    for message in ("Hi", "Test", "..."):
        ref = s.source(message)
        assert ref["sha256"] == digest(message)
        assert s.read_source(ref) == message
        event = s.event(session, message)
        assert event["source_ref"]["sha256"] == digest(message)
        assert s.read_source(event["source_ref"]) == message
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
        _apply_plain_ui_recovery(code, target)
        _selftest(target)
        _check_stopped(home)
        next_launcher = _launcher_bytes(target, home)
        _atomic_file(launcher, next_launcher, 0o700)
        record = {"schema": "v13.runtime-deploy/1", "commit": commit,
                  "code": str(target), "backup_launcher": str(backup),
                  "build_profile": BUILD_PROFILE,
                  "source_ui_sha256": UI_SOURCE_SHA256,
                  "derived_ui_sha256": UI_DERIVED_SHA256,
                  "ui_builder_sha256": UI_BUILDER_SHA256,
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
    p.add_argument("--source", default=str(Path.home() / ".v13-runtime-source"))
    p.add_argument("--home", default=str(Path.home() / "v13"))
    a = p.parse_args(argv)
    try:
        print(json.dumps(deploy(a.source, home=a.home), ensure_ascii=False, sort_keys=True), flush=True)
    except (OSError, ValueError, RuntimeDeployError) as exc:
        p.exit(2, "V13 RUNTIME DEPLOY FAILED: " + str(exc) + "\n")


if __name__ == "__main__":
    main()

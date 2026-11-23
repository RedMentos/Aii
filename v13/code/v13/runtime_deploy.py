"""Install a CI-verified V13 runtime snapshot actually used by ~/v13/bin/v13.

A Git fetch alone never updates the existing pinned launcher. This module
stages a complete, immutable code snapshot, verifies canon and normal-text
source roundtrips, and atomically switches ONLY the launcher. Existing GGUF
models, user data, SQLite and control permissions remain untouched.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import fnmatch
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
# Candidate builders consume files outside the deployed tree. Export those
# inputs from the same commit as well, instead of importing mutable checkout
# files while constructing the generated replacements.
BUILD_INPUT_SUBTREES = (*COPY_SUBTREES, "candidates", "tests")
# Match exactly the exclusions of the pinned stage builder and Canon copier.
# Data omitted by both builders stays in place and does not block an update.
STAGE_COPY_IGNORES = ("__pycache__", "*.pyc", "*.db", "*.sqlite", "*.sqlite3",
                      "*.gguf", "*.safetensors", "*.pt", "*.pth", "*.log")
CANON_COPY_IGNORES = ("__pycache__", "*.pyc", "*.pyo")
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
MARKER_NAME = "runtime-active.json"
ACTIVATION_JOURNAL_NAME = ".runtime-activation.json"
# This journal coordinates only the launcher/marker pair; models and user data stay outside the transaction.
BUILD_PROFILE = "integrated-runtime-source-pinned-v2"
STAGER = "scripts/stage_integrated_candidate.py"
STAGER_SHA256 = "82be3d5ca850fda4111ec280d547ff77b6caaa0804b9f05c34058b18b4b30053"
STAGE_MANIFEST = "INTEGRATION_STAGE.json"
UI_SOURCE = "v13/ui.py"
UI_SOURCE_SHA256 = "ad1c495b1a09989ca307ae7b34f045abe60b390996787ee604e20273c975d4e8"
UI_DERIVED_SHA256 = "0c2e5fb15a78b37017f2b2c296afd0275705e70276a47dc9b47429d38aeac5a1"
UI_BUILDER = "scripts/termux_chat_recovery_candidate_20261112.py"
UI_BUILDER_SHA256 = "befbaca164fd5453d4c93017eca1b556f2d771b1b7cf54879c6764e4716587c7"


class RuntimeDeployError(RuntimeError):
    pass


def _git(root, *args, timeout=50):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1"}
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


def _tracked_stage_paths(root, commit):
    """Names owned by the exact Git tree, independent of .gitignore and index."""
    paths = _git(root, "ls-tree", "-r", "-z", "--name-only", commit, "--",
                 *("v13/code/" + part for part in COPY_SUBTREES)).split("\0")
    prefix = "v13/code/"
    return {path[len(prefix):] for path in paths if path.startswith(prefix)}


def _commit_blob_entries(root, commit):
    """Return ordinary tracked source blobs, bound to the requested commit."""
    if not HEX40.fullmatch(commit):
        raise RuntimeDeployError("Invalid runtime source commit")
    entries = {}
    rows = _git(root, "ls-tree", "-r", "-z", commit, "--",
                *("v13/code/" + part for part in BUILD_INPUT_SUBTREES), timeout=180)
    for row in rows.split("\0"):
        if not row:
            continue
        metadata, separator, path = row.partition("\t")
        fields = metadata.split()
        prefix = "v13/code/"
        if (not separator or len(fields) != 3 or fields[0] not in ("100644", "100755")
                or fields[1] != "blob" or not HEX40.fullmatch(fields[2])
                or not path.startswith(prefix)):
            raise RuntimeDeployError("Unsafe Git source entry")
        relative = path[len(prefix):]
        name = Path(relative)
        if (not relative or name.is_absolute() or ".." in name.parts
                or name.as_posix() != relative or relative in entries):
            raise RuntimeDeployError("Unsafe Git source path")
        entries[relative] = (fields[2], fields[0])
    if not entries:
        raise RuntimeDeployError("No tracked runtime sources in commit")
    return entries


def _export_commit_sources(root, commit, destination):
    """Materialize and hash-verify Git blobs without reading the checkout."""
    entries = _commit_blob_entries(root, commit)
    destination = Path(destination)
    # Temporary files keep the batch result off the Python heap on the phone.
    with tempfile.TemporaryFile() as requests, tempfile.TemporaryFile() as replies:
        for oid, _mode in entries.values():
            requests.write((oid + "\n").encode("ascii"))
        requests.seek(0)
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), "cat-file", "--batch"], stdin=requests,
                stdout=replies, stderr=subprocess.PIPE, timeout=180, check=False,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1"})
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeDeployError("Git source export unavailable") from exc
        if proc.returncode:
            raise RuntimeDeployError("Git source export failed")
        replies.seek(0)
        for relative, (oid, mode) in entries.items():
            header = replies.readline(256).split()
            if (len(header) != 3 or header[0] != oid.encode("ascii")
                    or header[1] != b"blob" or not header[2].isdigit()):
                raise RuntimeDeployError("Invalid Git source blob header")
            size = int(header[2])
            digest = hashlib.sha1(b"blob " + str(size).encode("ascii") + b"\0")
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as out:
                remaining = size
                while remaining:
                    part = replies.read(min(remaining, 1024 * 1024))
                    if not part:
                        raise RuntimeDeployError("Truncated Git source blob")
                    out.write(part)
                    digest.update(part)
                    remaining -= len(part)
            if replies.read(1) != b"\n" or digest.hexdigest() != oid:
                raise RuntimeDeployError("Git source blob does not match commit")
            path.chmod(0o700 if mode == "100755" else 0o600)
        if replies.read(1):
            raise RuntimeDeployError("Unexpected Git source export data")
    return entries


def _git_blob_hash(path):
    """Compute the Git SHA-1 blob identity of an ordinary staged file."""
    size = path.stat().st_size
    digest = hashlib.sha1(b"blob " + str(size).encode("ascii") + b"\0")
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def _check_copy_inputs(root, code, commit):
    """Do not copy local files into a snapshot labelled as a verified commit."""
    tracked = _tracked_stage_paths(root, commit)

    def onerror(exc):
        raise RuntimeDeployError("Cannot inspect runtime source") from exc

    for subtree in COPY_SUBTREES:
        start = code / subtree
        if start.is_symlink() or not start.is_dir():
            raise RuntimeDeployError("Runtime source subtree missing or unsafe: " + subtree)
        ignored = CANON_COPY_IGNORES if subtree == "docs/canon" else STAGE_COPY_IGNORES
        def excluded(name):
            return any(fnmatch.fnmatchcase(name, pattern) for pattern in ignored)
        for directory, dirs, files in os.walk(start, topdown=True, onerror=onerror,
                                              followlinks=False):
            dirs[:] = [name for name in dirs if not excluded(name)]
            for name in dirs:
                if (Path(directory) / name).is_symlink():
                    raise RuntimeDeployError("Symlink inside runtime source tree")
            for name in files:
                if excluded(name):
                    continue
                path = Path(directory) / name
                if path.is_symlink() or not path.is_file():
                    raise RuntimeDeployError("Unsafe runtime source entry")
                if path.relative_to(code).as_posix() not in tracked:
                    raise RuntimeDeployError(
                        "Untracked or ignored file in runtime source; update deferred")


def _source(source):
    root, commit = _checkout(source)
    code = root / "v13/code"
    for rel in REQUIRED:
        path = code / rel
        if path.is_symlink() or not path.is_file():
            raise RuntimeDeployError("Required runtime file missing: " + rel)
    _check_copy_inputs(root, code, commit)
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
             "v13/code/candidates/", "v13/code/tests/",
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
    journal = private / ACTIVATION_JOURNAL_NAME
    if journal.exists() or journal.is_symlink():
        # A partially written pair must force the worker through deploy(),
        # whose first operation is the journal recovery transaction.
        return True
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
            or target.get("ui_builder_sha256") != UI_BUILDER_SHA256
            or not isinstance(target.get("stage_manifest_sha256"), str)):
        return True
    try:
        installed = Path(codepath)
        if _verify_stage(installed) != target["stage_manifest_sha256"]:
            return True
        # The integrated stage deliberately applies further reviewed UI
        # transformations AFTER the standalone plain-chat recovery. The
        # deployed renderer therefore has a different hash from the
        # intermediate UI_DERIVED_SHA256. Its exact final bytes are bound by
        # the verified immutable stage manifest, not by the intermediate hash.
        manifest = json.loads((installed / STAGE_MANIFEST).read_text(encoding="utf-8"))
        final_ui = manifest["files_sha256"].get(UI_SOURCE)
        generated = manifest.get("replaced_files", [])
        if (type(generated) is not list or type(final_ui) is not str
                or not re.fullmatch(r"[a-f0-9]{64}", final_ui)):
            return True
        # Legacy plain-chat staging legitimately copies the independently
        # pinned intermediate UI without a generated-file entry. The composed
        # Runtime adds a generated UI and is checked against its manifest.
        if UI_SOURCE not in generated and final_ui != UI_DERIVED_SHA256:
            return True
    except (OSError, ValueError, KeyError, TypeError, RuntimeDeployError):
        return True
    ui = installed / UI_SOURCE
    if (ui.is_symlink() or not ui.is_file()
            or hashlib.sha256(ui.read_bytes()).hexdigest() != final_ui
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
        # Never dereference a symlink into an immutable release snapshot.
        # copytree(symlinks=False) otherwise copies arbitrary host/private bytes.
        for directory, dirs, files in os.walk(src, followlinks=False):
            for name in dirs + files:
                entry = Path(directory) / name
                if entry.is_symlink():
                    raise RuntimeDeployError("Symlink inside runtime source tree")
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



def _verify_stage(root):
    """Verify the complete installed snapshot against its owner-only receipt."""
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeDeployError("Integrated runtime snapshot is missing or unsafe")
    manifest_path = root / STAGE_MANIFEST
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeDeployError("Integrated runtime manifest is missing")
    raw = manifest_path.read_bytes()
    if len(raw) > 8 * 1024 * 1024:
        raise RuntimeDeployError("Integrated runtime manifest is too large")
    data = json.loads(raw)
    hashes = data.get("files_sha256") if isinstance(data, dict) else None
    if not isinstance(data, dict) or data.get("status") != "SHADOW_REVIEW_ONLY" or not isinstance(hashes, dict) or not hashes:
        raise RuntimeDeployError("Integrated runtime manifest is invalid")
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise RuntimeDeployError("Integrated runtime contains a symbolic link")
        if path.is_file() and path != manifest_path:
            actual.add(path.relative_to(root).as_posix())
    if actual != set(hashes):
        raise RuntimeDeployError("Integrated runtime file set changed")
    for relative, expected in hashes.items():
        name = Path(relative)
        if (not isinstance(relative, str) or name.is_absolute() or ".." in name.parts
                or name.as_posix() != relative or not isinstance(expected, str)
                or not re.fullmatch(r"[a-f0-9]{64}", expected)):
            raise RuntimeDeployError("Integrated runtime manifest entry is invalid")
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeDeployError("Integrated runtime source hash mismatch: " + relative)
    if any(name not in hashes for name in REQUIRED):
        raise RuntimeDeployError("Integrated runtime dependencies are missing")
    return hashlib.sha256(raw).hexdigest()


def _stage_integrated_runtime(source, target, *, expected_commit=None):
    """Materialize the exact reviewed stage; never modify source or user data."""
    source, target = Path(source), Path(target)
    source_resolved = source.resolve(strict=True)
    target_resolved = target.resolve()
    if source_resolved == target_resolved or source_resolved in target_resolved.parents:
        raise RuntimeDeployError("Integrated staging overlaps source tree")
    repo = source.parent.parent
    staged_commit = expected_commit or _git(repo, "rev-parse", "HEAD")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        # The input is a private materialization of exact Git objects, never a
        # working tree whose tracked contents can change and be restored during
        # copy. This also binds generated files to the same builder inputs.
        with tempfile.TemporaryDirectory(prefix=".v13-verified-source-", dir=target.parent) as tmp:
            frozen = Path(tmp) / "code"
            frozen.mkdir(mode=0o700)
            blobs = _export_commit_sources(repo, staged_commit, frozen)
            builder = frozen / STAGER
            if builder.is_symlink() or not builder.is_file():
                raise RuntimeDeployError("Integrated stage builder missing or unsafe")
            raw = builder.read_bytes()
            if hashlib.sha256(raw).hexdigest() != STAGER_SHA256:
                raise RuntimeDeployError("Integrated stage builder changed")
            namespace = {"__name__": "v13_checked_runtime_stager", "__file__": str(builder)}
            exec(compile(raw, str(builder), "exec"), namespace)
            manifest = namespace["stage"](frozen, target)
            # Canon is not part of the stage builder's normal copy.
            canon_source = frozen / "docs/canon"
            if canon_source.is_symlink() or not canon_source.is_dir():
                raise RuntimeDeployError("Integrated runtime Canon missing or unsafe")
            canon_target = target / "docs/canon"
            canon_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(canon_source, canon_target, symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
            for entry in canon_target.rglob("*"):
                if entry.is_symlink():
                    raise RuntimeDeployError("Integrated runtime Canon contains a symlink")
                if entry.is_file():
                    manifest["files_sha256"][entry.relative_to(target).as_posix()] = hashlib.sha256(entry.read_bytes()).hexdigest()
            generated = manifest.get("replaced_files")
            hashes = manifest.get("files_sha256")
            if (not isinstance(generated, list)
                    or any(not isinstance(name, str) for name in generated)
                    or len(generated) != len(set(generated))
                    or not isinstance(hashes, dict) or set(generated) - set(hashes)):
                raise RuntimeDeployError("Integrated runtime provenance is invalid")
            if set(hashes) - set(blobs) - set(generated):
                raise RuntimeDeployError("Integrated runtime contains untracked source")
            manifest["source"] = str(source)
            manifest["source_commit"] = staged_commit
            (target / STAGE_MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            manifest_sha = _verify_stage(target)
            # The generated set comes only from the already hash-pinned stager,
            # run against the verified export. Everything else must equal its
            # Git blob, rather than merely matching a self-generated manifest.
            for relative in set(hashes) - set(generated):
                if _git_blob_hash(target / relative) != blobs[relative][0]:
                    raise RuntimeDeployError("Integrated runtime differs from Git commit: " + relative)
            return manifest_sha
    except RuntimeDeployError:
        raise
    except Exception as exc:
        raise RuntimeDeployError("Integrated runtime staging failed: " + type(exc).__name__) from exc

def _selftest(code):
    env = {**os.environ,
           "PYTHONPATH": str(code),
           "NO_MODEL_DOWNLOADS": "1", "DO_NOT_TRACK": "1",
           "NEEDLE_TELEMETRY": "0", "PYTHONDONTWRITEBYTECODE": "1"}
    script = """
from pathlib import Path
from tempfile import TemporaryDirectory
from v13.config import initialize
from v13.store import Store
from v13.common import digest
import sys
import traceback
try:
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
except OSError as exc:
    # Only allowlisted source BASENAMES, Python function names, line and errno.
    # Never leak the private probe path, filesystem names, text or traceback.
    allowed = {"source_lifecycle_candidate.py", "store.py",
               "source_reuse_archive_candidate.py", "config.py",
               "archive_stream_range_candidate.py"}
    for entry in reversed(traceback.extract_tb(exc.__traceback__)):
        name = Path(entry.filename).name
        if name in allowed and entry.name.isidentifier():
            print("V13_PROBE_LOCATION=" + name[:-3] + "." + entry.name
                  + ":" + str(entry.lineno) + ":" + str(int(exc.errno or 0)),
                  file=sys.stderr)
            break
    raise
"""
    # Probe output is never forwarded to a public repo, a telemetry endpoint
    # or an AI agent. Only a fixed phase, exit status and recognized exception
    # class may appear in the local installer error. No traceback/user paths.
    for phase, args in (("module_help", [sys.executable, "-m", "v13", "--help"]),
                        ("sqlite_source_roundtrip", [sys.executable, "-c", script])):
        try:
            run = subprocess.run(args, cwd=str(code), env=env,
                                 capture_output=True, timeout=45, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeDeployError(
                "Staged runtime selftest timed out (phase=" + phase + ")") from exc
        except OSError as exc:
            raise RuntimeDeployError(
                "Staged runtime selftest spawn failed (phase=" + phase +
                ", error=" + type(exc).__name__ + ")") from exc
        if run.returncode:
            tail = run.stderr.decode("utf-8", errors="replace")
            kind = "UNKNOWN_ERROR"
            for line in reversed(tail.splitlines()):
                found = re.match(
                    r"^\s*([a-zA-Z_][a-zA-Z_0-9.]*(?:Error|Exception))(?::|$)",
                    line)
                if found:
                    kind = found.group(1)[:80]
                    if kind == "ModuleNotFoundError":
                        missing = re.search(
                            r"""No module named ['"]([a-zA-Z_][a-zA-Z_0-9.]*)['"]""",
                            line)
                        if missing:
                            kind += "(" + missing.group(1)[:70] + ")"
                    break
            # Trusted selftest emits only a whitelisted source module name,
            # function identifier, line number and errno. Never show stderr.
            detail = ""
            if phase == "sqlite_source_roundtrip":
                location = re.search(
                    r"^V13_PROBE_LOCATION=(source_lifecycle_candidate|store|"
                    r"source_reuse_archive_candidate|config|archive_stream_range_candidate)"
                    r"\.([a-zA-Z_][a-zA-Z_0-9]*):([0-9]{1,6}):([0-9]{1,4})$",
                    tail, re.MULTILINE)
                if location:
                    detail = ", site=" + location.group(1) + "." + location.group(2) + \
                             ":" + location.group(3) + ", errno=" + location.group(4)
            raise RuntimeDeployError(
                "Staged V13 source-ref/startup selftest failed " +
                "(phase=" + phase + ", exit=" + str(run.returncode) +
                ", error=" + kind + detail + ", python=" +
                str(sys.version_info.major) + "." + str(sys.version_info.minor) + ")")


def _launcher_bytes(code, home):
    python = str(Path(sys.executable).resolve())
    # -P prevents a package in the caller's cwd from shadowing the verified
    # snapshot. Before Python 3.11, initialise site only after replacing that
    # cwd entry, preserving the caller's directory and normal site packages.
    if sys.version_info >= (3, 11):
        command = shlex.quote(python) + " -P -m v13 --home "
    else:
        # Keep the launcher path in the OS command line for the update/stop
        # checks, then remove it from the arguments presented to V13.
        bootstrap = ("import sys; sys.argv.pop(1); sys.path[0] = sys.argv.pop(1); "
                     "import site; site.main(); import runpy; "
                     "runpy.run_module('v13', run_name='__main__', alter_sys=True)")
        command = (shlex.quote(python) + " -S -B -c " + shlex.quote(bootstrap)
                   + " " + shlex.quote(str(home / "bin/v13"))
                   + " " + shlex.quote(str(code)) + " --home ")
    return ("#!/data/data/com.termux/files/usr/bin/bash\n"
            "set -e\n"
            "export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1 PYTHONDONTWRITEBYTECODE=1\n"
            "export PYTHONPATH=" + shlex.quote(str(code)) + "\n"
            "exec " + command + shlex.quote(str(home)) + ' "$@"\n').encode("utf-8")



def _fsync_directory(path):
    fd = os.open(str(path), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_file(dest, data, mode=0o600):
    dest = Path(dest)
    if dest.parent.is_symlink() or not dest.parent.is_dir():
        raise RuntimeDeployError("Atomic destination parent is missing or unsafe")
    fd, name = tempfile.mkstemp(prefix=".v13-deploy-", dir=str(dest.parent))
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, dest)
        _fsync_directory(dest.parent)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _remove_private_file(path, private):
    path, private = Path(path), Path(private)
    if path.is_symlink():
        raise RuntimeDeployError("Private transaction file is a symbolic link")
    if not path.exists():
        return
    if path.parent.resolve(strict=True) != private.resolve(strict=True):
        raise RuntimeDeployError("Private transaction file escapes its directory")
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or info.st_nlink != 1
            or info.st_size > 65536):
        raise RuntimeDeployError("Private transaction file permissions or size invalid")
    path.unlink()
    _fsync_directory(path.parent)


def _read_current_marker(path):
    path = Path(path)
    if path.is_symlink():
        raise RuntimeDeployError("Existing runtime marker is unsafe")
    if not path.exists():
        return None
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or info.st_nlink != 1
            or info.st_size > 4096):
        raise RuntimeDeployError("Existing runtime marker is unsafe")
    return path.read_bytes()


def _private_backup_bytes(value, private, pattern, max_bytes):
    if not isinstance(value, str) or not value:
        raise RuntimeDeployError("Runtime transaction backup path missing")
    private = Path(private)
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = private / candidate
    if candidate.is_symlink() or not re.fullmatch(pattern, candidate.name):
        raise RuntimeDeployError("Runtime transaction backup path invalid")
    if candidate.parent.resolve(strict=True) != private.resolve(strict=True):
        raise RuntimeDeployError("Runtime transaction backup escapes private directory")
    info = candidate.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or info.st_nlink != 1
            or info.st_size > max_bytes):
        raise RuntimeDeployError("Runtime transaction backup permissions or size invalid")
    return candidate.read_bytes()


def _read_activation_journal(private):
    private = Path(private)
    path = private / ACTIVATION_JOURNAL_NAME
    if path.is_symlink():
        raise RuntimeDeployError("Runtime activation journal is a symbolic link")
    if not path.exists():
        return None
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or info.st_nlink != 1
            or info.st_size > 8192):
        raise RuntimeDeployError("Runtime activation journal permissions or size invalid")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise RuntimeDeployError("Runtime activation journal is invalid") from exc
    fields = {
        "schema", "transaction_id", "phase", "backup_launcher",
        "backup_launcher_sha256", "old_marker_present", "backup_marker",
        "backup_marker_sha256", "new_launcher_sha256",
        "new_marker_present", "new_marker_sha256",
    }
    if (not isinstance(record, dict) or set(record) != fields
            or record.get("schema") != "v13.runtime-activation/1"
            or not isinstance(record.get("transaction_id"), str)
            or not re.fullmatch(r"[a-f0-9]{32}", record["transaction_id"])
            or record.get("phase") not in ("PREPARED", "LAUNCHER_SWITCHED", "COMMITTED")
            or type(record.get("old_marker_present")) is not bool
            or type(record.get("new_marker_present")) is not bool):
        raise RuntimeDeployError("Runtime activation journal schema invalid")
    for key in ("backup_launcher_sha256", "new_launcher_sha256"):
        if not isinstance(record.get(key), str) or not re.fullmatch(r"[a-f0-9]{64}", record[key]):
            raise RuntimeDeployError("Runtime activation journal hash invalid")
    if record["old_marker_present"]:
        if (not isinstance(record.get("backup_marker"), str)
                or not isinstance(record.get("backup_marker_sha256"), str)
                or not re.fullmatch(r"[a-f0-9]{64}", record["backup_marker_sha256"])):
            raise RuntimeDeployError("Runtime activation journal old marker invalid")
    elif record.get("backup_marker") is not None or record.get("backup_marker_sha256") is not None:
        raise RuntimeDeployError("Runtime activation journal old marker is inconsistent")
    if record["new_marker_present"]:
        if not isinstance(record.get("new_marker_sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", record["new_marker_sha256"]):
            raise RuntimeDeployError("Runtime activation journal new marker invalid")
    elif record.get("new_marker_sha256") is not None:
        raise RuntimeDeployError("Runtime activation journal new marker is inconsistent")
    return record


def _recover_activation(home, private):
    """Idempotently finish a committed pair or restore the previous pair."""
    private = Path(private)
    record = _read_activation_journal(private)
    if record is None:
        return "NONE"
    launcher = _launcher(Path(home))
    marker_path = private / MARKER_NAME
    old_launcher = _private_backup_bytes(
        record["backup_launcher"], private, r"launcher-backup-[a-f0-9]{16}\.sh", 65536)
    if hashlib.sha256(old_launcher).hexdigest() != record["backup_launcher_sha256"]:
        raise RuntimeDeployError("Runtime activation launcher backup hash mismatch")
    old_marker = None
    if record["old_marker_present"]:
        old_marker = _private_backup_bytes(
            record["backup_marker"], private, r"marker-backup-[a-f0-9]{16}\.json", 4096)
        if hashlib.sha256(old_marker).hexdigest() != record["backup_marker_sha256"]:
            raise RuntimeDeployError("Runtime activation marker backup hash mismatch")
    current_launcher = launcher.read_bytes()
    current_launcher_sha = hashlib.sha256(current_launcher).hexdigest()
    if current_launcher_sha not in (record["backup_launcher_sha256"], record["new_launcher_sha256"]):
        raise RuntimeDeployError("Runtime activation found an unknown launcher; refusing recovery")
    current_marker = _read_current_marker(marker_path)
    current_marker_sha = hashlib.sha256(current_marker).hexdigest() if current_marker is not None else None
    allowed_marker_hashes = set()
    if record["old_marker_present"]:
        allowed_marker_hashes.add(record["backup_marker_sha256"])
    if record["new_marker_present"]:
        allowed_marker_hashes.add(record["new_marker_sha256"])
    if current_marker is None:
        if record["old_marker_present"] and record["new_marker_present"]:
            raise RuntimeDeployError("Runtime activation marker disappeared unexpectedly")
    elif current_marker_sha not in allowed_marker_hashes:
        raise RuntimeDeployError("Runtime activation found an unknown marker; refusing recovery")
    new_pair_is_durable = (
        current_launcher_sha == record["new_launcher_sha256"]
        and ((record["new_marker_present"] and current_marker_sha == record["new_marker_sha256"])
             or (not record["new_marker_present"] and current_marker is None))
    )
    journal_path = private / ACTIVATION_JOURNAL_NAME
    if record["phase"] == "COMMITTED" and new_pair_is_durable:
        _remove_private_file(journal_path, private)
        return "COMMITTED"
    if current_launcher_sha != record["backup_launcher_sha256"]:
        _atomic_file(launcher, old_launcher, 0o700)
    if record["old_marker_present"]:
        if current_marker != old_marker:
            _atomic_file(marker_path, old_marker, 0o600)
    elif current_marker is not None:
        _remove_private_file(marker_path, private)
    _remove_private_file(journal_path, private)
    return "ROLLED_BACK_INCOMPLETE"


def recover_pending_activation(*, home=None, private=None):
    """Recover only an existing activation journal; never stage or install code."""
    home = Path(home or Path.home() / "v13").expanduser().resolve()
    private = _protected_dir(private or Path.home() / ".v13-private")
    journal = private / ACTIVATION_JOURNAL_NAME
    if not journal.exists() and not journal.is_symlink():
        return "NONE"
    _check_stopped(home)
    return _recover_activation(home, private)


def _activation_transaction(home, private, *, old_launcher, old_marker,
                            new_launcher, new_marker, backup_launcher,
                            backup_marker=None):
    """Durably switch launcher + marker as one recoverable transaction."""
    home, private = Path(home), _protected_dir(private)
    launcher = _launcher(home)
    marker_path = private / MARKER_NAME
    if launcher.read_bytes() != old_launcher or _read_current_marker(marker_path) != old_marker:
        raise RuntimeDeployError("Installed runtime changed before activation transaction")
    if (not isinstance(old_launcher, bytes) or not isinstance(new_launcher, bytes)
            or (old_marker is not None and not isinstance(old_marker, bytes))
            or (new_marker is not None and not isinstance(new_marker, bytes))):
        raise RuntimeDeployError("Runtime activation transaction payload invalid")
    backup_launcher_path = Path(backup_launcher)
    backup_launcher_bytes = _private_backup_bytes(
        str(backup_launcher_path), private, r"launcher-backup-[a-f0-9]{16}\.sh", 65536)
    if backup_launcher_bytes != old_launcher:
        raise RuntimeDeployError("Runtime activation launcher backup does not match")
    backup_marker_name = None
    backup_marker_sha = None
    if old_marker is not None:
        if backup_marker is None:
            raise RuntimeDeployError("Runtime activation marker backup missing")
        backup_marker_path = Path(backup_marker)
        backup_marker_bytes = _private_backup_bytes(
            str(backup_marker_path), private, r"marker-backup-[a-f0-9]{16}\.json", 4096)
        if backup_marker_bytes != old_marker:
            raise RuntimeDeployError("Runtime activation marker backup does not match")
        backup_marker_name = backup_marker_path.name
        backup_marker_sha = hashlib.sha256(old_marker).hexdigest()
    elif backup_marker is not None:
        raise RuntimeDeployError("Unexpected runtime activation marker backup")
    journal_path = private / ACTIVATION_JOURNAL_NAME
    if journal_path.exists() or journal_path.is_symlink():
        raise RuntimeDeployError("Unrecovered runtime activation journal already exists")
    record = {
        "schema": "v13.runtime-activation/1",
        "transaction_id": secrets.token_hex(16),
        "phase": "PREPARED",
        "backup_launcher": backup_launcher_path.name,
        "backup_launcher_sha256": hashlib.sha256(old_launcher).hexdigest(),
        "old_marker_present": old_marker is not None,
        "backup_marker": backup_marker_name,
        "backup_marker_sha256": backup_marker_sha,
        "new_launcher_sha256": hashlib.sha256(new_launcher).hexdigest(),
        "new_marker_present": new_marker is not None,
        "new_marker_sha256": hashlib.sha256(new_marker).hexdigest() if new_marker is not None else None,
    }

    def write_journal():
        _atomic_file(journal_path, json.dumps(record, sort_keys=True).encode("utf-8"), 0o600)

    try:
        write_journal()
        _atomic_file(launcher, new_launcher, 0o700)
        record["phase"] = "LAUNCHER_SWITCHED"
        write_journal()
        if new_marker is None:
            _remove_private_file(marker_path, private)
        else:
            _atomic_file(marker_path, new_marker, 0o600)
        record["phase"] = "COMMITTED"
        write_journal()
        _remove_private_file(journal_path, private)
        return "COMMITTED"
    except BaseException:
        recovered = _recover_activation(home, private)
        if recovered == "COMMITTED":
            return recovered
        raise



def deploy(source, *, home=None, private=None, builds=None, ci_verified=False,
           expected_commit=None, activation_guard=None):
    root, code, commit = _source(source)
    if expected_commit is not None and expected_commit != commit:
        raise RuntimeDeployError("Runtime source changed after CI verification")
    home = Path(home or Path.home() / "v13").expanduser().resolve()
    private = _protected_dir(private or Path.home() / ".v13-private")
    builds = _protected_dir(builds or Path.home() / ".v13-runtime-builds")
    _check_stopped(home)
    recover_pending_activation(home=home, private=private)
    launcher = _launcher(home)
    if not ci_verified:
        from .source_updater import ci_passed
        if not ci_passed(commit, scope="runtime"):
            raise RuntimeDeployError("Exact V13 runtime source commit is not CI-green")
    if not needs_deploy(root, home=home, private=private):
        return {"status": "UP_TO_DATE", "commit": commit,
                "launcher_verified": True}
    before = launcher.read_bytes()
    marker_path = private / MARKER_NAME
    marker_before = _read_current_marker(marker_path)
    if marker_before is not None:
        try:
            previous = json.loads(marker_before)
        except (ValueError, UnicodeError) as exc:
            raise RuntimeDeployError("Existing runtime marker is invalid") from exc
        if (not isinstance(previous, dict)
                or previous.get("schema") != "v13.runtime-deploy/1"
                or previous.get("launcher_sha256") != hashlib.sha256(before).hexdigest()):
            raise RuntimeDeployError("Existing runtime marker does not match launcher")
    stage = builds / ("v13-" + commit[:12] + "-" + secrets.token_hex(4))
    if stage.exists() or stage.is_symlink():
        raise RuntimeDeployError("Runtime staging collision")
    stage.mkdir(mode=0o700)
    target = stage / "code"
    manifest_sha256 = _stage_integrated_runtime(code, target, expected_commit=commit)
    if _source(root)[2] != commit:
        raise RuntimeDeployError("Runtime source changed during staging")
    _selftest(target)
    if _verify_stage(target) != manifest_sha256:
        raise RuntimeDeployError("Integrated runtime changed during selftest")
    with (activation_guard() if activation_guard is not None else nullcontext()):
        _check_stopped(home)
        if launcher.read_bytes() != before or _read_current_marker(marker_path) != marker_before:
            raise RuntimeDeployError("Installed runtime changed during staging")
        next_launcher = _launcher_bytes(target, home)
        backup = private / ("launcher-backup-" + secrets.token_hex(8) + ".sh")
        _atomic_file(backup, before, 0o600)
        backup_marker = None
        if marker_before is not None:
            backup_marker = private / ("marker-backup-" + secrets.token_hex(8) + ".json")
            _atomic_file(backup_marker, marker_before, 0o600)
        record = {"schema": "v13.runtime-deploy/1", "commit": commit,
                  "code": str(target), "backup_launcher": str(backup),
                  "backup_launcher_sha256": hashlib.sha256(before).hexdigest(),
                  "backup_marker": str(backup_marker) if backup_marker else None,
                  "backup_marker_sha256": hashlib.sha256(marker_before).hexdigest() if marker_before is not None else None,
                  "build_profile": BUILD_PROFILE,
                  "source_ui_sha256": UI_SOURCE_SHA256,
                  "derived_ui_sha256": UI_DERIVED_SHA256,
                  "ui_builder_sha256": UI_BUILDER_SHA256,
                  "stage_manifest_sha256": manifest_sha256,
                  "launcher_sha256": hashlib.sha256(next_launcher).hexdigest(),
                  "installed_at": int(time.time()),
                  "models_untouched": True, "sqlite_untouched": True}
        marker_after = json.dumps(record, sort_keys=True).encode("utf-8")
        _activation_transaction(
            home, private, old_launcher=before, old_marker=marker_before,
            new_launcher=next_launcher, new_marker=marker_after,
            backup_launcher=backup, backup_marker=backup_marker)
        return {"status": "DEPLOYED", "commit": commit, "code": str(target),
                "launcher_verified": True}


def _verified_stage_from_marker(record, builds):
    commit = record.get("commit")
    code_value = record.get("code")
    manifest_sha = record.get("stage_manifest_sha256")
    if (not isinstance(commit, str) or not HEX40.fullmatch(commit)
            or not isinstance(code_value, str)
            or not isinstance(manifest_sha, str)
            or not re.fullmatch(r"[a-f0-9]{64}", manifest_sha)):
        raise RuntimeDeployError("Rollback marker fields invalid")
    code = Path(code_value)
    if code.is_symlink() or not code.is_dir():
        raise RuntimeDeployError("Rollback code snapshot missing or unsafe")
    resolved = code.resolve(strict=True)
    if builds.resolve(strict=True) not in resolved.parents:
        raise RuntimeDeployError("Rollback code snapshot escapes runtime builds")
    if _verify_stage(code) != manifest_sha:
        raise RuntimeDeployError("Rollback code snapshot integrity mismatch")
    return commit


def rollback(*, home=None, private=None, builds=None, activation_guard=None):
    """Restore the exact previous launcher/marker using the same crash journal."""
    home = Path(home or Path.home() / "v13").expanduser().resolve()
    private = _protected_dir(private or Path.home() / ".v13-private")
    builds = _protected_dir(builds or Path.home() / ".v13-runtime-builds")
    _check_stopped(home)
    recover_pending_activation(home=home, private=private)
    launcher = _launcher(home)
    marker_path = private / MARKER_NAME
    current_marker_bytes = _read_current_marker(marker_path)
    if current_marker_bytes is None:
        raise RuntimeDeployError("Current runtime marker missing or unsafe")
    try:
        current = json.loads(current_marker_bytes)
    except (ValueError, UnicodeError) as exc:
        raise RuntimeDeployError("Current runtime marker invalid") from exc
    current_launcher_bytes = launcher.read_bytes()
    if (not isinstance(current, dict) or current.get("schema") != "v13.runtime-deploy/1"
            or current.get("launcher_sha256") != hashlib.sha256(current_launcher_bytes).hexdigest()):
        raise RuntimeDeployError("Current launcher does not match runtime marker")
    _verified_stage_from_marker(current, builds)
    backup_launcher_bytes = _private_backup_bytes(
        current.get("backup_launcher"), private, r"launcher-backup-[a-f0-9]{16}\.sh", 65536)
    expected_launcher_sha = current.get("backup_launcher_sha256")
    if (not isinstance(expected_launcher_sha, str)
            or not re.fullmatch(r"[a-f0-9]{64}", expected_launcher_sha)
            or hashlib.sha256(backup_launcher_bytes).hexdigest() != expected_launcher_sha):
        raise RuntimeDeployError("Previous launcher backup integrity mismatch")
    backup_marker_value = current.get("backup_marker")
    backup_marker_sha = current.get("backup_marker_sha256")
    previous_marker_bytes = None
    restored_commit = None
    legacy = backup_marker_value is None
    if backup_marker_value is not None:
        previous_marker_bytes = _private_backup_bytes(
            backup_marker_value, private, r"marker-backup-[a-f0-9]{16}\.json", 4096)
        if (not isinstance(backup_marker_sha, str)
                or not re.fullmatch(r"[a-f0-9]{64}", backup_marker_sha)
                or hashlib.sha256(previous_marker_bytes).hexdigest() != backup_marker_sha):
            raise RuntimeDeployError("Previous runtime marker backup integrity mismatch")
        try:
            previous = json.loads(previous_marker_bytes)
        except (ValueError, UnicodeError) as exc:
            raise RuntimeDeployError("Previous runtime marker backup invalid") from exc
        if (not isinstance(previous, dict)
                or previous.get("schema") != "v13.runtime-deploy/1"
                or previous.get("launcher_sha256") != hashlib.sha256(backup_launcher_bytes).hexdigest()):
            raise RuntimeDeployError("Previous marker does not match launcher backup")
        restored_commit = _verified_stage_from_marker(previous, builds)
        legacy = False
    elif backup_marker_sha is not None:
        raise RuntimeDeployError("Previous runtime marker receipt is inconsistent")
    transaction_backup = private / ("launcher-backup-" + secrets.token_hex(8) + ".sh")
    transaction_marker_backup = private / ("marker-backup-" + secrets.token_hex(8) + ".json")
    with (activation_guard() if activation_guard is not None else nullcontext()):
        _check_stopped(home)
        if (launcher.read_bytes() != current_launcher_bytes
                or _read_current_marker(marker_path) != current_marker_bytes):
            raise RuntimeDeployError("Installed runtime changed during rollback")
        _atomic_file(transaction_backup, current_launcher_bytes, 0o600)
        _atomic_file(transaction_marker_backup, current_marker_bytes, 0o600)
        _activation_transaction(
            home, private, old_launcher=current_launcher_bytes,
            old_marker=current_marker_bytes, new_launcher=backup_launcher_bytes,
            new_marker=previous_marker_bytes, backup_launcher=transaction_backup,
            backup_marker=transaction_marker_backup)
    return {"status": "ROLLED_BACK_LEGACY" if legacy else "ROLLED_BACK",
            "restored_commit": restored_commit,
            "models_untouched": True, "sqlite_untouched": True}


def main(argv=None):
    p = argparse.ArgumentParser(description="Activate or roll back the installed V13 runtime without touching models or memory")
    p.add_argument("--source", default=str(Path.home() / ".v13-runtime-source"))
    p.add_argument("--home", default=str(Path.home() / "v13"))
    p.add_argument("--rollback", action="store_true", help="restore the previous verified launcher and marker")
    a = p.parse_args(argv)
    try:
        result = rollback(home=a.home) if a.rollback else deploy(a.source, home=a.home)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    except (OSError, ValueError, RuntimeDeployError) as exc:
        p.exit(2, "V13 RUNTIME DEPLOY FAILED: " + str(exc) + "\n")


if __name__ == "__main__":
    main()

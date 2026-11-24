"""Explicit reversible launcher activation of a reviewed staged candidate.

No inference, installation, learning permission or canonical promotion. Rollback
restores only the launcher; configuration/database snapshots are manual backups.
"""
import argparse
import ast
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import sqlite3
import stat
import sys
import tempfile
import time


SHA = re.compile(r"[0-9a-f]{64}\Z")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def real_path(value, *, directory=False, within=None):
    path = Path(os.path.abspath(Path(value).expanduser()))
    # Android may expose /data/data through a platform-owned ancestor alias.
    # Resolve declared roots, but never accept a root leaf or an internal path
    # supplied by this installation as a symbolic link.
    entries = [path]
    if within is not None:
        root = Path(within)
        try:
            relative = path.relative_to(root)
        except ValueError as exc:
            raise ValueError("path escapes owned root") from exc
        entries = [root.joinpath(*relative.parts[:index])
                   for index in range(1, len(relative.parts) + 1)]
    for entry in entries:
        if entry.is_symlink():
            raise ValueError("symbolic links are refused: " + str(entry))
    path = path.resolve(strict=True)
    info = path.stat()
    if directory and not stat.S_ISDIR(info.st_mode):
        raise ValueError("expected a real directory")
    if not directory and not stat.S_ISREG(info.st_mode):
        raise ValueError("expected a regular file")
    return path


def validate_stage(code_dir):
    root = real_path(code_dir, directory=True)
    manifest_path = real_path(root / "INTEGRATION_STAGE.json", within=root)
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    hashes = manifest.get("files_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("stage manifest has no file SHA map")
    actual = set()
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("stage contains a symbolic link")
        if path.is_dir():
            continue
        real_path(path, within=root)
        relative = path.relative_to(root).as_posix()
        if relative != "INTEGRATION_STAGE.json":
            actual.add(relative)
    if actual != set(hashes):
        raise ValueError("stage manifest file set differs from staged files")
    for relative, expected in hashes.items():
        name = Path(relative)
        if (not isinstance(expected, str) or not SHA.fullmatch(expected) or name.is_absolute()
                or ".." in name.parts or name.as_posix() != relative):
            raise ValueError("unsafe stage manifest entry")
        data = real_path(root / name, within=root).read_bytes()
        if digest(data) != expected:
            raise ValueError("stage SHA mismatch: " + relative)
        if name.suffix == ".py":
            ast.parse(data, filename=relative)
    if "v13/__main__.py" not in hashes or "v13/__init__.py" not in hashes:
        raise ValueError("staged V13 package entrypoint is missing")
    return root, digest(raw)


def validate_home(home):
    root = real_path(home, directory=True)
    launcher = real_path(root / "bin/v13", within=root)
    settings = real_path(root / "config/settings.json", within=root)
    database = real_path(root / "data/db/brain.sqlite3", within=root)
    if any(path.stat().st_uid != os.getuid() for path in (root, launcher, settings, database)):
        raise ValueError("runtime and its files must belong to the current user")
    json.loads(settings.read_bytes())
    return root, launcher, settings, database


def require_stopped():
    proc = Path("/proc")
    if not proc.is_dir():
        raise ValueError("process visibility unavailable; stop V13 before activation")
    seen = False
    for entry in proc.iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            args = [item.decode("utf-8", "replace")
                    for item in (entry / "cmdline").read_bytes().split(b"\0") if item]
        except OSError:
            continue
        seen = seen or bool(args)
        if any(arg == "v13" or arg.endswith("/bin/v13") for arg in args):
            raise ValueError("V13 is running; first use 'V13 beenden'. No process was signalled.")
    if not seen:
        raise ValueError("process visibility unavailable")


def private_directory(path):
    if path.exists() or path.is_symlink():
        real_path(path, directory=True)
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("recovery directory must be owner-only")
    else:
        path.mkdir(mode=0o700)
    return path


def atomic_bytes(path, data, mode=0o600):
    descriptor, temporary = tempfile.mkstemp(prefix=".recovery-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            os.fchmod(output.fileno(), mode)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def receipt_write(path, receipt):
    atomic_bytes(path, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())


@contextmanager
def recovery_lock(state):
    private_directory(state)
    descriptor = os.open(state / "activation.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if os.fstat(descriptor).st_uid != os.getuid():
            raise ValueError("unsafe recovery lock owner")
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def launcher_bytes(code_dir, home):
    found = shutil.which("bash")
    if not found:
        raise ValueError("bash interpreter is missing; activation refused")
    bash = Path(found).resolve(strict=True)
    if (not bash.is_file() or not os.access(bash, os.X_OK)
            or any(character.isspace() for character in str(bash))):
        raise ValueError("invalid bash interpreter path; activation refused")
    python = str(Path(sys.executable).resolve(strict=True))
    return ("#!" + str(bash) + "\nset -e\n"
            "# Explicit reviewed recovery candidate; no gate or learning promotion.\n"
            "unset PYTHONHOME PYTHONSTARTUP\n"
            "export NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1 PYTHONDONTWRITEBYTECODE=1\n"
            "export PYTHONPATH=" + shlex.quote(str(code_dir)) + "\n"
            "cd " + shlex.quote(str(code_dir)) + "\n"
            "exec " + shlex.quote(python) + " -B -P -m v13 --home "
            + shlex.quote(str(home)) + ' "$@"\n').encode()


def read_receipt(path):
    if not path.exists():
        return None
    real_path(path)
    if path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise ValueError("unsafe activation receipt")
    receipt = json.loads(path.read_bytes())
    if not isinstance(receipt, dict):
        raise ValueError("invalid activation receipt")
    return receipt


def operate(code_dir, home, *, action=None):
    home, launcher, settings, database = validate_home(home)
    state = home / "recovery-state"
    active = state / "ACTIVE.json"
    if action == "rollback":
        # A broken or missing candidate must never prevent launcher recovery.
        stage = Path(os.path.abspath(Path(code_dir).expanduser()))
        if stage.is_symlink():
            raise ValueError("candidate root leaf cannot be a symbolic link")
        stage = stage.resolve()
        manifest_hash = None
    else:
        stage, manifest_hash = validate_stage(code_dir)
    if action is None:
        return {"status": "CHECKED_NO_ACTION", "code_dir": str(stage),
                "manifest_sha256": manifest_hash, "home": str(home)}
    if action not in ("activate", "rollback"):
        raise ValueError("unknown activation action")
    # Resolve the actual Termux bash before creating recovery state/backups.
    # Android has no ordinary /usr/bin/env interpreter.
    new_launcher = launcher_bytes(stage, home) if action == "activate" else None
    require_stopped()
    if action == "rollback" and not state.exists():
        raise ValueError("no activation receipt to roll back")
    with recovery_lock(state):
        receipt = read_receipt(active)
        current = launcher.read_bytes()
        if action == "rollback":
            if not receipt or receipt.get("code_dir") != str(stage) or receipt.get("home") != str(home):
                raise ValueError("activation receipt does not match this home and candidate")
            if digest(current) == receipt.get("prior_launcher_sha256"):
                if receipt.get("status") != "ROLLED_BACK":
                    receipt["status"] = "ROLLED_BACK"
                    receipt_write(active, receipt)
                return dict(receipt, status="ALREADY_ROLLED_BACK")
            if digest(current) != receipt.get("launcher_sha256"):
                raise ValueError("launcher changed after activation; rollback lease refused")
            backup = real_path(receipt["prior_launcher_path"], within=state)
            if not backup.is_relative_to(state) or digest(backup.read_bytes()) != receipt["prior_launcher_sha256"]:
                raise ValueError("launcher backup failed verification")
            require_stopped()
            if digest(launcher.read_bytes()) != receipt["launcher_sha256"]:
                raise ValueError("launcher changed during rollback")
            atomic_bytes(launcher, backup.read_bytes(), receipt["prior_launcher_mode"])
            receipt["status"] = "ROLLED_BACK"
            receipt_write(active, receipt)
            return receipt
        new = new_launcher
        if receipt and receipt.get("status") in ("PREPARED", "ACTIVE"):
            if (receipt.get("code_dir") == str(stage) and receipt.get("manifest_sha256") == manifest_hash
                    and digest(current) == receipt.get("launcher_sha256") == digest(new)):
                return dict(receipt, status="ALREADY_ACTIVE")
            raise ValueError("another activation or changed launcher exists; roll back first")
        folder = Path(tempfile.mkdtemp(prefix="activation-", dir=state))
        os.chmod(folder, 0o700)
        prior = folder / "launcher.before"
        atomic_bytes(prior, current)
        atomic_bytes(folder / "settings.before.json", settings.read_bytes())
        backup_db = folder / "brain.before.sqlite3"
        descriptor = os.open(backup_db, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        source = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5)
        target = sqlite3.connect(backup_db)
        try:
            deadline = time.monotonic() + 15
            def progress(status, remaining, total):
                if time.monotonic() >= deadline:
                    raise ValueError("database backup timed out; activation refused")
            source.backup(target, pages=128, progress=progress, sleep=.05)
            if target.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("database backup integrity failed")
        finally:
            target.close()
            source.close()
        backup_db.chmod(0o600)
        receipt = {"status": "PREPARED", "home": str(home), "code_dir": str(stage),
                   "manifest_sha256": manifest_hash, "launcher_path": str(launcher),
                   "launcher_sha256": digest(new), "prior_launcher_path": str(prior),
                   "prior_launcher_sha256": digest(current),
                   "prior_launcher_mode": stat.S_IMODE(launcher.stat().st_mode),
                   "settings_backup": str(folder / "settings.before.json"),
                   "database_backup": str(backup_db),
                   "rollback_scope": "LAUNCHER_ONLY_NO_DATA_REWIND",
                   "canonical_promotion": False}
        receipt_write(active, receipt)
        require_stopped()
        if digest(launcher.read_bytes()) != receipt["prior_launcher_sha256"]:
            raise ValueError("launcher changed during backup; activation refused")
        atomic_bytes(launcher, new, receipt["prior_launcher_mode"] | 0o100)
        receipt["status"] = "ACTIVE"
        receipt_write(active, receipt)
        return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code-dir", type=Path, required=True)
    parser.add_argument("--home", type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--activate", action="store_true")
    group.add_argument("--rollback", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = operate(args.code_dir, args.home,
                         action="activate" if args.activate else "rollback" if args.rollback else None)
    except (OSError, ValueError, SyntaxError, sqlite3.Error) as exc:
        parser.exit(2, "BLOCKED: " + str(exc) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

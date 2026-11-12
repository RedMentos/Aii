"""Conservative, incremental updater for a Git-installed V13 source checkout.

Fetches Git deltas, fast-forwards only to a descendant on the already selected
branch of the user's explicit GitHub source repo, preserves ~/v13 data/models,
does not auto-run installers or enable any learning/update permissions.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
from contextlib import contextmanager

EXPECTED_ORIGINS = (
    "https://github.com/RedMentos/Aii",
    "https://github.com/RedMentos/Aii.git",
    "git@github.com:RedMentos/Aii.git",
)
SHA = re.compile(r"[0-9a-f]{40}\Z")
BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,180}\Z")
TIMEOUT = 75
HISTORY = Path.home() / ".v13-private" / "source-update-state.json"
LOCK = Path.home() / ".v13-private" / "source-update.lock"


class UpdateDenied(Exception):
    pass


def git(root, *args, ok=(0,), timeout=TIMEOUT):
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    proc = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True,
        timeout=timeout, env=env, check=False
    )
    if proc.returncode not in ok:
        raise UpdateDenied("git " + args[0] + " failed (exit " + str(proc.returncode) + ")")
    return proc.stdout.strip()


def _is_clean(root):
    return not git(root, "status", "--porcelain", "--untracked-files=no")


def _repo_root(root):
    root = Path(root).expanduser().resolve()
    if not root.is_dir() or root.is_symlink() or not (root / ".git").is_dir():
        raise UpdateDenied("Expected a real Git checkout, not a ZIP or symbolic link")
    top = Path(git(root, "rev-parse", "--show-toplevel")).resolve()
    if top != root:
        raise UpdateDenied("Update target must be the Git checkout root")
    origin = git(root, "remote", "get-url", "origin")
    if origin not in EXPECTED_ORIGINS:
        raise UpdateDenied("Unexpected source repository; update refused")
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if not BRANCH.fullmatch(branch) or branch.startswith("-") or ".." in branch or "//" in branch or branch.endswith((".lock", ".","/")):
        raise UpdateDenied("Invalid or detached source branch")
    # Do not silently move across V13 development branches.
    head = git(root, "rev-parse", "HEAD")
    if not SHA.fullmatch(head):
        raise UpdateDenied("Invalid installed source commit")
    if not _is_clean(root):
        raise UpdateDenied("Local edited tracked files; refusing to overwrite")
    return root, branch, head


def _runtime_active():
    """Fail closed when OS process list cannot be inspected; no live source swapping."""
    proc = Path("/proc")
    if not proc.is_dir():
        return True
    own_uid = os.getuid()
    seen = 0
    for child in proc.iterdir():
        if not child.name.isdecimal():
            continue
        try:
            if child.stat().st_uid != own_uid:
                continue
            raw = (child / "cmdline").read_bytes()[:4096]
        except (OSError, PermissionError):
            continue
        args = [x.decode("utf8", "replace") for x in raw.split(b"\0") if x]
        if not args:
            continue
        seen += 1
        if any(x == "v13" or x.endswith("/bin/v13") for x in args):
            return True
        if "-m" in args and any(args[n + 1] == "v13" for n, x in enumerate(args[:-1]) if x == "-m"):
            return True
    # A readable own process must exist, otherwise process visibility is not reliable.
    return seen == 0


@contextmanager
def _lock():
    LOCK.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if LOCK.parent.is_symlink() or LOCK.parent.stat().st_mode & 0o077:
        raise UpdateDenied("Update state directory must be private")
    if LOCK.is_symlink():
        raise UpdateDenied("Unsafe updater lock")
    with LOCK.open("a+b") as f:
        os.chmod(LOCK, 0o600)
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise UpdateDenied("Another source update is already running") from exc
        yield


def _fetch(root, branch):
    # Only the *already checked out branch* and *already configured source*.
    ref = "refs/remotes/origin/" + branch
    git(root, "fetch", "--no-tags", "--filter=blob:none", "origin",
        "refs/heads/" + branch + ":" + ref, timeout=90)
    new = git(root, "rev-parse", ref)
    if not SHA.fullmatch(new):
        raise UpdateDenied("Remote source revision could not be verified")
    return new


def status(root=None, *, fetch=True):
    root, branch, old = _repo_root(root or Path.home() / "V13-Phone")
    new = _fetch(root, branch) if fetch else git(root, "rev-parse", "refs/remotes/origin/" + branch)
    if not SHA.fullmatch(new):
        raise UpdateDenied("Cannot verify update commit")
    if new == old:
        return {"status":"UP_TO_DATE", "branch":branch, "current":old, "available":new, "changed_files":0}
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", old, new],
                      capture_output=True, timeout=TIMEOUT).returncode != 0:
        raise UpdateDenied("Remote history is not fast-forward; no update applied")
    changed = git(root, "diff", "--name-only", old, new).splitlines()
    return {"status":"UPDATE_AVAILABLE", "branch":branch, "current":old,
            "available":new, "changed_files":len(changed),
            "source_files":len([p for p in changed if p.startswith("v13/code/")])}


def _remember(data):
    HISTORY.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if HISTORY.is_symlink():
        raise UpdateDenied("Unsafe state file")
    tmp = HISTORY.with_name(HISTORY.name + ".new")
    if tmp.exists() or tmp.is_symlink():
        raise UpdateDenied("Updater state write already pending")
    with tmp.open("x") as f:
        json.dump(data, f, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, HISTORY)


def _check_python(root, before, after):
    files = git(root, "diff", "--name-only", before, after).splitlines()
    # Syntax-check new/changed Python files only, no module imports executed.
    paths = [p for p in files if p.startswith("v13/code/") and p.endswith(".py")]
    if len(paths) > 500:
        raise UpdateDenied("Too many changed Python source files")
    for path in paths:
        candidate = root / path
        if candidate.is_symlink() or not candidate.is_file():
            continue  # deleted paths already validated by Git
        p = subprocess.run(["python", "-c", "import ast,sys;ast.parse(open(sys.argv[1], encoding='utf-8').read())",
                            str(candidate)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if p.returncode:
            raise UpdateDenied("Syntax check failed for source update")


CI_WORKFLOW = "V13 private owner-read Termux bootstrap"
CI_WORKFLOW_PATH = ".github/workflows/v13-private-owner-read-ci.yml"
REQUIRED_CI = {
    "dashboard": (CI_WORKFLOW, "v13-private-remote-bridge-tests"),
    "runtime": (CI_WORKFLOW, "v13-private-remote-bridge-tests",
                "V13 staged context and integrated regression"),
}


def _ci_runs(commit):
    """Read the exact-commit GitHub workflow results, never invent CI success."""
    if not isinstance(commit, str) or not SHA.fullmatch(commit):
        return []
    p = subprocess.run(
        ["gh", "api", "--method", "GET", "repos/RedMentos/Aii/actions/runs",
         "-f", "head_sha=" + commit, "-f", "per_page=100"],
        capture_output=True, text=True, timeout=30, check=False)
    if p.returncode:
        raise UpdateDenied("GitHub CI lookup failed; update held")
    try:
        value = json.loads(p.stdout)
    except (ValueError, UnicodeError) as exc:
        raise UpdateDenied("Invalid GitHub CI reply") from exc
    runs = value.get("workflow_runs") if isinstance(value, dict) else None
    if not isinstance(runs, list):
        raise UpdateDenied("Missing GitHub workflow_runs")
    return runs


def ci_passed(commit, *, scope="runtime"):
    """Separate gates: UI/bridge tests for dashboard; integrated tests for runtime."""
    if scope not in REQUIRED_CI:
        return False
    try:
        runs = _ci_runs(commit)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False
    successful = set()
    for run in runs:
        if not isinstance(run, dict):
            continue
        if (run.get("head_sha") != commit or run.get("status") != "completed"
            or run.get("conclusion") != "success"
            or not isinstance(run.get("head_repository"), dict)
            or run["head_repository"].get("full_name") != "RedMentos/Aii"):
            continue
        name = run.get("name")
        if name == CI_WORKFLOW and run.get("path", "").split("@",1)[0] != CI_WORKFLOW_PATH:
            continue
        successful.add(name)
    return set(REQUIRED_CI[scope]).issubset(successful)


def apply(root=None, *, expected_tip=None):
    with _lock():
        s = status(root)
        if s["status"] == "UP_TO_DATE":
            return s
        if expected_tip is not None and s["available"] != expected_tip:
            raise UpdateDenied("Remote changed after approval; refusing unreviewed new commit")
        if _runtime_active():
            raise UpdateDenied("V13 process detected (or process visibility unavailable). Stop running V13 before updating.")
        root, branch, before = _repo_root(root or Path.home() / "V13-Phone")
        if before != s["current"]:
            raise UpdateDenied("Checkout changed during update")
        after = s["available"]
        # Retain the old commit in Git locally, so old sparse blobs stay reachable.
        backup = "refs/v13-local-rollback/" + str(int(time.time())) + "-" + secrets.token_hex(3)
        git(root, "update-ref", backup, before)
        try:
            git(root, "merge", "--ff-only", after, timeout=180)
            if not _is_clean(root):
                raise UpdateDenied("Post-update source is not clean")
            _check_python(root, before, after)
        except Exception:
            # We only touch tracked source after ensuring the checkout was clean.
            git(root, "reset", "--hard", before, timeout=90)
            raise
        result = {"status":"UPDATED", "branch":branch,
                  "previous":before, "current":after, "changed_files":s["changed_files"],
                  "updated_at":int(time.time()), "rollback_ref":backup}
        _remember(result)
        return result



REQUIRED_PHONE_MODULES = (
    "v13/code/v13/__init__.py",
    "v13/code/v13/common.py",
    "v13/code/v13/source_updater.py",
    "v13/code/v13/owner_read_bridge.py",
    "v13/code/v13/remote_maintenance_bridge.py",
    "v13/code/v13/remote_chat.py",
    "v13/code/v13/phone_monitor.py",
    "v13/code/v13/chat_service.py",
    "v13/code/v13/managed_console.py",
    "v13/code/v13/mobile_dashboard.py",
    "v13/code/v13/pipeline_agent.py",
    "v13/code/v13/lifecycle.py",
    "v13/code/v13/runtime_deploy.py",
    "v13/code/v13/diagnostic_push.py",
    "v13/code/v13/termux_patch_staging.py",
    "v13/code/v13/mobile_dashboard.html",
)
PHONE_PACKAGE = "v13/code/v13/"


def ensure_sparse_phone_modules(root=None):
    """Safely migrate an older phone checkout to the fixed package subtree.

    Git fast-forward updates historically left newly introduced modules
    invisible because the one-command installer pinned exact old file paths.
    Keeping the directory selected also materializes future dependencies on
    fast-forward. Only regular files committed under this fixed code subtree
    are restored; private user/model data is never part of the migration.
    """
    target = Path(root or (Path.home() / ".v13-agent-source")).expanduser().resolve()
    with _lock():
        checkout, _, head = _repo_root(target)
        return _ensure_sparse_phone_modules(checkout, head)


def _ensure_sparse_phone_modules(checkout, head):
    """Materialize the verified package while the caller holds _lock()."""
    files = []
    for entry in git(checkout, "ls-tree", "-r", "-z", head, "--", PHONE_PACKAGE).split("\0"):
        if not entry:
            continue
        metadata, separator, path = entry.partition("\t")
        if (not separator or not path.startswith(PHONE_PACKAGE) or
                metadata.split()[:2] not in (["100644", "blob"], ["100755", "blob"])):
            raise UpdateDenied("Unsafe committed phone package member")
        files.append(path)
    if not set(REQUIRED_PHONE_MODULES).issubset(files):
        raise UpdateDenied("Expected trusted phone module missing from commit")
    # Refuse existing symlinks before Git can write through a directory
    # supplied by an untracked file in the old sparse checkout.
    def present():
        complete = True
        for path in files:
            file = checkout / path
            for member in (file, *file.parents):
                if member == checkout:
                    break
                if member.is_symlink():
                    raise UpdateDenied("Unsafe phone package symlink")
            complete = complete and file.is_file()
        return complete

    complete = present()
    sparse = git(checkout, "config", "--bool", "core.sparseCheckout", ok=(0, 1)) == "true"
    cone = sparse and git(checkout, "config", "--bool", "core.sparseCheckoutCone", ok=(0, 1)) == "true"
    pattern = PHONE_PACKAGE.rstrip("/") if cone else "/" + PHONE_PACKAGE
    selected = not sparse or pattern in git(checkout, "sparse-checkout", "list").splitlines()
    if complete and selected:
        return {"status": "ALREADY_PRESENT", "commit": head}
    if not sparse:
        raise UpdateDenied("Required phone package files missing from full checkout")
    git(checkout, "sparse-checkout", "add", pattern, timeout=90)
    if not present():
        raise UpdateDenied("Required phone module missing after sparse migration")
    if not _is_clean(checkout):
        raise UpdateDenied("Sparse module migration changed tracked content")
    return {"status": "MIGRATED", "commit": head}


def apply_dashboard(root=None, *, expected_tip=None):
    """Update only the independent dashboard checkout, not live model files.

    Unlike V13 runtime updates, the dashboard is restarted by its supervisor
    after the current HTTP response. Refuse modified sources or rewritten
    Git history, retain old commit and perform syntax checks before restart.
    """
    actual = Path.home() / ".v13-agent-source"
    requested = Path(root or actual).expanduser().resolve()
    if root is None and requested != actual.resolve():
        raise UpdateDenied("Dashboard path changed")
    with _lock():
        s = status(requested)
        if s["status"] == "UP_TO_DATE":
            checkout, _, head = _repo_root(requested)
            _ensure_sparse_phone_modules(checkout, head)
            return s
        if expected_tip is not None and s["available"] != expected_tip:
            raise UpdateDenied("Dashboard remote revision changed after CI approval")
        checkout, branch, before = _repo_root(requested)
        if before != s["current"]:
            raise UpdateDenied("Dashboard changed during source fetch")
        backup = "refs/v13-dashboard-rollback/" + str(int(time.time())) + "-" + secrets.token_hex(3)
        git(checkout, "update-ref", backup, before)
        try:
            git(checkout, "merge", "--ff-only", s["available"], timeout=180)
            if not _is_clean(checkout):
                raise UpdateDenied("Dashboard checkout is dirty after update")
            _ensure_sparse_phone_modules(checkout, s["available"])
            _check_python(checkout, before, s["available"])
            html_file = checkout / "v13/code/v13/mobile_dashboard.html"
            if html_file.is_symlink() or not html_file.is_file():
                raise UpdateDenied("Required mobile UI HTML template missing in sparse checkout")
        except Exception:
            git(checkout, "reset", "--hard", before, timeout=90)
            raise
        return {"status":"UPDATED", "source":"CONTROL_PANEL", "previous":before,
                "current":s["available"], "changed_files":s["changed_files"],
                "rollback_ref":backup, "restart_required":True}


def auto_apply(root=None):
    s = status(root)
    if s["status"] == "UP_TO_DATE":
        return s
    if not ci_passed(s["available"]):
        raise UpdateDenied("Automatic update held: required GitHub CI did not pass for the exact commit")
    return apply(root, expected_tip=s["available"])


def rollback(root=None):
    with _lock():
        root, branch, current = _repo_root(root or Path.home() / "V13-Phone")
        if _runtime_active():
            raise UpdateDenied("Stop V13 before restoring previous code")
        if HISTORY.is_symlink() or not HISTORY.is_file():
            raise UpdateDenied("No prior update recorded")
        rec = json.loads(HISTORY.read_text())
        if rec.get("status") != "UPDATED" or rec.get("current") != current or rec.get("branch") != branch:
            raise UpdateDenied("Local commit changed since last update; refusing rollback")
        previous = rec.get("previous")
        if not isinstance(previous, str) or not SHA.fullmatch(previous):
            raise UpdateDenied("Invalid rollback revision")
        if git(root, "rev-parse", rec["rollback_ref"]) != previous:
            raise UpdateDenied("Rollback ref mismatch")
        git(root, "reset", "--hard", previous, timeout=90)
        result = {"status":"ROLLED_BACK", "previous":current, "current":previous,
                  "rolled_back_at":int(time.time())}
        _remember(result)
        return result


def main(argv=None):
    p = argparse.ArgumentParser(description="V13 incremental Git source updater (no data/model modifications)")
    p.add_argument("action", choices=("check", "apply", "auto", "rollback"))
    p.add_argument("--root", default=str(Path.home() / "V13-Phone"))
    a = p.parse_args(argv)
    try:
        result = (status(a.root) if a.action == "check" else apply(a.root) if a.action == "apply"
                  else auto_apply(a.root) if a.action == "auto" else rollback(a.root))
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    except (OSError, subprocess.TimeoutExpired, UpdateDenied, ValueError) as exc:
        print(json.dumps({"status":"REFUSED", "reason": str(exc)[:260]}, sort_keys=True))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())

"""Incremental V13 source updater, fail-closed and independent of model/data caches.

Fetches only Git objects missing locally. Can stage remote commits automatically.
Only activates with owner-enabled local policy, matching successful GitHub CI,
a clean fast-forward checkout, syntactically valid source, and no active V13 run.
Never updates ~/v13 (models, SQLite memory, exports, private keys).
"""
from __future__ import annotations
import argparse
import ast
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

SOURCE = "RedMentos/Aii"
ORIGIN = "https://github.com/RedMentos/Aii.git"
BRANCH = "gpt6/v13-private-remote-bridge-20261111"
PRIVATE = Path.home() / ".v13-private"
POLICY = PRIVATE / "autoupdate-policy.json"
STATUS = PRIVATE / "autoupdate-status.json"
TRACKED = {"bridge": Path.home() / ".v13-agent-source",
           "v13": Path.home() / "V13-Phone"}
REF = "refs/remotes/origin/" + BRANCH
SHA = re.compile(r"[a-f0-9]{40}\Z")
ALLOWED_EXTENSIONS = (".py", ".sh", ".md", ".txt", ".json",
                      ".toml", ".cpp", ".h", ".hpp", ".yml", ".yaml")
MAX_CHANGED = 100
MAX_FILE = 1_048_576
DEFAULT_INTERVAL = 600


class UpdateDenied(RuntimeError):
    pass


def _call(cmd, *, timeout=90, data=None, check=True):
    try:
        p = subprocess.run(cmd, input=data, capture_output=True, timeout=timeout,
                           check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise UpdateDenied("operation unavailable") from exc
    if check and p.returncode:
        raise UpdateDenied("verification or Git command failed")
    return p


def _git(root, *args, timeout=90, check=True):
    return _call(["git", "-C", str(root), *args], timeout=timeout, check=check)


def _safe_repo(root):
    if root.is_symlink() or not root.is_dir():
        raise UpdateDenied("checkout missing or linked")
    git = root / ".git"
    if git.is_symlink() or not git.is_dir():
        raise UpdateDenied("checkout metadata missing/linked")
    try:
        origin = _git(root, "remote", "get-url", "origin").stdout.decode().strip()
        current = _git(root, "branch", "--show-current").stdout.decode().strip()
    except UnicodeError as exc:
        raise UpdateDenied("invalid checkout metadata") from exc
    if origin != ORIGIN or current != BRANCH:
        raise UpdateDenied("unexpected source repository or branch")
    if _git(root, "status", "--porcelain", "--untracked-files=no").stdout:
        raise UpdateDenied("checkout has local changes; not overwriting")
    head = _git(root, "rev-parse", "HEAD").stdout.decode().strip()
    if not SHA.fullmatch(head):
        raise UpdateDenied("invalid current Git revision")
    return head


def _fetch(root, head):
    # A verified history relationship is mandatory even in a shallow clone.
    # Retry limited depths; never accept force pushes or branch rewrites.
    for depth in (128, 512, 2048):
        _git(root, "fetch", "--quiet", "--no-tags", "--depth", str(depth),
             "origin", "+refs/heads/" + BRANCH + ":" + REF, timeout=180)
        target = _git(root, "rev-parse", REF).stdout.decode().strip()
        if not SHA.fullmatch(target):
            raise UpdateDenied("invalid remote Git commit")
        if target == head:
            return target
        ok = _git(root, "merge-base", "--is-ancestor", head, target,
                  check=False).returncode == 0
        if ok:
            return target
    raise UpdateDenied("unverified fast-forward or rewritten Git history")


def _changed(root, old, target):
    raw = _git(root, "diff", "--name-only", "-z", old, target).stdout
    paths = [p.decode("utf-8") for p in raw.split(b"\0") if p]
    if len(paths) > MAX_CHANGED:
        raise UpdateDenied("too many changed files; manual review required")
    for name in paths:
        if (not name.startswith(("v13/code/", ".github/workflows/")) or
            name.startswith("/") or "\\" in name or
            any(x in (".", "..", "") for x in name.split("/")) or
            not name.endswith(ALLOWED_EXTENSIONS)):
            raise UpdateDenied("change outside permitted source/docs/CI paths")
    return paths


def _verify_syntax(root, target, paths):
    """Validate bytes without importing or running downloaded code."""
    for name in paths:
        blob = _git(root, "show", target + ":" + name, timeout=20, check=False)
        if blob.returncode:
            # Deletions cannot be auto-activated.
            raise UpdateDenied("deleted or unreadable source file")
        if len(blob.stdout) > MAX_FILE:
            raise UpdateDenied("oversized source change")
        try:
            if name.endswith(".py"):
                ast.parse(blob.stdout.decode("utf-8"))
            elif name.endswith(".json"):
                json.loads(blob.stdout)
            elif name.endswith(".toml"):
                import tomllib
                tomllib.loads(blob.stdout.decode("utf-8"))
            elif name.endswith(".sh"):
                if _call(["bash", "-n"], data=blob.stdout, timeout=10,
                         check=False).returncode:
                    raise UpdateDenied("invalid shell syntax")
        except (SyntaxError, UnicodeError, ValueError) as exc:
            raise UpdateDenied("changed source syntax failed") from exc


def _ci_success(target):
    """Require a successful GitHub-owned always-on updater workflow for exact SHA."""
    try:
        p = _call(["gh", "api", "--method", "GET",
                   f"repos/{SOURCE}/commits/{target}/check-runs?per_page=100"],
                  timeout=25)
        obj = json.loads(p.stdout)
        runs = obj.get("check_runs", [])
        return (isinstance(runs, list) and
                any(isinstance(r, dict) and
                    r.get("name") == "auto-update-safety" and
                    r.get("head_sha") == target and
                    r.get("status") == "completed" and
                    r.get("conclusion") == "success" and
                    r.get("app", {}).get("slug") == "github-actions"
                    for r in runs))
    except (UpdateDenied, ValueError, TypeError, KeyError):
        return False


def _v13_idle():
    """Do not change the live app while a model or acceptance process may run."""
    p = _call(["ps", "-A", "-o", "args="], timeout=5, check=False)
    if p.returncode or not p.stdout:
        return False  # unable to verify -> defer activation
    for line in p.stdout.decode("utf-8", errors="replace").splitlines():
        if ("-m v13 " in line and
                not any(s in line for s in ("v13.auto_update", "v13.owner_read_bridge",
                                            "v13.mobile_dashboard"))):
            return False
        if "/v13/code/scripts/acceptance.py" in line:
            return False
    return True


@contextmanager
def _exclusive():
    PRIVATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if PRIVATE.is_symlink() or PRIVATE.stat().st_mode & 0o077:
        raise UpdateDenied("private updater directory not protected")
    with (PRIVATE / "autoupdate.lock").open("a+b") as fp:
        os.chmod(fp.name, 0o600)
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def _store(path, obj):
    tmp = path.with_suffix(".new")
    if tmp.is_symlink() or tmp.exists():
        raise UpdateDenied("temporary state path occupied")
    with tmp.open("x") as f:
        json.dump(obj, f, sort_keys=True, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def policy():
    if not POLICY.exists():
        return {"auto_activate": False, "interval_seconds": DEFAULT_INTERVAL}
    if POLICY.is_symlink() or POLICY.stat().st_mode & 0o077:
        raise UpdateDenied("insecure updater policy")
    p = json.loads(POLICY.read_text())
    if not isinstance(p, dict) or set(p) != {"auto_activate", "interval_seconds"}:
        raise UpdateDenied("invalid updater policy")
    if type(p["auto_activate"]) is not bool or type(p["interval_seconds"]) is not int or not 120 <= p["interval_seconds"] <= 3600:
        raise UpdateDenied("invalid updater policy fields")
    return p


def toggle(enabled):
    if type(enabled) is not bool:
        raise UpdateDenied("auto activation requires explicit owner choice")
    with _exclusive():
        p = policy()
        p["auto_activate"] = enabled
        _store(POLICY, p)
    return p


def inspect_one(key):
    root = TRACKED[key]
    if not root.exists():
        return {"status": "NOT_INSTALLED"}
    old = _safe_repo(root)
    target = _fetch(root, old)
    if target == old:
        return {"status": "UP_TO_DATE", "head": old[:12]}
    paths = _changed(root, old, target)
    _verify_syntax(root, target, paths)
    result = {"status": "UPDATE_DOWNLOADED", "head": old[:12],
              "candidate": target[:12], "changed_files": len(paths),
              "requires_v13_idle": key == "v13"}
    result["ci_passed"] = _ci_success(target)
    return result


def check_all():
    with _exclusive():
        data = {"schema": "v13.autoupdate/1", "checked_at": int(time.time()),
                "auto_activate": policy()["auto_activate"], "repos": {}}
        for key in TRACKED:
            try:
                data["repos"][key] = inspect_one(key)
            except (UpdateDenied, OSError, UnicodeError) as exc:
                data["repos"][key] = {"status": "CHECK_FAILED",
                                      "error_code": type(exc).__name__}
        _store(STATUS, data)
        return data


def apply_one(key):
    root = TRACKED[key]
    if not root.exists():
        return {"status": "NOT_INSTALLED"}
    old = _safe_repo(root)
    target = _fetch(root, old)
    if target == old:
        return {"status": "UP_TO_DATE"}
    paths = _changed(root, old, target)
    _verify_syntax(root, target, paths)
    if not _ci_success(target):
        return {"status": "WAITING_FOR_GREEN_CI"}
    if key == "v13" and not _v13_idle():
        return {"status": "WAITING_FOR_V13_IDLE"}
    # Update source only. No package install, no GGUF changes, no automatic code
    # execution or subprocess restart. Next explicit invocation loads new code.
    _git(root, "merge", "--ff-only", "--no-edit", target, timeout=60)
    return {"status": "SOURCE_UPDATED_NEXT_START", "from": old[:12],
            "to": target[:12], "changed_files": len(paths)}


def apply_all(*, owner_approved=False):
    if not owner_approved and not policy()["auto_activate"]:
        raise UpdateDenied("automatic source activation is disabled locally")
    with _exclusive():
        results = {}
        for key in TRACKED:
            try:
                results[key] = apply_one(key)
            except (UpdateDenied, OSError) as exc:
                results[key] = {"status": "APPLY_REFUSED", "error_code": type(exc).__name__}
        return results


def status():
    if not STATUS.is_file() or STATUS.is_symlink() or STATUS.stat().st_size > 32_000:
        return {"status": "NOT_CHECKED", "auto_activate": policy()["auto_activate"]}
    try:
        result = json.loads(STATUS.read_bytes())
        if isinstance(result, dict):
            return result
    except (OSError, ValueError):
        pass
    return {"status": "INVALID"}


def main(argv=None):
    p = argparse.ArgumentParser(description="V13 incremental GitHub source updater")
    p.add_argument("mode", choices=("check", "apply", "serve", "status", "auto-on", "auto-off"))
    args = p.parse_args(argv)
    if args.mode in ("auto-on", "auto-off"):
        print(json.dumps(toggle(args.mode == "auto-on")))
    elif args.mode == "check":
        print(json.dumps(check_all(), sort_keys=True))
    elif args.mode == "status":
        print(json.dumps(status(), sort_keys=True))
    elif args.mode == "apply":
        print(json.dumps(apply_all(owner_approved=True), sort_keys=True))
    else:
        while True:
            try:
                print(json.dumps(check_all(), sort_keys=True), flush=True)
                if policy()["auto_activate"]:
                    print(json.dumps(apply_all(), sort_keys=True), flush=True)
            except (UpdateDenied, OSError, ValueError) as exc:
                print(json.dumps({"status": "UPDATE_ERROR",
                                  "error_code": type(exc).__name__}), flush=True)
            time.sleep(policy()["interval_seconds"])


if __name__ == "__main__":
    main()

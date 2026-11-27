"""Git provenance checks shared by M1 preregistration and model runs."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path


def current_git_commit(repo_root: str | Path | None = None) -> str:
    """Return HEAD only when the executing repository has no tracked or untracked changes."""
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise RuntimeError("executing repository must have a clean working tree for preregistration")
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("git rev-parse HEAD did not return a full lowercase commit SHA")
    return commit

"""Opt-in, SHA-bound V13 release queue. Runs ONLY from trusted default branch.

This bot cannot choose code to ship. The Boss reviews a PR and adds the exact
owner-authored marker V13-RELEASE-APPROVED SHA=<40 lowercase hex>. We re-check
the PR head, fast-forward ancestry, changed paths, and GitHub-owned CI BEFORE
merging one safe candidate. After merge, the independent phone CI/installer
still has to accept the exact release commit. No private phone data is read.
"""
import argparse
import json
import os
from pathlib import PurePosixPath
import re
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPO = "RedMentos/Aii"
OWNER = "RedMentos"
RELEASE = "gpt6/v13-private-remote-bridge-20261111"
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
MARKER = "V13-RELEASE-APPROVED SHA="
REQUIRED = {
    "V13 staged context and integrated regression":
        ".github/workflows/v13-integrated-context-stage-20261111.yml",
    "v13-private-remote-bridge-tests":
        ".github/workflows/v13-private-remote-bridge-tests.yml",
}
PHONE_PATHS = (
    "v13/code/v13/source_updater.py",
    "v13/code/v13/pipeline_agent.py",
    "v13/code/v13/runtime_deploy.py",
    "v13/code/v13/lifecycle.py",
    "v13/code/v13/chat_service.py",
    "v13/code/v13/mobile_dashboard.py",
    "v13/code/v13/mobile_dashboard.html",
    "v13/code/v13/managed_console.py",
    "v13/code/v13/owner_read_bridge.py",
    "v13/code/v13/remote_maintenance_bridge.py",
    "v13/code/scripts/termux_one_command.sh",
)
OWNER_READ = ("V13 private owner-read Termux bootstrap",
              ".github/workflows/v13-private-owner-read-ci.yml")
# High-authority files MUST go through direct reviewed/CI-gated integration,
# not a scheduled bot merge. This includes any source permission/updater path.
FORBIDDEN_PREFIX = (".github/", "v13/code/docs/canon/", "v13/code/models/",
                    "v13/code/weights/", "v13/code/keys/", "v13/code/.env")
FORBIDDEN_EXACT = set(PHONE_PATHS) | {"v13/code/specs/models.json",
                                     "v13/AGENTS.md",
                                     "v13/coordination/PHONE_RELEASE_TRAIN_2026-11-12.md"}
SAFE_SUFFIX = {".py", ".md", ".txt", ".json", ".sh", ".cpp", ".c",
               ".h", ".hpp", ".js", ".html", ".kt", ".yaml", ".yml"}


class QueueError(Exception):
    pass


class GitHub:
    def __init__(self, token):
        if not token:
            raise QueueError("GITHUB_TOKEN missing")
        self.token = token

    def call(self, method, path, data=None):
        if not path.startswith("/repos/" + REPO + "/"):
            raise QueueError("outside allowed repo")
        body = None if data is None else json.dumps(data, separators=(",", ":")).encode()
        req = Request("https://api.github.com" + path, data=body, method=method,
                      headers={"Authorization": "Bearer " + self.token,
                               "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28",
                               "User-Agent": "V13-reviewed-release-queue",
                               "Content-Type": "application/json"})
        with urlopen(req, timeout=25) as response:
            return json.load(response)


def _list(api, resource):
    # Review queues may have >100 open PRs. A list result must not silently
    # omit a later candidate; cap total work and fail closed at this bound.
    rows = []
    for page in range(1, 5):
        separator = "&" if "?" in resource else "?"
        part = api.call("GET", resource + separator + urlencode(
            {"per_page": 100, "page": page}))
        if not isinstance(part, list):
            raise QueueError("invalid GitHub list response")
        rows.extend(part)
        if len(part) < 100:
            return rows
    raise QueueError("release queue pagination bound exceeded")


def _safe_files(files):
    if not files or len(files) > 30:
        return False
    changes = 0
    for item in files:
        if not isinstance(item, dict):
            return False
        name = item.get("filename")
        status = item.get("status")
        if (not isinstance(name, str) or name.startswith("/")
                or "\\" in name or ".." in name.split("/")
                or not name.startswith("v13/") or
                any(name.startswith(p) for p in FORBIDDEN_PREFIX) or
                name in FORBIDDEN_EXACT or
                PurePosixPath(name).suffix not in SAFE_SUFFIX or
                status not in ("modified", "added")):
            return False
        count = item.get("changes")
        if type(count) is not int or count < 0:
            return False
        changes += count
        if changes > 1500:
            return False
    return True


def _approved(api, number, head):
    # Owner-authored consent bound to the exact current PR commit.
    # A changed PR head invalidates approval; no fuzzy textual matching.
    replies = _list(api, f"/repos/{REPO}/issues/{number}/comments")
    exact = MARKER + head
    return any(
        isinstance(c, dict)
        and c.get("user", {}).get("login") == OWNER
        and isinstance(c.get("body"), str)
        and exact in c["body"].splitlines()
        for c in replies
    )


def _green(api, sha, phone):
    runs = _list(api, f"/repos/{REPO}/actions/runs?" +
                 urlencode({"head_sha": sha}))
    found = {}
    required = dict(REQUIRED)
    if phone:
        required[OWNER_READ[0]] = OWNER_READ[1]
    for run in runs:
        if not isinstance(run, dict) or run.get("head_sha") != sha:
            continue
        if (run.get("event") not in ("pull_request", "push", "workflow_dispatch")
                or run.get("status") != "completed"
                or run.get("conclusion") != "success"
                or run.get("head_repository", {}).get("full_name") != REPO):
            continue
        name, path = run.get("name"), run.get("path")
        if name in required and isinstance(path, str):
            if path.split("@", 1)[0] == required[name]:
                found[name] = True
    return set(found) == set(required)


def candidate(api, pr):
    if not isinstance(pr, dict) or pr.get("draft") is not False:
        return False, "draft"
    number = pr.get("number")
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    sha = head.get("sha")
    if (type(number) is not int or not isinstance(sha, str)
            or not HEX40.fullmatch(sha)
            or head.get("repo", {}).get("full_name") != REPO
            or base.get("ref") != RELEASE):
        return False, "scope"
    if not _approved(api, number, sha):
        return False, "unapproved_sha"
    current = api.call("GET", f"/repos/{REPO}/pulls/{number}")
    if (current.get("head", {}).get("sha") != sha
            or current.get("base", {}).get("ref") != RELEASE
            or current.get("draft") is not False
            or current.get("mergeable") is not True
            or current.get("mergeable_state") != "clean"):
        return False, "stale_or_conflict"
    compare = api.call("GET", f"/repos/{REPO}/compare/" +
                       base["sha"] + "..." + sha)
    if (compare.get("status") != "ahead" or
            compare.get("behind_by") != 0 or
            compare.get("base_commit", {}).get("sha") != base["sha"]):
        return False, "non_fast_forward"
    files = _list(api, f"/repos/{REPO}/pulls/{number}/files")
    if not _safe_files(files):
        return False, "review_only_paths"
    phone = any(x["filename"] in PHONE_PATHS for x in files)
    if not _green(api, sha, phone):
        return False, "missing_exact_sha_ci"
    # Final re-read protects against synchronizing new code between review
    # and merge; GitHub PUT /merge also receives exact expected head SHA.
    latest = api.call("GET", f"/repos/{REPO}/pulls/{number}")
    if (latest.get("head", {}).get("sha") != sha or
            latest.get("base", {}).get("sha") != base["sha"] or
            latest.get("mergeable") is not True):
        return False, "head_or_release_moved"
    return True, "approved"


def run(api, *, execute=False):
    prs = _list(api, f"/repos/{REPO}/pulls?" + urlencode({
        "state": "open", "base": RELEASE, "direction": "asc", "sort": "created"}))
    results = []
    for pr in prs:
        number = pr.get("number")
        # No raw PR descriptions are logged. User content is not instructions.
        ok, reason = candidate(api, pr)
        results.append({"pr": number, "status": reason})
        if ok:
            if execute:
                response = api.call("PUT", f"/repos/{REPO}/pulls/{number}/merge",
                                    {"sha": pr["head"]["sha"], "merge_method": "merge",
                                     "commit_title": f"Integrate reviewed V13 PR #{number}"})
                if response.get("merged") is not True:
                    raise QueueError("GitHub refused reviewed merge")
                results[-1]["status"] = "merged"
                results[-1]["release_commit"] = response.get("sha")
            # One per run; after any merge the other PRs need fresh ancestry
            # and CI checks. Never auto-update phone from this workflow.
            break
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="V13 SHA-bound CI release queue")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if os.getenv("GITHUB_REPOSITORY") != REPO:
        raise QueueError("repository identity mismatch")
    api = GitHub(os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"))
    result = run(api, execute=args.execute)
    print(json.dumps({"schema": "v13.release-queue/1",
                      "mode": "execute" if args.execute else "dry_run",
                      "results": result}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (QueueError, OSError, ValueError) as error:
        print(json.dumps({"status": "BLOCKED",
                          "error_code": type(error).__name__}))
        sys.exit(2)

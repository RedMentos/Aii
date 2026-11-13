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
READY_LABEL = "v13-release-ready"
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
ADDITIVE_CHECK = ("V13 safe additive candidate tests",
                  ".github/workflows/v13-safe-additive-candidate.yml")
RELEASE_GATES = tuple(REQUIRED.values()) + (OWNER_READ[1],)
# Narrow fully unattended lane authorized by the owner: new inert modules,
# matching new regression tests and no installed runtime/permission/weight edit.
INERT_MODULE = re.compile(r"v13/code/v13/[a-z][a-z0-9_]*\\.py\\Z")
INERT_TEST = re.compile(r"v13/code/tests/test_[a-z0-9_]+\\.py\\Z")
INERT_HANDOFF = re.compile(r"v13/code/docs/handoffs/[A-Za-z0-9_.-]+\\.md\\Z")
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
            payload = response.read()
            # GitHub returns HTTP 204/no body for workflow_dispatch.
            return json.loads(payload) if payload else {}


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
        # A scheduled bot may import brand-new, inert organ modules, but it
        # must NEVER rewrite installed runtime/permission/update Python code.
        # Existing runtime modules, installer scripts, model specs and active
        # integration policy always require direct Boss merge and device gates.
        if (name.startswith("v13/code/v13/") and status != "added") or (
                name.startswith("v13/code/scripts/")) or (
                name.startswith("v13/code/specs/")):
            return False
        count = item.get("changes")
        if type(count) is not int or count < 0:
            return False
        changes += count
        if changes > 1500:
            return False
    return True


def _safe_additive(pr, files):
    """Only owner-created, not-yet-imported and strictly additive research code.

    This lane is intentionally independent of any prompt-in-PR-body: no model
    can grant itself tool, age, network or weight-update permissions here.
    Draft PRs are eligible only for this narrow checked/inert path.
    """
    if ((pr.get("user") or {}).get("login") != OWNER
            or not isinstance(files, list) or not 2 <= len(files) <= 20):
        return False
    modules = tests = changes = 0
    for row in files:
        if not isinstance(row, dict) or row.get("status") != "added":
            return False
        name = row.get("filename")
        c = row.get("changes")
        if type(c) is not int or c < 1:
            return False
        changes += c
        if changes > 650:
            return False
        if not isinstance(name, str):
            return False
        if INERT_MODULE.fullmatch(name):
            modules += 1
        elif INERT_TEST.fullmatch(name):
            tests += 1
        elif INERT_HANDOFF.fullmatch(name):
            pass
        else:
            return False
    return 1 <= modules <= 8 and 1 <= tests <= 12


def _approved(api, number, head):
    # Owner-authored consent bound to the exact current PR commit.
    # A changed PR head invalidates approval; no fuzzy textual matching.
    replies = _list(api, f"/repos/{REPO}/issues/{number}/comments")
    exact = MARKER + head
    return any(
        isinstance(c, dict)
        and (c.get("user") or {}).get("login") == OWNER
        and isinstance(c.get("body"), str)
        and exact in c["body"].splitlines()
        for c in replies
    )


def _green(api, sha, phone, additive=False):
    runs = []
    for page in range(1, 5):
        data = api.call("GET", f"/repos/{REPO}/actions/runs?" +
                        urlencode({"head_sha": sha, "per_page": 100, "page": page}))
        part = data.get("workflow_runs") if isinstance(data, dict) else None
        if not isinstance(part, list):
            raise QueueError("invalid GitHub workflow listing")
        runs.extend(part)
        if len(part) < 100:
            break
    else:
        raise QueueError("too many CI runs for a candidate SHA")
    found = {}
    required = dict(REQUIRED)
    if phone:
        required[OWNER_READ[0]] = OWNER_READ[1]
    if additive:
        required[ADDITIVE_CHECK[0]] = ADDITIVE_CHECK[1]
    for run in runs:
        if not isinstance(run, dict) or run.get("head_sha") != sha:
            continue
        if (run.get("event") not in ("pull_request", "push", "workflow_dispatch")
                or run.get("status") != "completed"
                or run.get("conclusion") != "success"
                or (run.get("head_repository") or {}).get("full_name") != REPO):
            continue
        name, path = run.get("name"), run.get("path")
        if name in required and isinstance(path, str):
            if path.split("@", 1)[0] == required[name]:
                found[name] = True
    return set(found) == set(required)


def candidate(api, pr):
    if not isinstance(pr, dict):
        return False, "invalid"
    number = pr.get("number")
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    sha = head.get("sha")
    if (type(number) is not int or not isinstance(sha, str)
            or not HEX40.fullmatch(sha)
            or (head.get("repo") or {}).get("full_name") != REPO
            or base.get("ref") != RELEASE):
        return False, "scope"
    files = _list(api, f"/repos/{REPO}/pulls/{number}/files")
    if not _safe_files(files):
        return False, "review_only_paths"
    auto = _safe_additive(pr, files)
    manual = (not pr.get("draft") and _approved(api, number, sha))
    if not (manual or auto):
        return False, "unapproved_or_incomplete"
    current = api.call("GET", f"/repos/{REPO}/pulls/{number}")
    if (current.get("head", {}).get("sha") != sha
            or current.get("base", {}).get("ref") != RELEASE
            or current.get("draft") != pr.get("draft")
            or current.get("mergeable") is not True
            or current.get("mergeable_state") not in
               (("clean", "draft") if auto else ("clean",))):
        return False, "stale_or_conflict"
    if not auto and pr.get("draft") is not False:
        return False, "draft"
    compare = api.call("GET", f"/repos/{REPO}/compare/" +
                       base["sha"] + "..." + sha)
    # A strictly additive change may be on an older release ancestor: the
    # current GitHub mergeability check, not fast-forward ancestry, governs
    # compatibility. Existing-runtime edits remain strict fast-forward only.
    if (compare.get("status") == "ahead"
            and compare.get("behind_by") == 0
            and (compare.get("base_commit") or {}).get("sha") == base["sha"]):
        pass
    elif not (auto and compare.get("status") == "diverged"
              and type(compare.get("ahead_by")) is int
              and compare["ahead_by"] > 0
              and type(compare.get("behind_by")) is int
              and 0 < compare["behind_by"] <= 1500):
        return False, "non_fast_forward"
    phone = any(x["filename"] in PHONE_PATHS for x in files)
    if not _green(api, sha, phone, additive=auto):
        return False, "missing_exact_sha_ci"
    latest = api.call("GET", f"/repos/{REPO}/pulls/{number}")
    if (latest.get("head", {}).get("sha") != sha
            or latest.get("base", {}).get("sha") != base["sha"]
            or latest.get("mergeable") is not True):
        return False, "head_or_release_moved"
    return True, "safe_additive" if auto else "owner_approved"


def _release_tip(api):
    ref = api.call("GET", f"/repos/{REPO}/git/ref/heads/{RELEASE}")
    sha = (ref.get("object") or {}).get("sha") if isinstance(ref, dict) else None
    if not isinstance(sha, str) or not HEX40.fullmatch(sha):
        raise QueueError("release head cannot be verified")
    return sha


def _post_merge_ci(api, sha):
    """GITHUB_TOKEN merge does not fire push workflows: explicitly dispatch.

    Workflows are also registered on default branch; dispatch at the fixed
    release ref. The phone checks three successes *for the exact release SHA*.
    If Boss races the queue, fail closed and let a later cycle repair the tip.
    """
    if _release_tip(api) != sha:
        raise QueueError("release changed before trusted CI dispatch")
    dispatched = []
    for workflow in RELEASE_GATES:
        # Each trusted workflow exists on main AND the release branch.
        name = workflow.rsplit("/", 1)[-1]
        api.call("POST", f"/repos/{REPO}/actions/workflows/{name}/dispatches",
                 {"ref": RELEASE})
        dispatched.append(name)
    return dispatched


def run(api, *, execute=False):
    # Do not rely on a human-operated label nobody sets. Examine the current
    # phone-release PR list, but the actual unattended subset is *only*
    # new modules+new tests with a specific green read-only CI check.
    issues = _list(api, f"/repos/{REPO}/issues?" + urlencode({
        "state": "open", "labels": READY_LABEL,
        "direction": "asc", "sort": "created"}))
    prs = _list(api, f"/repos/{REPO}/pulls?" + urlencode({
        "state": "open", "base": RELEASE, "direction": "asc", "sort": "created"}))
    ordered, seen = [], set()
    for issue in issues:
        if not isinstance(issue, dict) or "pull_request" not in issue:
            continue
        number = issue.get("number")
        if type(number) is int and number not in seen:
            ordered.append(number); seen.add(number)
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        number = pr.get("number")
        if type(number) is int and number not in seen:
            ordered.append(number); seen.add(number)
    results = []
    for number in ordered:
        pr = api.call("GET", f"/repos/{REPO}/pulls/{number}")
        if not isinstance(pr, dict):
            continue
        ok, reason = candidate(api, pr)
        # No sensitive PR descriptions or private device details in Actions.
        results.append({"pr": number, "status": reason})
        if ok:
            if execute:
                response = api.call("PUT", f"/repos/{REPO}/pulls/{number}/merge",
                                    {"sha": pr["head"]["sha"],
                                     "merge_method": "merge",
                                     "commit_title": f"Integrate checked V13 PR #{number}"})
                if response.get("merged") is not True:
                    raise QueueError("GitHub refused checked merge")
                release_sha = response.get("sha")
                if not isinstance(release_sha, str) or not HEX40.fullmatch(release_sha):
                    raise QueueError("merge response missing release commit")
                results[-1]["status"] = "merged"
                results[-1]["release_commit"] = release_sha
                results[-1]["ci_dispatched"] = _post_merge_ci(api, release_sha)
            # At most one merge per cycle. Remaining PRs must see the new
            # branch HEAD; bot never enables auto-update on the phone.
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

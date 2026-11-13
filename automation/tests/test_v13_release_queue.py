"""Offline proofs for unattended inert-code merging and exact release CI repair."""
import copy
import unittest
from unittest import mock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from automation import v13_release_queue as q

SHA = "a" * 40
BASE = "b" * 40
MERGED = "c" * 40


def pr(number=1):
    return {"number": number, "draft": False, "mergeable": True,
            "mergeable_state": "clean",
            "head": {"sha": SHA, "repo": {"full_name": q.REPO}},
            "base": {"sha": BASE, "ref": q.RELEASE}}


def success(name, path, sha=SHA):
    return {"name": name, "path": path + "@refs/heads/release",
            "head_sha": sha, "event": "push", "status": "completed",
            "conclusion": "success", "head_repository": {"full_name": q.REPO}}


class FakeGitHub:
    def __init__(self):
        self.pr = pr()
        self.comments = [{"user": {"login": q.OWNER},
                          "body": q.MARKER + SHA}]
        self.files = [{"filename": "v13/code/v13/a5_bridge.py",
                       "status": "added", "changes": 42}]
        self.runs = [success(k, v) for k, v in q.REQUIRED.items()]
        self.release_runs = [
            success(k, v, MERGED) for k, v in
            [*q.REQUIRED.items(), q.OWNER_READ]]
        self.issues = [{"number": 1, "pull_request": {"url": "exists"}}]
        self.prs = []
        self.compare = {"status": "ahead", "ahead_by": 1,
                        "behind_by": 0, "base_commit": {"sha": BASE}}
        self.merge_calls = []
        self.dispatches = []
        self.release_sha = MERGED

    def call(self, method, path, data=None):
        parsed = urlsplit(path)
        route = parsed.path
        if method == "POST" and "/actions/workflows/" in route and route.endswith("/dispatches"):
            self.dispatches.append((route, data))
            return {}
        if method == "PUT" and route.endswith("/merge"):
            self.merge_calls.append((route, data))
            return {"merged": True, "sha": MERGED}
        if route.startswith(f"/repos/{q.REPO}/git/ref/heads/"):
            return {"object": {"sha": self.release_sha}}
        if route == f"/repos/{q.REPO}/issues":
            return copy.deepcopy(self.issues)
        if route == f"/repos/{q.REPO}/pulls":
            return copy.deepcopy(self.prs)
        if route.endswith("/files") and "/pulls/" in route:
            return copy.deepcopy(self.files)
        if route.endswith("/comments") and "/issues/" in route:
            return copy.deepcopy(self.comments)
        if "/pulls/" in route:
            return copy.deepcopy(self.pr)
        if "/compare/" in route:
            return copy.deepcopy(self.compare)
        if route == f"/repos/{q.REPO}/actions/runs":
            sha = parse_qs(parsed.query).get("head_sha", [""])[0]
            return {"workflow_runs": copy.deepcopy(
                self.release_runs if sha == MERGED else self.runs)}
        raise AssertionError((method, path, data))


def additive(api, draft=True):
    api.pr["user"] = {"login": q.OWNER}
    api.pr["draft"] = draft
    api.pr["mergeable_state"] = "draft" if draft else "clean"
    api.files = [
        {"filename": "v13/code/v13/world_candidate.py",
         "status": "added", "changes": 72},
        {"filename": "v13/code/tests/test_world_candidate.py",
         "status": "added", "changes": 88}]
    api.runs.append(success(*q.ADDITIVE_CHECK))
    api.issues = []
    api.prs = [{"number": 1}]
    api.comments = []
    api.compare = {"status": "diverged", "ahead_by": 2,
                   "behind_by": 7, "base_commit": {"sha": BASE}}


class QueueTests(unittest.TestCase):
    def test_explicit_owner_reviewed_head_merges_and_dispatches_3_gates(self):
        api = FakeGitHub()
        result = q.run(api, execute=True)
        self.assertEqual(result[0]["status"], "merged")
        self.assertEqual(result[0]["release_commit"], MERGED)
        self.assertEqual(len(api.merge_calls), 1)
        self.assertEqual(api.merge_calls[0][1]["sha"], SHA)
        self.assertEqual(len(api.dispatches), len(q.RELEASE_GATES))
        self.assertTrue(all(d["ref"] == q.RELEASE for _, d in api.dispatches))

    def test_dry_run_never_changes_repo_or_dispatches(self):
        api = FakeGitHub()
        self.assertEqual(q.run(api)[0]["status"], "owner_approved")
        self.assertEqual(api.merge_calls, [])
        self.assertEqual(api.dispatches, [])

    def test_unlabelled_unapproved_pr_is_inspected_not_merged(self):
        api = FakeGitHub()
        api.issues = []
        api.prs = [{"number": 1}]
        api.comments = []
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "unapproved_or_incomplete")
        self.assertFalse(api.merge_calls)

    def test_new_module_and_new_test_draft_auto_import_even_if_behind(self):
        api = FakeGitHub()
        additive(api)
        out = q.run(api, execute=True)
        self.assertEqual(out[0]["status"], "merged")
        self.assertEqual(len(api.merge_calls), 1)
        self.assertEqual(len(api.dispatches), 3)

    def test_draft_without_new_test_cannot_auto_merge(self):
        api = FakeGitHub()
        additive(api)
        api.files.pop()
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "unapproved_or_incomplete")
        self.assertFalse(api.merge_calls)

    def test_new_module_without_additive_ci_is_blocked(self):
        api = FakeGitHub()
        additive(api)
        api.runs.pop()
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "missing_exact_sha_ci")
        self.assertFalse(api.merge_calls)

    def test_non_owner_draft_cannot_auto_merge(self):
        api = FakeGitHub()
        additive(api)
        api.pr["user"]["login"] = "outsider"
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "unapproved_or_incomplete")
        self.assertFalse(api.merge_calls)

    def test_runtime_paths_never_use_auto_lane(self):
        for path in (
                "v13/code/v13/runtime.py",
                "v13/code/v13/android_outcomes.py",
                "v13/code/v13/owner_read_bridge.py",
                "v13/code/v13/exec.py",
                "v13/code/v13/__init__.py",
                "v13/code/scripts/termux_start.sh",
                "v13/code/specs/models.json",
                "v13/code/docs/canon/locked.md",
                ".github/workflows/evil.yml",
                "v13/code/v13/../../outside.py"):
            with self.subTest(path=path):
                api = FakeGitHub()
                additive(api)
                api.files[0]["filename"] = path
                api.files[0]["status"] = "modified"
                self.assertNotEqual(q.run(api, execute=True)[0]["status"], "merged")
                self.assertFalse(api.merge_calls)

    def test_modified_runtime_only_owner_label_does_not_bypass_path_gate(self):
        api = FakeGitHub()
        api.files[0]["filename"] = "v13/code/v13/runtime.py"
        api.files[0]["status"] = "modified"
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "review_only_paths")
        self.assertFalse(api.merge_calls)

    def test_stale_approval_sha_is_not_accepted(self):
        api = FakeGitHub()
        api.comments[0]["body"] = q.MARKER + ("1" * 40)
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "unapproved_or_incomplete")
        self.assertFalse(api.merge_calls)

    def test_approval_line_needs_exact_boundary(self):
        api = FakeGitHub()
        api.comments[0]["body"] = "PREPEND" + q.MARKER + SHA
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "unapproved_or_incomplete")

    def test_manual_source_divergence_is_blocked(self):
        api = FakeGitHub()
        api.compare["status"] = "diverged"
        api.compare["behind_by"] = 3
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "non_fast_forward")

    def test_dirty_conflict_is_blocked_even_for_additive(self):
        api = FakeGitHub()
        additive(api)
        api.pr["mergeable_state"] = "dirty"
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "stale_or_conflict")

    def test_missing_base_sha_or_changed_head_blocks(self):
        api = FakeGitHub()
        api.pr["base"]["ref"] = "jepa/other-branch"
        self.assertEqual(q.run(api, execute=True)[0]["status"], "scope")
        api = FakeGitHub()
        api.pr["head"]["sha"] = "z" * 40
        self.assertEqual(q.run(api, execute=True)[0]["status"], "scope")

    def test_only_one_merge_per_cycle(self):
        api = FakeGitHub()
        api.issues = [{"number": 1, "pull_request": {}},
                      {"number": 2, "pull_request": {}}]
        out = q.run(api, execute=True)
        self.assertEqual(len(api.merge_calls), 1)
        self.assertEqual(out[0]["status"], "merged")

    def test_no_missing_release_gate_never_re_dispatches(self):
        api = FakeGitHub()
        api.issues = []
        api.prs = []
        self.assertEqual(q.run(api, execute=True), [])
        self.assertEqual(api.dispatches, [])

    def test_recovery_dispatches_only_missing_exact_release_gates(self):
        api = FakeGitHub()
        api.issues = []
        api.prs = []
        api.release_runs = api.release_runs[:1]
        out = q.run(api, execute=True)
        self.assertEqual(out[-1]["release_ci"]["status"],
                         "DISPATCHED_MISSING_RELEASE_CI")
        self.assertEqual(len(api.dispatches), 2)

    def test_failed_release_gate_never_retries_blindly(self):
        api = FakeGitHub()
        api.issues = []
        api.prs = []
        api.release_runs[0]["conclusion"] = "failure"
        out = q.run(api, execute=True)
        self.assertEqual(out[-1]["release_ci"]["status"], "FAILED_RELEASE_CI")
        self.assertEqual(api.dispatches, [])

    def test_pr_events_scan_only_recent_eight_unlabelled_candidates(self):
        api = FakeGitHub()
        api.issues = []
        api.prs = [{"number": i} for i in range(20)]
        api.comments = []
        result = q.run(api)
        self.assertEqual(len(result), 8)
        self.assertEqual(api.merge_calls, [])

    def test_github_rate_limit_retry_has_bounded_sleep_and_no_body_leak(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"ok":true}'
        rate = HTTPError("https://api.github.com", 429, "rate", {"Retry-After":"0"}, None)
        with mock.patch.object(q, "urlopen", side_effect=[rate, Response()]) as getter, \
             mock.patch.object(q.time, "sleep") as sleeper:
            result = q.GitHub("private-test-token").call(
                "GET", f"/repos/{q.REPO}/pulls/1")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(getter.call_count, 2)
        self.assertEqual(sleeper.call_args.args[0], 1.)

    def test_permanent_403_does_not_retry_or_print_payload(self):
        denied = HTTPError("https://api.github.com", 403, "private", {}, None)
        with mock.patch.object(q, "urlopen", side_effect=denied) as getter:
            with self.assertRaisesRegex(q.QueueError, "GitHub_HTTP_403"):
                q.GitHub("private-test-token").call(
                    "GET", f"/repos/{q.REPO}/pulls/1")
        self.assertEqual(getter.call_count, 1)

    def test_release_tip_changed_cannot_dispatch_stale_merge(self):
        api = FakeGitHub()
        api.release_sha = "e" * 40
        with self.assertRaises(q.QueueError):
            q.run(api, execute=True)
        self.assertEqual(len(api.merge_calls), 1)
        self.assertEqual(api.dispatches, [])


if __name__ == "__main__":
    unittest.main()

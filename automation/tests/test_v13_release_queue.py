"""Offline review-queue tests. No network, GitHub token, Redmi or model usage."""
import copy
import unittest
from automation import v13_release_queue as q

SHA = "a" * 40
BASE = "b" * 40


def pr(number=1):
    return {"number": number, "draft": False, "mergeable": True,
            "mergeable_state": "clean",
            "head": {"sha": SHA, "repo": {"full_name": q.REPO}},
            "base": {"sha": BASE, "ref": q.RELEASE}}


def success(name, path):
    return {"name": name, "path": path + "@refs/heads/test",
            "head_sha": SHA, "event": "pull_request",
            "status": "completed", "conclusion": "success",
            "head_repository": {"full_name": q.REPO}}


class FakeGitHub:
    def __init__(self):
        self.pr = pr()
        self.comments = [{"user": {"login": q.OWNER},
                          "body": q.MARKER + SHA}]
        self.files = [{"filename": "v13/code/v13/a5_bridge.py",
                       "status": "added", "changes": 42}]
        self.runs = [success(k, v) for k, v in q.REQUIRED.items()]
        self.issues = [{"number": 1, "pull_request": {"url": "exists"}}]
        self.merge_calls = []

    def call(self, method, path, data=None):
        if method == "PUT":
            self.merge_calls.append((method, path, data))
            return {"merged": True, "sha": "c" * 40}
        if "/issues?" in path:
            return copy.deepcopy(self.issues)
        if "/pulls/" in path and path.endswith("/files"):
            return copy.deepcopy(self.files)
        if "/issues/" in path and path.endswith("/comments"):
            return copy.deepcopy(self.comments)
        if "/pulls/" in path:
            return copy.deepcopy(self.pr)
        if "/compare/" in path:
            return {"status": "ahead", "behind_by": 0,
                    "base_commit": {"sha": BASE}}
        if "/actions/runs?" in path:
            return {"workflow_runs": copy.deepcopy(self.runs)}
        raise AssertionError((method, path))


class QueueTests(unittest.TestCase):
    def test_owner_approved_exact_sha_with_ci_merges_one(self):
        api = FakeGitHub()
        result = q.run(api, execute=True)
        self.assertEqual(result[0]["status"], "merged")
        self.assertEqual(result[0]["release_commit"], "c" * 40)
        self.assertEqual(len(api.merge_calls), 1)
        self.assertEqual(api.merge_calls[0][2]["sha"], SHA)

    def test_dry_run_does_not_write_release(self):
        api = FakeGitHub()
        self.assertEqual(q.run(api), [{"pr": 1, "status": "approved"}])
        self.assertEqual(api.merge_calls, [])

    def test_unlabelled_prs_are_not_even_examined(self):
        api = FakeGitHub()
        api.issues = []
        self.assertEqual(q.run(api, execute=True), [])
        self.assertFalse(api.merge_calls)

    def test_modified_sha_invalidates_old_owner_approval(self):
        api = FakeGitHub()
        api.comments[0]["body"] = q.MARKER + ("1" * 40)
        self.assertEqual(q.run(api, execute=True)[0]["status"], "unapproved_sha")
        self.assertEqual(api.merge_calls, [])

    def test_not_an_owner_comment_is_not_approval(self):
        api = FakeGitHub()
        api.comments[0]["user"]["login"] = "attacker"
        self.assertEqual(q.run(api, execute=True)[0]["status"], "unapproved_sha")

    def test_stacked_or_diverged_source_is_not_auto_merged(self):
        api = FakeGitHub()
        api.pr["base"]["ref"] = "jepa/other-branch"
        self.assertEqual(q.run(api, execute=True)[0]["status"], "scope")
        self.assertEqual(api.merge_calls, [])

    def test_runtime_permission_updater_requires_manual_review(self):
        for path in (
            "v13/code/v13/runtime_deploy.py",
            "v13/code/v13/remote_maintenance_bridge.py",
            ".github/workflows/evil.yml",
            "v13/code/docs/canon/frozen.md",
            "v13/code/specs/models.json",
            "v13/code/models/weights.gguf",
            "v13/code/v13/../../outside.py",
        ):
            with self.subTest(path=path):
                api = FakeGitHub()
                api.files[0]["filename"] = path
                self.assertEqual(q.run(api, execute=True)[0]["status"],
                                 "review_only_paths")
                self.assertFalse(api.merge_calls)

    def test_missing_or_failed_exact_sha_ci_blocks(self):
        api = FakeGitHub()
        api.runs = api.runs[:-1]
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "missing_exact_sha_ci")
        api = FakeGitHub()
        api.runs[0]["head_sha"] = "c" * 40
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "missing_exact_sha_ci")
        api = FakeGitHub()
        api.runs[0]["event"] = "schedule"
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "missing_exact_sha_ci")

    def test_base_movement_or_conflicts_block(self):
        api = FakeGitHub()
        api.pr["mergeable_state"] = "dirty"
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "stale_or_conflict")

    def test_only_one_candidate_integrated_per_cycle(self):
        api = FakeGitHub()
        api.issues = [{"number": 1, "pull_request": {}},
                      {"number": 2, "pull_request": {}}]
        result = q.run(api, execute=True)
        self.assertEqual(result, [{"pr": 1, "status": "merged",
                                   "release_commit": "c" * 40}])
        self.assertEqual(len(api.merge_calls), 1)

    def test_approval_marker_has_exact_line_boundary(self):
        api = FakeGitHub()
        api.comments[0]["body"] = "UNTRUSTED:" + q.MARKER + SHA
        self.assertEqual(q.run(api, execute=True)[0]["status"],
                         "unapproved_sha")


if __name__ == "__main__":
    unittest.main()

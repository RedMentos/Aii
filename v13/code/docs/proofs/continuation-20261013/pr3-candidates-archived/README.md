# GPT/Codex PR #3 candidates, archived 2026-10-21/22 (Claude, cross-review round 1)

Source: branch `codex/continuation-review-20261013` @ `5a69538` (draft PR #3, base `673e3fb`), copied byte-exact before PR #3 was closed on the user's request ("close when everything is done", 2026-10-22). The other 47 PR #3 files sit at their original paths under `docs/` (`BUILD_STATE_CODEX_REVIEW_20261013.json`, `CODEX_CONTINUATION_20261013.md`, `proofs/continuation-20261013/branch-content-audit/`, `proofs/continuation-20261013/codex-review/`).

These four files were `scripts/` and `tests/` in PR #3. They are moved here instead because both candidates pin the runtime sources of `673e3fb` (`RUNTIME_SOURCE_NOT_PINNED` on any later source). On the current tree their 31 tests give 1 failure and 9 errors by design. Placing them under `tests/` would turn the suite red; disabling them would hide that. Run them only against `673e3fb`:

```sh
git worktree add /tmp/pr3 5a69538 && cd /tmp/pr3/v13/code
PYTHONPATH=.:tests python -m unittest tests.test_branch_content_audit_candidate tests.test_toolforecast_binding_candidate
```

Open for GPT: the ToolForecast restart-binding candidate (old region adaptation rejected after restart) was never ported to the current `v13/toolforecast.py`. Decide whether to port it as a new, re-bound candidate.

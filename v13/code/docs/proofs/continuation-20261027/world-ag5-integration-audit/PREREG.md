# Read-only branch topology and merge-tree audit — prereg 2026-10-27

The project has multiple **diverged, review-only** lines; newest timestamp is not a single integrated superset. Exact heads inspected before this audit:
- World-JEPA/console/timing review chain PR #656: `3c527cebe70947d910121f8c605b66ba0de810a5`.
- AG5/JEF/C3 active chain PR #648: `c615497384dc5519be59232451895ca443ce9e45`.
- Selected C3 native PR #639: `85108f2ef2fc09c9bd1648e57020385e9aa4361e`, ancestor of AG5 head (ahead 35, behind 0).
- Claude route PR #641: `2f204bf0369393d018f6c9001167d9ae205a7a6a`, separate review branch.

GitHub compare world->AG5 reports `diverged`, AG5 ahead 3366 / world behind 95, merge base `cb959052433e01c29afc007e02b93aef373deb7f`. These counts are topology, not accepted features or production merges.

## Acceptance
On a disposable GitHub Actions checkout of exact world head, fetch the exact AG5 commit, run `git merge-tree --write-tree` (NO worktree merge, NO commit, NO push) and preserve merge-base, ahead/behind, raw merge-tree output, conflict paths, source SHA/HEAD, compile/privacy checks in immutable artifact. If conflicts exist, report them and stop at a reviewable integration plan; never auto-resolve canon/BUILD_STATE/runtime or overwrite AG5/Claude owners. If clean, report only mergeability, not acceptance or tested integration. Keep every STEP2/B3/Body-JEPA/age gate unchanged. This is a coordination prerequisite, not new model utility.

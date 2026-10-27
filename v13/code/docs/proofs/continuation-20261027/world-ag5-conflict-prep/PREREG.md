# World/AG5 two-file conflict capture — prereg 2026-10-27

Base PR #657 exact `ab206487ae7799963de0ea84058b96b1f4bdc9a2`, other AG5 PR #648 exact `c615497384dc5519be59232451895ca443ce9e45`. Read-only merge-tree Actions `40451319263` found exactly two content conflicts: `scripts/handy_pflicht.py` and `v13/operator.py`; no branch was modified.

Next run in a disposable GitHub Actions checkout: `git merge --no-commit --no-ff` solely to capture Git conflict-marker worktree versions and base/world/AG5 stage blobs for these two files. Record exact HEAD/other/merge-base, SHA256 of all six original blobs and two conflict-marker versions, and the raw merge stderr/exit. Abort merge, verify clean worktree, upload immutable raw artifact. No push, no merge commit, no automatic resolution. Only after inspecting all versions may a new candidate integration branch be constructed and tested. Preserve both policy/approval gates and all organ routes. No source/model/seed/age changes.

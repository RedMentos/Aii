# CI harness correction before rerun — 2026-10-27

First disposable capture Actions `40451696368` at `4131056fdf4b4a8813b77f13b926df89b7a56677` failed **before merge**: `git merge --no-commit` required a local committer identity on the fresh runner (exit128), so `git merge --abort` also exited128. No merge was started, no source changed, no valid conflict-marker files. Original failed ZIP preserved; do not relabel as conflict evidence.

Narrow correction: pass temporary command-scoped `git -c user.name='V13 Read-only Merge Probe' -c user.email='probe@localhost.invalid' merge --no-commit --no-ff`. This does not create a commit, change Git config, push or contact anyone. Enforce merge exit1, abort exit0, exactly two expected conflict paths, nonempty stage/conflict files and clean post-abort worktree. No changes to source/acceptance.

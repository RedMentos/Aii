# AG5/World two-conflict integration candidate — prereg 2026-10-27

Review-only branch `codex/automation11-ag5-world-merge-candidate-20261027` from World PR #664 exact `aab74aa900bfbd767f2983ba40a16fc0b8b95a3b`. Other parent **AG5 PR #648** exact `c615497384dc5519be59232451895ca443ce9e45`. This follows the independent two-conflict capture PR #658 (base World `ab206487...`); because the World branch has since advanced, verify the conflict set again rather than assuming it is unchanged. No AG5 owner branch, World owner branch or main may be overwritten.

## Candidate resolution locked before merge attempt

Perform an **uncommitted, disposable** two-parent merge in CI, with command-scoped Git committer identity and no network provisioning beyond exact GitHub checkout/fetch. Enforce exactly the two previously identified content conflicts `v13/code/scripts/handy_pflicht.py` and `v13/code/v13/operator.py`; if new conflicts appear, fail and preserve raw, do not auto-resolve extras.

1. `handy_pflicht.py`: retain **AG5 V2** whole file, including atomic resume, source binding, interrupted-run retention, evidence validation, process-group cleanup. World V1 is not allowed to regress these.
2. `operator.py`: retain **AG5 version** as baseline (bounded chat/search/export, English language selection, idle/config/effort locks, Context OS and newer commands). Graft exactly World additions: `:world shadow` read-only SHA-bound probe with existing local TTY/READ_LOCAL/prohibition/notaus/announce gates **before any file read**; `:ersetze` route supersession; `:effort detail|gist` single-body mode under the AG5 idle lock; corresponding help lines and `atomic_write` import only if needed by retained code. Do not downgrade AG5 safety controls.
3. All nonconflicting changes from BOTH parents must survive Git's normal merge, including new World-JEPA and AG5 learning/context code. Do not rebase AG5, cherry-pick partial source or replace the binding blueprint.

## Required evidence before a merge commit

Capture exact parent SHAs, common ancestor, conflict paths, stage2/stage3 SHA, resolution SHA, complete merge diff, no unresolved markers, no missing tracked files, and candidate tree SHA. Compile and run AG5 and World focused tests (operator world gate, route supersession, single-body effort, handy resume, new World scripts) and the broad software suite. Compare critical AG5 and World behavior with assertions, preserving negative results. Test scripts must not download models or claim Redmi/native execution. Upload raw tests, exit codes, privacy scan and candidate patch to GitHub Actions artifact. A failing merge/test is a retained RED and **not** a reason to overwrite another branch.

No remote two-parent merge commit until this candidate passes and the exact resolution has independent review. Any later commit must be on a new review branch with both parents and no force push. STEP2 UTILITY_FAIL, B3 L1_FAIL, Body-JEPA UNAVAILABLE, `jepa_weight=0`, Age/approval and whole-system negatives remain.

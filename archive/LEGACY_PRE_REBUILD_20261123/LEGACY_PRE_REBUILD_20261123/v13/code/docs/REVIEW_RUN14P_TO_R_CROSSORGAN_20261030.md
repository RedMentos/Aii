# Run14P–R cross-organ review — 2026-10-30 UTC

Review scope: parent Run14O PR #1331 @ `0867211473912e2ca41725579be2c72e710e177d`; child Run14P PR #1332 @ `49e7eb3edbee83a7717a4d4356df086406a2a817`; child Run14Q PR #1333 @ `b83e19e07c1a662b8b54e98cc99649f95bf48a2e`; child Run14R PR #1334 @ `eb9cc12f5275b2bfb9e3dc03af0988270891708c`. These are review branches, not production merges. No independent external reviewer/agent was available in this run. This scoped file does not overwrite the shared Claude/GPT review document.

## Confirmed evidence and source review

- Run14O parent candidate CI 41115672901 GREEN. No body/native/STEP2 promotion inferred.
- Run14P original RED 41116728497: 18 tests, 9 true cross-language holdout failures, raw SHA256 `5af7029be2e17a960ae8f2d116ad20cc58584afc96f285dd8796c6e0708bfe0c`. Candidate 41116924224: 61/61 SQLite AG12/AG9 tests, pinned source blob `43831251af47dbdd718fa9ee3289955fc7f84a87`, all 5 stages 0. Both ZIPs CRC/inner SHA verified and backed up privately byte-identically.
- Run14Q original RED 41117321284: 13 tests, 3 actual Sleep TTT holdout leaks plus one zero-registry fixture error; preserved. Candidate v1 41117528182: 44 tests, 1 fixture timing failure + 1 missing numpy prerequisite; preserved. Candidate v2 41117744397: 44/44 with isolated `numpy==2.2.6`, 8/8 stages 0, source blobs AG12 `84ca3580c37a00701286d0d9b00d535ee8c3153f`, Sleep `622f3c202c70464c7426e590979428e41f6e50a6`. No Sleep staging is permission to train.
- Run14R original RED 41118121753: 8 tests, 4 real AG6 stage/fit/approval bypasses + 1 counting-trainer expected-status fixture error; preserved. Candidate 41118296402: 52/52 with isolated numpy, 8/8 stages 0, source AG6 blob `2ea853c8517674f22bc551b361a8d96b9c89c9f5`. Approval rechecks under both write transactions. No actual model fit.
- Each candidate workflow ran `python3 v13/code/scripts/public_repo_privacy_scan.py --base <exact-parent> --head HEAD --no-worktree` and `git diff --check <exact-parent> HEAD`; both exited 0. Prereg docs committed before original test-first runs. Source/Canon blobs pinned and verified by `git hash-object` inside CI. Raw ZIPs verified for CRC and all inner SHA256; private Library readback matched downloaded bytes.

## Findings and remaining counterexamples

1. **Open, not waived:** AG6 `gate()` can still create a human approval request if a new holdout suite is registered after fit but before gate. `approve()` now vetoes activation. A new preregistered test could require gate-time rejection to avoid presenting a stale request.
2. **Open, not waived:** AG12/Sleep/AG6 exact normalized prompt digests do not protect paraphrases or future unregistered suite prompts. No semantic generalization claim.
3. **Open, not waived:** Sleep TTT JSONL remains an untrusted staging export; a later consumer must revalidate source/AG12 registry at consumption time. The current export is not a training authorization.
4. **Open, not waived:** AG6 pre-fit guard and approval checks cannot prevent a foreign writer rotating a suite while a long-running optimizer is already fitting. Preserve serialized trainer/coordinator ownership and revalidate before activation.
5. **Open, not waived:** Historical unfiltered full-suite RED, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, jepa_weight=0, Age0 RECORD_ONLY, no Redmi proof, no whole-system completion. Run14R unfiltered full-suite CI 41118615931 was launched; result pending at this review checkpoint.

Next independent work: inspect current active branches before editing; prioritize a measurable Body/C3/Context utility package or a fresh preregistered AG6 gate-time use check, not repeating already-passing focused tests. Keep native heavy jobs serialized and never promote gates from software-only evidence.

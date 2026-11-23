# Core handoff — authenticated Android receipt recovery (2026-11-23)

## Ownership and ancestry

- Owner: Core & Harness
- Parent PR: #2450 — Android ActionIntent / ActionOutcome journal
- Exact parent head: `d09fe4034742679c22f196141abd71204cc74c21`
- Branch: `core/v14-android-receipt-revalidation-20261123-run1`
- Intended PR base: `core/v14-android-action-journal-qa-rebase-20261123-run1`
- This is a security correction stacked on the journal PR, not a release branch or a device deployment.

## Defect addressed

QA found that `_stored_receipt_outcome()` trusted mutable derived status fields after a crash between Store commit and broker finalization. An internally consistent SQLite edit could turn a signed DISPATCHED receipt into USER_DENIED (or the inverse) and then be finalized with `verified=True`. Field consistency did not authenticate the original receipt.

## Implementation

- Preserve the exact ECDSA receipt envelope (body, key id, signature) in the source-bound ActionOutcome packet, together with the verification timestamp.
- Validate the envelope against the derived outcome at initial persistence.
- During local recovery, load only the explicitly pinned local public key; recovery does not require a live companion connection.
- Re-run the P-256 signature verifier against the exact action id, capability and digest. The stored verification timestamp is checked against the signed issued/expires window, so a delayed restart can recover without accepting an expired-at-current-time receipt.
- Compare the freshly authenticated status/consent/evidence fields with the persisted ActionOutcome before broker finalization.
- Preserve receipt-only semantics: observed=false, T8=false, World learning=false. Recovery never redispatches the Android action.

## Regression tests

- Both adversarial directions are covered: signed DISPATCHED -> forged DENIED and signed DENIED -> forged DISPATCHED.
- Tests require signature mismatch rejection, broker remains RECEIPT_CONSUMED, no remote outcome retry, and exactly one companion submission.
- Existing digest-tamper and crash/restart tests remain in the suite.
- The exact workflow now runs for this branch and for PRs stacked on the parent Core branch.

## Evidence boundary

- Local full Aii checkout is unavailable: `/mnt` contains no Aii checkout and `git ls-remote` fails with DNS `Could not resolve host: github.com`. No full LOCAL_LINUX suite is claimed.
- Exact-head GitHub Actions has not yet run for this new branch; pending after push/PR creation.
- Redmi and Android emulator remain unverified for this candidate. No phone command, companion dispatch, APK install, pairing, permission, model, weight or user-data change was performed.
- Parent QA #2356 still has an Android process-restart/System-UI ANR failure; this stacked security fix does not resolve that independent gate.

## Next step

Run exact-head Python 3.13/3.14 Core and staged Runtime CI, fix any failures, then request independent QA/Boss review. Merge only after the parent companion process-restart acceptance is green. No user action is required.


## Run 2 — exact parent-PR integration and verification readback (2026-11-23)

- The security correction is now included directly in existing Core PR #2450, avoiding a second stacked PR. The branch was fast-forwarded from the verified parent head `d09fe4034742679c22f196141abd71204cc74c21`; current PR branch head after follow-up timestamp hardening is `5534b24d55a7efb68283d4b5cb94ea94fa58e5ec`.
- Follow-up hardening rejects non-finite float timestamps without converting arbitrary-size integers to float. The positive crash-recovery test now restarts at local clock 5000 while the signed receipt's validity window is around 1000; it must still recover using the stored, signed-window-bound verification timestamp.
- Exact source readback: signed envelope persistence and signature revalidation are present in `android_outcomes.py` and `android_companion_runtime.py`; both adversarial status-forgery directions are present in `test_android_companion_runtime.py`. The current workflow file was restored byte-identically to the previously green branch version (blob `1331781aafd53b42521c1e8f9ae1a0f54299abba`).
- LOCAL_LINUX synthetic cryptographic reproduction: PASS on CPython 3.13.5 / cryptography 46.0.0. The exact test helper's deterministic P-256 signing construction was reproduced; both signed-status/forged-derived-status directions were rejected, and verification at stored time 1000 passed while current-time verification at 5000 failed as expected. This is a focused cryptographic invariant probe, NOT the project pytest suite or exact production module execution.
- LOCAL_LINUX project suite: BLOCKED / NOT_RUN — no repository checkout is mounted and `git ls-remote` cannot resolve GitHub.
- GitHub Actions: prior exact-head runs `45264814820` (pull_request) and `45264803102` (push) ended `startup_failure` with zero jobs. After restoring the workflow file, the new code head `5534b24` has no associated run yet. The older green #2450 runs `45220123902` and `45220124028` are for parent head `d09fe403` and do not verify this fix. No CI PASS is claimed.
- Creating a separate PR and posting a PR comment both returned GitHub HTTP 403: the connected GitHub account has no verified email address. The correction remains committed on existing PR #2450, so no new PR is required for the current integration path.
- Redmi remains `REDMI_UNVERIFIED`; the last known owner-authenticated receipt was STOPPED_BY_USER. No device command, restart, chat send, update request, permission change, model/weight swap or data mutation was performed.

**Next:** resolve why GitHub Actions creates `startup_failure`/zero-job runs for the updated branch, then obtain exact Python 3.13/3.14 CI and independent QA review. Keep #2450 NOT_RELEASED until its parent Android process-restart/System-UI ANR gate is green. Boss should mirror this Core handoff into the shared `V14_USER_NEXT_ACTION.md`/board; Core does not overwrite the concurrently owned shared board.


## Run 3 — receipt material redaction at the user-facing boundary (2026-11-23)

- Added regression assertions that neither the signed envelope, receipt nonce nor signature appears in the Android poll result or Android history output. The exact signed envelope remains internal to the source-bound Store packet solely for recovery authentication.
- Current Core PR #2450 branch has advanced through the code/test and handoff commits; verify the live PR head before using this checkpoint. The signed-envelope revalidation, expiry-safe recovery and bidirectional status-forgery controls remain present.
- This is a privacy/output-boundary regression, not a device action or proof of Android execution.
- Exact-head Actions remains blocked at workflow startup (BuildFailed / startup_failure, zero jobs); no project pytest result is available. The local cryptographic invariant probe from Run 2 remains the only local PASS.


## Run 4 — final branch/PR/CI readback (2026-11-23)

- Exact current branch and PR #2450 head: `8bc50de8aec7ec4fa8b1e2b9c9f3f0d642b1404d`; PR #2450 remains OPEN, metadata `draft=false`, mergeable=true, base QA head `6dab323f1b59663682d0af65ffbd75c5de489578`. Its description still contains the old “DRAFT” wording; the PR metadata is authoritative for draft state. No release merge has occurred.
- Latest exact-head Actions run `45266675329` is a push run ending `startup_failure`, `path=BuildFailed`, workflow ID `428247013`, zero jobs. Earlier runs `45264814820`, `45264803102`, `45265670309`, `45266269969`, `45266257875` show the same zero-job startup failure. The previous green #2450 checks are only for old head `d09fe403`; no exact-head CI PASS exists.
- Parent QA #2356 is still at `6dab323f`: staged/integrated, Core outcome and Android outcome contract PASS; Android companion process-restart workflow FAIL. This parent gate remains blocking.
- GitHub API explicitly rejected separate PR creation and PR comment creation with HTTP 403 because the connected account has no verified email address. Existing PR #2450 can still be updated through branch commits. This is a user-side account prerequisite for creating additional PRs/comments; do not infer that it caused the separate Actions startup failures.
- Local CPython 3.13.5 synthetic P-256 invariant probe remains PASS for both status-forgery directions and delayed verification timestamp. It is not a project-module pytest run. Full local Aii tests remain BLOCKED by absent checkout and GitHub DNS failure.
- No Redmi/emulator action was taken; REDMI_UNVERIFIED. The last private device receipt remains STOPPED_BY_USER.

**Next:** user should verify at least one email address on the connected GitHub account if further standalone PRs or review comments are required. Separately, investigate the zero-job Actions startup failure and rerun exact Python 3.13/3.14 project tests. Keep PR #2450 unmerged until its exact-head CI and parent Android process-restart gate pass.

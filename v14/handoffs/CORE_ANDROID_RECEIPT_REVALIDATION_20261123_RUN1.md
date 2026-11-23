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

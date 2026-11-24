# Core & Harness — companion SQLite receipt-recovery regression

Date: 2026-11-23
Role: Core & Harness (shared Android companion lane with QA)
Branch: `core/v14-capability-registry-mediaprojection-20261123`
PR: #2406
Code/test head: `dc848768c6797b60c329d5d7485545b579d232f8`
PR base: `core/v14-android-capability-registry-current-qa-20261123` at `41b43cb139d68caf8c459cec668061b4eda6b6db`

## Concrete change

Added `sqliteReceiptWriteFailureRecoversAfterRestartWithoutRedispatch` to `CompanionProviderRecoveryTest.java`.

The test uses a SQLite trigger to inject a durable receipt-write failure for both required recovery transitions:

- `EXECUTING → OUTCOME_UNKNOWN`: the external action was dispatched once; failed receipt persistence must leave the claimed row without a receipt, retain the approval notification, and never dispatch again.
- `DENYING → USER_DENIED`: failed receipt persistence must leave the denial claim recoverable and must not create execution authority.

After dropping the failure trigger and simulating provider restart, the test requires both rows to finalize with receipts, notifications to disappear only after persistence, and a second recovery pass to be idempotent.

No production Android behavior, permissions, model, weights or user data were changed; this commit adds regression coverage only.

## Verification

- LOCAL_LINUX / CPython 3.13.5 / SQLite: PASS for the injected `RAISE(ABORT)` behavior, preservation of both claimed rows, and successful restart-equivalent retry to the two terminal states. This validates SQLite trigger semantics only, not Android Java execution.
- LOCAL_LINUX Android Gradle/Robolectric exact test: NOT_RUN; this environment has JDK 21 but no Android SDK/Gradle/full repository checkout.
- Prior exact code head `429f62ad4e0d1c8561f148a862267a1749f96d38`: the Android companion Gradle/unit-test job succeeded; the separate emulator process-restart job failed because System UI stopped responding and `com.android.phone` reported ANR. That is an emulator/environment failure, not evidence that the new SQLite test passes.
- New exact head `dc848768c6797b60c329d5d7485545b579d232f8`: Actions produced synthetic `startup_failure` run `45284177523` with zero jobs. GitHub refused to retry that run (`This workflow run cannot be retried`). The new Java test is therefore UNVERIFIED by CI.
- Redmi/Termux: REDMI_UNVERIFIED. No APK install, pairing, action, update request or device permission was performed.
- PR remains DRAFT / NOT_RELEASED.

## Next action

Obtain an executable exact-head `V14 Android companion` run for `dc848768` and confirm the new Robolectric test passes. Separately stabilize the emulator process-restart job without masking the System UI/phone ANR. Then obtain independent QA review of the receipt-only recovery implementation before any APK/device acceptance.


## 2026-11-24 Core follow-up — exact receipt readback

Code/test head: `0956cafae9fc1d36229e30e4593cb1267751454e`.

A further race/corruption edge was found in the shared provider recovery path: it ignored the conditional `finishClaimed` result and accepted any non-null readback receipt. It could therefore report recovery success and remove the approval notification even when a different finalizer had persisted different receipt bytes, or when a receipt appeared on a nonterminal `EXECUTING` row.

The Core branch now:
- treats a pre-existing receipt as complete only when the row is in `OUTCOME_UNKNOWN` or `USER_DENIED` and the receipt is non-empty;
- after finalization, requires readback of the exact expected terminal status **and exact receipt bytes** before returning success or removing the notification;
- adds Robolectric regressions for a competing finalizer that stores a different receipt and for a receipt attached to a nonterminal claim.

This is additive to the existing SQLite trigger failure/restart tests for both EXECUTING and DENYING rows. It still never repeats the external action.

Verification at this checkpoint:
- GitHub exact-head workflows: `V14 Core Android companion outcome`, `V14 Android companion`, and staged/integrated regression were queued/in progress after push; no new PASS claim yet.
- LOCAL_LINUX Android Gradle/Robolectric: NOT_RUN; no full checkout, Android SDK or Gradle installation is available in this runtime.
- Parent #2356 emulator process-restart/System-UI ANR remains a separate blocker; this follow-up does not clear it.
- REDMI_UNVERIFIED; no APK install, pairing, permission change, device action, model/weight change or user-data mutation.

Coordination: this changes `CompanionProvider.java`, also touched by #2379. A coordination comment was posted on #2379 asking that this exact-receipt guard be preserved during composition. Keep #2406 stacked on the current Core capability-registry branch until #2379/#2356 are independently reviewed; NOT_RELEASED.

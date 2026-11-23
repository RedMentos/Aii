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

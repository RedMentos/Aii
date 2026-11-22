# QA Android pairing durability — 2026-11-22

**Owner:** QA & Android  
**Parent:** Core Android companion branch `core/v14-android-companion-native-20261121`  
**State:** DRAFT / CI_PENDING / REDMI_UNVERIFIED

## Finding

The visible Termux pairing dialog wrote `paired_package` and `paired_cert_sha256` with asynchronous SharedPreferences `.apply()`, then immediately showed “Termux paired” without checking durable persistence. This was a trust-state durability/reporting gap; it did not bypass the caller certificate check or the separate per-action approval.

## Fix

- Added pure-Java `PairingPersistence`, which accepts only exact `com.termux`, a lowercase 64-hex SHA-256 signing-certificate fingerprint and a non-null writer.
- The writer must return true; false and runtime exceptions fail closed.
- MainActivity now uses synchronous checked `.commit()` and displays success only after a true commit. A failed write displays an explicit failure message.
- Tests cover successful and failed commit, exact values, invalid package, malformed/uppercase digest, missing writer and writer exception.

## Proof boundary

This does not add any permission or new capability. The companion still implements only consent-gated `launch_app`; screen/UI observation, Accessibility taps, shell, network, AudioRecord and learning authority remain OFF. The Android app is not installed on the Redmi and no real Android process/OS action was executed.

## Required follow-up

- Run the Android companion Gradle/Robolectric suite on the exact PR head.
- Rebase the signed audio consumer after the companion/provider contract is stable.
- Install and validate only after the parent Core stack is integrated and the user explicitly approves a bounded device test.


## QA follow-up — failed SharedPreferences commit and in-memory pairing

The pairing writer now requires a rollback callback. Android `SharedPreferences.Editor.commit()` can update its in-memory map before a disk write reports failure; merely returning false from the writer would therefore leave the newly supplied package/fingerprint visible to `CompanionProvider.isPairedCaller()` in the current process.

`MainActivity` snapshots the previous pair before the write. If the durable commit returns false or throws, the rollback callback restores/removes both previous keys with `apply()`, which updates the in-memory preference view synchronously before the failure toast. Tests cover a writer that mutates memory then returns false, a writer that mutates then throws, successful commit, invalid inputs, and rollback failure. No pairing is reported as successful on a failed commit.

This is a source/CI regression fix only. No Android device, companion APK or Redmi pairing was exercised; the PR remains stacked on the draft companion base.

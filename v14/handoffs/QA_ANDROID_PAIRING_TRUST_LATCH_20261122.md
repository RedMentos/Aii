# QA & Android — pairing trust latch after unverified rollback

Date: 2026-11-22  
Lane: Android companion caller identity / QA  
Base: receipt-recovery candidate 955cb4b3c37f2c054bd0fc4d6e26177e2d41a365

## Defect

The earlier pairing persistence regression checked that a failed SharedPreferences commit returned false and attempted rollback. It did not verify the provider's actual caller-identity gate when both the commit and rollback fail. Android may update SharedPreferences' in-memory map before a failed durable commit. If rollback also fails, a matching new package/certificate pair could remain visible to the provider in the current process even though the UI correctly reported failure.

## Change

- Serialize pairing writes/rollback and provider identity admission through one process-local trust lock.
- Revoke caller admission before changing the in-memory preference map.
- Restore trust only after a successful new durable commit or a rollback callback that verifies a durable restoration.
- Keep the latch false after unknown rollback state until a later successful durable pairing.
- Read the provider's persisted pair under the same lock used for the trust check, preventing stale pre-update snapshots from being admitted.
- Keep exact package, single-package UID, and signing-certificate checks unchanged. No capability or Android permission is added.

## Tests

- PairingPersistenceTest: success, false commit + verified restore, writer exception + verified restore, failed rollback, invalid input.
- CompanionProviderPairingTrustTest: exact identity accepted when trusted; multi-package UID rejected; failed commit + failed rollback rejected even when the in-memory pair exactly matches the caller; verified rollback restores only the prior identity.

## Proof boundary

This is a source-level companion trust fix. It does not establish Android SharedPreferences behavior on physical Redmi hardware, APK installation, Termux pairing, launch-app dispatch, screen/UI observation, Accessibility, background control, audio or learning. Companion remains default STOPPED and per-action local approval remains required. No device action, permission change, model/weight change or user-data mutation was performed.

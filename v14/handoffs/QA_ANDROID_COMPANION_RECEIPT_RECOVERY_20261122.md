# QA Android companion claimed-action receipt recovery

Date: 2026-11-22  
Owner: QA & Android  
Candidate branch: qa/v14-companion-receipt-only-recovery-20261122-run12  
Base: core/v14-android-companion-native-20261121 at 24e059d1f54e54d2285c9a542df207372fb27f4a

## Defect

A one-shot Android action is first durably claimed as EXECUTING or DENYING. The prior Activity finalizer removed the approval notification in finally, even if Android Keystore signing or the SQLite finish update failed. The action could then remain claimed without a receipt: outcome() returned NOT_READY, pending() could not show it, and the user could not retry finalization. Re-dispatch is unsafe because the launch may already have happened.

## Change

- Added an atomic finishClaimed update guarded by the original claimed state and receipt_json IS NULL; added a read-only query for claimed rows needing recovery.
- Added a shared receipt factory that revalidates action ID, package, canonical digest, capability and consent boundary before signing.
- Recovery is receipt-only and idempotent. EXECUTING becomes signed OUTCOME_UNKNOWN (approved locally, dispatch result not asserted); DENYING becomes signed USER_DENIED. It never invokes the launch intent.
- Provider startup, outcome(), pending() and reopening the consent Activity retry recovery. The notification is cancelled only after a durable receipt exists. Finalization and recovery share the action gate to prevent the normal result and conservative recovery racing each other.
- Python's pinned ECDSA verifier and source-bound ActionOutcome consumer accept COMPANION_OUTCOME_UNKNOWN as a non-observed, non-authoritative outcome. No T8/World learning authority is granted.

## Verification plan and boundaries

- Android Gradle/Robolectric tests cover execution and denial recovery, retry after injected Keystore failure, notification retention, process/database reopen, concurrency, request-scope rejection and exact receipt fields.
- Python 3.13/3.14 companion-outcome workflow covers signature verification and persistence of COMPANION_OUTCOME_UNKNOWN.
- No local Android SDK/Gradle or full Aii checkout is present in this run; exact GitHub CI is required. No APK install, Android permission, companion launch, Redmi action, Termux mutation, model/weight change or device deployment is claimed.
- The change does not enable UI observation, Accessibility, tap/type, shell, network or AudioRecord. Companion remains default-OFF; a signed receipt is not proof that the app reached foreground and never authorizes learning.

Status at authoring: candidate / CI not yet observed / NOT_RELEASED / REDMI_UNVERIFIED.

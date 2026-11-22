# Core & Harness — Android action intent/outcome journal

## Recovery extension — 2026-11-22

A claimed companion action can outlive the Activity that attempted to sign its receipt. The read-only `outcome` poll now reconciles stale `EXECUTING` rows to a signed `OUTCOME_UNKNOWN` receipt and stale `DENYING` rows to a signed `USER_DENIED` receipt. It never repeats the Android launch. Recovery is idempotent across restart, validates the stored action/request/digest binding, and leaves a failed signing or SQLite write retryable as `NOT_READY`.

- `OUTCOME_UNKNOWN` is mapped end-to-end to `COMPANION_DISPATCH_UNKNOWN` with `observed=false`, `t8_authoritative=false`, and `world_learning_eligible=false`.
- Java Robolectric regressions inject signing and SQLite finalization failures, then retry the same claimed row without redispatch.
- Python Runtime/Store regression authenticates and persists the new signed unknown receipt while preserving the non-authoritative boundary.
- Exact CI and Android hardware status must be recorded only after the new commit runs; no APK installation or Redmi action is claimed here.


**Date:** 2026-11-22  
**Owner:** Core & Harness  
**Branch:** `core/v14-android-action-journal-20261122`  
**Parent stack:** Core companion PR [#2271](https://github.com/RedMentos/Aii/pull/2271) → QA durability PR [#2342](https://github.com/RedMentos/Aii/pull/2342) → this PR  
**Base SHA:** `ab99ad94f25db2e5ce363045de4d175595bd2619`  
**Release base observed separately:** `gpt6/v13-private-remote-bridge-20261111` at `c4eb82deec915f65894c20d6ebbaf0ebf58fa335`

## Connected code

- `:android launch <package> --confirm` now persists a typed, source-bound `ActionIntent` packet from `C5_ANDROID_COMPANION` with the action ID, capability and explicit operator-plus-companion approval contract.
- `:android history [1..50]` reads the current chat session's intent/outcome packets and the durable broker state. It does not contact Android, expose package names or source text, or combine unrelated sessions.
- A signed companion receipt appears as `COMPANION_ATTESTED_NOT_DEVICE_VERIFIED`; history preserves `observed=false`, `t8_authoritative=false` and `world_learning_eligible=false`. The journal is an audit/continuity path, not a learning promotion or a claim that the app reached foreground.
- The Python regression workflow now runs on this stacked branch and base for CPython 3.13/3.14.

## Tests and evidence

- **LOCAL_LINUX_ISOLATED / CPython 3.13.5:** PASS — independent SQLite reproduction of session scoping, intent/outcome join, privacy projection, bounded limits and negative T8 authority.
- **Full local Aii checkout:** BLOCKED — no repository checkout is mounted and `git ls-remote` fails DNS resolution for github.com. No full local pytest or exact-source compile is claimed.
- **Exact GitHub CI:** pending for this branch; workflow runs the existing companion, broker, ECDSA, transport, outcome and new runtime tests on Python 3.13 and 3.14.
- **Android / Termux / Redmi:** REDMI_UNVERIFIED. No APK install, pairing, capability enablement, app launch, screen observation, tap/type or device receipt was performed.
- No model, weights, Age, permissions, updater settings or user data were changed.

## Acceptance boundary and next step

This adds a real source-scoped C5 action journal on top of the existing permission-gated companion candidate. It does not implement an Android UI observer, a verified foreground transition, T8 learning eligibility, B3 latent coupling or a release. Keep this PR stacked until QA #2342 and Core #2271 are reviewed and Boss rebases the companion stack onto the current release-development head. Any Redmi exercise requires the already separate explicit device-side approval and a fresh authenticated receipt; do not send a manual Termux command or update request from this PR.


## Exact-head verification — 2026-11-22 19:25 UTC

- Code-bearing SHA: `1eb512668074b1daa7da6e96e8e38aaec5931e1c`; parent chain remains #2271 → QA #2342 → Core #2344.
- The recovery implementation is receipt-only. `outcome(action_id)` calls `recoverClaimedAction` only for claimed `EXECUTING`/`DENYING` rows without a receipt. The recovery revalidates action ID, capability, package, request digest and signer key; it never calls the Android launch/dispatch function. `EXECUTING` becomes signed `OUTCOME_UNKNOWN`; `DENYING` becomes signed `USER_DENIED`. The shared action gate serializes recovery with the consent/dispatch transition. A failed signing or SQLite finalization leaves the claim retryable.
- Python maps `OUTCOME_UNKNOWN` to `COMPANION_DISPATCH_UNKNOWN` and preserves `observed=false`, `t8_authoritative=false`, `world_learning_eligible=false`.

### Exact CI evidence
All four observed workflow runs for this exact code-bearing SHA completed SUCCESS:
- #45027904692 — Android companion: Gradle `:app:assembleDebug` and `:app:testDebugUnitTest` BUILD SUCCESSFUL.
- #45027904705 — Core companion outcome adapter: CPython 3.13 and 3.14, 52 passed each.
- #45027904734 — Android outcome contract: 3 passed.
- #45027904702 — staged runtime 240 passed / 10 skipped; integrated regression 415 passed / 3 skipped plus its extra smoke check.

The Java unit-test source includes restart/idempotency for EXECUTING→OUTCOME_UNKNOWN, DENYING→USER_DENIED, signing failure with no redispatch, and injected SQLite receipt-write failure followed by retry. Gradle's exact-head `testDebugUnitTest` task completed successfully. Python outcome and staged/integrated workflows also completed successfully.

### Boundaries
- LOCAL_FULL_REPOSITORY remains BLOCKED by absent checkout/GitHub DNS; the isolated SQLite reproduction in the original handoff is not an exact-source full-suite test.
- Android Gradle build/unit tests are CI only. No APK installed, pairing enabled, app launched or Redmi receipt observed. REDMI_UNVERIFIED; NOT_RELEASED.
- Companion remains default-OFF. No device permission, app launch or remote action occurred.

### Next
Boss/QA may mark the code/CI portion of the EXECUTING/DENYING receipt-recovery prerequisite as implemented after independent review, but APK/device acceptance remains open. Keep the companion default-OFF and require a separate explicit device authorization for any real action.

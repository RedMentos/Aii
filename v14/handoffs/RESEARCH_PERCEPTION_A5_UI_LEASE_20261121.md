# Research/Perception handoff — A5 UI observation lease — 2026-11-21

## Exact source state

- Working branch: research-perception/v14-a5-ui-observation-lease-20261121-run11
- Exact branch HEAD: 508ac19622bfa64dc4bb94602585603716fc0cde
- PR: #2246, DRAFT, stacked on #2243 (branch research-perception/v14-dense-latent-kv-toy-20261121, base SHA 543349894b5392582969f06a4485ff9d18e4504d)
- Release: NOT_RELEASED. No force-push or merge performed.
- PR #2246 is mergeable after GitHub refresh, but remains draft because runtime.py is protected and requires independent Boss review. No PR-triggered workflow run is currently reported for this draft head; exact repository-level CI is therefore PENDING/NOT_RUN, not PASS.

## Implemented code

- v13/code/v13/a5_ui_admission_bridge.py
  - Strict v14.a5.ui-observation/1 metadata-only contract.
  - Requires Android ELAPSED_REALTIME, bounded event interval, explicit method/scope/API level, opaque receipt reference, capture session, source ID and PROVISIONAL/FINAL provenance.
  - Rejects raw screenshot/UI text/node tree/package/notification fields and any action/learning authority.
  - Adds a non-copyable, non-serializable, thread-bound UIObservationLease, with current-grant check, linearizable provider guard and persistent revocation subscription.
  - Persists only a content-free A5_UI_EVENT summary and PerceptPacket; calls existing A4 attention and source-bound admission. Provisional packets are stored but not admitted and do not request A4 re-look.
- v13/code/v13/runtime.py
  - Adds Runtime lease acquisition, ingestion, FINAL-only per-event context read and revocation entrypoints.
  - Revocation tombstones the UI source, deletes dependent packets, clears the process cache, unsubscribes and removes an unshared blob.
  - Runtime shutdown revokes outstanding UI observation sessions before Store close.
- v13/code/tests/test_a5_ui_observation_lease.py
  - Repository-level test uses the actual Runtime/Store/Attention classes and a synthetic OS provider.
- v14/V14_RESEARCH_LEDGER.md
  - Adds R-038: official Android AccessibilityService, MediaProjection and NotificationListenerService API constraints and the resulting A5 design.

## Tests and evidence

- LOCAL_LINUX / CPython 3.13.5: isolated bridge py_compile PASS.
- LOCAL_LINUX / CPython 3.13.5: isolated harness 14/14 PASS with a synthetic SQLite Store and fake A4/provider. Covered source/generation/receipt/thread binding, provisional exclusion, Android API scope rules, non-reentrant revocation race, packet/source/cache/blob cleanup, and raw-field/authority rejection.
- The isolated harness is not the full Aii repository test suite. The added repository-level unittest has not yet run locally because no complete checkout is mounted in this execution environment.
- CI: no exact-head PR workflow result is available while the PR remains draft. Do not promote CI to PASS.
- Redmi/Android: REDMI_UNVERIFIED. No connected authorized phone, OS capture provider, AccessibilityService, NotificationListenerService or MediaProjection session was exercised.

## Actual consumer effect and limits

The normal Runtime now exposes an A5 ingress API that persists a metadata-only PerceptPacket, drives the existing A4 scorer and returns bounded source-bound admission for an active turn. The process cache exposes FINAL packets only and revocation removes them.

This does not yet make the installed app observe or understand the screen. There is no authenticated OS-issued observe_ui provider, no screenshot decoding/visual model, and no automatic _turn queue hookup or B1/B2/C3 delivery. The Runtime API is the Perception-side seam for Core, not a completed Android feature. A5 UI remains SHADOW / WIRED_SYNTHETIC, not ANDROID_VERIFIED.

## Research and permissions

- Android AccessibilityService is restricted to genuine disability-assistance use; this contract rejects generic accessibility harvesting.
- MediaProjection is session-consented; Android 13/API 33 is full-display scope, while app-window sharing requires API 34. Redmi Android 13 must not be described as app-only projection.
- NotificationListenerService is notification-scoped and separately user-enabled.
- App intents/content providers are preferred when the target app provides them.
- No third-party OSS, model, weights, dependencies, user data, app permission, model selection or installed setting changed.

## Next executable ownership

1. Core: provide a trusted Android observe_ui receipt provider and call Runtime ingress from the active-turn path; hold the lease across all downstream source reads and C3 generation.
2. QA: adversarially test revocation through capture → admission → A4 → B1/B2/C3/cache, stale receipt/session, Runtime shutdown and provider failure.
3. Research/Perception: after Core's provider exists, add actual screen/UI feature packets and compare API-first event feeds against permitted visual capture; keep raw UI content out of logs and public artifacts.
4. Boss: review protected Runtime changes, update the shared board and V14_USER_NEXT_ACTION.md, and retarget #2246 to the integration branch after #2243 is accepted.

No user action is needed. Current installed Redmi SHA/updater status was not queried in this run; no update request or deployment was attempted.

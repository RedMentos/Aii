# Research/Perception handoff — A5 UI observation lease — 2026-11-21

## Exact source state

- Working branch: research-perception/v14-a5-ui-observation-lease-20261121-run11
- Runtime source: restored byte-for-byte to the base blob 30360f40eb784be5ea975ee85e94a57f0b154164; no pinned Runtime source edit remains.
- Latest A5 code checkpoint: 4456c00b72f4ae13b004265ec7b80c5211440982 (later ledger/handoff commits are documentation-only).
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
- v13/code/v13/a5_ui_admission_bridge.py
  - A5UIRuntimeAdapter wraps the existing Runtime object and uses its real Store and A4 controller without changing the pinned Runtime source.
  - Provides lease, ingest, FINAL-only context, revoke and explicit close operations. Core must instantiate it in the active-turn path and call adapter.close() before Store shutdown.
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

A5UIRuntimeAdapter consumes the existing Runtime object: it persists a metadata-only PerceptPacket, drives the existing A4 scorer and returns bounded source-bound admission for an active turn. Its process cache exposes FINAL packets only and adapter revocation removes the source and dependent data.

This does not yet make the installed app observe or understand the screen. There is no authenticated OS-issued observe_ui provider, no screenshot decoding/visual model, and no automatic _turn queue hookup or B1/B2/C3 delivery. Core must call the adapter from the active turn and close it before Store shutdown; this Perception adapter is not a completed Android feature. A5 UI remains SHADOW / WIRED_SYNTHETIC, not ANDROID_VERIFIED.

## Research and permissions

- Android AccessibilityService is restricted to genuine disability-assistance use; this contract rejects generic accessibility harvesting.
- MediaProjection is session-consented; Android 13/API 33 is full-display scope, while app-window sharing requires API 34. Redmi Android 13 must not be described as app-only projection.
- NotificationListenerService is notification-scoped and separately user-enabled.
- App intents/content providers are preferred when the target app provides them.
- No third-party OSS, model, weights, dependencies, user data, app permission, model selection or installed setting changed.

## Additional visual-teacher research (R-039)

MobileVLM V2 1.7B is a plausible on-demand A5 visual teacher, not a default or always-on model. The full main sections of arXiv:2402.03766v1 (2024-02-06 preprint) were reviewed. It uses CLIP ViT-L/14 at 336×336, MobileLLaMA-1.4B-Chat and LDPv2, reducing 576 visual tokens to 144. The paper reports 51.63 tok/s on Jetson Orin with a 4-bit LLM; this is not Android evidence.

The current llama.cpp MobileVLM guide (blob 6c17dbf902eafc6d262d6faa846ff5999fd6d8ab) documents an Android aarch64 build and a Snapdragon 778G V2 run: 20.61 s image encoding, 12.83 output tok/s, 44.41 s total for 377 tokens using release-2005b and F16 mmproj. The Redmi Note 10 Pro / Snapdragon 732G remains unmeasured and may be slower. A community Q4_K pair is about 961 MB on disk (792 MB LLM + 169 MB mmproj); this is not a RAM estimate.

License caution: code is Apache-2.0; model cards label V2 and MobileLLaMA Apache-2.0; CLIP is labeled MIT; the paper uses ShareGPT4V-PT, whose dataset card is CC-BY-NC-4.0. Do not treat the entire trained artifact as cleared for commercial redistribution without provenance review. No download, conversion, build or swap was attempted.

## Next executable ownership

1. Core: provide a trusted Android observe_ui receipt provider and call Runtime ingress from the active-turn path; hold the lease across all downstream source reads and C3 generation.
2. QA: adversarially test revocation through capture → admission → A4 → B1/B2/C3/cache, stale receipt/session, Runtime shutdown and provider failure.
3. Research/Perception: after Core's provider exists, add actual screen/UI feature packets and compare API-first event feeds against permitted visual capture; keep raw UI content out of logs and public artifacts.
4. Boss: review the adapter/contract, update the shared board and V14_USER_NEXT_ACTION.md, and retarget #2246 to the integration branch after #2243 is accepted.

No user action is needed. Current installed Redmi SHA/updater status was not queried in this run; no update request or deployment was attempted.

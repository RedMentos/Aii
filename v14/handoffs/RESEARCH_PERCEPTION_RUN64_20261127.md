# Research & Perception — Run 64 (2026-11-27)

## Product checkpoint

- New draft [PR #2557 — signed MediaProjection RAW-EYE receiver](https://github.com/RedMentos/Aii/pull/2557).
- Branch: `research-perception/v14-vision-ui-frame-ingress-20261127-run64`.
- Parent: Perception #2556 exact head `0367e5db3a4bd0e44c5192bc785823fc6f1f35f0`.
- Exact code/test head: `642b981e9a91bfc618992cabb0c72ac8c801b51c`.
- New file blobs read back exactly: module `96c8ee1ac71a56024f6f35200e2e35f4edd616db`; ingress tests `e08ee176587a0573de6ce662aa4a900bd5d2ffb4`; provider-entrypoint tests `fcf8337b36472ce19cbcaddfb9f2ad17dab55f52`; workflow `7af7bbd098ec9c6623f98055d1062ac6bf6e83dc`.

## Why this work

Core's Android MediaProjection provider PR #2408 calls `vision_ui_frame_ingress.consume_projected_frame_from_provider`, but that module is absent from its current tree. The provider therefore fails closed because the RAW-EYE consumer is not installed. This PR restores the missing Perception receiver rather than duplicating the provider or claiming that the new #2554 A5VisualFrameAdapter is already wired to Android.

The receiver verifies the one-shot provider capability, exact observation, live source/session/generation-bound UIObservationLease, frame digest and byte count; enforces 8 MiB / 4 MP bounds; decodes a private snapshot; computes RAW-EYE global + 4×4 tile features, A4 attention and bounded A5 context admission; excludes provisional frames from final C3 context; and zeroizes caller-owned frame bytes on success and failure. Optional installed tile projector is read-only LAB_SHADOW_ONLY with descriptor-relative no-follow checks. No screenshot, pixel, feature, transcript, model or weight is persisted or changed. Action, learning and truth authority remain false.

The earlier #2375 implementation was reviewed against current #2556 dependencies. Blob identity matches for `vision.py`, `a5_context_envelope.py`, `percept_admission.py`, `attention.py` and `a5_ui_admission_bridge.py`. Current `contracts.py` adds A4AttentionReceipt but leaves PerceptPacket validation unchanged.

## Tests

**GitHub Actions — exact head 642b981e9a91bfc618992cabb0c72ac8c801b51c**
- Workflow 45974814847, Python 3.13: `py_compile` PASS; **25 passed in 0.70s**.
- Workflow 45974814847, Python 3.14: `py_compile` PASS; **25 passed in 0.51s**.
- The tests use generated PNGs and synthetic provider/lease fixtures. They do not prove an Android capture or a real C3 turn.

**Shared staged/integrated**
- Workflow 45974814855 staged-runtime: **FAIL**, 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests.
- Failure log shows the existing stale Core Recovery audio-composer pin, Core arithmetic `v13/contracts.py` pin, Core observer `v13/cognition.py` pin, and QA migration assertions expecting UPDATED while the safe result is PARTIAL. These match the previously recorded #2553/#2554 shared failures; this PR did not edit those owners' files.
- Integrated regression was still IN_PROGRESS at the last poll; no pass is claimed.

**LOCAL_LINUX**
- Full local Aii checkout/pytest: **BLOCKED / NOT_RUN**. No checkout is mounted and `git ls-remote https://github.com/RedMentos/Aii.git` cannot resolve github.com. No local test pass is claimed.

## Research note

R-181 records XBridge (arXiv:2608.11676 v2, accepted NeurIPS 2026): discrete receiver-native lexical anchors plus receiver-conditioned cross-attention to sender hidden states outperform continuous-only bridging on its 7B/GPU benchmarks. The paper's 264M bridge and 7B base models are not Redmi candidates; code and bridge weights are Apache-2.0 but base-model terms remain separate. It motivates an anchor-swap/rare-entity ablation for V14 B3, not a direct dependency or a claim that current B3 is native.

## Integration / device boundary

- Core #2408 must rebase onto #2557 and wire `UIFrameGrant.consume()` into the normal Runtime turn/C3 context while the UIObservationLease remains live.
- QA owns independent OS consent, MediaProjection onStop, cancel/revoke, process death/restart and rollback acceptance.
- Fresh private owner-read issues #1014 HEALTH, #1015 PIPELINE_STATUS and #1016 DIAGNOSTICS returned no comments before expiry. Latest available V13OBS #115 is still historical (2026-11-24): auto-update enabled, but runtime STOPPED_BY_USER, model process STOPPED, autostart false. Current updater/runtime state remains unverified.
- **REDMI_UNVERIFIED / NOT_RELEASED / B3 OFF.** No device action, model download/swap, permission change, shell, UPDATE_REQUEST, CHAT_SEND or LOG_PAGE was performed.

## Next

Core rebase #2408 onto #2557 and implement the normal-turn Runtime/C3 consumer. QA validates Android consent and lifecycle. Keep the provider OFF until explicit device permission and a real Redmi receipt.


## Final verification addendum (2026-11-27)

- Final PR head at last readback: `cf8a0ea75712171d28b6ed9c10d3b189bb41393f`; code/test SHA remains `642b981e9a91bfc618992cabb0c72ac8c801b51c`.
- Focused workflow **45975248573 PASS**: py_compile and 25/25 tests on Python 3.13; py_compile and 25/25 on Python 3.14. Runtime deployment integrity **45975248638 PASS**.
- Shared staged workflow **45975248465 FAIL**: 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests. Integrated regression **45975248465 FAIL**: one failure on Core Recovery's stale audio-composer pin (expected `831080bceec90711bd42e0fa4eba47c669975c98`). Staged failures also show Core arithmetic/observer pins and QA PARTIAL-vs-UPDATED migration assertions. No Perception ingress test failed; no pin or assertion was weakened.
- Core #2408 and current #2555 have been notified to rebase/port the provider onto #2557 and wire the normal Runtime/C3 consumer. QA retains OS consent/onStop/cancel/restart/rollback.
- Static Android source review of #2408 matches official MediaProjection one-shot requirements (one consent token / one VirtualDisplay, registered onStop cleanup, mediaProjection foreground-service type); this is not an Android build or device test. Android 13 notification permission may be denied; companion has a visible notification-enable control, and QA should test the denial path.
- Fresh private read-only relay requests #1014–#1016 produced no comments before expiry. Latest V13OBS #115 remains historical 2026-11-24; runtime STOPPED_BY_USER, model STOPPED, autostart false. REDMI_UNVERIFIED / NOT_RELEASED.


## Verification wording correction

The initial checkpoint above records the state at the first poll. The final exact-head outcomes are in the final verification addendum below: focused ingress and runtime-deployment integrity PASS; shared staged and integrated regression FAIL on the pre-existing Core/QA pin chain.
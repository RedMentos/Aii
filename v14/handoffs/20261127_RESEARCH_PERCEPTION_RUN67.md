# Research & Perception — Run 67 handoff
Date: 2026-11-27
Repo: RedMentos/Aii
PR: https://github.com/RedMentos/Aii/pull/2559
Branch: research-perception/v14-a5-raw-eye-a4-structure-20261127-run67b
Exact code/test head: 0411d6fc539a2442e7f49886da87cc7fbbb25c73
Base: research-perception/v14-vision-ui-frame-ingress-20261127-run64 @ 95c6dd27e15de798cb4b69ddc1d1f5abda746386

## Delivered
- A5 provider-facing MediaProjection RAW-EYE now feeds the existing A4 structural-salience adapter.
- Reuses a5_visual_frame_bridge.raw_eye_structure and a4_visual_salience.apply_raw_eye_structure; no duplicate extractor or capture provider.
- Reconstructs 117-value descriptor from cached global 37-value row plus 16 existing 5-value tile summaries.
- Global segment carries visual modality, exact frame SHA, MediaProjection capture/session/receipt provenance and A5 producer identity.
- PerceptPacket carries the five bounded structure components and A4 signal.
- Authority remains ATTENTION_ONLY, learned=false, truth_authority=0, action_authority=false, learning_authority=false. Raw and derived packet remain ephemeral.

## Exact evidence
- Module blob: 14198bbd33b5394c787fe31b9fbce7778cbd11e0
- Test blob: 6f654d8b90500d0b089ae3154851ba6d22a440f4
- Focused workflow 46016491056 PASS:
  - Python 3.13: py_compile PASS; 29/29 focused tests PASS.
  - Python 3.14: py_compile PASS; 29/29 focused tests PASS.
- Initial head 7ae077f... had 28 pass / 1 fail because the test expected rounded A4 weights to sum within 1e-6; the existing helper rounds each of 18 weights to six decimals. Test tolerance corrected to 1e-5; exact head 0411d6f passed both jobs.
- LOCAL_LINUX scratch helper reproduction: 3/3 PASS (positive, uniform negative, invalid provenance). This is not the full repo suite.
- Full local Aii checkout/pytest BLOCKED / NOT_RUN (no checkout mounted; GitHub DNS unavailable).
- Shared staged/integrated workflow 46016490897 completed FAIL: integrated 1 Core audio-composer pin failure; staged 20 failed / 233 passed / 10 skipped / 2 errors / 41 subtests. Perception-focused workflow remains PASS; Core/QA own the blocking pins.
- REDMI_UNVERIFIED / NOT_RELEASED. No device, private relay, model, permission, updater, or data action.

## Research
- R-186: full WM-VS v2 paper review. Main lesson: progress claims require action-conditioned predicted future error and observed closed-loop retention, not just static visual structure. The current A4 cue remains attention-only.
- GlanceWAM full paper unavailable; only abstract and MIT-licensed repository README inspected. 1.3B video backbone / 21 GB bundle / A100-H200 evidence makes it unsuitable as a Redmi model candidate; checkpoint/data license not verified.

## Integration owners
- Core: rebase/port #2408/#2555 onto #2557 and include #2559 before the normal same-turn Runtime/C3 consumer; keep outer UIObservationLease alive through C3.
- QA: verify OS MediaProjection consent/denial, onStop, revoke, process death, restart and rollback on actual authorized Android.
- Perception: after integration, continue the next source-to-consumer gap (audio RAW EAR / timed acoustic packet or visual action-outcome progress) without duplicating capture providers.

## Board update requested for Boss/Integrator
- V14-006: append PR #2559, exact SHA, focused CI 29/29 on 3.13 and 3.14, shared staged workflow still pending at last poll, local full suite blocked, REDMI_UNVERIFIED / NOT_RELEASED.
- Keep V14-001 P0 and whole-canon coverage unchanged; this is one WIRED_SYNTHETIC path, not system acceptance.
- No user action required.

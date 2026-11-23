# Core & Harness — MediaProjection capability contract follow-up (2026-11-23)

## Checkpoint

- Branch: `core/v14-capability-registry-mediaprojection-20261123`
- Base: Core capability-registry PR #2394, exact base SHA `41b43cb139d68caf8c459cec668061b4eda6b6db`
- PR: #2406 (DRAFT / NOT_RELEASED)
- Exact head: `db46bec44cf52626b4aeea3caeeaee635008acce`
- Parent contract source: Android companion MediaProjection provider PR #2379, whose current Java registry advertises `screen_capture` as `READY_WITH_PER_SESSION_OS_CONSENT` / `MEDIA_PROJECTION_ONE_SHOT`.

## Defect and repair

The Core Python registry parser in #2394 accepted only the launch capability's per-action-ready status and required `screen_capture` to be OFF / provider NONE. That was incompatible with the native companion's one-shot MediaProjection registry. Once the provider was composed, parsing the full inventory would fail and would also block the existing launch path, because launch validates the whole registry before dispatch.

This branch:
- accepts the exact MediaProjection provider/status/consent/OS-permission/result-observed tuple;
- keeps the capability OFF when the companion stop switch is off or Termux is not paired;
- retains compatibility with the older companion's OFF_NOT_IMPLEMENTED / NONE snapshot;
- leaves tap, swipe, type_text, back, audio_capture and observe_ui fail-closed;
- keeps network, shell and model authority false;
- makes `require_ready("screen_capture")` a contract check only. It does not launch capture, invoke Android's OS consent UI, read a frame, or grant learning authority.

## Verification

- LOCAL_LINUX_ISOLATED, CPython 3.13.5: `py_compile` PASS and 6 focused parser-contract unit tests PASS against an isolated local copy of the implementation logic.
- Full Aii checkout: BLOCKED; no checkout is mounted and `git ls-remote` cannot resolve github.com from this runner.
- Exact GitHub Actions at head `db46bec`: Core companion outcome workflow PASS (run 45101897353); private bridge tests PASS (run 45101897302); staged/integrated regression run 45102050069 was IN_PROGRESS at this checkpoint.
- Android emulator / Redmi: NOT_RUN / REDMI_UNVERIFIED. No APK installation, screenshot, OS permission, model, weight, or user-data change.

## Integration dependencies and next step

- Stacked on #2394; do not merge this child without its parent.
- Reconcile with #2379's current QA/provider base and Perception's A5 lease/RAW EYE consumer. #2379 is still a draft with stale-base/import/workflow/lifecycle findings; this PR does not turn those into passing behavior.
- After exact staged/integrated CI finishes, request Core/QA review. A future capture path must retain the same UIObservationLease from provider frame read through C3 consumption and must cancel/zeroize on revocation.
- No user action is required for this repository checkpoint.

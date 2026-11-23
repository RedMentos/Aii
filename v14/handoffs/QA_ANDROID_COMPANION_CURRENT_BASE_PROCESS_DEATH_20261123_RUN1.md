# QA Android companion process-death current-base rebase — 2026-11-23

## Scope

Port only the reviewed Android companion lifecycle test infrastructure from QA PR #2427 onto the current companion QA base. No production companion behavior, manifest permission, pairing state, action execution, model, weight, Runtime, or user data changes.

## Base and source

- Exact base: `qa/v14-companion-final-qa-20261122` at `6dab323f1b59663682d0af65ffbd75c5de489578`.
- Source test candidate: QA PR #2427, code head `ae56dd1e54b3b78161f226d7735ed919879ea6cf`.
- Source PR #2427 exact Android 13 x86_64 emulator run: `45171482801` SUCCESS. It exercised visible MainActivity Stop/Enable view handlers, persisted OFF, process death, new process identity and provider restart. It explicitly used `View.performClick()`, not physical touch.
- The source PR was stacked on a divergent stop-durability branch; this port deliberately copies only test/workflow files onto the current QA base rather than merging that stack.

## Ported files

- Added `CompanionLifecycleInstrumentedTest.java` and the host-side `test_process_restart_instrumented.py` / `test_process_restart_instrumented_unit.py`.
- Added the AndroidX instrumentation runner/dependencies in `android-companion/app/build.gradle`.
- Updated the existing host UI test and UI-helper regression files from the reviewed source candidate.
- Updated `.github/workflows/v14-android-companion.yml` to compile/install the AndroidTest APK and run the instrumented lifecycle test on the current QA base branch.

The Android app's `MainActivity.java` and `CompanionProvider.java` were byte-identical between source PR #2427 and this base. No app implementation code was copied or modified.

## Safety and proof boundaries

The emulator test checks the actual visible Button and status TextView, calls the Button's registered listener through `View.performClick()`, and verifies the persisted OFF state after a new provider process starts. It does not claim physical touch, AccessibilityService, external input injection, background execution, Android Keystore hardware proof, or Redmi behavior.

The host driver only operates on the disposable GitHub Actions emulator. It does not pair Termux, submit an action, enable a user device, send chat, or alter phone data.

## Validation status on this current-base port

- Source PR #2427 exact-head emulator proof: ANDROID_EMULATOR PASS on its own older/divergent base.
- This current-base branch: CI PENDING until the new exact head completes.
- LOCAL_LINUX full Aii/Android SDK suite: NOT_RUN; this worker has no mounted Aii checkout, Android SDK, Gradle or adb.
- Physical Redmi: REDMI_UNVERIFIED.
- No device action, APK installation, pairing, permission change, model/weight change, or user-data mutation.

## Next

Run the exact-head Android helper/build, AndroidTest compilation and API-33 emulator process-death workflow. If green, ask Boss/Core to rebase the Python ActionIntent/receipt adapter #2450 onto this QA branch. If red, preserve the exact failure and fix the test harness without bypassing visible-state, PID, persisted-OFF or no-redispatch checks.


## Publication / CI access limitation

- Exact current branch head before this note: `25b3b905a9e37b013e2634aa94047df5cf3a796e`.
- The code and handoff are pushed and read back on the branch above.
- Creating a PR and posting a cross-lane comment were both rejected by GitHub with HTTP 403: the linked GitHub identity has no verified email address. No PR was created and no Boss/Core comment was posted.
- The available connector exposes PR-triggered workflow runs only; the current branch has no PR-triggered run record and combined status returned no statuses. Therefore **no exact-head CI result is verified for this current-base port**. Do not use the older #2427 run as current-base CI.
- Next administrative unblock: a verified email on the linked GitHub identity is required before this branch can be converted into a reviewable PR/comment handoff. The branch itself is preserved; no force-push was used.

# QA & Android handoff — Espresso process-death lifecycle

Date: 2026-11-23  
Owner: QA & Android  
Branch: `qa/v14-companion-instrumented-process-death-20261123-run4`  
Base: `qa/v14-companion-stop-durability-followup-20261123-run3` (initial base `3210892d420d234e5b96dbdb856a6966e89509da`)  
Status: DRAFT / NOT_RELEASED / CI_PENDING

## Defect reproduced

The previous host-side UIAutomator process-death harness repeatedly failed before reaching the user's Stop action. GitHub Actions run `45131391006`, job `137547472794`, built and installed the APK successfully, but Android's `System UI` entered an ANR. The host test could not observe the initial STOPPED screen and correctly refused to select Close app. Emulator logs also reported invalid ColorBuffer/texture state. Earlier attempts showed the same System-UI / WindowManager contention.

This is a real emulator-test failure, not proof of a companion product defect. The durable Stop fallback could not run because the test never reached a verified visible Stop tap.

## Change

The new acceptance path uses AndroidX Espresso against the real `MainActivity` view tree, while retaining the host as the independent process-death controller:

1. The host force-stops the companion and verifies the package PID is absent.
2. The first Android instrumentation method launches `MainActivity`, checks the visible STOPPED state, taps the actual Enable button, checks the visible ENABLED state and persisted `enabled=true`, then taps Stop and checks visible STOPPED plus persisted `enabled=false`.
3. The host issues `am force-stop` from outside the app and waits until the PID disappears.
4. A second instrumentation invocation starts a fresh target process. Provider startup must reset the process grant and persisted state to OFF; Espresso launches the real Activity and verifies the visible STOPPED state and `enabled=false`.

This removes repeated System-UI hierarchy dumps from the acceptance path. It does **not** claim external Accessibility/UiAutomator control or a Redmi result. The old UIAutomator helper remains in the repository as diagnostic history; its observed ANR stays FAIL/BLOCKED and is not relabelled as a pass.

## Files

- `android-companion/app/build.gradle`: AndroidX test runner, JUnit extension and Espresso dependencies.
- `android-companion/app/src/androidTest/java/com/redmentos/v14/companion/CompanionLifecycleInstrumentedTest.java`: actual visible enable/stop and fresh-provider-start assertions.
- `android-companion/scripts/test_process_restart_instrumented.py`: allowlisted instrumentation invocations, host force-stop, PID disappearance and restart orchestration. It rejects test failure, missing one-test success marker, unknown test method and incomplete instrumentation exit.
- `android-companion/scripts/test_process_restart_instrumented_unit.py`: seven host-driver tests.
- `.github/workflows/v14-android-companion.yml`: compiles AndroidTest APK, installs app + test APK, runs the instrumented lifecycle sequence, and triggers on this branch/base.

A CI trigger prerequisite was added to the parent QA branch `qa/v14-companion-stop-durability-followup-20261123-run3` at commit `7d6f73de2dd1ddc5ad1929bdfc4c71bcc2c1664e`, so PRs targeting that branch can trigger the Android workflow.

## Verification

### LOCAL_LINUX_ISOLATED

Environment: CPython 3.13.5 x86_64, scratch copy of exact GitHub-readback Python files (not a full Aii checkout).

- `python3 -m py_compile test_process_restart_instrumented.py test_process_restart_instrumented_unit.py`: PASS.
- `python3 -m unittest -v test_process_restart_instrumented_unit.py`: **7/7 PASS**.
- Covered exact allowlisted instrumentation command, success-marker parsing, failure/missing-marker rejection, method allowlist, PID polling, force-stop ordering, and fail-closed behavior when the PID does not disappear.

### Android / CI

- Exact PR-head Gradle/Robolectric, AndroidTest compilation, emulator instrumentation and process-death jobs: PENDING until the new branch's run completes.
- No Android SDK/emulator is installed in this local worker; no local APK or instrumentation execution is claimed.
- Redmi physical device: REDMI_UNVERIFIED. No APK install, pairing, permission change, companion action, chat send, update request, model/weight change or user-data mutation was performed.

## Acceptance boundary

A green GitHub emulator run would establish Android emulator + Espresso + external host process-death behavior only. It would not establish physical Redmi lifecycle, Android OS companion permissions, Accessibility/MediaProjection, background execution, action dispatch, or full V14 Android-control integration.

Latest known private owner-read before this candidate: installed release `aed1d2b826290c95c70356b5d8b864b5ef382be4`; last stored chat turn remained about 57.74 s total / 41.63 s TTFT / 38.95 s C3 prefill / 2 generated tokens, with B1/B2 TIME_BUDGET and zero valid offers in the recent aggregate. This was a stored diagnostic snapshot, not a new test performed by this run.

## Next action

Read the exact-head Android companion and emulator jobs. If the instrumentation run passes, request independent review and hand it to Boss/Core for the companion QA stack. If it fails, retain the failure and inspect the instrumentation output, provider startup, and PID timeline; do not skip the emulator gate or convert the prior UIAutomator ANR into success.

**User action: none.**


---

## Run 4 follow-up — emulator window-focus preflight (2026-11-23)

### Reproduced failure on the first Espresso head

- Exact head: \`a5fd31e3fc3bb858003ddd5ce1a851e3a0a3435d\`.
- Android Gradle / Robolectric / AndroidTest compilation passed, but both duplicate emulator attempts failed before the initial STOPPED assertion could complete.
- Exact Espresso failure: \`RootViewPicker$RootViewWithoutFocusException\` after 61.786 s. The Activity root existed, but WindowManager reported \`has-window-focus=false\`; no Enable/Stop tap occurred, so this was not a Stop or persistence acceptance result.
- The previous UIAutomator System-UI ANR remains a separate failed path and is not converted into a pass.

### Harness correction

- New exact head: \`d5711530b4381524b33934ce45fcbbb2f02b41c3\`.
- Before each Espresso invocation the host now wakes the disposable CI emulator, dismisses the keyguard, returns to Home, starts the explicit \`MainActivity\` component, and waits for both:
  - WindowManager \`mCurrentFocus\` / \`mFocusedApp\` to identify the companion package.
  - ActivityTaskManager \`mResumedActivity\` / \`topResumedActivity\` to identify the companion package.
- If focus is not established within the bounded wait, the harness fails with the exact focus/resume lines instead of starting Espresso against an unfocused root.
- Two new host regressions cover the wake/unlock/foreground sequence and the requirement for both focus and resumed activity. The allowlisted instrumentation methods, PID-exit handling, force-stop ordering and failure-marker checks remain intact.

### Exact current-head CI

- Python harness helper step: **23/23 existing UI helper tests PASS; 11/11 instrumentation-driver tests PASS**.
- Android Gradle/Robolectric + AndroidTest compilation: **PASS**.
- Offline bridge security: **PASS**.
- The two exact-head emulator process-restart jobs are still **IN_PROGRESS** at this readback; no emulator lifecycle PASS is claimed yet.
- Full local Aii checkout/Gradle/Android SDK is not available in this worker. These are GitHub CI results, not LOCAL_LINUX or physical-device tests.
- Redmi remains **REDMI_UNVERIFIED**. No APK install, pairing, permissions, companion action, chat send, update request, model/weight change or user-data mutation was performed.

### Next action

Read both exact-head emulator jobs. If they pass, hand the emulator-only lifecycle evidence to Boss/Core for independent review; if they fail, preserve the new focus/resume diagnostics and keep the visible UI gate blocked. Do not bypass Espresso focus, select Close app, or treat a durable-state partial result as visible UI acceptance.

**User action: none.**

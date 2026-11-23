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


---

## Fresh installed-runtime receipt — 2026-11-23

A separate authenticated private owner-read after the release update confirms:

- Installed release: \`4dc7595f383e7ba932ee8e9fcf52c5541210ed5e\`.
- Auto-update enabled; Runtime and Dashboard \`UP_TO_DATE\`; \`last_error=NONE\`.
- Service/model process reported RUNNING; 8 managed sessions.
- Last stored turn is unchanged and therefore is **not a post-update functional test**: FINAL, 57.739 s total, 41.627 s TTFT, 38.945 s C3 prefill, 751 prompt tokens, 2 generated tokens; no prompt layers removed and source text not rewritten.
- B1_DETAIL and B2_GIST remain TIME_BUDGET at 53.2 s / 54.2 s; C2 OK; C3 probe 3.1 s; native probe SMOKE_PARTIAL.
- Instant native-process map: 0 mapped native processes / 0 MiB PSS/RSS, with child readability UNKNOWN_NO_GROUP_CHILDREN. This is not free-RAM or sustained-residency evidence.
- Official Age 0; lab selector active/requested stage 10/effective implemented stage 5; physical feature execution remains unverified and learning commit authority still requires separate SHADOW mode.
- Console excerpt remains redacted; console_errors is USER_NOT_OPTED_IN. No LOG_PAGE, CHAT_SEND, model/weight/permission change or device mutation was performed.

A separate read-only HEALTH request is pending to refresh MemAvailable/free-disk metadata. This release receipt proves installation only. The companion Espresso PR still has no physical Redmi APK install, pairing or Android UI-control evidence; REDMI companion acceptance remains UNVERIFIED.


### Additional read-only resource / learning receipts

- HEALTH: MemAvailable 1,488 MiB of 5,569 MiB; free disk 993 MiB. HEALTH reports Runtime UNAVAILABLE while DIAGNOSTICS reports service/model RUNNING and Dashboard RUNNING; retain the conflict.
- LEARNING_STATUS: UNAVAILABLE. DIAGNOSTICS says learning commit authority requires separate SHADOW mode; no active persistent weight-learning state is verified.
- No LOG_PAGE or CHAT_SEND was issued. No permission, learning-mode, model or weight changes were made.


---

## Run 5 follow-up — launch/focus diagnostics and renderer correction (2026-11-23)

### Exact failure on code head d571153

Both duplicate emulator jobs completed **FAIL** before Espresso instrumentation started. APK installation and Gradle AndroidTest compilation succeeded. The host preflight then timed out with:

\`AssertionError: companion MainActivity did not obtain window focus; focus=[]; resumed=[]\`

The first attempt did not record the am-start output, package PID or raw package-related WindowManager/ActivityTaskManager lines, so it does **not** establish whether the Activity failed to launch, the process crashed, or the queried summary fields were absent. The emulator also emitted ColorBuffer/texture binding errors. No Enable/Stop tap or process-death acceptance occurred.

### New correction

- Code-bearing head: \`60e7e92d9d2544e32c75e5ef4b131a7cd705616f\`.
- The launch path now matches the previously used companion launcher: wake, dismiss keyguard, explicit \`am start -n\` (without \`-W\` or an unnecessary HOME key), wait 2 s, require a package PID, then require focus + resumed state.
- Focus inspection now uses the top-level \`dumpsys window\` summary (which carries \`mCurrentFocus\`) plus \`dumpsys activity activities\`. On failure it records bounded am-start output, PID, package-related lines and filtered emulator logcat.
- Added a negative unit test for am-start returning without creating the app process.
- The emulator renderer changed from \`lavapipe\` to headless \`swiftshader_indirect\` because the prior emulator logs reported invalid ColorBuffer/texture binding.

### New exact-head CI

- The new code-bearing head \`60e7e92d9d2544e32c75e5ef4b131a7cd705616f\` has a fresh push + PR CI matrix started; all five check runs were QUEUED/IN_PROGRESS at last readback.
- The previous \`d571153\` unit/compile/security results remain historical; they do not prove this new diagnostic path.
- Emulator lifecycle remains **BLOCKED / NOT ACCEPTED** until the new matrix finishes and the process-death test actually reaches Espresso and passes.

**Next action:** inspect exact-head helper tests, then both emulator runs. If focus still fails, use the captured am-start/PID/logcat evidence to decide between package launch failure, app crash, Android system focus failure or unsupported headless rendering; do not bypass the visible UI gate.


### Run 5 exact-head test readback

For code head \`60e7e92d9d2544e32c75e5ef4b131a7cd705616f\`:

- Existing process-restart UI helper tests: **23/23 PASS** on both duplicate CI executions.
- Instrumentation-driver tests: **12/12 PASS** on both duplicate CI executions, including process-not-created failure and the updated focus query.
- Android Gradle/Robolectric + AndroidTest compilation/install artifacts: **PASS**.
- Offline bridge security: **PASS**.
- Both emulator process-restart jobs remain **IN_PROGRESS**; no actual Espresso tap or lifecycle result is claimed until their logs complete.



---

## Run 4 follow-up — remove duplicate host Activity launch (2026-11-23)

### Exact emulator failure

- Code head `60e7e92d9d2544e32c75e5ef4b131a7cd705616f`, Android workflow run `45148385555`, emulator job `137603247340`.
- APK assembly, installation and AndroidTest compilation succeeded.
- The host launch/focus preflight completed, but Espresso then failed with `RootViewWithoutFocusException`: the Activity root existed while `has-window-focus=false`. No visible Enable/Stop tap or process-death acceptance occurred.
- This was an emulator harness failure, not a companion Stop/persistence failure.

### Source-level cause hypothesis and correction

The host launched `MainActivity` with `adb am start` before starting instrumentation. The Espresso method then launched the same Activity again through `ActivityScenario.launch`. That gave the test two competing Activity-launch owners and made the previously checked host window different from the root Espresso interacted with.

The new candidate removes the host-side `am start` entirely. The host only wakes/unlocks the emulator and verifies the target process is stopped. `ActivityScenario` is now the single owner of MainActivity launch. The AndroidTest adds a bounded in-process window-focus check on the exact ActivityScenario instance before any Espresso assertion or tap. The host still independently verifies PID creation, force-stop disappearance and fresh-process restart.

This is a falsifiable harness hypothesis, not yet a proven fix.

### Verification status

- Current exact-head emulator attempt: **FAIL** at Espresso focus before any Stop tap.
- New source/test patch: awaiting exact-head Python helper, Android Gradle/Robolectric, AndroidTest compile, emulator lifecycle and offline-bridge-security checks.
- No full local Android SDK/emulator is available; no local Android execution is claimed.
- Redmi physical device remains REDMI_UNVERIFIED. No APK install, pairing, permission change, companion action, chat send, update request, model/weight change or user-data mutation occurred.

**Next:** read back the exact new-head emulator result. If focus is still absent, inspect ActivityTaskManager/WindowManager state after the ActivityScenario launch rather than adding another external launch or bypassing Espresso.



### Exact-head update — 2026-11-23 09:56 UTC

- Current code/test head: `4da9781266d9a1947a97f7f8cf99854e04ab3a36`.
- Exact workflow run: `45151041687`.
- Completed Android helper/build job `137612193615`: **23/23 UI helper tests + 11/11 instrumentation-driver tests PASS**; Android Gradle/Robolectric unit tests and AndroidTest APK compilation both completed with `BUILD SUCCESSFUL`.
- LOCAL_LINUX_ISOLATED: a separate four-case harness for the changed host launch ownership and fail-closed checks passed **4/4**. No full Aii checkout was available.
- Emulator process-restart job `137612193066` remains IN_PROGRESS at this readback. No visible Stop, PID-death or restart PASS is claimed yet.
- The earlier `60e7e92` RootViewWithoutFocusException remains a recorded FAIL; the duplicate host Activity launch is removed on the current head, but the hypothesis is not accepted until the exact current-head emulator sequence completes.
- Physical Redmi remains REDMI_UNVERIFIED; no companion APK/device action occurred.

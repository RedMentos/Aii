# QA & Android — companion process-death acceptance

**Latest QA checkpoint — 2026-11-23 05:15 UTC**

- Branch head (harness): `4e70333ec7ca1c7d02566d127b6a924ed8b957a0`; app/test code head remains `0034b2c45b7c413e3a6610ff59c1ea928b93f5b1`.
- New workflow run `45116234588`: APK build and emulator setup completed; `android-companion-process-restart` is currently IN_PROGRESS. No process-death result yet.
- The immediately preceding run `45115319382` failed before APK installation: the emulator action executed each line of its multi-line `script` input in a separate `/usr/bin/sh -c`, so the loop ended with `Syntax error: end of file unexpected (expecting "done")`. This was a QA harness defect, not a companion or Android API failure.
- Corrective change: move the bounded readiness loop to `android-companion/scripts/wait_for_emulator.sh` and invoke it from the emulator action as one command line under Bash. It checks API 33, boot-complete and `pm path android`, with eight bounded attempts; on failure it emits device/logcat diagnostics and exits before `installDebug`.
- LOCAL_LINUX container checks: `bash -n` PASS; stubbed ready path PASS; stubbed non-ready path exits 1 after the bounded loop and emits diagnostics PASS. These are shell-harness tests only, not emulator proof.
- New exact-head Android Gradle/Robolectric job and outcome-adapter Python 3.13/3.14 jobs are PASS; staged-runtime and integrated-regression jobs were still running at last readback.
- Redmi remains REDMI_UNVERIFIED. No APK installation, pairing, device action, permission change, model/weight change or user-data mutation occurred. The emulator is a GitHub-hosted test device, not the Redmi.

**Next:** poll run `45116234588`. If the readiness gate passes but the process-restart UI still ANRs, retain the bounded System-UI failure and stop changing renderer/wait counts; if it passes, record the exact visible STOPPED-after-force-stop receipt. No user action is required.

---

Date: 2026-11-23  
Lane: QA & Android / V14-017, V14-019  
PR: #2356 (OPEN / NOT_RELEASED)  
Branch: `qa/v14-companion-final-qa-20261122`  
Base: `core/v14-android-companion-native-20261121`

## Acceptance contract

The host-side emulator harness must exercise the real companion APK and prove:

1. Initial process startup is STOPPED and persisted `enabled=false`.
2. The user-visible switch enables and stops the companion; persisted state follows each explicit action.
3. A force-stop actually removes the app PID.
4. Relaunch recreates the provider/activity with persisted OFF and no re-pairing, action submission or capability gain.

Robolectric process-start tests alone do not satisfy this process-death acceptance.

## Prior exact emulator failures — retained as FAIL/BLOCKED

- Exact QA head `43975b78659a02ce1ba9520ac5dfae10b2556d37`, process-restart run `45103190236`, job `137458477010`: the UI hierarchy showed Android's `System UI isn't responding` overlay, no usable app window, and an empty visible-label list. `pidof` still showed the companion process and `dumpsys activity` showed MainActivity top-resumed. Logcat included `ANR in com.android.phone` and WindowManager/system_server monitor contention. The harness never chose Close app. The STOPPED label was not observed; this is not a process-restart PASS.
- Prior exact head `43975b7`, run `45084178652`, showed the same System UI unresponsive overlay plus earlier ColorBuffer / texture / emulator-console errors. The app PID existed but no usable window/text was exposed.
- These logs do not establish that the companion's persisted OFF logic is wrong, but they also do not prove the requested visible stop/restart behavior. Do not relabel them as success or skip the emulator gate.

## Current QA harness adjustment

Code/test head: `0034b2c45b7c413e3a6610ff59c1ea928b93f5b1`.

The latest change is deliberately limited to reducing unnecessary emulator UI load:

- Removed the legacy `input keyevent 82` MENU event. `wm dismiss-keyguard` is sufficient; the MENU key is not part of this app's interaction and needlessly engages System UI.
- Changed UIAutomator capture to `uiautomator dump --compressed`, reducing hierarchy traversal.
- Added a bounded two-second first-frame settling interval after keyguard dismissal and activity launch, before the first hierarchy dump.
- Added unit tests asserting that launch sends no MENU key and that compressed hierarchy capture is used.
- Kept the strict maximum of two visible System-UI Wait actions. The harness still never selects Close app, guesses coordinates, or treats a missing UI as a pass.

No production permission, capability, pairing, model, weight, database or user data was changed by this harness update.

## Exact-head CI

On code/test head `0034b2c45b7c413e3a6610ff59c1ea928b93f5b1`, the following exact-head workflows were QUEUED at last readback:

- Android companion Gradle/Robolectric + emulator process restart: run `45113085672`.
- V13 staged context/integrated regression: run `45113085670`.
- V13 Android outcome contract: run `45113085759`.
- Core companion outcome adapter: run `45113085748`.
- Private bridge regression: run `45113083812`.

Queued is not PASS. Full local Aii checkout, Android SDK and adb execution are unavailable in this worker. No local emulator result is claimed.

## Device boundary

- Redmi physical device lifecycle remains `REDMI_UNVERIFIED`.
- No APK install, pairing, CHAT_SEND, UPDATE_REQUEST, shell action, permission change, stop/restart, model/weight change or user-data mutation was performed.
- The companion remains default STOPPED and launch_app-only with visible per-action approval. MediaProjection, Accessibility, tap/type, background execution, microphone and learning remain OFF/OPEN.

## Next action

Read exact-head CI for `0034b2c`. If the emulator still ANRs, preserve the failure and diagnose emulator/System-UI versus companion main-thread state from the bounded logcat and process/window evidence; do not increase the Wait budget again or weaken the process-death acceptance. If the emulator job passes, hand the exact evidence to Boss/Core for integration while retaining Redmi as unverified.

---

## QA run 11 — separate durable Stop evidence from System-UI ANR (2026-11-23 06:14 UTC)

### Exact prior emulator evidence

- Parent QA stack #2356 was read at head `b327c80861e640a9b2afb574698279ca4ed6307d`.
- Exact workflow run `45116548718`:
  - Android companion Gradle/Robolectric job `137500616062` failed during dependency resolution for Android Gradle Plugin transitive artifacts (including jose4j, slf4j, Gson and ASM). This is a dependency-fetch failure, not a demonstrated Java compile or test regression.
  - Emulator process-restart job `137500616248` built and installed the APK, then failed at the visible STOPPED-state wait after the safe System-UI Wait budget was exhausted. The harness refused Close app. The visible UI lifecycle remains FAIL/BLOCKED; this run did not establish the STOPPED label or process-death acceptance.
- The exact emulator log does not prove a Redmi result and does not justify another renderer or Wait-count experiment.

### QA-only follow-up branch

- Branch: `qa/v14-companion-stop-durability-20261123-run1`.
- Base: parent QA head `b327c80861e640a9b2afb574698279ca4ed6307d`.
- Current code/test head: `3c42a26694c3827eddcb574521535618777114f8`.
- The visible Stop button now writes an ephemeral host-side marker only after the companion's actual SharedPreferences `enabled=false` value is read back. A later UIAutomator/System-UI failure cannot create this marker by itself.
- If the visible STOPPED label is blocked after that verified Stop action, the harness separately:
  1. verifies the marker and OFF preference,
  2. force-stops the companion,
  3. observes the PID disappear,
  4. relaunches MainActivity,
  5. verifies the persisted preference remains OFF.
- It prints a clearly labelled `PARTIAL_PASS` for this independent durable-state proof, then re-raises the original UI assertion. The overall visible-UI lifecycle gate therefore remains failed; durable state is not relabelled as UI success.
- The post-restart path also reads the provider-startup OFF state before attempting the UI label.
- Added unit coverage for marker provenance, missing-marker rejection, force-stop/relaunch state verification, and preserving UI failure after a partial pass. Moved the unittest main guard to the end so all appended harness tests are discovered.
- Added the exact QA stack base and this branch to the Android workflow trigger filters. No production Android capability or permission changed.

### Verification boundary / next action

- New exact-head CI has not yet been observed on `3c42a266`; all changes remain unverified until the workflow result is read back.
- No full local Aii checkout, Gradle or Android SDK is available in this worker. No LOCAL_LINUX full-suite or local emulator PASS is claimed.
- Physical Redmi remains `REDMI_UNVERIFIED`. No phone install, pairing, CHAT_SEND, UPDATE_REQUEST, permission change, model/weight change or user-data mutation occurred.
- Next: open the stacked draft PR and inspect its exact-head Android unit/emulator plus staged/integrated checks. If the durable fallback passes while System UI remains unresponsive, report only the partial persistence proof and keep visible UI acceptance blocked. Do not increase wait counts or switch renderers again.

## Fresh Redmi owner-read — 2026-11-23 06:15 UTC

Read-only private receipts, no new chat turn or device action:

- Installed release `aed1d2b826290c95c70356b5d8b864b5ef382be4`; updater auto-enabled, Runtime/Dashboard UP_TO_DATE, last_error NONE.
- Runtime service/model process report RUNNING. HEALTH's Runtime field is UNAVAILABLE, so preserve the status disagreement.
- Last stored turn remains 57.74 s total / 41.63 s TTFT / 38.95 s C3 prefill / 2 tokens; B1/B2 remain TIME_BUDGET at 53.2/54.2 s; C3 probe 3.1 s.
- HEALTH: 1,371 MiB MemAvailable / 1,362 MiB disk free. Instant native-residency snapshot: 0 mapped processes, UNKNOWN_NO_GROUP_CHILDREN; not free-RAM or sustained residency proof.
- LEARNING_STATUS UNAVAILABLE. Official Age 0; lab stage request 10 / effective implemented stage 5; physical feature execution false.
- No CHAT_SEND, LOG_PAGE, UPDATE_REQUEST, shell, permission, model/weight or user-data mutation.

The Boss WorldJEPA cache candidate remains CI-green but not installed; this device receipt does not establish any improvement from that candidate. The Android companion lifecycle and MediaProjection paths remain REDMI_UNVERIFIED.

## CI trigger correction — 2026-11-23 06:34 UTC

- PR #2415's actual base is `qa/v14-companion-final-qa-20261122`, whose workflow did not include that branch in its own `pull_request.branches` filter. A filter change only in the head PR cannot trigger itself.
- Mis-targeted draft PR #2416 (based on Core's branch, whose workflow contains only Gradle/Robolectric and no process-restart emulator job) was closed after its Gradle/Robolectric-only run `45124508756` passed. That run is not evidence for the process-death test.
- Correct trigger prerequisite is ready-for-review PR #2417, based on the actual QA branch and adding the missing QA-base filter plus exact QA push branches. It has no exact workflow run yet because the base filter must first be integrated.
- #2415 remains DRAFT / CI_PENDING / NOT_RELEASED. Do not count its test additions as executed until the new exact-head run is visible.


## QA run 11 follow-up — exact branch readback and adb failure coverage (2026-11-23 07:35 UTC)

### Current QA branch

- Branch: `qa/v14-companion-stop-durability-20261123-run1`.
- Latest code/test head before this handoff append: `1ddd033e121a623b68182d2eeb48e58ce8db627e`.
- Commit `6884ab61b21056b842746e2d46eabf5c8083bc88`: the durable Stop fallback now runs after `AssertionError`, `subprocess.SubprocessError` (including adb timeout and nonzero exit), and `OSError` transport failures. It preserves and re-raises the original UI failure after the independent proof attempt.
- Commit `1ddd033e121a623b68182d2eeb48e58ce8db627e`: adds negative tests for four UI-observation failure classes: System-UI assertion/ANR, adb timeout, adb nonzero exit, and missing/failed transport.
- Exact GitHub source readback confirmed both modified files and their blob IDs. No local Python/Gradle/Android SDK execution was available, so these tests are **NOT_RUN locally**.

### Corrected workflow evidence

- PR #2417 exact run `45124910049` did execute the Android workflow: the Gradle/Robolectric job passed; the emulator process-restart job failed at the visible STOPPED wait after two safe System-UI Wait actions. This proves that the workflow trigger was active for that PR; it does not prove the durable fallback on #2415.
- PR #2356 exact run `45125561704`: emulator process-restart failed at the same System-UI wait; the companion unit job hit Maven Central HTTP 429 while resolving Robolectric.
- For #2415 head `1ddd033e121a623b68182d2eeb48e58ce8db627e`, the connector's PR-triggered workflow list is empty and combined commit status has no statuses. No exact-head CI result is observed. The base-branch workflow file at `b327c80861e640a9b2afb574698279ca4ed6307d` does contain the QA-base pull-request filter; therefore the earlier claim that the base branch definitely lacked that filter is not supported by this readback. The reason #2415 has no visible exact-head run is **UNRESOLVED**; do not invent a trigger cause.
- The process-restart gate remains FAIL/BLOCKED on the observed emulator runs. The durable OFF/process-death proof added in #2415 has not yet been exercised by an exact-head emulator run.

### Evidence boundary and next action

- #2415 remains DRAFT / NOT_RELEASED; no Android companion product behavior has been changed by these QA-harness commits.
- LOCAL_LINUX full Aii test suite: BLOCKED / NOT_RUN. Android emulator exact-head result: NOT_OBSERVED for #2415. Physical Redmi: REDMI_UNVERIFIED.
- Next: obtain a visible exact-head workflow result for #2415 head `1ddd033`; if the emulator again reports System UI ANR, retain the UI failure and read whether the independent durable marker/PID/SharedPreferences proof completed. Do not treat PARTIAL_PASS as full UI acceptance and do not increase Wait counts or select Close app.

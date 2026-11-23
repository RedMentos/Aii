# QA & Android — companion process-death acceptance

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

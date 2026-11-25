# Core & Harness — run 25 handoff — 2026-11-25

## Current code candidates

### Fair B1/B2 + native receiver

- Release base: `gpt6/v13-private-remote-bridge-20261111` @ `8d93236c753f0194224c19edc7411d8d7082b1d6`.
- #2478: `core/v14-fair-b1-b2-preanswer-budget-clean-20261124-run2` @ `55db58ae053c0e93430015a002ca620f8489bcc3`; 28 checks = 13 success / 14 failure / 1 skipped. Not green.
- #2485: `core/v14-fair-budget-guard-rebind-20261125-run1` @ `358b08934f3f36c37562dea02449fea649adb1a9`; 11/11 checks success. Exact source-pin rebind over #2478.
- #2488: `core/v14-native-probe-fair-budget-20261125-run1` @ `b8b43910a67a1b706be22e42f4e9cbcfa6de1fa6`; 17/17 checks success. Adds native receiver v3 and bounded four-pair matrix on the #2485 fair-budget chain.

### Android action/outcome

- #2481: `core/v14-android-action-journal-instrumented-restart-20261124-run1` @ `545ec845a35a4567aeaf7487d6765edf2229176f`, base #2450 head `523c04eb1e96d0e01e1cdda0c9832632360de044`.
- At last read: 16/17 checks success; one Android process-death emulator job still in progress. Companion-outcome: 64 tests on Python 3.13 and 64 on 3.14; staged/integrated and Android companion assemble/unit pass.
- New regression verifies signed receipt context reaches B1_DETAIL, B2_GIST and C3_LANGUAGE as CONTROL_ONLY on the immediately following event and expires afterward.

## What is actually verified

- #2488 pinned llama.cpp `b29c606` Linux x86_64 native build + `--selftest` + `--version`: PASS.
- #2488 Android arm64-v8a / API 26 cross-compile: PASS; artifact SHA256 manifest emitted.
- #2488 integrated regression: 424 passed, 3 skipped, 58 subtests passed; Python 3.13/3.14, staged runtime, owner-read and offline security checks pass.
- #2488 source-lineage path: ActionSelection collects the current event plus admitted Memory/observer and B1/B2 OfferPacket/QueryPacket provenance, including Context OS, Enlightened Space and body-view refs. Same-session, digest/readability, query/offer binding and Runtime restart tests are included.
- #2481 Python 3.13/3.14 companion-outcome matrices: 64 passed each; staged runtime/integrated regression and Android companion assemble/unit pass. Android process-death emulator check is still pending at this read.

## Explicit non-claims

- No local full Aii checkout or local full suite: NOT_RUN. `git ls-remote` failed with GitHub DNS resolution failure.
- No GGUF was loaded; no real native model input/output or learned latent utility was measured.
- No Android APK installed and no Redmi/Termux execution. Emulator/cross-compile is not Redmi proof.
- No model/weight/permission/user-data mutation; no update request; no private LOG_PAGE or remote shell.
- Production B3 remains OFF. #2481 receipt is CONTROL_ONLY, not observation, reward, T8 training signal or device-visible app confirmation.

## Next exact actions

1. Poll #2481 job `android-companion-process-restart` on head `545ec845`; if it fails, fix only the reproduced lifecycle/test issue and rerun exact-head CI.
2. Request independent QA/Boss review and rebase/compose #2481 onto the newest compatible companion integration base. Do not merge directly to release.
3. Request Boss review of #2485/#2488 and integrate only after the fair-budget/source-pin/consumer chain is accepted.
4. After integrated release and verified installation only, ask for separate explicit user approval before one local native probe. Keep B3 OFF until paired model utility, negative controls, retention and rollback pass.
5. Continue whole-Canon work: Redmi B1/B2 offer quality/latency, correct C3 output, native consumed-organ telemetry, learned B3 alignment, permanent safe weight learning, voice and Android action providers remain open.

**User action now:** none. Future local native probe requires separate explicit approval after integration and installation.


## #2481 emulator completion update — 2026-11-25

- Exact head `545ec845a35a4567aeaf7487d6765edf2229176f`: 17/17 check-runs SUCCESS.
- Android API-33 x86_64 GitHub-hosted emulator: PASS. Espresso confirmed visible Stop control; provider startup after process death remained OFF; PID/start changed `2176@493104 → 2621@560711`; first death boundary was Activity teardown.
- The instrumented test uses the actual button/listener through `View.performClick()` after visibility checks; it does not claim physical touch injection.
- This is not Redmi/Termux proof. No APK install on the user's phone, signer pairing, Accessibility, screen capture or device action.
- #2481 remains DRAFT / NOT_RELEASED and awaits independent QA/Boss review and safe rebase/compose onto the newest compatible companion base.

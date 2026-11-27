# QA & Android — whole-Canon checkpoint, 2026-11-23

## Exact source state

- Repository: `RedMentos/Aii`.
- Release-development branch: `gpt6/v13-private-remote-bridge-20261111`.
- Read-back base HEAD at start: `fb563d771fe2d493c4ec25abe94280981d24ef5c` (2026-11-23 12:46:30 UTC).
- The branch is not itself a release receipt. No master or historical Canon bytes were changed.

## P0 Redmi / real-chat evidence boundary

- Fresh authenticated private PIPELINE_STATUS #813 confirms the phone has runtime/dashboard `UP_TO_DATE`, auto-update enabled, `last_error=NONE`, and installed SHA `fb563d771fe2d493c4ec25abe94280981d24ef5c`, matching the current release-development base at the time of the read.
- This is installation evidence only. No duplicate UPDATE_REQUEST, manual Termux command or device mutation was used.
- Latest public-safe device evidence in #1904: last stored turn FINAL at 57.739 s total / 41.627 s TTFT / 38.945 s C3 prefill, 751 prompt tokens, 2 generated tokens; correctness UNKNOWN. B1/B2 remain TIME_BUDGET at 53.2/54.2 s and 0 valid offers in the latest five-turn aggregate. No new CHAT_SEND was performed.
- No current Android/Termux session, model residency, APK, microphone, UI capture/control, sustained PSS/RSS, 20-turn acceptance or new Redmi installation was tested. Keep `REDMI_UNVERIFIED` for current HEAD.

## QA implementation — M1 DATA test/ingestion regression

PR [#2444](https://github.com/RedMentos/Aii/pull/2444), branch `qa/v14-m1-data-ci-repair-20261123-run11`.

- Repaired double-escaped newline fixtures in `v14/m1/test_data.py` and `test_array_data.py`; malformed CSV tests now reach the intended timestamp/truncation checks.
- Corrected the strict-NaN affected-origin interval: with L=5, H=2, a missing row at 100 affects origins 98–104, not 96–97.
- Added `v14.m1.test_baselines` to the M1 workflow so persistence, seasonal persistence, train mean/median, Ridge-AR, LAD-AR and MAE tests actually execute.
- First repaired exact CI (head `8ab5c7182ca29aa028578b4b9f2b59a2b5f1aba7`): fixture/window and baseline cases passed; direct-array/reference fingerprint parity exposed the production hash separator bug.
- Root cause: `ArrayDataset.from_uci()` hashed literal backslash-n bytes, while `dataset_sha256()` hashed newline bytes. The direct-array record separator now matches the reference. The next run caught one final fixture expectation: a missing row at index 12 correctly filtered seven origins, so the first batch contained 9 rather than 16 windows.
- Final exact M1 head before this handoff sync: `98dc265a8e0dc7b29e3cb729407a0890e48e5467`. Exact GitHub CI: `synthetic-data-tests (3.13)` PASS (43 tests), `synthetic-data-tests (3.14)` PASS (43 tests), and `offline-bridge-security` PASS. This is synthetic CI, not a local full checkout or real UCI run.
- Full local Aii checkout/tests: `NOT_RUN/BLOCKED` (no mounted checkout). No real UCI cohort, preregistered test-year access, training or weight update. M1 remains experimental.

## Independent integration QA

Boss source-forget composition PR [#2443](https://github.com/RedMentos/Aii/pull/2443), exact inspected head `32f2ce6e9195da5fd781a6a4e9564ec0862f97ba`, is NOT ready for merge:

- `staged-runtime`: 19 failed, 234 passed, 10 skipped, 2 errors.
- Exact nested-builder pin expected `cbc62ff7c4489517744c8d76b8ee0b58008604a8bee861d2375690495ff71b64`, actual `088b31a752b1db21872634f35c9491e58da52e13b251c8f66bc02f405bbfe050`; integrated deploy also reports `Integrated stage builder changed`.
- `record_only_controller_guard_20261116.py` is rejected as changed.
- Optimizer-resume (3.13/3.14), staged Python 3.14, Lab-Age, consumer, verify and staged audio/arithmetic inherit the pin mismatch.
- Old-phone migration separately returns PARTIAL / UPDATE / runtime ERROR even though both source checkouts reach the target SHA. This is not a successful staged activation.
- QA comment was posted on #2443 with the exact failures and required bottom-up pin/migration retest. No gate was weakened.

## Whole-Canon acceptance still open

- A0–A5: source-bound audio/vision/UI paths have partial producer/SHADOW work, but real Android microphone, MediaProjection/Accessibility, revocation and end-to-end perception remain unverified.
- B1/B2/C4/C3: native useful offers and same-turn consumption are not proven; #1904 P0 remains open.
- B3: production activation-to-activation learned latent receiver remains OFF; symbolic/JSON and synthetic probes are not latent acceptance.
- World/Self/Memory/JEPA: source-bound SQLite/NumPy paths and rollback guards exist, but persistent native body-weight update, held-out utility, retention and true unlearning are not accepted.
- Voice, Android background/API control, tool agency, sleep/replay, self-edit and full Canon consumer coverage remain incomplete or gated.

## Next QA actions

1. Poll exact PR #2444 head CI; fix any remaining M1 failure and keep it DRAFT until all three test modules pass on Python 3.13/3.14.
2. Recheck Boss #2443 after pin-chain and migration repairs; do not merge a red exact head.
3. Poll private issue #813 for the current installed SHA. Do not send another update request or manual Termux command; do not infer installation from GitHub CI.
4. Continue the whole-Canon evidence map, prioritizing actual B1/B2→C4→C3 and native chat correctness/latency once a consented device receipt/test path is available.

User action: none at this checkpoint. No chat send, log-page request, shell, model/weight swap, permission change or device mutation was performed.


## Android companion Stop / process-death emulator evidence

- QA PR [#2427](https://github.com/RedMentos/Aii/pull/2427) exact head `ae56dd1e54b3b78161f226d7735ed919879ea6cf` has 5/5 associated checks SUCCESS: two Android companion build/unit runs, two Android 13 emulator process-restart runs, and offline bridge security.
- Emulator log: `PASS: Espresso visibly enabled/stopped the companion; target process identity changed across provider restart; persisted OFF survived`. Target process identity changed from `2415@653888` to `2925@736298`; first death boundary `activity-teardown`.
- The test exercises the actual MainActivity Button's registered handler with `View.performClick()`, verifies persisted OFF, force-stops the process externally, then starts a fresh provider process and confirms OFF remains. This is real Android emulator process-lifecycle evidence.
- It is **not** physical touch injection, Accessibility control or Redmi proof. No APK was installed on the user's phone.
- PR #2427 remains DRAFT / NOT_RELEASED: it is 55 commits ahead of an unmerged base branch `qa/v14-companion-stop-durability-followup-20261123-run3` at `7d6f73de2dd1ddc5ad1929bdfc4c71bcc2c1664e`; no open PR currently exposes that base. A clean current-release-base integration/rebase and independent review are required.


## Android companion integration dependency chain

- The current release-development branch `fb563d77` does **not** contain `android-companion/app/src/main/java/com/redmentos/v14/companion/MainActivity.java` or `android-companion/app/build.gradle`; those paths are NOT_FOUND on the release branch. The native companion is not yet part of the release candidate.
- Core dependency chain is still open/draft: #2119 (authenticated receipt verifier) → #2134 (atomic outcome persistence) → #2271 (native Android companion). #2271 exact head `24e059d1f54e54d2285c9a542df207372fb27f4a` has 17/17 associated checks SUCCESS but remains DRAFT.
- QA #2356 is open/ready for review on top of #2271. Its exact head `6dab323f1b59663682d0af65ffbd75c5de489578` has two Android job failures: the unit/build job hit Maven Central HTTP 429 for a Robolectric artifact; the emulator process-restart job hit Android System UI ANR/ColorBuffer errors and never observed STOPPED. Other checks pass.
- QA #2427 replaces the flaky System-UI/UiAutomator lifecycle dependency with AndroidX ActivityScenario and the actual MainActivity button handler. Exact head `ae56dd1e54b3b78161f226d7735ed919879ea6cf` passes all five checks and records a real emulator Stop → persisted OFF → external force-stop → new process → OFF/unpaired sequence.
- #2427's base branch `qa/v14-companion-stop-durability-followup-20261123-run3` at `7d6f73de2dd1ddc5ad1929bdfc4c71bcc2c1664e` is not represented by an open PR and diverges from #2356 head at merge base `b327c80861e640a9b2afb574698279ca4ed6307d` (19 commits ahead / 1 behind). #2427 itself is 55 commits ahead of that base. Do not merge this stack wholesale; after the Core/QA companion parent is integrated, transplant/rebase only the reviewed lifecycle delta onto the current release ancestor and rerun exact CI.
- Physical touch, AccessibilityService, real Redmi companion install/pairing, background API execution and user-device process-death remain unverified.

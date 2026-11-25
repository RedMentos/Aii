# Core & Harness — run 26 — 2026-11-25

## Persisted code candidate

- Repository: `RedMentos/Aii`
- Release/development base: `gpt6/v13-private-remote-bridge-20261111` @ `8d93236c753f0194224c19edc7411d8d7082b1d6`
- PR: [#2488](https://github.com/RedMentos/Aii/pull/2488)
- Branch: `core/v14-native-probe-fair-budget-20261125-run1`
- Exact head: `d2932cc7ae15a2b53087337efbd0dcdc0e2d092e`
- PR remains DRAFT / NOT_RELEASED. It is stacked on #2485 (which repairs exact source pins) and #2478 (the fair B1/B2 pre-answer path). Do not treat the red standalone #2478 parent as green.

## New executable consumer

`v13/code/v13/brain_panel.py` now exposes a read-only per-turn evidence path:

1. Reads persisted B1/B2 `body_offer_attempt` telemetry and `OfferPacket` metadata.
2. Correlates exact packet presence with C4's selected-offer IDs and C3's native-template receipt.
3. Compares each role's exact `LLAMA_SERVER_TOKENIZE` prompt count with pinned llama.cpp final `prompt_n + cache_n` accounting.
4. Reports native `predicted_n` against the runner's generated-token count, plus TTFT, duration and sampled peak PSS.
5. Keeps all raw prompt text, offer summaries, source refs and resource samples out of the panel. `semantic_use_proven=false` remains explicit: accounting and template inclusion do not prove attention or semantic use.

This is a real Runtime/SQLite/WebView diagnostic consumer, not a model-quality or learned-latent claim.

## Verification

- LOCAL_PYTHON isolated checks: native accounting 5/5 PASS; B1/B2 packet-to-C4/C3 delivery/privacy 1/1 PASS. These are isolated helper tests, not a full repository checkout.
- GitHub exact-head CI: 7 workflow runs / 13 jobs, all completed SUCCESS.
- New panel tests: 5 passed on Python 3.13 and 3.14; exact-source py_compile PASS; public privacy scan CLEAN.
- Native receiver Runtime/stage tests: 27 passed.
- Staged/integrated regression: 424 passed, 3 skipped, 58 subtests passed.
- Pinned llama.cpp `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`: Linux x86_64 CMake Release build, `--selftest`, `--version` PASS.
- Android arm64-v8a/API 26 cross-compile PASS. This is CI cross-compilation, not an APK install or phone test.
- LOCAL_LINUX full Aii suite: BLOCKED / NOT_RUN; `git ls-remote` failed because this environment cannot resolve github.com.
- Redmi/Termux: REDMI_UNVERIFIED. No fresh device receipt, no device action, no update request, no model/weight/permission/data mutation. Preserve prior AI STOPPED_BY_USER state.

## Related Core branch

- PR #2481 exact head `545ec845a35a4567aeaf7487d6765edf2229176f`: 17/17 check-runs SUCCESS; API-33 x86_64 emulator process-death/Stop persistence passed. Still DRAFT / NOT_RELEASED, QA/Boss review and safe rebase/compose required. Emulator is not Redmi proof.

## Next executable work

1. Boss/QA independently review and safely compose #2478 → #2485 → #2488 on the newest integration base; keep the fair B1/B2 path and C3 reserve.
2. Review/compose #2481 with QA's Android companion lifecycle harness; do not activate or install it on the user's phone.
3. After a reviewed integration and an authenticated installed-SHA receipt, obtain separate explicit approval before any local native model-pair probe. Keep production B3 OFF until semantic utility, negative controls, retention, restart and rollback are measured.
4. Continue the next whole-Canon consumer after integration: actual Redmi B1/B2 offer quality and native C3 correctness remain unverified.

## User action

NONE. No manual Termux command, restart, update request, model download/swap, permission change or device action is requested.

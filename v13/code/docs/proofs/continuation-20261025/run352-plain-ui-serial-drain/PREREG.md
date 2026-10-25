# Run352 preregistration — serial delivery for plain Termux notices (2026-10-25)

Parent: Run351 PR347 exact head `340b7a51a8e89e284c95e377b3c637b024eceb45`, itself on the Run350 review chain, not main. Independent review of Run351 exact-head GitHub Actions `40225789412` found 3/4 new UI tests passing, one genuine FIFO violation: `test_concurrent_new_notice_cannot_overtake_held_fifo_during_render` fails `AssertionError: 82 not less than 58`. The render thread removes the first queued notice and begins slow formatting, while a worker calls `notify` and prints the second notice first. The Run351 workflow is RED; this is not a completed Run351 gate.

Owner: only `v13/code/v13/ui.py`, this proof folder, and if necessary a new isolated test. Do not mutate Run351 branch, original tests, native/model/seed cohorts, frozen runtime, other owners, learning/age/approval gates or the Canon.

## Frozen change and acceptance
1. Make plain UI notices a single FIFO producer/consumer queue: worker callbacks enqueue, render thread alone prints. Render must skip notice delivery while the input buffer is nonempty, flush without a second notice once typing ends, and print each notice once in order even when formatting/printing is delayed. Keep prompt-toolkit behavior and persisted chat data unchanged.
2. Run the existing four `tests.test_ui_plain_notice_run351` tests and both `tests.test_chat_operator_persistence_run214` and `tests.test_phone_chat_sessions_run89` with exact-head GitHub Actions. Add a source-only counterexample if needed. Independently inspect raw logs and artifact integrity; privacy scan must be CLEAN.
3. Explicitly separate this UI-only synthetic/fake-operator test from native and Redmi evidence. Preserve all original negative gates, including STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA and jepa_weight=0. No V13 completion claim.

Observed unrelated baseline: exact-head focused workflow `40225789375` also failed in source-handoff candidate tests because the packaged runtime no longer matches either frozen baseline or fully reviewed candidate; preserve that failure for separate source-bound follow-up, never relax its guard as part of this UI patch.

Next command: GitHub Actions on the new Run352 PR against `codex/run351-plain-ui-notice-flush-20261025`, with exact-head source and privacy verification.
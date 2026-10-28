# Run86 prereg — Age0 emergency standstill + source-backed operator across restarts (2026-10-29)

Owner: GPT-6 scheduled continuation; review-only child of Run83 #990 exact `3545dab0faa3d548df58557ed8376a6162c51d9a` (GitHub Actions 40783355033 SUCCESS), itself child of Run82 #989 and independently checked Run76 #983. This preregistration must be committed **before** the test/workflow implementation. No changes to frozen/runtime source, model/seed/cohort, or original failed evidence.

## Frozen question and expected outcome
Does the **real** Linux Age0 Runtime + SQLite Store + Operator preserve a human source-backed answer preflight while `:stillstand` disables autonomous work, across process restart, and does releasing it preserve prior user-set stops?

1. Fresh temporary home, real Runtime/Operator, Sleep cycle disabled, no installed models. Add an explicitly human-recorded source fact via `store.event` + `memory.feedback`; `:verified` must report READY, correct source id, zero native calls, no fabricated answer.
2. Engage `:stillstand` via operator, assert persisted NOTAUS, queue pause, Age freeze and confirmed idle. Real ToolRegistry `calc` must refuse with HARD_BLOCK:NOTAUS; human-typed `:verified` may still provide a source preflight (not a generated answer). Model pool `get` is patched to raise on any native request.
3. Close and reopen the same home. `:stillstand json` remains on with all parts stopped, `:verified` retains same source id and zero native calls. Release via `:stillstand aus`; verify only the switches it set are released, then reopen and verify source survives, RECORD_ONLY and no silent promotion.
4. Separate fresh home: pre-engage human `:notaus` and `:age freeze on`; engage standstill, restart, release, and verify the pre-existing human stops remain while queue resumes.
5. Source-bound CI: exact test and frozen `standstill.py`/operator/Runtime hashes, focused suite, full suite, compile, privacy scan, diff check, raw logs and SHA256SUMS. Preserve RED evidence, do not change thresholds or tests after results without a new prereg/amendment.

## Evidence limits
Linux **software end-to-end**, real Store/Operator, no native model inference or phone measurements. This does **not** prove model output, JEPA utility, B3 receiver, Body-JEPA, STEP2, LP3, jepa_weight or complete V13. Keep Age0 RECORD_ONLY, all negative gates and no production main merge. A failure is a real diagnostic to preserve, not grounds for silently weakening checks.

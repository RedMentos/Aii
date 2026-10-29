# Run99 prereg — explicit offline source-answer --exact, deterministic F1/F5 answer (2026-10-29)

Owner GPT-6 scheduled continuation. Preregister FIRST on independently raw-verified GREEN Run94 #1001 exact `ba70be403b24898ec6d4a1aa7609acbbc4cebaa3` (Actions 40793294571, 25 focused/2660 full OK, ZIP SHA256 `da48441cbaa0aef22869842c6211e0c52b550d0d94b695e258e3b0e4f0d6a17e`). Import exact independently GREEN Run97 #1003 `scripts/source_exact.py` blob `ab67f77fb988f8a0e48fda390a52e94126e084da` (Actions 40793807136, 34 focused/2659 full OK, ZIP SHA256 `81928e413a87d1358e38a53fd53dd30daa80fedaf7f2e3310666e815b46131cb`). No main merge or frozen source changes.

## User-facing behavior

Existing `python -m v13 --home EXISTING_HOME source-answer QUESTION` remains model-free **READY preflight only**. Add **explicit `--exact`** for deterministic SOURCE_EXACT `FINAL` using Run97's unchanged double-checked F1/F5 source and exact answer `Project Elyra budget: 615 Euro.` when the current session has that human correction. Existing `--native` remains separately opt-in to pinned C3 and mutually exclusive with `--exact`; default no model, no answer. No changes to live `:verified`, Runtime._turn, Memory, Store, SourceConsumer or model catalog.

## Fixed checks

- Only edit `v13/__main__.py` to add mutually exclusive flags and delegate `--exact` to the imported unchanged `scripts.source_exact.query_exact(context,text,session)`. Keep existing-home check, exclusive Store lock, safe error output and existing preflight/native route.
- Test real persisted Age0 F1/F5 source, default READY no answer, explicit exact FINAL with exact SourceRef, wrong/out-of-scope/cross-session/revoked source abstention, --native/--exact conflict rejection, concurrent runtime lock refusal, missing home no initialization. No model called or downloaded in tests.
- Source exact imported with its original tests/docs/prereg; source hashes and new tests frozen in workflow before running. Focused/full suite, privacy/diff, closed raw hashes, original failures retained.

## Negative gates

SOURCE_EXACT is deterministic rendering, **not** native C3 quality, general semantic retrieval, learning, STEP2, B3, Body-JEPA, LP3, Redmi, Age promotion or whole-system completion. Age0 RECORD_ONLY, jepa_weight=0, no auto-approval/weight update.
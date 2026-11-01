# Phone learning integrity integrated — 2026-10-16

The original learning driver now sends all Phase-A and Phase-B rows to the existing strict `analyze_checked` gate. The numerical `analyze` function is AST-identical to its preserved prior version; fixed gain/retention gates remain 0.90 and 1.02. A partial set of actions previously accepted by the low-level analyzer now returns NOT_CONFIRMED before numerical analysis. Only a confirmed result returns zero.

Each completed original-driver call is appended to fsynced `rows.jsonl`. `rows.json` and the negative/partial report are written in `finally`, including a shutdown failure. Nonempty output directories are rejected so an old journal cannot be appended. The already journaled source-bound worker retains this behavior too.

Both original and source-bound workers copy the exact raw Phase-A Experience NPZ files before learning or held-out calls. A manifest binds byte hashes, per-world row counts (160 calc / 90 note for the 610-call plan), ordered forecast IDs and encoder/checkpoint binding. Snapshot files and manifest are checked after learn and after Phase B; the learner's recorded input hashes/counts must match. Phase-B calls may update the mutable runtime buffer, while the exact prelearn bytes remain available. No NPZ is reconstructed after the fact.

The phone driver now propagates live and learning failures, requires integrity and actual numerical analysis before success, and includes both fields in its report. The bounded wrapper allows the actual full verdict `LIVE_PATH_CONFIRMED+CONTINUAL_LEARNING_CONFIRMED`; the previously allowed fake short suffix `+CONFIRMED` is rejected.

## Verification and limits

`PYTHONPATH=.:tests python -m unittest tests.test_phone_learning_integrity_integration tests.test_tool_forecast_bound_learning_candidate tests.test_tool_forecast_bounded_phone_candidate tests.test_tool_forecast_learning_integrity_candidate -v`

48 tests passed, zero failures/errors/skips. Twelve new integration tests cover partial false-PASS rejection through the original driver, interrupted Phase A, shutdown failure, old-journal preservation, complete 610-row positive and numerical-negative controls, exact prelearn snapshots surviving changed Phase-B buffer bytes, changed learn-input hash rejection, source-bound worker snapshot ordering, phone exit propagation and actual/fake wrapper suffixes. Focused log is preserved here.

Orchestration controls use explicit test-only Runtime/learner/runner stubs and synthetic scored rows; they do not establish native utility. A separate test uses actual Runtime, ToolStep, approval transactions, checkpoint prediction/scoring, SQLite state and Experience persistence, with only the tap provider replaced by deterministic FakeTaps: seven actual calc/note software tool calls are SCORED/EXECUTED and a 4+3 input snapshot is closed. Its learning result remains negative because no native retention installation is supplied. No model job or device measurement was run by this package; no gate was promoted.

The four sources in `before/` match the first native-v2 preregistration hashes exactly (see `source-comparison.json`). Those original sources and the incomplete first-50-row/parity evidence remain historical; changing current drivers does not complete or resume that cohort. The coordinator must issue a fresh source binding before any new native inference.

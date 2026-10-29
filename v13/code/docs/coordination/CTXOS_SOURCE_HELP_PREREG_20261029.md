# Context OS exact-source operator discoverability prereg — 2026-10-29

- Parent: exact-head software GREEN PR #1111 `e0f247a159c5acfcc5104f1f5c1154e6a494a53c` (focused 48/48; full 3195, 11 skipped). Review-only child, no production merge.
- User-facing gap: `ContextOS.operator_command` supports read-only `:ctxos source <Event-ID>` but the main `:help` command omits it, so exact-source audit is undiscoverable through the operator's own help.
- RED-first regression: `:help` must list exact `:ctxos source <Event-ID>` and explain read-only current-chat scope; a real Store event must still roundtrip exact Unicode via `:ctxos source`, with `SOURCE_EXACT_READ_ONLY`, `context_applied=false`, and unchanged Context OS SHADOW mode.
- Fix ownership only `v13/code/v13/operator.py` HELP text; new `tests/test_ctxos_source_help_20261029.py`, prereg/handoff and dedicated source-only workflow. No ContextOS implementation, native runner, age, memory or training changes. Preserve donor source SHA `acb86c61d59e422a8395f3144d297eca7934b33a`.
- Evidence: test-only RED then exact-head focused/full software CI, raw SHA256SUMS, privacy/diff checks. No STEP2/B3/Body-JEPA/LP3/jepa_weight promotion; Age0 RECORD_ONLY, V13 incomplete.

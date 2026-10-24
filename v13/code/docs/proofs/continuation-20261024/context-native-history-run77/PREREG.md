# Run77 prereg — Context OS real SQLite/native_history reentry integration

2026-10-24. Base Run76 PR109 `2fc8e539ef628416e33d6047ba1871d6b88f72e4`. Owner only `v13/code/tests/test_context_append_provenance_run74.py` and new `v13/code/docs/proofs/continuation-20261024/context-native-history-run77/**`. Do not touch other production or CI files unless a real RED demonstrates a narrow defect.

Goal: independently test Run76 bindings using actual Runtime Store SQLite rows and the canonical `native_history` filter, rather than only a FakeStore. Before executing, register four cases: valid SourceRef -> ACTIVE append, persisted ContextOS state/restart -> append, deleted older source -> history omission and rebuild, and mutated older message source metadata -> history omission and rebuild. Assert that invalid sources never enter the planned prompt. No model inference, no artificial authority or gate promotion.

Use existing read-only GitHub-hosted Linux CI and official public privacy scan. Preserve full raw CI logs, original failures, exact commit IDs, software-vs-native/Redmi separation. If tests fail for fixture reasons, fix tests without weakening the safety condition. Retain STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0, full V13 INCOMPLETE.

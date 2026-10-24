# Run45 preregistration — Sleep TTT source lineage through the exact V13 native_history implementation

Parent Run44 `6f029f88726edd21edd53fd369747e10ac644228`. Ownership exclusively `v13/code/docs/proofs/continuation-20261024/sleep-real-history-run45/`. No edits to frozen production, Run42–44, Body/JEF or original gates.

Use exact, byte-verified source of `v13/code/v13/history.py` Git blob `05455f297205b40fe8e0f818c4657f1fedcd9fa3` and Run42 staging blob `8dcd4b36cbe58f06ea330a510f1735b37f0ad600`, with a small deterministic fake Store implementing the real history interface (including source refs, context_source_refs, fixed-answer approvals, read_source and source deletion). Unlike Run42 tests, do NOT mock the history validation function.

Predeclared cases: valid two-turn source chain stages one; deleted input source of target excludes target; deleted input source of earlier context excludes target; deleted transitive context_source_ref excludes target; fixed-answer query/answer rule removal excludes; malformed metadata and missing lineage exclude; history window truncation fail-closed; revoked source re-export empties stale file; unchanged output deterministic. Compare against legacy unguarded stage_ttt to show risk only if reproducible with the fixture. No model weights or source writes. Real `Store`/Runtime, Linux-native model and Redmi remain NOT RUN.

Pass condition: all tests pass using **unmodified** exact native_history source and Run42 candidate. No promotion of STEP2 UTILITY_FAIL, B3 L1 FAIL, Body-JEPA UNAVAILABLE, jepa_weight=0 or full V13 INCOMPLETE.
